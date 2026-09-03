"""Regression tests for config-entry upgrade compatibility."""

import custom_components.nibe_local as integration
from custom_components.nibe_local.config_flow import NibeLocalConfigFlow


def test_config_entry_version_requires_migration_handler() -> None:
    """A schema version bump must never ship without a migration handler."""
    assert NibeLocalConfigFlow.VERSION >= 1
    if NibeLocalConfigFlow.VERSION > 1:
        assert hasattr(integration, "async_migrate_entry")
