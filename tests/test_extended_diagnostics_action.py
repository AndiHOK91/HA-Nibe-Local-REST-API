"""Regression tests for the explicit extended diagnostics action."""

import pytest
import voluptuous as vol

from custom_components.nibe_local import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_HISTORY_DAYS,
    SERVICE_EXPORT_EXTENDED_DIAGNOSTICS,
    SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA,
)


def test_extended_diagnostics_action_contract() -> None:
    """The extended export stays explicit and defaults to one day."""
    assert SERVICE_EXPORT_EXTENDED_DIAGNOSTICS == "export_extended_diagnostics"
    validated = SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA(
        {ATTR_CONFIG_ENTRY_ID: "test-entry"}
    )
    assert validated[ATTR_CONFIG_ENTRY_ID] == "test-entry"
    assert validated[ATTR_HISTORY_DAYS] == 1


def test_extended_diagnostics_action_accepts_only_supported_days() -> None:
    """The service accepts exactly 1, 3, 5 and 7 days."""
    for history_days in (1, 3, 5, 7):
        validated = SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA(
            {
                ATTR_CONFIG_ENTRY_ID: "test-entry",
                ATTR_HISTORY_DAYS: history_days,
            }
        )
        assert validated[ATTR_HISTORY_DAYS] == history_days

    with pytest.raises(vol.Invalid):
        SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA(
            {ATTR_CONFIG_ENTRY_ID: "test-entry", ATTR_HISTORY_DAYS: 2}
        )
