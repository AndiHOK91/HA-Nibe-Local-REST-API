"""Regression tests for the v0.11.0 pump mapping and individual defaults."""

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    KNOWN_POINT_IDS,
    STANDARD_PROFILE_POINT_IDS,
    normalize_selected_ids,
)


def test_gp1_gp6_curated_point_mapping() -> None:
    definitions = {definition.point_id: definition for definition in POINTS}

    # VVM S320/S325: 2792 is the GP1 speed (%) and 10895 is the GP6
    # running status. Point 1975 is a model-family duplicate and is therefore
    # deliberately not part of the curated point catalogue.
    assert 1975 not in definitions
    assert definitions[2792].key == "heating_circulation_pump_gp1"
    assert definitions[2792].platform == "sensor"
    assert definitions[10895].key == "heating_medium_pump_gp6"
    assert definitions[10895].platform == "binary_sensor"


def test_standard_profile_uses_vvm_s320_pump_points() -> None:
    assert 1975 not in STANDARD_PROFILE_POINT_IDS
    assert 1975 not in KNOWN_POINT_IDS
    assert 2792 in STANDARD_PROFILE_POINT_IDS
    assert 10895 in STANDARD_PROFILE_POINT_IDS


def test_model_specific_gp1_duplicate_can_still_be_selected_explicitly() -> None:
    # Unknown/discovered IDs are intentionally preserved for the Individual
    # profile, so users of another NIBE product family can still expose 1975.
    assert normalize_selected_ids([1975]) == frozenset({1975})


def test_unset_individual_selection_defaults_to_curated_points() -> None:
    assert normalize_selected_ids(None) == KNOWN_POINT_IDS


def test_explicit_empty_individual_selection_stays_empty() -> None:
    assert normalize_selected_ids([]) == frozenset()
