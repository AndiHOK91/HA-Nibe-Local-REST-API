"""Diagnostics support for NIBE Local REST API."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

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
from .entity import device_product_details, point_value, raw_value, scaled_value
from .profiles import DEFAULT_ENTITY_PROFILE

_POINT_METADATA_KEYS = (
    "variableId",
    "description",
    "name",
    "unit",
    "dataType",
    "variableType",
    "variableSize",
    "isWritable",
    "minValue",
    "maxValue",
    "divisor",
    "decimal",
    "step",
)
_HISTORY_DAYS = 7
_HISTORY_TYPES = {"min", "max", "mean", "state"}


def _isoformat(value: Any) -> str | None:
    """Return a stable ISO timestamp for diagnostics."""
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _timestamp_isoformat(value: Any) -> str | None:
    """Return a recorder timestamp as ISO text."""
    if isinstance(value, (int, float)):
        return dt_util.utc_from_timestamp(value).isoformat()
    return _isoformat(value)


def _safe_point_metadata(point: Any) -> dict[str, Any]:
    """Return non-secret point metadata."""
    if not isinstance(point, dict):
        return {}
    metadata = point.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    return {key: metadata[key] for key in _POINT_METADATA_KEYS if key in metadata}


def _diagnostic_point_value(point: Any) -> dict[str, Any]:
    """Return the current point value in raw and integration-scaled form."""
    if not isinstance(point, dict):
        return {}
    value = point_value(point)
    result: dict[str, Any] = {
        "raw_value": raw_value(point),
        "scaled_value": scaled_value(point),
        "is_ok": bool(value.get("isOk", True)),
    }
    title = point.get("title")
    if title not in (None, ""):
        result["title"] = str(title).replace("\u00ad", "").strip()
    return result


def _safe_device_metadata(device: Any) -> dict[str, Any]:
    """Return normalized device metadata without serial/network identifiers."""
    details = device_product_details(device)
    result: dict[str, Any] = {}
    if details["manufacturer"]:
        result["manufacturer"] = details["manufacturer"]
    if details["name"]:
        result["model"] = details["name"]
    if details["software_version"]:
        result["software_version"] = details["software_version"]
    return result


def _alarm_count(notifications: Any) -> int:
    """Return the number of active alarms without exporting alarm payloads."""
    if not isinstance(notifications, dict):
        return 0
    alarms = notifications.get("alarms")
    return len(alarms) if isinstance(alarms, list) else 0


def _point_entity_ids(
    hass: HomeAssistant, entry: ConfigEntry, enabled_ids: set[int]
) -> dict[int, str]:
    """Map enabled NIBE point IDs to Home Assistant entity IDs."""
    registry = er.async_get(hass)
    result: dict[int, str] = {}
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        suffix = str(registry_entry.unique_id).rsplit("_", 1)[-1]
        try:
            point_id = int(suffix)
        except ValueError:
            continue
        if point_id in enabled_ids:
            result[point_id] = registry_entry.entity_id
    return result


def _format_hourly_statistic(row: dict[str, Any]) -> dict[str, Any]:
    """Return one compact hourly recorder row."""
    result: dict[str, Any] = {}
    if "start" in row:
        result["start"] = _timestamp_isoformat(row.get("start"))
    if "end" in row:
        result["end"] = _timestamp_isoformat(row.get("end"))
    for key in ("min", "max", "mean", "state"):
        if key in row and row[key] is not None:
            result[key] = row[key]
    return result


def _history_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize hourly recorder rows while preserving extrema timestamps."""
    result: dict[str, Any] = {"hour_count": len(rows)}

    mins = [(row["min"], row) for row in rows if isinstance(row.get("min"), (int, float))]
    maxes = [(row["max"], row) for row in rows if isinstance(row.get("max"), (int, float))]
    means = [row["mean"] for row in rows if isinstance(row.get("mean"), (int, float))]
    states = [row["state"] for row in rows if isinstance(row.get("state"), (int, float))]

    if mins:
        minimum, minimum_row = min(mins, key=lambda item: item[0])
        result["min"] = minimum
        result["min_at"] = _timestamp_isoformat(minimum_row.get("start"))
    if maxes:
        maximum, maximum_row = max(maxes, key=lambda item: item[0])
        result["max"] = maximum
        result["max_at"] = _timestamp_isoformat(maximum_row.get("start"))
    if means:
        result["mean"] = round(sum(means) / len(means), 6)
    if states:
        result["first_state"] = states[0]
        result["last_state"] = states[-1]

    return result


async def _async_get_7d_history(
    hass: HomeAssistant | None,
    entry: ConfigEntry,
    enabled_ids: set[int],
) -> dict[str, Any]:
    """Return bounded seven-day hourly recorder statistics for point entities."""
    if hass is None or not hasattr(entry, "entry_id"):
        return {"available": False, "reason": "recorder_context_unavailable", "points": {}}

    point_entities = _point_entity_ids(hass, entry, enabled_ids)
    if not point_entities:
        return {"available": True, "days": _HISTORY_DAYS, "points": {}}

    end = dt_util.utcnow()
    start = end - timedelta(days=_HISTORY_DAYS)
    entity_ids = set(point_entities.values())

    try:
        statistics = await get_instance(hass).async_add_executor_job(
            statistics_during_period,
            hass,
            start,
            end,
            entity_ids,
            "hour",
            None,
            _HISTORY_TYPES,
        )
    except Exception as err:  # Diagnostics must still work if recorder is unavailable.
        return {
            "available": False,
            "reason": "recorder_query_failed",
            "error_type": type(err).__name__,
            "days": _HISTORY_DAYS,
            "points": {},
        }

    history_points: dict[str, Any] = {}
    for point_id, entity_id in sorted(point_entities.items()):
        raw_rows = statistics.get(entity_id) or []
        rows = [_format_hourly_statistic(row) for row in raw_rows]
        history_points[str(point_id)] = {
            "entity_id": entity_id,
            "statistics_available": bool(rows),
            "summary": _history_summary(raw_rows) if raw_rows else {"hour_count": 0},
            "hourly": rows,
        }

    return {
        "available": True,
        "days": _HISTORY_DAYS,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "period": "hour",
        "points": history_points,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics for a config entry."""
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
    enabled_id_set = set(enabled_ids)
    current_values = {
        str(point_id): _diagnostic_point_value(points.get(str(point_id)) or points.get(point_id))
        for point_id in enabled_ids
        if points.get(str(point_id)) is not None or points.get(point_id) is not None
    }
    seven_day_history = await _async_get_7d_history(hass, entry, enabled_id_set)

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
            "current_values": current_values,
            "history_7d": seven_day_history,
        },
        "notifications": {
            "active_alarm_count": _alarm_count(coordinator_data.get("notifications")),
        },
    }
