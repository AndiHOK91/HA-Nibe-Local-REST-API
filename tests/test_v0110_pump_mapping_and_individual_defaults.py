"""Regression tests for the v0.11.0 pump mapping and individual defaults."""

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    KNOWN_POINT_IDS,
    STANDARD_PROFILE_POINT_IDS,
    normalize_selected_ids,
)


def test_gp1_gp6_curated_point_mapping() -> None:
    definitions = {definition.point_id: definition for definition in POINTS}

    assert 1975 not in definitions
    assert definitions[2792].key == "heating_circulation_pump_gp1"
    assert definitions[2792].platform == "sensor"
    assert definitions[10895].key == "heating_medium_pump_gp6"
    assert definitions[10895].platform == "binary_sensor"


def test_standard_profile_uses_correct_pump_points() -> None:
    assert 1975 not in STANDARD_PROFILE_POINT_IDS
    assert 2792 in STANDARD_PROFILE_POINT_IDS
    assert 10895 in STANDARD_PROFILE_POINT_IDS


def test_unset_individual_selection_defaults_to_curated_points() -> None:
    assert normalize_selected_ids(None) == KNOWN_POINT_IDS


def test_explicit_empty_individual_selection_stays_empty() -> None:
    assert normalize_selected_ids([]) == frozenset()
