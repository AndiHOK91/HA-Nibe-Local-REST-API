"""Config and options flow for NIBE Local REST API."""
from __future__ import annotations

from typing import Any

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
    CONF_ENTITY_NAMING,
    CONF_ENTITY_PROFILE,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_POINT_IDS,
    CONF_VERIFY_SSL,
    DEFAULT_COMMAND_POLL_DELAY_MS,
    DEFAULT_ENTITY_NAMING,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTITY_NAMING_MODES,
    MIN_SCAN_INTERVAL,
    NIBE_DEVICE_ID,
)
from .profiles import (
    DEFAULT_ENTITY_PROFILE,
    ENTITY_PROFILES,
    PROFILE_INDIVIDUAL,
    normalize_selected_ids,
    profile_counts,
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
    return SelectSelector(
        SelectSelectorConfig(
            options=list(_AUTH_METHODS),
            translation_key="auth_method",
        )
    )


def _entity_profile_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=list(ENTITY_PROFILES),
            translation_key="entity_profile",
        )
    )


def _entity_naming_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=list(ENTITY_NAMING_MODES),
            translation_key="entity_naming",
        )
    )


def _connection_schema(
    defaults: dict,
    *,
    password_default: str = "",
    auth_header_default: str = "",
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                int, vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_AUTH_METHOD, default=auth_method_from_values(defaults)
            ): _auth_method_selector(),
            vol.Optional(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Optional(CONF_PASSWORD, default=password_default): _secret_selector(
                autocomplete="current-password"
            ),
            vol.Optional(CONF_AUTH_HEADER, default=auth_header_default): _secret_selector(),
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


def _options_schema(current: dict) -> vol.Schema:
    fields = dict(
        _connection_schema(
            current,
            password_default="",
            auth_header_default="",
        ).schema
    )
    fields[
        vol.Required(
            CONF_ENTITY_PROFILE,
            default=current.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE),
        )
    ] = _entity_profile_selector()
    fields[
        vol.Required(
            CONF_ENTITY_NAMING,
            default=current.get(CONF_ENTITY_NAMING, DEFAULT_ENTITY_NAMING),
        )
    ] = _entity_naming_selector()
    return vol.Schema(fields)


def _reauth_schema(current: dict) -> vol.Schema:
    if auth_method_from_values(current) == AUTH_METHOD_HEADER:
        return vol.Schema(
            {vol.Optional(CONF_AUTH_HEADER, default=""): _secret_selector()}
        )
    return vol.Schema(
        {
            vol.Optional(CONF_USERNAME, default=current.get(CONF_USERNAME, "")): str,
            vol.Optional(CONF_PASSWORD, default=""): _secret_selector(
                autocomplete="current-password"
            ),
        }
    )


def _api(hass, values: dict) -> NibeLocalApi:
    return NibeLocalApi(
        async_get_clientsession(hass),
        host=values[CONF_HOST],
        port=values[CONF_PORT],
        username=values.get(CONF_USERNAME),
        password=values.get(CONF_PASSWORD),
        auth_header=values.get(CONF_AUTH_HEADER),
        auth_method=values.get(CONF_AUTH_METHOD),
        verify_ssl=values[CONF_VERIFY_SSL],
    )


async def _validate(hass, values: dict) -> dict:
    return await _api(hass, values).get_device()


async def _validate_and_discover(hass, values: dict) -> tuple[dict, dict[str, Any]]:
    api = _api(hass, values)
    device = await api.get_device()
    points = await api.get_points()
    return device, points


def _point_label(point_id: str, point: dict[str, Any]) -> str:
    metadata = point.get("metadata") or {}
    description = (
        point.get("description")
        or point.get("name")
        or metadata.get("description")
        or metadata.get("name")
        or f"Variable {point_id}"
    )
    text = str(description).replace("\u00ad", "").strip().replace("\n", " ")
    unit = metadata.get("shortUnit") or metadata.get("unit")
    suffix = f" [{unit}]" if unit else ""
    return f"{point_id} | {text[:120]}{suffix}"


def _point_options(points: dict[str, Any]) -> list[str]:
    def sort_key(item: tuple[str, Any]) -> tuple[int, str]:
        key = str(item[0])
        return (int(key) if key.isdigit() else 2**31, key)

    return [_point_label(str(pid), point) for pid, point in sorted(points.items(), key=sort_key)]


def _selected_options(points: dict[str, Any], selected_ids) -> list[str]:
    selected = normalize_selected_ids(selected_ids)
    labels = {int(pid): _point_label(str(pid), point) for pid, point in points.items() if str(pid).isdigit()}
    return [labels[pid] for pid in sorted(selected) if pid in labels]


def _parse_selected_options(values) -> list[int]:
    point_ids: set[int] = set()
    for value in values or ():
        prefix = str(value).split(" | ", 1)[0].strip()
        try:
            point_ids.add(int(prefix))
        except ValueError:
            continue
    return sorted(point_ids)


def _entity_selection_schema(
    points: dict[str, Any], selected_ids=None
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_SELECTED_POINT_IDS,
                default=_selected_options(points, selected_ids),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_point_options(points),
                    multiple=True,
                )
            )
        }
    )


class NibeLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    _reauth_entry: ConfigEntry | None = None
    _pending_data: dict | None = None
    _pending_device: dict | None = None
    _available_points: dict[str, Any] | None = None

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            candidate = merge_auth_settings(dict(user_input), {})
            try:
                device, points = await _validate_and_discover(self.hass, candidate)
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
                self._pending_data = candidate
                self._pending_device = device
                self._available_points = points
                return await self.async_step_entity_profile()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema({}),
            errors=errors,
        )

    def _create_pending_entry(self):
        if self._pending_data is None or self._pending_device is None:
            return self.async_abort(reason="setup_state_missing")
        product = self._pending_device.get("product") or {}
        title = product.get("name") or "NIBE API"
        return self.async_create_entry(title=title, data=self._pending_data)

    async def async_step_entity_profile(self, user_input=None):
        if self._pending_data is None:
            return self.async_abort(reason="setup_state_missing")
        if user_input is not None:
            profile = str(user_input[CONF_ENTITY_PROFILE])
            self._pending_data[CONF_ENTITY_PROFILE] = profile
            self._pending_data[CONF_ENTITY_NAMING] = str(
                user_input.get(CONF_ENTITY_NAMING, DEFAULT_ENTITY_NAMING)
            )
            if profile == PROFILE_INDIVIDUAL:
                return await self.async_step_entity_selection()
            return self._create_pending_entry()

        points = self._available_points or {}
        counts = profile_counts(points.keys())
        return self.async_show_form(
            step_id="entity_profile",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENTITY_PROFILE,
                        default=DEFAULT_ENTITY_PROFILE,
                    ): _entity_profile_selector(),
                    vol.Required(
                        CONF_ENTITY_NAMING,
                        default=DEFAULT_ENTITY_NAMING,
                    ): _entity_naming_selector(),
                }
            ),
            description_placeholders={
                "minimal": str(counts["minimal"]),
                "standard": str(counts["standard"]),
                "extended": str(counts["extended"]),
                "complete": str(counts["complete"]),
                "individual": str(counts["individual"]),
            },
        )

    async def async_step_entity_selection(self, user_input=None):
        if self._pending_data is None:
            return self.async_abort(reason="setup_state_missing")
        points = self._available_points or {}
        if user_input is not None:
            self._pending_data[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            return self._create_pending_entry()

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=_entity_selection_schema(points),
            description_placeholders={"count": str(len(points))},
        )

    async def async_step_reauth(self, entry_data: dict):
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_entry_missing")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
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
    """Edit connection, polling and entity-profile settings after setup."""

    _pending_options: dict | None = None
    _available_points: dict[str, Any] | None = None

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            candidate = merge_auth_settings(dict(user_input), current)
            profile = str(
                user_input.get(
                    CONF_ENTITY_PROFILE,
                    current.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE),
                )
            )
            candidate[CONF_ENTITY_PROFILE] = profile
            candidate[CONF_ENTITY_NAMING] = str(
                user_input.get(
                    CONF_ENTITY_NAMING,
                    current.get(CONF_ENTITY_NAMING, DEFAULT_ENTITY_NAMING),
                )
            )
            try:
                _device, points = await _validate_and_discover(self.hass, candidate)
            except NibeAuthError:
                errors["base"] = "invalid_auth"
            except NibeApiError:
                errors["base"] = "cannot_connect"
            else:
                if profile == PROFILE_INDIVIDUAL:
                    self._pending_options = candidate
                    self._available_points = points
                    return await self.async_step_entity_selection()
                return self.async_create_entry(title="", data=candidate)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
            errors=errors,
        )

    async def async_step_entity_selection(self, user_input=None):
        if self._pending_options is None:
            return self.async_abort(reason="setup_state_missing")
        points = self._available_points or {}
        if user_input is not None:
            self._pending_options[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            return self.async_create_entry(title="", data=self._pending_options)

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=_entity_selection_schema(
                points,
                self._pending_options.get(CONF_SELECTED_POINT_IDS),
            ),
            description_placeholders={"count": str(len(points))},
        )
