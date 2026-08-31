"""Regression tests for NIBE Local REST core logic."""

from custom_components.nibe_local.entity import scaled_value, to_raw
from custom_components.nibe_local.number import metadata_limits
from custom_components.nibe_local.sensor import periodic_hot_water_date
from custom_components.nibe_local.switch import write_allowed_for_mode
from custom_components.nibe_local.const import (
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
)


def _point(raw: int, *, divisor: int = 10, decimal: int = 1) -> dict:
    return {
        "metadata": {"divisor": divisor, "decimal": decimal},
        "value": {"integerValue": raw, "stringValue": ""},
    }


def test_scaled_value_and_to_raw_roundtrip() -> None:
    point = _point(222)
    assert scaled_value(point) == 22.2
    assert to_raw(point, 22.2) == 222


def test_periodic_hot_water_date_epoch() -> None:
    assert periodic_hot_water_date(6093) == "07.09.2026"
    assert periodic_hot_water_date(6096) == "10.09.2026"
    assert periodic_hot_water_date(-1) is None


def test_mode_dependent_write_protection() -> None:
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, 0)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 0)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 1)
    assert write_allowed_for_mode(POINT_COOLING_ALLOWED, 1)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 2)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 2)
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, None)


def test_metadata_limits_reject_ambiguous_zero_range() -> None:
    point = {
        "metadata": {
            "divisor": 10,
            "minValue": 0,
            "maxValue": 0,
        }
    }
    assert metadata_limits(point, 22.2) is None
    assert metadata_limits(point, 0) == (0.0, 0.0)


def test_metadata_limits_scale_values() -> None:
    point = {
        "metadata": {
            "divisor": 10,
            "minValue": 100,
            "maxValue": 500,
        }
    }
    assert metadata_limits(point, 20.0) == (10.0, 50.0)
