"""Diagnostics support for NIBE Local REST API."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.recorder import history
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.recorder import get_instance
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
from .entity import (
    device_product_details,
    point_value,
    raw_value,
    raw_value_is_sentinel,
    scaled_value,
)
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
_HISTORY_HOURS = 24


def _isoformat(value: Any) -> str | None:
    """Return a stable ISO timestamp for diagnostics."""
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


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
    sentinel = raw_value_is_sentinel(point)
    api_ok = bool(value.get("isOk", True))
    result: dict[str, Any] = {
        "raw_value": raw_value(point),
        "scaled_value": scaled_value(point),
        "is_ok": api_ok,
        "raw_value_is_sentinel": sentinel,
        "value_valid": api_ok and not sentinel,
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


def _history_state_value(state: Any) -> float | None:
    """Return a recorder state as a finite numeric value when possible."""
    value = state.get("state") if isinstance(state, dict) else getattr(state, "state", None)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        return None
    return numeric


def _history_state_time(state: Any) -> datetime | None:
    """Return the timestamp of a recorder state."""
    if isinstance(state, dict):
        value = state.get("last_updated") or state.get("last_changed")
        if isinstance(value, (int, float)):
            return dt_util.utc_from_timestamp(value)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return dt_util.parse_datetime(value)
        return None
    return getattr(state, "last_updated", None) or getattr(state, "last_changed", None)


def _minute_buckets(states: list[Any]) -> list[dict[str, Any]]:
    """Aggregate recorder states into one compact row per minute."""
    buckets: dict[datetime, list[float]] = {}
    for state in states:
        value = _history_state_value(state)
        timestamp = _history_state_time(state)
        if value is None or timestamp is None:
            continue
        minute = timestamp.replace(second=0, microsecond=0)
        buckets.setdefault(minute, []).append(value)

    result: list[dict[str, Any]] = []
    for minute, values in sorted(buckets.items()):
        result.append(
            {
                "minute": minute.isoformat(),
                "min": min(values),
                "max": max(values),
                "mean": round(sum(values) / len(values), 6),
                "last": values[-1],
                "samples": len(values),
            }
        )
    return result


def _history_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize minute buckets while preserving extrema timestamps."""
    result: dict[str, Any] = {"minute_count": len(rows)}
    if not rows:
        return result

    minimum_row = min(rows, key=lambda row: row["min"])
    maximum_row = max(rows, key=lambda row: row["max"])
    sample_count = sum(int(row.get("samples", 0)) for row in rows)

    result.update(
        {
            "sample_count": sample_count,
            "min": minimum_row["min"],
            "min_at": minimum_row["minute"],
            "max": maximum_row["max"],
            "max_at": maximum_row["minute"],
            "first": rows[0]["last"],
            "last": rows[-1]["last"],
        }
    )
    if sample_count:
        result["mean"] = round(
            sum(row["mean"] * row["samples"] for row in rows) / sample_count,
            6,
        )
    return result


async def _async_get_24h_history(
    hass: HomeAssistant | None,
    entry: ConfigEntry,
    enabled_ids: set[int],
) -> dict[str, Any]:
    """Return 24 hours of recorder history aggregated into minute buckets."""
    if hass is None or not hasattr(entry, "entry_id"):
        return {"available": False, "reason": "recorder_context_unavailable", "points": {}}

    point_entities = _point_entity_ids(hass, entry, enabled_ids)
    if not point_entities:
        return {
            "available": True,
            "hours": _HISTORY_HOURS,
            "period": "minute",
            "points": {},
        }

    end = dt_util.utcnow()
    start = end - timedelta(hours=_HISTORY_HOURS)
    entity_ids = list(point_entities.values())

    try:
        recorded_states = await get_instance(hass).async_add_executor_job(
            history.get_significant_states,
            hass,
            start,
            end,
            entity_ids,
            None,
            False,
            False,
            False,
            True,
        )
    except Exception as err:  # Diagnostics must still work if recorder is unavailable.
        return {
            "available": False,
            "reason": "recorder_query_failed",
            "error_type": type(err).__name__,
            "hours": _HISTORY_HOURS,
            "period": "minute",
            "points": {},
        }

    history_points: dict[str, Any] = {}
    for point_id, entity_id in sorted(point_entities.items()):
        rows = _minute_buckets(recorded_states.get(entity_id) or [])
        history_points[str(point_id)] = {
            "history_available": bool(rows),
            "summary": _history_summary(rows),
            "minutes": rows,
        }

    return {
        "available": True,
        "hours": _HISTORY_HOURS,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "period": "minute",
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
    history_24h = await _async_get_24h_history(hass, entry, enabled_id_set)

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
            "history_24h": history_24h,
        },
        "notifications": {
            "active_alarm_count": _alarm_count(coordinator_data.get("notifications")),
        },
    }
