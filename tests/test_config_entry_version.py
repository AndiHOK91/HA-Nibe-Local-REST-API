"""Regression test for config-entry upgrade compatibility."""

from custom_components.nibe_local.config_flow import NibeLocalConfigFlow


def test_config_entry_version_stays_compatible_with_pre_090_entries() -> None:
    """0.9.x adds optional fields only and must not require a migration handler."""
    assert NibeLocalConfigFlow.VERSION == 1
