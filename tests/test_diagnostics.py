"""Tests for privacy-conscious diagnostics."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from custom_components.nibe_local.diagnostics import async_get_config_entry_diagnostics


def test_diagnostics_exclude_credentials_and_current_values() -> None:
    """Diagnostics must be useful without exposing credentials or point values."""
    coordinator = SimpleNamespace(
        data={
            "points": {
                "4": {
                    "value": 222,
                    "integerValue": 222,
                    "metadata": {
                        "variableId": 4,
                        "description": "Current outdoor temperature (BT1)",
                        "unit": "°C",
                        "isWritable": False,
                    },
                }
            },
            "device": {
                "model": "VVM S320",
                "serialNumber": "SECRET-SERIAL",
            },
            "notifications": {"alarms": [{"description": "private alarm text"}]},
        },
        enabled_point_ids={4},
        last_update_success=True,
        bulk_fallback_active=False,
        last_successful_poll=datetime(2026, 9, 3, tzinfo=UTC),
        last_connection_error=None,
    )
    entry = SimpleNamespace(
        data={
            "host": "192.0.2.10",
            "username": "admin",
            "password": "super-secret",
            "auth_header": "Bearer top-secret",
            "port": 8443,
        },
        options={"entity_profile": "minimal"},
        runtime_data=coordinator,
    )

    diagnostics = asyncio.run(async_get_config_entry_diagnostics(None, entry))
    rendered = repr(diagnostics)

    assert "192.0.2.10" not in rendered
    assert "admin" not in rendered
    assert "super-secret" not in rendered
    assert "top-secret" not in rendered
    assert "SECRET-SERIAL" not in rendered
    assert "private alarm text" not in rendered
    assert "222" not in rendered
    assert diagnostics["device"] == {"model": "VVM S320"}
    assert diagnostics["points"]["enabled_point_ids"] == [4]
    assert diagnostics["notifications"]["active_alarm_count"] == 1
