"""Regression tests for the explicit extended diagnostics action."""

import json
from types import SimpleNamespace

import pytest

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

    # Home Assistant may expose Voluptuous directly or through Probatio depending
    # on the supported core version. Assert the validation behavior, not the
    # implementation-specific exception class.
    with pytest.raises(Exception, match="value must be one of"):
        SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA(
            {ATTR_CONFIG_ENTRY_ID: "test-entry", ATTR_HISTORY_DAYS: 2}
        )


def test_extended_diagnostics_json_download_is_utf8_and_pretty() -> None:
    """The downloadable payload is valid, readable UTF-8 JSON."""
    from custom_components.nibe_local.diagnostics_download import _serialize_diagnostics

    payload = {"device": {"name": "Wärmepumpe"}, "value": 12.5}
    content = _serialize_diagnostics(payload)

    assert content.endswith(b"\n")
    assert json.loads(content.decode("utf-8")) == payload
    assert "Wärmepumpe" in content.decode("utf-8")


def test_extended_diagnostics_download_metadata_uses_signed_path(monkeypatch) -> None:
    """The service helper stores the JSON in memory and returns a signed path."""
    from custom_components.nibe_local import diagnostics_download

    hass = SimpleNamespace(data={})
    entry = SimpleNamespace(title="VVM S320")
    payload = {"diagnostic_mode": "extended", "history_days": 1}

    monkeypatch.setattr(
        diagnostics_download,
        "async_sign_path",
        lambda _hass, path, _expiry: f"{path}?authSig=test",
    )
    monkeypatch.setattr(
        diagnostics_download.dt_util,
        "utcnow",
        lambda: SimpleNamespace(strftime=lambda _fmt: "20260918T150000Z"),
    )

    result = diagnostics_download.create_extended_diagnostics_download(
        hass,
        entry,
        payload,
    )

    assert result["filename"] == (
        "nibe_extended_diagnostics_vvm_s320_20260918T150000Z.json"
    )
    assert result["expires_in_seconds"] == 600
    assert result["url"].startswith("/api/nibe_local/extended_diagnostics/")
    assert result["url"].endswith("?authSig=test")

    stored = next(iter(hass.data[diagnostics_download.DATA_DIAGNOSTICS_DOWNLOADS].values()))
    assert json.loads(stored["content"].decode("utf-8")) == payload
