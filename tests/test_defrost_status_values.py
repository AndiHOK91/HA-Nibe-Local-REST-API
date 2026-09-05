"""Regression tests for NIBE defrost status values."""

from custom_components.nibe_local.const import POINTS, POINT_TIME_TO_DEFROST
from custom_components.nibe_local.sensor import description_enum_map


def test_time_to_defrost_is_diagnostic() -> None:
    definition = next(point for point in POINTS if point.point_id == POINT_TIME_TO_DEFROST)
    assert definition.diagnostic is True


def test_current_status_is_diagnostic_only() -> None:
    definition = next(point for point in POINTS if point.point_id == 2022)
    assert definition.diagnostic is True


def test_last_defrost_enum_is_parsed_only_from_rest_description() -> None:
    point = {
        "description": (
            "0 = Successful, 1: Low supply, 2: Low return, "
            "3: Low flow, 4: Low LP, 5: Max time, 255 = Not accessible"
        )
    }
    assert description_enum_map(point) == {
        0: "Successful",
        1: "Low supply",
        2: "Low return",
        3: "Low flow",
        4: "Low LP",
        5: "Max time",
        255: "Not accessible",
    }


def test_last_defrost_without_rest_description_has_no_assumed_mapping() -> None:
    assert description_enum_map({}) == {}
