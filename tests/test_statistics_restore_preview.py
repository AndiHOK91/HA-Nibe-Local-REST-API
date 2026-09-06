"""Regression tests for read-only statistics backup restore previews."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.nibe_local.statistics_restore import (
    _backup_summary,
    _list_backups,
    _load_backup,
    _restore_safety,
    _safe_backup_path,
)


def _hass_for_path(tmp_path: Path):
    """Return the minimal Home Assistant path interface used by backup helpers."""
    return SimpleNamespace(
        config=SimpleNamespace(path=lambda *parts: str(tmp_path.joinpath(*parts)))
    )


def _payload(created_at: str, target: str = "sensor.nibe_api_bt1") -> dict:
    return {
        "version": 1,
        "created_at": created_at,
        "source_entity_id": "sensor.nibe_modbus_bt1",
        "target_entity_id": target,
        "source_metadata": {"unit_of_measurement": "°C"},
        "target_metadata": {"unit_of_measurement": "°C"},
        "target_statistics": [{"start": "2026-09-01T00:00:00+00:00", "mean": 10.0}],
        "planned_import_starts": ["2026-08-31T23:00:00+00:00"],
    }


def test_backup_filename_cannot_escape_integration_directory(tmp_path: Path) -> None:
    hass = _hass_for_path(tmp_path)
    with pytest.raises(Exception):
        _safe_backup_path(hass, "../configuration.yaml")
    with pytest.raises(Exception):
        _safe_backup_path(hass, "/tmp/backup.json")

    safe = _safe_backup_path(hass, "sensor_nibe_api_bt1_20260906T120000Z.json")
    assert safe.parent == tmp_path / "nibe_local_backups"


def test_backup_listing_keeps_older_backups_and_sorts_newest_first(tmp_path: Path) -> None:
    backup_dir = tmp_path / "nibe_local_backups"
    backup_dir.mkdir()
    older = backup_dir / "older.json"
    newer = backup_dir / "newer.json"
    older.write_text(json.dumps(_payload("2026-09-05T10:00:00+00:00")), encoding="utf-8")
    newer.write_text(json.dumps(_payload("2026-09-06T10:00:00+00:00")), encoding="utf-8")

    backups, invalid = _list_backups(backup_dir)

    assert invalid == []
    assert [item["file"] for item in backups] == ["newer.json", "older.json"]
    assert backups[1]["target_statistics_saved"] == 1
    assert backups[1]["planned_import_statistics"] == 1


def test_damaged_backup_is_reported_without_hiding_valid_backups(tmp_path: Path) -> None:
    backup_dir = tmp_path / "nibe_local_backups"
    backup_dir.mkdir()
    (backup_dir / "valid.json").write_text(
        json.dumps(_payload("2026-09-06T10:00:00+00:00")), encoding="utf-8"
    )
    (backup_dir / "broken.json").write_text("{not-json", encoding="utf-8")

    backups, invalid = _list_backups(backup_dir)

    assert [item["file"] for item in backups] == ["valid.json"]
    assert invalid[0]["file"] == "broken.json"


def test_backup_summary_contains_selection_information(tmp_path: Path) -> None:
    path = tmp_path / "backup.json"
    payload = _payload("2026-09-06T10:00:00+00:00")
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = _load_backup(path)
    summary = _backup_summary(path, loaded)

    assert summary["file"] == "backup.json"
    assert summary["created_at"] == "2026-09-06T10:00:00+00:00"
    assert summary["source_entity_id"] == "sensor.nibe_modbus_bt1"
    assert summary["target_entity_id"] == "sensor.nibe_api_bt1"


def test_restore_safety_is_fail_closed_without_selective_delete_api() -> None:
    safety = _restore_safety(
        public_selective_delete_available=False,
        invalid_original_timestamps=0,
        invalid_planned_timestamps=0,
        original_values_currently_missing=0,
        newer_unrelated_values_at_risk=0,
    )

    assert safety["safe_to_restore"] is False
    assert safety["blocked"] is True
    assert safety["policy"] == "fail_closed"
    assert any("Recorder-API" in reason for reason in safety["blocking_reasons"])


def test_restore_safety_explains_all_detected_data_risks() -> None:
    safety = _restore_safety(
        public_selective_delete_available=True,
        invalid_original_timestamps=2,
        invalid_planned_timestamps=3,
        original_values_currently_missing=4,
        newer_unrelated_values_at_risk=5,
    )

    assert safety["safe_to_restore"] is False
    assert len(safety["blocking_reasons"]) == 4
    combined = " ".join(safety["blocking_reasons"])
    assert "2 Zeitstempel" in combined
    assert "3 Zeitstempel" in combined
    assert "4 bereits vor der Migration" in combined
    assert "5 neuere" in combined


def test_restore_safety_can_be_true_only_when_no_blocker_exists() -> None:
    safety = _restore_safety(
        public_selective_delete_available=True,
        invalid_original_timestamps=0,
        invalid_planned_timestamps=0,
        original_values_currently_missing=0,
        newer_unrelated_values_at_risk=0,
    )

    assert safety["safe_to_restore"] is True
    assert safety["blocked"] is False
    assert safety["blocking_reasons"] == []
