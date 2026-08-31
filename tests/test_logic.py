"""Regression tests for NIBE Local REST core logic."""

from datetime import time

from custom_components.nibe_local.api import NibeLocalApi
from custom_components.nibe_local.const import (
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
    POINT_OPERATING_MODE_SETTING,
    POINT_VENTILATION_MODE,
)
from custom_components.nibe_local.entity import scaled_value, to_raw
from custom_components.nibe_local.number import metadata_limits
from custom_components.nibe_local.select import NibePointSelect
from custom_components.nibe_local.sensor import (
    OPERATING_MODE_MAP,
    periodic_hot_water_date,
)
from custom_components.nibe_local.switch import write_allowed_for_mode
from custom_components.nibe_local.time import seconds_from_time, time_from_seconds


def _point(raw: int, *, divisor: int = 10, decimal: int = 1) -> dict:
    return {
        "metadata": {"divisor": divisor, "decimal": decimal},
        "value": {"integerValue": raw, "stringValue": ""},
    }


def test_scaled_value_and_to_raw_roundtrip() -> None:
    point = _point(222)
    assert scaled_value(point) == 22.2
    assert to_raw(point, 22.2) == 222


def test_normalize_points_accepts_single_point_and_wrappers() -> None:
    point = {
        "metadata": {"variableId": 4},
        "value": {"integerValue": 222, "stringValue": ""},
    }
    assert NibeLocalApi._normalize_points(point) == {"4": point}
    assert NibeLocalApi._normalize_points({"points": [point]}) == {"4": point}
    assert NibeLocalApi._normalize_points({"data": {"4": point}}) == {"4": point}


def test_normalize_points_accepts_mapping_without_variable_id() -> None:
    point = {"value": {"integerValue": 1, "stringValue": ""}}
    assert NibeLocalApi._normalize_points({"3920": point}) == {"3920": point}


def test_periodic_hot_water_date_epoch() -> None:
    assert periodic_hot_water_date(6093) == "07.09.2026"
    assert periodic_hot_water_date(6096) == "10.09.2026"
    assert periodic_hot_water_date(-1) is None
    assert periodic_hot_water_date("ungueltig") is None


def test_operating_mode_labels_match_select() -> None:
    assert OPERATING_MODE_MAP == {
        0: "Auto",
        1: "Manuell",
        2: "Nur Zusatzheizung",
    }
    assert NibePointSelect.ENUM_LABELS[POINT_OPERATING_MODE_SETTING] == OPERATING_MODE_MAP


def test_ventilation_mode_labels() -> None:
    assert NibePointSelect.ENUM_LABELS[POINT_VENTILATION_MODE] == {
        0: "Normal",
        1: "Aus",
        2: "Reduziert",
        3: "Erhöht",
        4: "Maximal",
    }


def test_mode_dependent_write_protection() -> None:
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, 0)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 0)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 1)
    assert write_allowed_for_mode(POINT_COOLING_ALLOWED, 1)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 2)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 2)
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, None)


def test_time_conversion_roundtrip() -> None:
    assert time_from_seconds(34200) == time(9, 30)
    assert seconds_from_time(time(9, 30)) == 34200
    assert time_from_seconds(0) == time(0, 0)
    assert time_from_seconds(86399) == time(23, 59, 59)
    assert time_from_seconds(-1) is None
    assert time_from_seconds(86400) is None
    assert time_from_seconds("ungueltig") is None


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
