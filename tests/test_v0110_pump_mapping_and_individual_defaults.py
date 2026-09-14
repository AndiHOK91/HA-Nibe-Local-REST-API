"""Regression tests for the v0.11.x pump mapping and individual defaults."""

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    KNOWN_POINT_IDS,
    PROFILE_INDIVIDUAL,
    STANDARD_PROFILE_POINT_IDS,
    normalize_selected_ids,
    point_enabled,
)


def test_vvm_s320_gp1_gp6_curated_point_mapping() -> None:
    definitions = {definition.point_id: definition for definition in POINTS}

    assert definitions[2792].key == "heating_circulation_pump_gp1"
    assert definitions[2792].platform == "sensor"
    assert definitions[1975].key == "heating_medium_pump_gp6"
    assert definitions[1975].platform == "binary_sensor"
    # GP12 remains discoverable/selectable through the Individual profile but
    # is deliberately not part of the curated automatic profiles.
    assert 3138 not in definitions
    assert 10895 not in definitions


def test_standard_profile_uses_gp1_but_extended_knows_gp6() -> None:
    assert 1975 not in STANDARD_PROFILE_POINT_IDS
    assert 1975 in KNOWN_POINT_IDS
    assert 2792 in STANDARD_PROFILE_POINT_IDS
    assert 2792 in KNOWN_POINT_IDS
    assert 3138 not in KNOWN_POINT_IDS
    assert 10895 not in STANDARD_PROFILE_POINT_IDS
    assert 10895 not in KNOWN_POINT_IDS


def test_curated_gp6_can_be_selected_explicitly() -> None:
    assert normalize_selected_ids([1975]) == frozenset({1975})


def test_gp12_can_still_be_enabled_explicitly_in_individual_profile() -> None:
    # Individual selection intentionally supports discovered IDs that are not
    # curated in POINTS, so GP12/3138 remains available on systems exposing it.
    assert normalize_selected_ids([3138]) == frozenset({3138})
    assert point_enabled(PROFILE_INDIVIDUAL, 3138, [3138])


def test_unset_individual_selection_defaults_to_curated_points() -> None:
    assert normalize_selected_ids(None) == KNOWN_POINT_IDS


def test_explicit_empty_individual_selection_stays_empty() -> None:
    assert normalize_selected_ids([]) == frozenset()
