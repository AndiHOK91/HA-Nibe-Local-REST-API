"""Tests for privacy-conscious diagnostics."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from custom_components.nibe_local.diagnostics import (
    ALLOWED_HISTORY_DAYS,
    DEFAULT_HISTORY_DAYS,
    _history_summary,
    _minute_buckets,
    async_get_config_entry_diagnostics,
    async_get_extended_config_entry_diagnostics,
)


def _fixture_entry() -> SimpleNamespace:
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
    return SimpleNamespace(
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


def _assert_secrets_absent(diagnostics: dict) -> None:
    rendered = repr(diagnostics)
    assert "192.0.2.10" not in rendered
    assert "admin" not in rendered
    assert "super-secret" not in rendered
    assert "top-secret" not in rendered
    assert "SECRET-SERIAL" not in rendered
    assert "private alarm text" not in rendered


def test_standard_diagnostics_exclude_values_history_and_credentials() -> None:
    """Normal HA diagnostics are privacy-first and contain no live/home history."""
    diagnostics = asyncio.run(async_get_config_entry_diagnostics(None, _fixture_entry()))

    _assert_secrets_absent(diagnostics)
    assert diagnostics["diagnostic_mode"] == "standard"
    assert diagnostics["privacy"] == {
        "contains_current_values": False,
        "contains_history": False,
    }
    assert diagnostics["device"] == {
        "model": "NIBE VVM S320 E EM 3x400V",
        "software_version": "4.12.8",
    }
    assert diagnostics["points"]["enabled_point_ids"] == [4]
    assert "current_values" not in diagnostics["points"]
    assert "history" not in diagnostics["points"]
    assert diagnostics["notifications"]["active_alarm_count"] == 1


def test_extended_diagnostics_default_to_one_day() -> None:
    """Extended diagnostics default to a one-day recorder history."""
    diagnostics = asyncio.run(
        async_get_extended_config_entry_diagnostics(None, _fixture_entry())
    )

    _assert_secrets_absent(diagnostics)
    assert DEFAULT_HISTORY_DAYS == 1
    assert ALLOWED_HISTORY_DAYS == (1, 3, 5, 7)
    assert diagnostics["diagnostic_mode"] == "extended"
    assert diagnostics["history_days"] == 1
    assert diagnostics["privacy"]["contains_current_values"] is True
    assert diagnostics["privacy"]["contains_history"] is True
    assert "up to 1 day" in diagnostics["privacy"]["warning"]
    assert diagnostics["points"]["current_values"]["4"] == {
        "raw_value": 222,
        "scaled_value": 22.2,
        "is_ok": True,
        "raw_value_is_sentinel": False,
        "value_valid": True,
        "title": "Current outdoor temperature (BT1)",
    }
    assert diagnostics["points"]["history"] == {
        "available": False,
        "reason": "recorder_context_unavailable",
        "days": 1,
        "hours": 24,
        "points": {},
    }


def test_extended_diagnostics_accept_supported_history_ranges() -> None:
    """The explicit export supports only 1, 3, 5 or 7 days."""
    for history_days in ALLOWED_HISTORY_DAYS:
        diagnostics = asyncio.run(
            async_get_extended_config_entry_diagnostics(
                None, _fixture_entry(), history_days=history_days
            )
        )
        assert diagnostics["history_days"] == history_days
        assert diagnostics["points"]["history"]["days"] == history_days
        assert diagnostics["points"]["history"]["hours"] == history_days * 24


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
