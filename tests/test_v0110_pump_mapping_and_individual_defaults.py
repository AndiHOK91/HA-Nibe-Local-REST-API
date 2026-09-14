"""Regression tests for the v0.11.x pump mapping and individual defaults."""

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    EXTENDED_PROFILE_POINT_IDS,
    KNOWN_POINT_IDS,
    PROFILE_EXTENDED,
    PROFILE_INDIVIDUAL,
    STANDARD_PROFILE_POINT_IDS,
    normalize_selected_ids,
    point_enabled,
)


def test_vvm_s320_gp1_gp6_gp12_curated_point_mapping() -> None:
    definitions = {definition.point_id: definition for definition in POINTS}

    assert definitions[2792].key == "heating_circulation_pump_gp1"
    assert definitions[2792].platform == "sensor"
    assert definitions[1975].key == "heating_medium_pump_gp6"
    assert definitions[1975].platform == "binary_sensor"
    assert definitions[3138].key == "internal_charge_pump_gp12"
    assert definitions[3138].platform == "binary_sensor"
    assert 10895 not in definitions


def test_standard_extended_and_individual_pump_profiles() -> None:
    assert 1975 in STANDARD_PROFILE_POINT_IDS
    assert 1975 in EXTENDED_PROFILE_POINT_IDS
    assert 1975 in KNOWN_POINT_IDS

    assert 2792 in STANDARD_PROFILE_POINT_IDS
    assert 2792 in EXTENDED_PROFILE_POINT_IDS
    assert 2792 in KNOWN_POINT_IDS

    # GP12 stays curated so an explicit Individual selection creates the proper
    # binary sensor, but it is not enabled automatically by Standard/Extended.
    assert 3138 not in STANDARD_PROFILE_POINT_IDS
    assert 3138 not in EXTENDED_PROFILE_POINT_IDS
    assert 3138 in KNOWN_POINT_IDS
    assert point_enabled(PROFILE_EXTENDED, 3138) is False
    assert point_enabled(PROFILE_INDIVIDUAL, 3138, [3138]) is True

    assert 10895 not in STANDARD_PROFILE_POINT_IDS
    assert 10895 not in EXTENDED_PROFILE_POINT_IDS
    assert 10895 not in KNOWN_POINT_IDS


def test_curated_optional_pumps_can_be_selected_explicitly() -> None:
    assert normalize_selected_ids([1975, 3138]) == frozenset({1975, 3138})


def test_unset_individual_selection_defaults_to_curated_points() -> None:
    assert normalize_selected_ids(None) == KNOWN_POINT_IDS


def test_explicit_empty_individual_selection_stays_empty() -> None:
    assert normalize_selected_ids([]) == frozenset()
