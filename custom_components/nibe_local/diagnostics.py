"""Diagnostics support for NIBE Local REST API."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant

from .const import (
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
)
from .coordinator import NibeCoordinator
from .profiles import DEFAULT_ENTITY_PROFILE

_POINT_METADATA_KEYS = (
    "variableId",
    "description",
    "name",
    "unit",
    "dataType",
    "isWritable",
    "minValue",
    "maxValue",
    "divisor",
    "step",
)

_DEVICE_METADATA_KEYS = (
    "product",
    "productName",
    "model",
    "modelName",
    "softwareVersion",
    "firmwareVersion",
    "version",
)


def _isoformat(value: Any) -> str | None:
    """Return a stable ISO timestamp for diagnostics."""
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _safe_point_metadata(point: Any) -> dict[str, Any]:
    """Return non-secret point metadata without exposing the current value."""
    if not isinstance(point, dict):
        return {}
    metadata = point.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    return {key: metadata[key] for key in _POINT_METADATA_KEYS if key in metadata}


def _safe_device_metadata(device: Any) -> dict[str, Any]:
    """Return allowlisted device metadata and avoid serial/network identifiers."""
    if not isinstance(device, dict):
        return {}
    return {key: device[key] for key in _DEVICE_METADATA_KEYS if key in device}


def _alarm_count(notifications: Any) -> int:
    """Return the number of active alarms without exporting alarm payloads."""
    if not isinstance(notifications, dict):
        return 0
    alarms = notifications.get("alarms")
    return len(alarms) if isinstance(alarms, list) else 0


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics for a config entry."""
    del hass
    coordinator: NibeCoordinator = entry.runtime_data
    configured = {**entry.data, **entry.options}
    coordinator_data = coordinator.data or {}
    points = coordinator_data.get("points") or {}

    point_metadata = {
        str(point_id): _safe_point_metadata(point)
        for point_id, point in points.items()
    }

    selected_ids = configured.get(CONF_SELECTED_POINT_IDS, ()) or ()
    enabled_ids = sorted(coordinator.enabled_point_ids)

    return {
        "configuration": {
            # Deliberately allowlisted: host, username, password and Authorization
            # header are never included in diagnostics.
            "port": configured.get(CONF_PORT, DEFAULT_PORT),
            "verify_ssl": configured.get(CONF_VERIFY_SSL, False),
            "auth_method": configured.get(CONF_AUTH_METHOD),
            "scan_interval": configured.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            "command_poll_delay_ms": configured.get(
                CONF_COMMAND_POLL_DELAY_MS, DEFAULT_COMMAND_POLL_DELAY_MS
            ),
            "entity_profile": configured.get(
                CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE
            ),
            "entity_naming": configured.get(CONF_ENTITY_NAMING, DEFAULT_ENTITY_NAMING),
            "selected_point_ids": sorted(int(value) for value in selected_ids),
        },
        "connection": {
            "last_update_success": coordinator.last_update_success,
            "bulk_fallback_active": coordinator.bulk_fallback_active,
            "last_successful_poll": _isoformat(coordinator.last_successful_poll),
            "last_connection_error": _isoformat(coordinator.last_connection_error),
        },
        "device": _safe_device_metadata(coordinator_data.get("device")),
        "points": {
            "available_count": len(points),
            "enabled_count": len(enabled_ids),
            "enabled_point_ids": enabled_ids,
            "metadata": point_metadata,
        },
        "notifications": {
            "active_alarm_count": _alarm_count(coordinator_data.get("notifications")),
        },
    }
