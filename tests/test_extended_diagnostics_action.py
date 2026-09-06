"""Regression tests for the explicit extended diagnostics action."""

from custom_components.nibe_local import (
    ATTR_CONFIG_ENTRY_ID,
    SERVICE_EXPORT_EXTENDED_DIAGNOSTICS,
    SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA,
)


def test_extended_diagnostics_action_contract() -> None:
    """The extended export remains explicit and requires a config entry."""
    assert SERVICE_EXPORT_EXTENDED_DIAGNOSTICS == "export_extended_diagnostics"
    validated = SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA(
        {ATTR_CONFIG_ENTRY_ID: "test-entry"}
    )
    assert validated[ATTR_CONFIG_ENTRY_ID] == "test-entry"
