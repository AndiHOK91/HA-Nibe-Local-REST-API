"""Tests for NIBE point 2022 current-system-status decoding."""

from custom_components.nibe_local.system_status import (
    CURRENT_STATUS_STATE_OPTIONS,
    active_status_bits,
    current_status_attributes,
    decode_current_status,
)


def test_current_status_reference_values_from_vvm_s320_diagnostics() -> None:
    """Decode real values observed with VVM S320 firmware 4.13.12."""
    # 0x00200001: only currently unknown/background bits 0 and 21.
    assert decode_current_status(2097153) == "standby"
    assert active_status_bits(2097153) == [0, 21]

    # 0x0021200D: compressor bit + hot-water demand + unknown/background bits.
    assert decode_current_status(2170893) == "hot_water"
    attrs = current_status_attributes(2170893)
    assert attrs["compressor_active"] is True
    assert attrs["internal_additional_heat_active"] is False
    assert attrs["hot_water_active"] is True
    assert attrs["unknown_active_bits"] == [0, 3, 16, 21]

    # 0x00212409: internal addition + hot-water demand, compressor not active.
    assert decode_current_status(2171913) == "hot_water"
    attrs = current_status_attributes(2171913)
    assert attrs["compressor_active"] is False
    assert attrs["internal_additional_heat_active"] is True
    assert attrs["hot_water_active"] is True
    assert attrs["unknown_active_bits"] == [0, 3, 16, 21]


def test_current_status_confirmed_demand_bits() -> None:
    assert decode_current_status(1 << 12) == "heating"
    assert decode_current_status(1 << 13) == "hot_water"
    assert decode_current_status(1 << 20) == "cooling"
    assert decode_current_status((1 << 12) | (1 << 13)) == "multiple_demands"


def test_current_status_component_only_activity_is_not_mislabelled() -> None:
    assert decode_current_status(1 << 2) == "active"
    assert decode_current_status(1 << 10) == "active"


def test_current_status_attributes_keep_raw_and_unknown_bits() -> None:
    value = 2170893
    attrs = current_status_attributes(value)

    assert attrs["raw_status"] == value
    assert attrs["hex_status"] == "0x0021200D"
    assert attrs["active_bits"] == [0, 2, 3, 13, 16, 21]
    assert attrs["unknown_active_bits"] == [0, 3, 16, 21]


def test_current_status_invalid_value_is_safe() -> None:
    assert decode_current_status("not-a-number") == "unknown"
    assert active_status_bits("not-a-number") == []
    assert current_status_attributes("not-a-number")["hex_status"] is None
    assert "unknown" in CURRENT_STATUS_STATE_OPTIONS
