"""Read-only preview for migrating historical statistics to NIBE REST entities."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import partial
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import get_metadata, statistics_during_period
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant

_PREVIEW_START = datetime(1970, 1, 1, tzinfo=timezone.utc)
_PREVIEW_TYPES = {"min", "max", "mean", "state", "sum"}


def _metadata_payload(metadata: Any) -> dict[str, Any]:
    """Return the stable subset of recorder statistic metadata."""
    if not metadata:
        return {}
    # get_metadata() returns statistic_id -> (metadata_id, StatisticMetaData).
    item = metadata[1] if isinstance(metadata, tuple) and len(metadata) > 1 else metadata
    if isinstance(item, dict):
        return {
            "unit_of_measurement": item.get("unit_of_measurement"),
            "has_mean": item.get("has_mean"),
            "has_sum": item.get("has_sum"),
            "name": item.get("name"),
            "source": item.get("source"),
        }
    return {
        "unit_of_measurement": getattr(item, "unit_of_measurement", None),
        "has_mean": getattr(item, "has_mean", None),
        "has_sum": getattr(item, "has_sum", None),
        "name": getattr(item, "name", None),
        "source": getattr(item, "source", None),
    }


def _row_start(row: dict[str, Any]) -> float | None:
    value = row.get("start")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _iso_from_timestamp(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _compatibility(
    source_state: Any,
    target_state: Any,
    source_metadata: dict[str, Any],
    target_metadata: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Check conservative compatibility without modifying recorder data."""
    warnings: list[str] = []

    source_unit = source_metadata.get("unit_of_measurement") or (
        source_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if source_state else None
    )
    target_unit = target_metadata.get("unit_of_measurement") or (
        target_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if target_state else None
    )
    if source_unit != target_unit:
        warnings.append(f"Einheit unterschiedlich: {source_unit!r} -> {target_unit!r}")

    source_class = source_state.attributes.get(ATTR_DEVICE_CLASS) if source_state else None
    target_class = target_state.attributes.get(ATTR_DEVICE_CLASS) if target_state else None
    if source_class and target_class and source_class != target_class:
        warnings.append(f"Device-Class unterschiedlich: {source_class!r} -> {target_class!r}")

    source_mean = source_metadata.get("has_mean")
    target_mean = target_metadata.get("has_mean")
    source_sum = source_metadata.get("has_sum")
    target_sum = target_metadata.get("has_sum")
    if target_metadata and source_mean is not None and target_mean is not None and source_mean != target_mean:
        warnings.append("Statistiktyp 'mean' ist unterschiedlich")
    if target_metadata and source_sum is not None and target_sum is not None and source_sum != target_sum:
        warnings.append("Statistiktyp 'sum' ist unterschiedlich")

    return not warnings, warnings


async def _async_statistics(hass: HomeAssistant, statistic_id: str) -> list[dict[str, Any]]:
    """Read all available hourly long-term statistics for one statistic id."""
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        _PREVIEW_START,
        None,
        {statistic_id},
        "hour",
        None,
        _PREVIEW_TYPES,
    )
    return list(result.get(statistic_id, []))


async def async_preview_statistics_migration(
    hass: HomeAssistant,
    source_entity_id: str,
    target_entity_id: str,
) -> dict[str, Any]:
    """Return a read-only preview of a possible statistics migration."""
    source_state = hass.states.get(source_entity_id)
    target_state = hass.states.get(target_entity_id)

    metadata = await get_instance(hass).async_add_executor_job(
        partial(get_metadata, hass, statistic_ids={source_entity_id, target_entity_id})
    )
    source_metadata = _metadata_payload(metadata.get(source_entity_id))
    target_metadata = _metadata_payload(metadata.get(target_entity_id))

    source_rows = await _async_statistics(hass, source_entity_id)
    target_rows = await _async_statistics(hass, target_entity_id)

    source_starts = {start for row in source_rows if (start := _row_start(row)) is not None}
    target_starts = {start for row in target_rows if (start := _row_start(row)) is not None}
    overlap = source_starts & target_starts
    importable = source_starts - target_starts

    compatible, warnings = _compatibility(
        source_state, target_state, source_metadata, target_metadata
    )
    if not source_metadata:
        warnings.append("Für die Quelle wurden keine Langzeitstatistik-Metadaten gefunden")
        compatible = False
    if not source_rows:
        warnings.append("Für die Quelle wurden keine stündlichen Langzeitstatistiken gefunden")
        compatible = False

    result = {
        "preview_only": True,
        "writes_performed": False,
        "source": {
            "entity_id": source_entity_id,
            "exists": source_state is not None,
            "metadata": source_metadata,
            "statistics_count": len(source_rows),
            "first_statistic": _iso_from_timestamp(min(source_starts) if source_starts else None),
            "last_statistic": _iso_from_timestamp(max(source_starts) if source_starts else None),
        },
        "target": {
            "entity_id": target_entity_id,
            "exists": target_state is not None,
            "metadata": target_metadata,
            "statistics_count": len(target_rows),
            "first_statistic": _iso_from_timestamp(min(target_starts) if target_starts else None),
            "last_statistic": _iso_from_timestamp(max(target_starts) if target_starts else None),
        },
        "comparison": {
            "compatible": compatible,
            "source_statistics": len(source_starts),
            "already_present_on_target": len(overlap),
            "importable_statistics": len(importable),
            "warnings": warnings,
        },
    }

    status = "kompatibel" if compatible else "Prüfung erforderlich"
    message = (
        f"Quelle: `{source_entity_id}`\n\n"
        f"Ziel: `{target_entity_id}`\n\n"
        f"Gefundene Quellwerte: **{len(source_starts)}**  \n"
        f"Davon bereits am Ziel vorhanden: **{len(overlap)}**  \n"
        f"Voraussichtlich importierbar: **{len(importable)}**  \n"
        f"Bewertung: **{status}**\n\n"
        "Dies ist nur eine Vorschau. Es wurden keine Recorder-Daten verändert."
    )
    persistent_notification.async_create(
        hass,
        message,
        title="NIBE Statistikmigration – Vorschau",
        notification_id="nibe_local_statistics_migration_preview",
    )
    return result
