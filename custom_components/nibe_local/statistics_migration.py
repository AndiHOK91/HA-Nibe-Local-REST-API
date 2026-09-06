"""Preview and guarded migration of historical statistics to NIBE REST entities."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import partial
import json
from pathlib import Path
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_metadata,
    statistics_during_period,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

_PREVIEW_START = datetime(1970, 1, 1, tzinfo=timezone.utc)
_PREVIEW_TYPES = {"min", "max", "mean", "state", "sum", "last_reset"}
_BACKUP_DIR = "nibe_local_backups"
_BACKUP_VERSION = 1


def _metadata_item(metadata: Any) -> Any:
    """Return the metadata object from get_metadata()'s tuple wrapper."""
    if not metadata:
        return None
    return metadata[1] if isinstance(metadata, tuple) and len(metadata) > 1 else metadata


def _metadata_payload(metadata: Any) -> dict[str, Any]:
    """Return a serializable, stable subset of recorder statistic metadata."""
    item = _metadata_item(metadata)
    if item is None:
        return {}

    def value(name: str) -> Any:
        raw = item.get(name) if isinstance(item, dict) else getattr(item, name, None)
        # IntEnum values such as StatisticMeanType are JSON serializable as ints,
        # but converting explicitly keeps backup files stable across HA versions.
        if hasattr(raw, "value") and isinstance(getattr(raw, "value"), int):
            return int(raw.value)
        return raw

    return {
        "unit_of_measurement": value("unit_of_measurement"),
        "unit_class": value("unit_class"),
        "has_mean": value("has_mean"),
        "mean_type": value("mean_type"),
        "has_sum": value("has_sum"),
        "name": value("name"),
        "source": value("source"),
    }


def _full_metadata(metadata: Any) -> dict[str, Any]:
    """Return recorder metadata suitable for async_import_statistics()."""
    item = _metadata_item(metadata)
    if item is None:
        return {}
    if isinstance(item, dict):
        return dict(item)
    fields = (
        "statistic_id",
        "source",
        "name",
        "unit_of_measurement",
        "unit_class",
        "has_mean",
        "mean_type",
        "has_sum",
    )
    return {field: getattr(item, field) for field in fields if hasattr(item, field)}


def _row_start(row: dict[str, Any]) -> float | None:
    value = row.get("start")
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_datetime(value: Any) -> datetime | None:
    """Convert recorder timestamps to timezone-aware datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
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

    source_mean = source_metadata.get("mean_type")
    target_mean = target_metadata.get("mean_type")
    if source_mean is None:
        source_mean = source_metadata.get("has_mean")
    if target_mean is None:
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


def _statistics_for_import(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert recorder query rows to the public statistics import shape."""
    allowed = {"mean", "min", "max", "state", "sum"}
    converted: list[dict[str, Any]] = []
    for row in rows:
        start = _as_datetime(row.get("start"))
        if start is None:
            continue
        item: dict[str, Any] = {"start": start}
        for key in allowed:
            value = row.get(key)
            if isinstance(value, (int, float)):
                item[key] = value
        if "last_reset" in row:
            item["last_reset"] = _as_datetime(row.get("last_reset"))
        converted.append(item)
    return converted


def _json_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a statistics row to a stable JSON representation."""
    result: dict[str, Any] = {}
    for key in ("start", "mean", "min", "max", "last_reset", "state", "sum"):
        if key not in row:
            continue
        value = row[key]
        if key in {"start", "last_reset"}:
            dt_value = _as_datetime(value)
            result[key] = dt_value.isoformat() if dt_value else None
        elif value is None or isinstance(value, (int, float, str, bool)):
            result[key] = value
    return result


def _write_backup(
    backup_path: Path,
    *,
    source_entity_id: str,
    target_entity_id: str,
    source_metadata: dict[str, Any],
    target_metadata: dict[str, Any],
    target_rows: list[dict[str, Any]],
    import_starts: set[float],
) -> None:
    """Write an atomic pre-import backup snapshot."""
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": _BACKUP_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "source_metadata": source_metadata,
        "target_metadata": target_metadata,
        "target_statistics": [_json_row(row) for row in target_rows],
        "planned_import_starts": [
            _iso_from_timestamp(value) for value in sorted(import_starts)
        ],
    }
    temporary = backup_path.with_suffix(backup_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(backup_path)


def _backup_path(hass: HomeAssistant, target_entity_id: str) -> Path:
    safe_target = target_entity_id.replace(".", "_").replace(":", "_")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(hass.config.path(_BACKUP_DIR, f"{safe_target}_{stamp}.json"))


def _import_metadata(
    source_raw_metadata: Any,
    target_raw_metadata: Any,
    *,
    target_entity_id: str,
    target_state: Any,
) -> dict[str, Any]:
    """Build target metadata while preserving the recorder's statistic semantics."""
    metadata = _full_metadata(target_raw_metadata) or _full_metadata(source_raw_metadata)
    if not metadata:
        return {}
    metadata["statistic_id"] = target_entity_id
    metadata["source"] = "recorder"
    if target_state is not None:
        metadata["name"] = target_state.attributes.get(ATTR_FRIENDLY_NAME)
        target_unit = target_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if target_unit is not None:
            metadata["unit_of_measurement"] = target_unit
    # Newer HA versions require mean_type/unit_class. When source metadata comes
    # from an older schema these keys may legitimately not exist, so do not invent
    # converter metadata that the running HA version does not know about.
    return metadata


async def _async_migration_data(
    hass: HomeAssistant,
    source_entity_id: str,
    target_entity_id: str,
) -> dict[str, Any]:
    """Collect source/target states, metadata and statistics once."""
    source_state = hass.states.get(source_entity_id)
    target_state = hass.states.get(target_entity_id)
    raw_metadata = await get_instance(hass).async_add_executor_job(
        partial(get_metadata, hass, statistic_ids={source_entity_id, target_entity_id})
    )
    source_raw_metadata = raw_metadata.get(source_entity_id)
    target_raw_metadata = raw_metadata.get(target_entity_id)
    source_metadata = _metadata_payload(source_raw_metadata)
    target_metadata = _metadata_payload(target_raw_metadata)
    source_rows = await _async_statistics(hass, source_entity_id)
    target_rows = await _async_statistics(hass, target_entity_id)
    return {
        "source_state": source_state,
        "target_state": target_state,
        "source_raw_metadata": source_raw_metadata,
        "target_raw_metadata": target_raw_metadata,
        "source_metadata": source_metadata,
        "target_metadata": target_metadata,
        "source_rows": source_rows,
        "target_rows": target_rows,
    }


async def async_preview_statistics_migration(
    hass: HomeAssistant,
    source_entity_id: str,
    target_entity_id: str,
) -> dict[str, Any]:
    """Return a read-only preview of a possible statistics migration."""
    data = await _async_migration_data(hass, source_entity_id, target_entity_id)
    source_state = data["source_state"]
    target_state = data["target_state"]
    source_metadata = data["source_metadata"]
    target_metadata = data["target_metadata"]
    source_rows = data["source_rows"]
    target_rows = data["target_rows"]

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


async def async_import_statistics_migration(
    hass: HomeAssistant,
    source_entity_id: str,
    target_entity_id: str,
    *,
    create_backup: bool = True,
) -> dict[str, Any]:
    """Import missing hourly source statistics into a NIBE REST target entity."""
    data = await _async_migration_data(hass, source_entity_id, target_entity_id)
    source_state = data["source_state"]
    target_state = data["target_state"]
    source_metadata = data["source_metadata"]
    target_metadata = data["target_metadata"]
    source_rows = data["source_rows"]
    target_rows = data["target_rows"]

    compatible, warnings = _compatibility(
        source_state, target_state, source_metadata, target_metadata
    )
    if not source_metadata or not source_rows:
        compatible = False
        if not source_metadata:
            warnings.append("Keine Langzeitstatistik-Metadaten für die Quelle gefunden")
        if not source_rows:
            warnings.append("Keine stündlichen Langzeitstatistiken für die Quelle gefunden")
    if not compatible:
        raise ServiceValidationError(
            "Statistikmigration abgebrochen: " + "; ".join(warnings)
        )

    target_starts = {start for row in target_rows if (start := _row_start(row)) is not None}
    import_rows = [
        row
        for row in source_rows
        if (start := _row_start(row)) is not None and start not in target_starts
    ]
    import_starts = {
        start for row in import_rows if (start := _row_start(row)) is not None
    }

    metadata = _import_metadata(
        data["source_raw_metadata"],
        data["target_raw_metadata"],
        target_entity_id=target_entity_id,
        target_state=target_state,
    )
    if not metadata:
        raise ServiceValidationError(
            "Statistikmigration abgebrochen: Import-Metadaten konnten nicht erzeugt werden"
        )

    backup_file: str | None = None
    if create_backup:
        path = _backup_path(hass, target_entity_id)
        try:
            await hass.async_add_executor_job(
                partial(
                    _write_backup,
                    path,
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    source_metadata=source_metadata,
                    target_metadata=target_metadata,
                    target_rows=target_rows,
                    import_starts=import_starts,
                )
            )
        except OSError as err:
            raise ServiceValidationError(
                f"Statistikmigration abgebrochen: Backup konnte nicht erstellt werden: {err}"
            ) from err
        backup_file = str(path)

    converted_rows = _statistics_for_import(import_rows)
    if converted_rows:
        async_import_statistics(hass, metadata, converted_rows)

    message = (
        f"Quelle: `{source_entity_id}`\n\n"
        f"Ziel: `{target_entity_id}`\n\n"
        f"Importiert: **{len(converted_rows)}** Stundenwerte  \n"
        f"Bereits vorhanden und übersprungen: **{len(source_rows) - len(import_rows)}**  \n"
        f"Backup: **{'erstellt' if create_backup else 'deaktiviert'}**"
    )
    if backup_file:
        message += f"  \nSicherungsdatei: `{backup_file}`"
    persistent_notification.async_create(
        hass,
        message,
        title="NIBE Statistikmigration – Import",
        notification_id="nibe_local_statistics_migration_import",
    )

    return {
        "preview_only": False,
        "writes_performed": bool(converted_rows),
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "source_statistics": len(source_rows),
        "imported_statistics": len(converted_rows),
        "already_present_on_target": len(source_rows) - len(import_rows),
        "backup": {
            "enabled": create_backup,
            "created": backup_file is not None,
            "path": backup_file,
            "target_statistics_saved": len(target_rows) if create_backup else 0,
        },
    }
