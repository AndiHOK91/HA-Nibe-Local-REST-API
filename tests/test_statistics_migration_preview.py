"""Regression tests for the read-only statistics migration preview."""

import inspect

from custom_components.nibe_local import (
    SERVICE_PREVIEW_STATISTICS_MIGRATION,
    SERVICE_PREVIEW_STATISTICS_MIGRATION_SCHEMA,
)
from custom_components.nibe_local import statistics_migration


def test_preview_action_schema_requires_source_and_target() -> None:
    validated = SERVICE_PREVIEW_STATISTICS_MIGRATION_SCHEMA(
        {
            "source_entity_id": "sensor.old_modbus_bt1",
            "target_entity_id": "sensor.nibe_api_outdoor_temperature_bt1",
        }
    )
    assert validated["source_entity_id"] == "sensor.old_modbus_bt1"
    assert validated["target_entity_id"] == "sensor.nibe_api_outdoor_temperature_bt1"
    assert SERVICE_PREVIEW_STATISTICS_MIGRATION == "preview_statistics_migration"


def test_preview_action_is_strictly_read_only() -> None:
    source = inspect.getsource(statistics_migration.async_preview_statistics_migration)
    assert "async_import_statistics" not in source
    assert "session_scope" not in source
    assert "INSERT" not in source
    assert "UPDATE " not in source
    assert '"writes_performed": False' in source
    assert '"preview_only": True' in source


def test_preview_module_uses_supported_statistics_read_apis() -> None:
    source = inspect.getsource(statistics_migration)
    assert "statistics_during_period" in source
    assert "get_metadata" in source


def test_preview_creates_persistent_summary_notification() -> None:
    source = inspect.getsource(statistics_migration.async_preview_statistics_migration)
    assert "persistent_notification.async_create" in source
    assert "Dies ist nur eine Vorschau" in source
    assert "keine Recorder-Daten verändert" in source
