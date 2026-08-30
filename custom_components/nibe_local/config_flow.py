"""Config and options flow for NIBE Local REST."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NibeApiError, NibeAuthError, NibeLocalApi
from .const import (
    CONF_AUTH_HEADER,
    CONF_COMMAND_POLL_DELAY_MS,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_COMMAND_POLL_DELAY_MS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    COMMAND_POLL_DELAY_OPTIONS_MS,
    MIN_SCAN_INTERVAL,
)


def _connection_schema(defaults: dict, *, password_default: str = "") -> vol.Schema:
    """Build the connection/settings schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                int, vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, "0")
            ): str,
            vol.Optional(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
            ): str,
            vol.Optional(CONF_PASSWORD, default=password_default): str,
            vol.Optional(
                CONF_AUTH_HEADER, default=defaults.get(CONF_AUTH_HEADER, "")
            ): str,
            vol.Required(
                CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, False)
            ): bool,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL, max=600)),
            vol.Required(
                CONF_COMMAND_POLL_DELAY_MS,
                default=defaults.get(
                    CONF_COMMAND_POLL_DELAY_MS, DEFAULT_COMMAND_POLL_DELAY_MS
                ),
            ): vol.In(COMMAND_POLL_DELAY_OPTIONS_MS),
        }
    )


async def _validate(hass, values: dict) -> dict:
    """Validate connection settings and return device metadata."""
    api = NibeLocalApi(
        async_get_clientsession(hass),
        host=values[CONF_HOST],
        port=values[CONF_PORT],
        device_id=values[CONF_DEVICE_ID],
        username=values.get(CONF_USERNAME),
        password=values.get(CONF_PASSWORD),
        auth_header=values.get(CONF_AUTH_HEADER),
        verify_ssl=values[CONF_VERIFY_SSL],
    )
    device = await api.get_device()
    await api.get_points()
    return device


class NibeLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                device = await _validate(self.hass, user_input)
            except NibeAuthError:
                errors["base"] = "invalid_auth"
            except NibeApiError:
                errors["base"] = "cannot_connect"
            else:
                product = device.get("product") or {}
                serial = product.get("serialNumber") or (
                    f"{user_input[CONF_HOST]}:{user_input[CONF_DEVICE_ID]}"
                )
                await self.async_set_unique_id(str(serial))
                self._abort_if_unique_id_configured()
                title = product.get("name") or f"NIBE {user_input[CONF_HOST]}"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema({}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        # Home Assistant injects the ConfigEntry into OptionsFlow and exposes it
        # as self.config_entry. Since HA 2025.12 it must no longer be passed to
        # or assigned by the custom flow itself.
        return NibeLocalOptionsFlow()


class NibeLocalOptionsFlow(config_entries.OptionsFlow):
    """Edit connection and polling settings after setup."""

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}

        # Current effective values = original setup data overridden by options.
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            candidate = dict(user_input)

            # Leaving the password field empty means "keep current password".
            if not candidate.get(CONF_PASSWORD):
                candidate[CONF_PASSWORD] = current.get(CONF_PASSWORD, "")

            try:
                await _validate(self.hass, candidate)
            except NibeAuthError:
                errors["base"] = "invalid_auth"
            except NibeApiError:
                errors["base"] = "cannot_connect"
            else:
                # Options contain the complete effective configuration so setup
                # can simply overlay them on top of the original entry data.
                return self.async_create_entry(title="", data=candidate)

        # Never pre-fill/show the stored password in the UI.
        return self.async_show_form(
            step_id="init",
            data_schema=_connection_schema(current, password_default=""),
            errors=errors,
            description_placeholders={
                "password_hint": "Passwort leer lassen, um das vorhandene Passwort beizubehalten."
            },
        )
