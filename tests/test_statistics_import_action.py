"""Regression tests for the guarded statistics migration import action."""

from datetime import datetime, timezone

from custom_components.nibe_local import (
    ATTR_CREATE_BACKUP,
    ATTR_SOURCE_ENTITY_ID,
    ATTR_TARGET_ENTITY_ID,
    SERVICE_IMPORT_STATISTICS_MIGRATION,
    SERVICE_IMPORT_STATISTICS_MIGRATION_SCHEMA,
)
from custom_components.nibe_local.statistics_migration import (
    _json_row,
    _statistics_for_import,
)


def test_import_action_enables_backup_by_default() -> None:
    """A statistics import must default to creating a backup."""
    assert SERVICE_IMPORT_STATISTICS_MIGRATION == "import_statistics_migration"
    validated = SERVICE_IMPORT_STATISTICS_MIGRATION_SCHEMA(
        {
            ATTR_SOURCE_ENTITY_ID: "sensor.old_modbus",
            ATTR_TARGET_ENTITY_ID: "sensor.nibe_api_target",
        }
    )
    assert validated[ATTR_CREATE_BACKUP] is True


def test_import_action_allows_explicit_backup_opt_out() -> None:
    """Users may deliberately disable the pre-import backup."""
    validated = SERVICE_IMPORT_STATISTICS_MIGRATION_SCHEMA(
        {
            ATTR_SOURCE_ENTITY_ID: "sensor.old_modbus",
            ATTR_TARGET_ENTITY_ID: "sensor.nibe_api_target",
            ATTR_CREATE_BACKUP: False,
        }
    )
    assert validated[ATTR_CREATE_BACKUP] is False


def test_statistics_import_shape_uses_datetimes_and_known_fields_only() -> None:
    """Recorder query rows are converted to the public import data shape."""
    start = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc).timestamp()
    rows = [
        {
            "start": start,
            "end": start + 3600,
            "mean": 12.5,
            "min": 10.0,
            "max": 14.0,
            "state": None,
            "sum": None,
            "change": 1.0,
        }
    ]
    converted = _statistics_for_import(rows)
    assert len(converted) == 1
    assert converted[0]["start"] == datetime.fromtimestamp(start, tz=timezone.utc)
    assert converted[0]["mean"] == 12.5
    assert "end" not in converted[0]
    assert "change" not in converted[0]
    assert "state" not in converted[0]


def test_backup_row_is_json_serializable() -> None:
    """Backup snapshots represent recorder timestamps as ISO strings."""
    start = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    payload = _json_row({"start": start, "mean": 12.5, "last_reset": None})
    assert payload["start"] == "2026-09-01T12:00:00+00:00"
    assert payload["mean"] == 12.5
    assert payload["last_reset"] is None
