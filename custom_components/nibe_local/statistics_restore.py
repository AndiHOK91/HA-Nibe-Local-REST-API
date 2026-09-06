"""Read-only inspection of NIBE statistics migration backups."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import partial
import json
from pathlib import Path
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

_BACKUP_DIR = "nibe_local_backups"
_SUPPORTED_BACKUP_VERSION = 1
_PREVIEW_START = datetime(1970, 1, 1, tzinfo=timezone.utc)
_PREVIEW_TYPES = {"min", "max", "mean", "state", "sum", "last_reset"}


def _backup_directory(hass: HomeAssistant) -> Path:
    """Return the integration-owned backup directory."""
    return Path(hass.config.path(_BACKUP_DIR))


def _safe_backup_path(hass: HomeAssistant, backup_file: str) -> Path:
    """Resolve one backup filename without permitting path traversal."""
    candidate = Path(backup_file)
    if candidate.name != backup_file or candidate.suffix.lower() != ".json":
        raise ServiceValidationError("Ungültiger Backup-Dateiname")
    return _backup_directory(hass) / candidate.name


def _load_backup(path: Path) -> dict[str, Any]:
    """Load and validate one integration-owned statistics backup."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ServiceValidationError("Backup-Datei wurde nicht gefunden") from err
    except (OSError, json.JSONDecodeError) as err:
        raise ServiceValidationError(f"Backup-Datei konnte nicht gelesen werden: {err}") from err

    if not isinstance(payload, dict):
        raise ServiceValidationError("Backup-Datei hat ein ungültiges Format")
    if payload.get("version") != _SUPPORTED_BACKUP_VERSION:
        raise ServiceValidationError("Backup-Version wird nicht unterstützt")
    if not isinstance(payload.get("target_entity_id"), str):
        raise ServiceValidationError("Backup enthält keinen gültigen Zielsensor")
    if not isinstance(payload.get("source_entity_id"), str):
        raise ServiceValidationError("Backup enthält keinen gültigen Quellsensor")
    if not isinstance(payload.get("target_statistics"), list):
        raise ServiceValidationError("Backup enthält keine gültige Zielstatistik")
    if not isinstance(payload.get("planned_import_starts"), list):
        raise ServiceValidationError("Backup enthält keine gültige Importplanung")
    return payload


def _parse_iso(value: Any) -> float | None:
    """Parse one backup ISO timestamp to a UTC timestamp."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _backup_summary(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Return a compact summary suitable for an action response."""
    planned = payload.get("planned_import_starts", [])
    target_rows = payload.get("target_statistics", [])
    return {
        "file": path.name,
        "created_at": payload.get("created_at"),
        "source_entity_id": payload.get("source_entity_id"),
        "target_entity_id": payload.get("target_entity_id"),
        "target_statistics_saved": len(target_rows),
        "planned_import_statistics": len(planned),
    }


def _list_backups(directory: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Read all valid backups, newest first, while reporting damaged files."""
    if not directory.exists():
        return [], []

    backups: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    for path in directory.glob("*.json"):
        try:
            payload = _load_backup(path)
        except ServiceValidationError as err:
            invalid.append({"file": path.name, "error": str(err)})
            continue
        backups.append(_backup_summary(path, payload))

    backups.sort(
        key=lambda item: (str(item.get("created_at") or ""), str(item.get("file") or "")),
        reverse=True,
    )
    invalid.sort(key=lambda item: item["file"], reverse=True)
    return backups, invalid


async def _async_statistics(hass: HomeAssistant, statistic_id: str) -> list[dict[str, Any]]:
    """Read all available hourly long-term statistics for one target sensor."""
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


def _row_start(row: dict[str, Any]) -> float | None:
    """Return one recorder row start as a timestamp."""
    value = row.get("start")
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    return None


async def async_list_statistics_backups(hass: HomeAssistant) -> dict[str, Any]:
    """Return all available statistics backups without modifying anything."""
    backups, invalid = await hass.async_add_executor_job(
        partial(_list_backups, _backup_directory(hass))
    )
    return {
        "preview_only": True,
        "writes_performed": False,
        "backup_count": len(backups),
        "backups": backups,
        "invalid_backups": invalid,
    }


async def async_preview_statistics_restore(
    hass: HomeAssistant,
    backup_file: str,
) -> dict[str, Any]:
    """Compare one backup with the current target statistics, read-only."""
    path = _safe_backup_path(hass, backup_file)
    payload = await hass.async_add_executor_job(partial(_load_backup, path))
    target_entity_id = payload["target_entity_id"]
    current_rows = await _async_statistics(hass, target_entity_id)

    original_starts = {
        start
        for row in payload["target_statistics"]
        if (start := _parse_iso(row.get("start") if isinstance(row, dict) else None)) is not None
    }
    planned_starts = {
        start for value in payload["planned_import_starts"] if (start := _parse_iso(value)) is not None
    }
    current_starts = {
        start for row in current_rows if (start := _row_start(row)) is not None
    }

    planned_currently_present = planned_starts & current_starts
    original_currently_missing = original_starts - current_starts
    current_not_in_original = current_starts - original_starts
    current_after_backup_not_planned = current_not_in_original - planned_starts

    result = {
        "preview_only": True,
        "writes_performed": False,
        "restore_available": False,
        "backup": _backup_summary(path, payload),
        "comparison": {
            "current_target_statistics": len(current_starts),
            "original_target_statistics": len(original_starts),
            "planned_import_statistics": len(planned_starts),
            "planned_import_values_currently_present": len(planned_currently_present),
            "original_values_currently_missing": len(original_currently_missing),
            "current_values_not_in_original_backup": len(current_not_in_original),
            "newer_unrelated_values_at_risk": len(current_after_backup_not_planned),
        },
        "safety": {
            "can_restore_safely_with_public_recorder_api": False,
            "reason": (
                "Home Assistant bietet derzeit keine saubere öffentliche Recorder-API, "
                "um nur einzelne importierte Stundenwerte gezielt zu löschen."
            ),
        },
    }

    persistent_notification.async_create(
        hass,
        (
            f"Backup: `{path.name}`\n\n"
            f"Ziel: `{target_entity_id}`\n\n"
            f"Vorher gesicherte Zielwerte: **{len(original_starts)}**  \n"
            f"Damals geplante Importwerte: **{len(planned_starts)}**  \n"
            f"Davon aktuell vorhanden: **{len(planned_currently_present)}**  \n"
            f"Neuere, nicht zum damaligen Import gehörende Werte: "
            f"**{len(current_after_backup_not_planned)}**\n\n"
            "Dies ist nur eine Wiederherstellungs-Vorschau. Es wurden keine "
            "Recorder-Daten verändert."
        ),
        title="NIBE Statistikmigration – Restore-Vorschau",
        notification_id="nibe_local_statistics_restore_preview",
    )
    return result
