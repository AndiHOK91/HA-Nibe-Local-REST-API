"""Tests for privacy-conscious diagnostics."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from custom_components.nibe_local.diagnostics import (
    _history_summary,
    _minute_buckets,
    async_get_config_entry_diagnostics,
)


def test_diagnostics_exclude_credentials_but_include_current_values() -> None:
    """Diagnostics keep secrets private while exporting useful point values."""
    coordinator = SimpleNamespace(
        data={
            "points": {
                "4": {
                    "title": "Current outdoor temperature (BT1)",
                    "value": {
                        "integerValue": 222,
                        "stringValue": "",
                        "isOk": True,
                    },
                    "metadata": {
                        "variableId": 4,
                        "description": "Current outdoor temperature (BT1)",
                        "unit": "°C",
                        "variableSize": "s16",
                        "isWritable": False,
                        "divisor": 10,
                        "decimal": 1,
                    },
                }
            },
            "device": {
                "product": {
                    "productName": "NIBE VVM S320 E EM 3x400V",
                    "softwareVersion": "4.12.8",
                    "serialNumber": "SECRET-SERIAL",
                }
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
        options={"entity_profile": "extended"},
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
    assert diagnostics["device"] == {
        "model": "NIBE VVM S320 E EM 3x400V",
        "software_version": "4.12.8",
    }
    assert diagnostics["points"]["enabled_point_ids"] == [4]
    assert diagnostics["points"]["current_values"]["4"] == {
        "raw_value": 222,
        "scaled_value": 22.2,
        "is_ok": True,
        "raw_value_is_sentinel": False,
        "value_valid": True,
        "title": "Current outdoor temperature (BT1)",
    }
    assert diagnostics["points"]["history_24h"] == {
        "available": False,
        "reason": "recorder_context_unavailable",
        "points": {},
    }
    assert diagnostics["notifications"]["active_alarm_count"] == 1


def test_minute_buckets_preserve_short_negative_spikes() -> None:
    """Minute aggregation must retain short-lived extrema."""
    states = [
        SimpleNamespace(
            state="20.0",
            last_updated=datetime(2026, 9, 5, 10, 0, 5, tzinfo=UTC),
        ),
        SimpleNamespace(
            state="-3276.8",
            last_updated=datetime(2026, 9, 5, 10, 0, 20, tzinfo=UTC),
        ),
        SimpleNamespace(
            state="21.5",
            last_updated=datetime(2026, 9, 5, 10, 0, 50, tzinfo=UTC),
        ),
        SimpleNamespace(
            state="22.0",
            last_updated=datetime(2026, 9, 5, 10, 1, 10, tzinfo=UTC),
        ),
    ]

    rows = _minute_buckets(states)
    summary = _history_summary(rows)

    assert len(rows) == 2
    assert rows[0]["min"] == -3276.8
    assert rows[0]["max"] == 21.5
    assert rows[0]["last"] == 21.5
    assert rows[0]["samples"] == 3
    assert summary["minute_count"] == 2
    assert summary["sample_count"] == 4
    assert summary["min"] == -3276.8
    assert summary["max"] == 22.0
    assert summary["first"] == 21.5
    assert summary["last"] == 22.0
