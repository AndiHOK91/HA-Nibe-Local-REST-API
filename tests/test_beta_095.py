"""Regression tests for the 0.9.5 beta point curation."""

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.equipment import HOT_WATER_CIRCULATION_POINT_IDS
from custom_components.nibe_local.profiles import STANDARD_PROFILE_POINT_IDS


def test_standard_profile_matches_verified_default_rest_set() -> None:
    assert STANDARD_PROFILE_POINT_IDS == {
        4,
        8,
        10,
        11,
        12,
        29,
        54,
        58,
        91,
        781,
        994,
        997,
        1708,
        1756,
        1760,
        2491,
        2494,
        2495,
        2496,
        2497,
        2766,
        2767,
        2792,
        3095,
        3096,
        3097,
        3170,
        3375,
        7934,
        7935,
        7936,
        7937,
        7939,
        10894,
    }


def test_verified_pump_points_are_curated_for_extended_profile() -> None:
    definitions = {definition.point_id: definition for definition in POINTS}
    assert definitions[1975].key == "heating_medium_pump_gp6"
    assert definitions[1975].platform == "binary_sensor"
    assert definitions[2792].key == "heating_circulation_pump_gp1"
    # GP12/3138 is not automatic, but remains available as a discovered point
    # through the Individual/Complete profiles when the device exposes it.
    assert 3138 not in definitions
    assert 10895 not in definitions


def test_hot_water_circulation_only_contains_verified_rest_points() -> None:
    assert HOT_WATER_CIRCULATION_POINT_IDS == {
        1829,
        3710,
        3711,
        7849,
        7850,
        7851,
        7852,
        7853,
        7854,
    }


def test_hot_water_circulation_schedule_is_curated_as_time_entities() -> None:
    definitions = {definition.point_id: definition for definition in POINTS}
    for point_id in range(7849, 7855):
        assert definitions[point_id].group == "hot_water"
        assert definitions[point_id].platform == "time"
