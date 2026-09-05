"""Config and options flow for NIBE Local REST API."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.translation import async_get_translations

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
    POINTS,
    POINT_VENTILATION_MODE,
)
from .equipment import (
    CONF_EQUIPMENT,
    EQUIPMENT_BE6,
    EQUIPMENT_BE7,
    EQUIPMENT_HOT_WATER_CIRCULATION,
    EQUIPMENT_OPTIONS,
    EQUIPMENT_VENTILATION,
    detect_equipment,
    filter_points_for_equipment,
    normalize_equipment,
    point_allowed_by_equipment,
)
from .profiles import (
    DEFAULT_ENTITY_PROFILE,
    ENTITY_PROFILES,
    PROFILE_INDIVIDUAL,
    normalize_selected_ids,
    point_enabled,
    profile_counts,
)

_AUTH_KEYS = (CONF_AUTH_METHOD, CONF_USERNAME, CONF_PASSWORD, CONF_AUTH_HEADER)
_AUTH_METHODS = (AUTH_METHOD_BASIC, AUTH_METHOD_HEADER)
CONF_REMOVE_INACTIVE_ENTITIES = "remove_inactive_entities"
CONF_BACKUP_BEFORE_CLEANUP = "backup_before_cleanup"
PREVIEW_LIST_LIMIT = 50


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


def _is_german(hass) -> bool:
    config = getattr(hass, "config", None)
    return str(getattr(config, "language", "")).lower().startswith("de")


def _equipment_form_key(hass) -> str:
    """Use a readable transient form key without adding persisted translation keys."""
    return "Ausstattung" if _is_german(hass) else "Equipment"


def _ordered_equipment(values) -> list[str]:
    enabled = normalize_equipment(values, legacy_default=False)
    return [value for value in EQUIPMENT_OPTIONS if value in enabled]


def _equipment_selector(hass, *, detected=()) -> SelectSelector:
    german = _is_german(hass)
    detected_values = normalize_equipment(detected, legacy_default=False)
    labels_de = {
        EQUIPMENT_BE6: "Energiezähler BE6",
        EQUIPMENT_BE7: "Energiezähler BE7",
        EQUIPMENT_VENTILATION: "Lüftungsanlage / ERS",
        EQUIPMENT_HOT_WATER_CIRCULATION: "Brauchwasserzirkulation",
    }
    labels_en = {
        EQUIPMENT_BE6: "Energy meter BE6",
        EQUIPMENT_BE7: "Energy meter BE7",
        EQUIPMENT_VENTILATION: "Ventilation / ERS",
        EQUIPMENT_HOT_WATER_CIRCULATION: "Hot-water circulation",
    }
    labels = labels_de if german else labels_en
    suffix = " (erkannt)" if german else " (detected)"
    options = [
        {
            "value": value,
            "label": labels[value] + (suffix if value in detected_values else ""),
        }
        for value in EQUIPMENT_OPTIONS
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            multiple=True,
            mode=SelectSelectorMode.LIST,
        )
    )


def _connection_schema(defaults: dict) -> vol.Schema:
    """Connection settings shown before method-specific credentials."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                int, vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_AUTH_METHOD, default=auth_method_from_values(defaults)
            ): _auth_method_selector(),
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


def _basic_auth_schema(defaults: dict, *, password_default: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Optional(CONF_PASSWORD, default=password_default): _secret_selector(
                autocomplete="current-password"
            ),
        }
    )


def _header_auth_schema(*, auth_header_default: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_AUTH_HEADER, default=auth_header_default): _secret_selector()
        }
    )


def _options_schema(current: dict, hass=None) -> vol.Schema:
    fields = dict(_connection_schema(current).schema)
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
    fields[
        vol.Required(
            _equipment_form_key(hass),
            default=_ordered_equipment(current.get(CONF_EQUIPMENT, EQUIPMENT_OPTIONS)),
        )
    ] = _equipment_selector(hass)
    fields[vol.Optional(CONF_REMOVE_INACTIVE_ENTITIES, default=False)] = bool
    fields[vol.Optional(CONF_BACKUP_BEFORE_CLEANUP, default=True)] = bool
    return vol.Schema(fields)


async def _async_create_cleanup_backup(hass) -> None:
    """Create and await the safest available Home Assistant backup before cleanup."""
    if hass.services.has_service("hassio", "backup_full"):
        await hass.services.async_call(
            "hassio",
            "backup_full",
            {"name": "NIBE Local REST API - Registry cleanup"},
            blocking=True,
        )
        return

    if hass.services.has_service("backup", "create"):
        await hass.services.async_call("backup", "create", {}, blocking=True)
        return

    try:
        from homeassistant.components.backup import async_get_backup_manager
    except ImportError:
        async_get_backup_manager = None
    if async_get_backup_manager is not None:
        manager = async_get_backup_manager(hass)
        create_automatic = getattr(manager, "async_create_automatic_backup", None)
        if create_automatic is not None:
            await create_automatic()
            return

    if hass.services.has_service("backup", "create_automatic"):
        await hass.services.async_call(
            "backup", "create_automatic", {}, blocking=True
        )
        return

    raise HomeAssistantError("No Home Assistant backup action is available")


def _point_is_enabled(
    points: dict[str, Any],
    profile: str,
    point_id: int,
    selected_ids,
    equipment,
) -> bool:
    return point_enabled(profile, point_id, selected_ids) and point_allowed_by_equipment(
        point_id,
        equipment,
        points.get(str(point_id)),
    )


async def _async_remove_inactive_point_entities(
    hass,
    entry: ConfigEntry,
    profile: str,
    selected_ids,
    equipment,
    points: dict[str, Any],
) -> int:
    """Remove only deselected point-backed entities when explicitly requested."""
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    removed = 0
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = registry_entry.unique_id
        if not unique_id.startswith(prefix):
            continue
        suffix = unique_id[len(prefix):]
        if not suffix.isdigit():
            continue
        point_id = int(suffix)
        if _point_is_enabled(points, profile, point_id, selected_ids, equipment):
            continue
        registry.async_remove(registry_entry.entity_id)
        removed += 1
    return removed


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


def _known_point_fallback_name(point_id: str) -> str | None:
    """Return a readable fallback name for a curated point."""
    if not str(point_id).isdigit():
        return None
    numeric_id = int(point_id)
    definition = next(
        (item for item in POINTS if item.point_id == numeric_id), None
    )
    if definition is None:
        return None
    return definition.key.replace("_", " ").strip().capitalize()


async def _async_translated_point_names(hass) -> dict[int, str]:
    """Load localized Home Assistant names for curated NIBE points."""
    resources = await async_get_translations(
        hass,
        hass.config.language,
        "entity",
        [DOMAIN],
    )
    names: dict[int, str] = {}
    for definition in POINTS:
        key = (
            f"component.{DOMAIN}.entity.{definition.platform}."
            f"{definition.key}.name"
        )
        if name := resources.get(key):
            names[definition.point_id] = str(name)
    return names


def _point_label(
    point_id: str,
    point: dict[str, Any],
    point_names: dict[int, str] | None = None,
) -> str:
    """Build a human-readable selection label with name, ID and unit."""
    metadata = point.get("metadata") or {}
    numeric_id = int(point_id) if str(point_id).isdigit() else None
    translated_name = (
        point_names.get(numeric_id)
        if point_names is not None and numeric_id is not None
        else None
    )
    description = (
        translated_name
        or point.get("description")
        or point.get("name")
        or metadata.get("description")
        or metadata.get("name")
        or _known_point_fallback_name(point_id)
    )
    unit = metadata.get("shortUnit") or metadata.get("unit")
    unit_suffix = f" [{unit}]" if unit else ""
    if description:
        cleaned = (
            str(description)
            .replace("\u00ad", "")
            .strip()
            .replace("\n", " ")
        )
        return f"{cleaned[:120]} · Variable ID {point_id}{unit_suffix}"
    return f"Variable ID {point_id}{unit_suffix}"


def _point_options(
    points: dict[str, Any], point_names: dict[int, str] | None = None
) -> list[dict[str, str]]:
    def sort_key(item: tuple[str, Any]) -> tuple[int, str]:
        key = str(item[0])
        return (int(key) if key.isdigit() else 2**31, key)

    return [
        {
            "value": str(pid),
            "label": _point_label(str(pid), point, point_names),
        }
        for pid, point in sorted(points.items(), key=sort_key)
    ]


def _selected_options(points: dict[str, Any], selected_ids) -> list[str]:
    selected = normalize_selected_ids(selected_ids)
    available = {int(pid) for pid in points if str(pid).isdigit()}
    return [str(pid) for pid in sorted(selected) if pid in available]


def _parse_selected_options(values) -> list[int]:
    """Parse new ID values and legacy labels from earlier 0.9.0 forms."""
    point_ids: set[int] = set()
    for value in values or ():
        text = str(value).strip()
        candidate = text if text.isdigit() else text.split(" | ", 1)[0].strip()
        try:
            point_ids.add(int(candidate))
        except ValueError:
            continue
    return sorted(point_ids)


def _entity_selection_schema(
    points: dict[str, Any],
    selected_ids=None,
    *,
    point_names: dict[int, str] | None = None,
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_SELECTED_POINT_IDS,
                default=_selected_options(points, selected_ids),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_point_options(points, point_names),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )
        }
    )


def _registered_point_ids(hass, entry: ConfigEntry | None) -> frozenset[int]:
    """Return numeric point IDs currently present in this entry's registry."""
    if entry is None:
        return frozenset()
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    result: set[int] = set()
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = registry_entry.unique_id
        if not unique_id.startswith(prefix):
            continue
        suffix = unique_id[len(prefix):]
        if suffix.isdigit():
            result.add(int(suffix))
    return frozenset(result)


def _preview_point_groups(
    points: dict[str, Any],
    profile: str,
    selected_ids,
    equipment=None,
    *,
    registered_ids=(),
    cleanup: bool = False,
) -> dict[str, frozenset[int]]:
    """Split discovered/registered points into the final preview groups."""
    available = normalize_selected_ids(points.keys())
    registered = normalize_selected_ids(registered_ids)
    active = frozenset(
        point_id
        for point_id in available
        if _point_is_enabled(points, profile, point_id, selected_ids, equipment)
    )
    disabled_registered = frozenset(
        point_id
        for point_id in registered
        if not _point_is_enabled(points, profile, point_id, selected_ids, equipment)
    )
    delete = disabled_registered if cleanup else frozenset()
    inactive = frozenset(((available - active) | disabled_registered) - delete)
    return {
        "active": active,
        "active_existing": frozenset(active & registered),
        "active_new": frozenset(active - registered),
        "inactive": inactive,
        "delete": delete,
    }


def _format_preview_ids(
    point_ids,
    points: dict[str, Any],
    point_names: dict[int, str],
    *,
    german: bool,
) -> str:
    """Format a bounded, human-readable point list for a config-flow preview."""
    ordered = sorted(normalize_selected_ids(point_ids))
    if not ordered:
        return "– Keine" if german else "– None"
    visible = ordered[:PREVIEW_LIST_LIMIT]
    lines = [
        f"- {_point_label(str(point_id), points.get(str(point_id), {}), point_names)}"
        for point_id in visible
    ]
    remaining = len(ordered) - len(visible)
    if remaining:
        lines.append(
            f"- … + {remaining} weitere" if german else f"- … + {remaining} more"
        )
    return "\n".join(lines)


def _preview_special_entities(
    points: dict[str, Any],
    profile: str,
    selected_ids,
    equipment,
    device: dict[str, Any] | None,
    *,
    german: bool,
) -> list[str]:
    """Return non-point helper entities that the integration will provide."""
    if german:
        result = [
            "REST API erreichbar",
            "Einzelpunkt-Fallback aktiv",
            "Meldungen / Alarme",
            "Letzter Verbindungsfehler",
        ]
    else:
        result = [
            "REST API reachable",
            "Individual-point fallback active",
            "Notifications / alarms",
            "Last connection error",
        ]

    if isinstance(device, dict) and "smartMode" in device:
        result.append("Smart Mode")

    ventilation = points.get(str(POINT_VENTILATION_MODE)) or {}
    ventilation_metadata = ventilation.get("metadata") or {}
    if (
        ventilation
        and _point_is_enabled(
            points,
            profile,
            POINT_VENTILATION_MODE,
            selected_ids,
            equipment,
        )
        and bool(ventilation_metadata.get("isWritable"))
    ):
        result.append("Lüftung+" if german else "Ventilation+")
    return result


def _profile_preview_label(profile: str, *, german: bool) -> str:
    labels_de = {
        "standard": "Standard",
        "extended": "Erweitert",
        "complete": "Komplett",
        "individual": "Individuell",
    }
    labels_en = {
        "standard": "Standard",
        "extended": "Extended",
        "complete": "Complete",
        "individual": "Individual",
    }
    return (labels_de if german else labels_en).get(profile, profile)


async def _async_entity_preview_placeholders(
    hass,
    *,
    points: dict[str, Any],
    profile: str,
    selected_ids,
    equipment,
    device: dict[str, Any] | None,
    entry: ConfigEntry | None = None,
    cleanup: bool = False,
    backup: bool = False,
) -> dict[str, str]:
    """Build localized placeholders for the final entity overview."""
    german = _is_german(hass)
    point_names = await _async_translated_point_names(hass)
    registered = _registered_point_ids(hass, entry)
    groups = _preview_point_groups(
        points,
        profile,
        selected_ids,
        equipment,
        registered_ids=registered,
        cleanup=cleanup,
    )
    special = _preview_special_entities(
        points, profile, selected_ids, equipment, device, german=german
    )
    yes = "Ja" if german else "Yes"
    no = "Nein" if german else "No"
    backup_value = yes if cleanup and backup else (no if cleanup else "–")
    allowed_points = filter_points_for_equipment(points, equipment)
    return {
        "profile": _profile_preview_label(profile, german=german),
        "discovered": str(len(normalize_selected_ids(allowed_points.keys()))),
        "active_count": str(len(groups["active"])),
        "active_existing": str(len(groups["active_existing"])),
        "active_new": str(len(groups["active_new"])),
        "inactive_count": str(len(groups["inactive"])),
        "delete_count": str(len(groups["delete"])),
        "special_count": str(len(special)),
        "active_list": _format_preview_ids(
            groups["active"], points, point_names, german=german
        ),
        "inactive_list": _format_preview_ids(
            groups["inactive"], points, point_names, german=german
        ),
        "delete_list": _format_preview_ids(
            groups["delete"], points, point_names, german=german
        ),
        "special_list": "\n".join(f"- {name}" for name in special),
        "cleanup": yes if cleanup else no,
        "backup": backup_value,
    }


class NibeLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    _reauth_entry: ConfigEntry | None = None
    _pending_data: dict | None = None
    _pending_device: dict | None = None
    _available_points: dict[str, Any] | None = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._pending_data = dict(user_input)
            if auth_method_from_values(self._pending_data) == AUTH_METHOD_HEADER:
                return await self.async_step_auth_header()
            return await self.async_step_auth_basic()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema({}),
        )

    async def _async_finish_auth(self, user_input: dict, step_id: str):
        if self._pending_data is None:
            return self.async_abort(reason="setup_state_missing")
        candidate = merge_auth_settings(
            {**self._pending_data, **dict(user_input)}, {}
        )
        errors: dict[str, str] = {}
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

        schema = (
            _header_auth_schema()
            if step_id == "auth_header"
            else _basic_auth_schema(self._pending_data)
        )
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def async_step_auth_basic(self, user_input=None):
        if self._pending_data is None:
            return self.async_abort(reason="setup_state_missing")
        if user_input is not None:
            return await self._async_finish_auth(dict(user_input), "auth_basic")
        return self.async_show_form(
            step_id="auth_basic", data_schema=_basic_auth_schema(self._pending_data)
        )

    async def async_step_auth_header(self, user_input=None):
        if self._pending_data is None:
            return self.async_abort(reason="setup_state_missing")
        if user_input is not None:
            return await self._async_finish_auth(dict(user_input), "auth_header")
        return self.async_show_form(
            step_id="auth_header", data_schema=_header_auth_schema()
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
        equipment_key = _equipment_form_key(self.hass)
        if user_input is not None:
            profile = str(user_input[CONF_ENTITY_PROFILE])
            self._pending_data[CONF_ENTITY_PROFILE] = profile
            self._pending_data[CONF_ENTITY_NAMING] = str(
                user_input.get(CONF_ENTITY_NAMING, DEFAULT_ENTITY_NAMING)
            )
            self._pending_data[CONF_EQUIPMENT] = _ordered_equipment(
                user_input.get(equipment_key, ())
            )
            if profile == PROFILE_INDIVIDUAL:
                return await self.async_step_entity_selection()
            return await self.async_step_entity_preview()

        points = self._available_points or {}
        detected = detect_equipment(points)
        filtered_points = filter_points_for_equipment(points, detected)
        counts = profile_counts(filtered_points.keys())
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
                    vol.Required(
                        equipment_key,
                        default=_ordered_equipment(detected),
                    ): _equipment_selector(self.hass, detected=detected),
                }
            ),
            description_placeholders={
                "standard": str(counts["standard"]),
                "extended": str(counts["extended"]),
                "complete": str(counts["complete"]),
                "individual": str(counts["individual"]),
            },
        )

    async def async_step_entity_selection(self, user_input=None):
        if self._pending_data is None:
            return self.async_abort(reason="setup_state_missing")
        equipment = self._pending_data.get(CONF_EQUIPMENT, ())
        points = filter_points_for_equipment(self._available_points or {}, equipment)
        point_names = await _async_translated_point_names(self.hass)
        if user_input is not None:
            self._pending_data[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            return await self.async_step_entity_preview()

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=_entity_selection_schema(points, point_names=point_names),
            description_placeholders={"count": str(len(points))},
        )

    async def async_step_entity_preview(self, user_input=None):
        if self._pending_data is None or self._pending_device is None:
            return self.async_abort(reason="setup_state_missing")
        if user_input is not None:
            return self._create_pending_entry()

        profile = str(
            self._pending_data.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
        )
        points = self._available_points or {}
        equipment = self._pending_data.get(CONF_EQUIPMENT, ())
        placeholders = await _async_entity_preview_placeholders(
            self.hass,
            points=points,
            profile=profile,
            selected_ids=self._pending_data.get(CONF_SELECTED_POINT_IDS, ()),
            equipment=equipment,
            device=self._pending_device,
        )
        return self.async_show_form(
            step_id="entity_preview",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders,
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
    """Edit connection, polling, entity profile, naming and credentials."""

    _pending_options: dict | None = None
    _available_points: dict[str, Any] | None = None
    _pending_device: dict[str, Any] | None = None
    _cleanup_inactive = False
    _backup_before_cleanup = True

    async def async_step_init(self, user_input=None):
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            submitted = dict(user_input)
            self._cleanup_inactive = bool(
                submitted.pop(CONF_REMOVE_INACTIVE_ENTITIES, False)
            )
            self._backup_before_cleanup = bool(
                submitted.pop(CONF_BACKUP_BEFORE_CLEANUP, True)
            )
            equipment_value = submitted.pop(_equipment_form_key(self.hass), None)
            if equipment_value is not None:
                submitted[CONF_EQUIPMENT] = _ordered_equipment(equipment_value)
            self._pending_options = merge_auth_settings(submitted, current)
            if auth_method_from_values(self._pending_options) == AUTH_METHOD_HEADER:
                return await self.async_step_auth_header()
            return await self.async_step_auth_basic()

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current, self.hass),
        )

    async def _async_finish_auth(self, user_input: dict, step_id: str):
        if self._pending_options is None:
            return self.async_abort(reason="setup_state_missing")
        candidate = merge_auth_settings(dict(user_input), self._pending_options)
        profile = str(candidate.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE))
        errors: dict[str, str] = {}
        try:
            device, points = await _validate_and_discover(self.hass, candidate)
        except NibeAuthError:
            errors["base"] = "invalid_auth"
        except NibeApiError:
            errors["base"] = "cannot_connect"
        else:
            self._pending_options = candidate
            self._available_points = points
            self._pending_device = device
            if profile == PROFILE_INDIVIDUAL:
                return await self.async_step_entity_selection()
            return await self.async_step_entity_preview()

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = (
            _header_auth_schema()
            if step_id == "auth_header"
            else _basic_auth_schema(current)
        )
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def async_step_auth_basic(self, user_input=None):
        if self._pending_options is None:
            return self.async_abort(reason="setup_state_missing")
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            return await self._async_finish_auth(dict(user_input), "auth_basic")
        return self.async_show_form(
            step_id="auth_basic",
            data_schema=_basic_auth_schema(current, password_default=""),
        )

    async def async_step_auth_header(self, user_input=None):
        if self._pending_options is None:
            return self.async_abort(reason="setup_state_missing")
        if user_input is not None:
            return await self._async_finish_auth(dict(user_input), "auth_header")
        return self.async_show_form(
            step_id="auth_header", data_schema=_header_auth_schema(auth_header_default="")
        )

    async def async_step_entity_selection(self, user_input=None):
        if self._pending_options is None:
            return self.async_abort(reason="setup_state_missing")
        equipment = self._pending_options.get(CONF_EQUIPMENT)
        points = filter_points_for_equipment(self._available_points or {}, equipment)
        point_names = await _async_translated_point_names(self.hass)
        if user_input is not None:
            self._pending_options[CONF_SELECTED_POINT_IDS] = _parse_selected_options(
                user_input.get(CONF_SELECTED_POINT_IDS)
            )
            return await self.async_step_entity_preview()

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=_entity_selection_schema(
                points,
                self._pending_options.get(CONF_SELECTED_POINT_IDS),
                point_names=point_names,
            ),
            description_placeholders={"count": str(len(points))},
        )

    async def async_step_entity_preview(self, user_input=None):
        if self._pending_options is None or self._pending_device is None:
            return self.async_abort(reason="setup_state_missing")

        profile = str(
            self._pending_options.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE)
        )
        points = self._available_points or {}
        equipment = self._pending_options.get(CONF_EQUIPMENT)
        placeholders = await _async_entity_preview_placeholders(
            self.hass,
            points=points,
            profile=profile,
            selected_ids=self._pending_options.get(CONF_SELECTED_POINT_IDS, ()),
            equipment=equipment,
            device=self._pending_device,
            entry=self.config_entry,
            cleanup=self._cleanup_inactive,
            backup=self._backup_before_cleanup,
        )

        if user_input is not None:
            if self._cleanup_inactive:
                if self._backup_before_cleanup:
                    try:
                        await _async_create_cleanup_backup(self.hass)
                    except Exception:
                        return self.async_show_form(
                            step_id="entity_preview",
                            data_schema=vol.Schema({}),
                            errors={"base": "backup_failed"},
                            description_placeholders=placeholders,
                        )
                await _async_remove_inactive_point_entities(
                    self.hass,
                    self.config_entry,
                    profile,
                    self._pending_options.get(CONF_SELECTED_POINT_IDS, ()),
                    equipment,
                    points,
                )
            return self.async_create_entry(title="", data=self._pending_options)

        return self.async_show_form(
            step_id="entity_preview",
            data_schema=vol.Schema({}),
            description_placeholders=placeholders,
        )
