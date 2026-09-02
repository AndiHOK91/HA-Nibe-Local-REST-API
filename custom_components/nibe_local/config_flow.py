"""Config and options flow for NIBE Local REST API."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import NibeApiError, NibeAuthError, NibeLocalApi, async_resolve_host_ip
from .const import (
    COMMAND_POLL_DELAY_OPTIONS_MS,
    CONF_AUTH_HEADER,
    CONF_COMMAND_POLL_DELAY_MS,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_COMMAND_POLL_DELAY_MS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_CREDENTIAL_KEYS = (CONF_USERNAME, CONF_PASSWORD, CONF_AUTH_HEADER)


def _secret_selector(*, autocomplete: str | None = None) -> TextSelector:
    """Create a masked text selector for credentials."""
    config = TextSelectorConfig(type=TextSelectorType.PASSWORD)
    if autocomplete is not None:
        config["autocomplete"] = autocomplete
    return TextSelector(config)


def _secret_is_blank(value: object) -> bool:
    """Return whether a secret field was effectively left empty."""
    return value is None or (isinstance(value, str) and not value.strip())


def merge_keep_credentials(candidate: dict, current: dict) -> dict:
    """Keep stored sensitive credentials when their masked fields are left empty."""
    merged = dict(candidate)
    if _secret_is_blank(merged.get(CONF_PASSWORD)):
        merged[CONF_PASSWORD] = current.get(CONF_PASSWORD, "")
    if _secret_is_blank(merged.get(CONF_AUTH_HEADER)):
        merged[CONF_AUTH_HEADER] = current.get(CONF_AUTH_HEADER, "")
    return merged


def _connection_schema(
    defaults: dict,
    *,
    password_default: str = "",
    auth_header_default: str = "",
) -> vol.Schema:
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
            vol.Optional(
                CONF_PASSWORD, default=password_default
            ): _secret_selector(autocomplete="current-password"),
            vol.Optional(
                CONF_AUTH_HEADER, default=auth_header_default
            ): _secret_selector(),
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


def _reauth_schema(current: dict) -> vol.Schema:
    """Build the credential-only reauthentication schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_USERNAME, default=current.get(CONF_USERNAME, "")
            ): str,
            vol.Optional(CONF_PASSWORD, default=""): _secret_selector(
                autocomplete="current-password"
            ),
            vol.Optional(CONF_AUTH_HEADER, default=""): _secret_selector(),
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
    return await api.get_device()


class NibeLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

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
                title = product.get("name") or "NIBE API"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema({}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict):
        """Start reauthentication after Home Assistant reports invalid credentials."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_entry_missing")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Validate and save replacement credentials."""
        errors: dict[str, str] = {}
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_entry_missing")

        current = {**self._reauth_entry.data, **self._reauth_entry.options}

        if user_input is not None:
            credentials = merge_keep_credentials(dict(user_input), current)
            candidate = {**current, **credentials}

            try:
                await _validate(self.hass, candidate)
            except NibeAuthError:
                errors["base"] = "invalid_auth"
            except NibeApiError:
                errors["base"] = "cannot_connect"
            else:
                new_data = dict(self._reauth_entry.data)
                new_options = dict(self._reauth_entry.options)

                for key in _CREDENTIAL_KEYS:
                    new_data[key] = candidate.get(key, "")
                    new_options.pop(key, None)

                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data=new_data,
                    options=new_options,
                )
                return self.async_abort(reason="reauth_successful")

        host = str(current.get(CONF_HOST, ""))
        ip_address = await async_resolve_host_ip(host) if host else None
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_reauth_schema(current),
            errors=errors,
            description_placeholders={
                "device_name": self._reauth_entry.title or "NIBE Local REST API",
                "host": host or "–",
                "ip_address": ip_address or "–",
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return NibeLocalOptionsFlow()


class NibeLocalOptionsFlow(config_entries.OptionsFlow):
    """Edit connection and polling settings after setup."""

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            candidate = merge_keep_credentials(dict(user_input), current)

            try:
                await _validate(self.hass, candidate)
            except NibeAuthError:
                errors["base"] = "invalid_auth"
            except NibeApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=candidate)

        return self.async_show_form(
            step_id="init",
            data_schema=_connection_schema(
                current,
                password_default="",
                auth_header_default="",
            ),
            errors=errors,
        )
