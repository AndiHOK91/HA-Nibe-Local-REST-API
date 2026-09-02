"""Config and options flow for NIBE Local REST API."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import NibeApiError, NibeAuthError, NibeLocalApi, async_resolve_host_ip
from .const import (
    AUTH_METHOD_BASIC,
    AUTH_METHOD_HEADER,
    COMMAND_POLL_DELAY_OPTIONS_MS,
    CONF_AUTH_HEADER,
    CONF_AUTH_METHOD,
    CONF_COMMAND_POLL_DELAY_MS,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_COMMAND_POLL_DELAY_MS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    NIBE_DEVICE_ID,
)

_AUTH_KEYS = (CONF_AUTH_METHOD, CONF_USERNAME, CONF_PASSWORD, CONF_AUTH_HEADER)
_AUTH_METHODS = (AUTH_METHOD_BASIC, AUTH_METHOD_HEADER)


def _secret_selector(*, autocomplete: str | None = None) -> TextSelector:
    """Create a masked text selector for credentials."""
    config = TextSelectorConfig(type=TextSelectorType.PASSWORD)
    if autocomplete is not None:
        config["autocomplete"] = autocomplete
    return TextSelector(config)


def _secret_is_blank(value: object) -> bool:
    """Return whether a secret field was effectively left empty."""
    return value is None or (isinstance(value, str) and not value.strip())


def auth_method_from_values(values: dict) -> str:
    """Return the configured auth method, inferring it for pre-0.8 entries."""
    configured = values.get(CONF_AUTH_METHOD)
    if configured in _AUTH_METHODS:
        return configured
    if not _secret_is_blank(values.get(CONF_AUTH_HEADER)):
        return AUTH_METHOD_HEADER
    return AUTH_METHOD_BASIC


def merge_auth_settings(candidate: dict, current: dict) -> dict:
    """Merge auth settings while keeping exactly one authentication method active."""
    merged = {**current, **candidate}
    method = candidate.get(CONF_AUTH_METHOD)
    if method not in _AUTH_METHODS:
        method = auth_method_from_values(current)
    merged[CONF_AUTH_METHOD] = method
    current_method = auth_method_from_values(current)
    method_unchanged = method == current_method

    if method == AUTH_METHOD_BASIC:
        if _secret_is_blank(candidate.get(CONF_PASSWORD)):
            merged[CONF_PASSWORD] = (
                current.get(CONF_PASSWORD, "") if method_unchanged else ""
            )
        merged[CONF_AUTH_HEADER] = ""
    else:
        if _secret_is_blank(candidate.get(CONF_AUTH_HEADER)):
            merged[CONF_AUTH_HEADER] = (
                current.get(CONF_AUTH_HEADER, "") if method_unchanged else ""
            )
        merged[CONF_USERNAME] = ""
        merged[CONF_PASSWORD] = ""

    return merged


def _auth_method_selector() -> SelectSelector:
    """Create the translated authentication-method selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=list(_AUTH_METHODS),
            translation_key="auth_method",
        )
    )


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
                CONF_AUTH_METHOD, default=auth_method_from_values(defaults)
            ): _auth_method_selector(),
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
    if auth_method_from_values(current) == AUTH_METHOD_HEADER:
        return vol.Schema(
            {
                vol.Optional(CONF_AUTH_HEADER, default=""): _secret_selector(),
            }
        )
    return vol.Schema(
        {
            vol.Optional(
                CONF_USERNAME, default=current.get(CONF_USERNAME, "")
            ): str,
            vol.Optional(CONF_PASSWORD, default=""): _secret_selector(
                autocomplete="current-password"
            ),
        }
    )


async def _validate(hass, values: dict) -> dict:
    """Validate connection settings and return device metadata."""
    api = NibeLocalApi(
        async_get_clientsession(hass),
        host=values[CONF_HOST],
        port=values[CONF_PORT],
        username=values.get(CONF_USERNAME),
        password=values.get(CONF_PASSWORD),
        auth_header=values.get(CONF_AUTH_HEADER),
        auth_method=values.get(CONF_AUTH_METHOD),
        verify_ssl=values[CONF_VERIFY_SSL],
    )
    return await api.get_device()


class NibeLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            candidate = merge_auth_settings(dict(user_input), {})
            try:
                device = await _validate(self.hass, candidate)
            except NibeAuthError:
                errors["base"] = "invalid_auth"
            except NibeApiError:
                errors["base"] = "cannot_connect"
            else:
                product = device.get("product") or {}
                serial = product.get("serialNumber") or (
                    f"{candidate[CONF_HOST]}:{NIBE_DEVICE_ID}"
                )
                await self.async_set_unique_id(str(serial))
                self._abort_if_unique_id_configured()
                title = product.get("name") or "NIBE API"
                return self.async_create_entry(title=title, data=candidate)

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
            candidate = merge_auth_settings(dict(user_input), current)

            try:
                await _validate(self.hass, candidate)
            except NibeAuthError:
                errors["base"] = "invalid_auth"
            except NibeApiError:
                errors["base"] = "cannot_connect"
            else:
                new_data = dict(self._reauth_entry.data)
                new_options = dict(self._reauth_entry.options)

                for key in _AUTH_KEYS:
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
            candidate = merge_auth_settings(dict(user_input), current)

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
