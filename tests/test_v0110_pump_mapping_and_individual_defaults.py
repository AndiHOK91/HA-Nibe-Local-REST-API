"""Regression tests for the v0.11.0 pump mapping and individual defaults."""

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    KNOWN_POINT_IDS,
    STANDARD_PROFILE_POINT_IDS,
    normalize_selected_ids,
)


def test_vvm_s320_gp1_curated_point_mapping() -> None:
    definitions = {definition.point_id: definition for definition in POINTS}

    # VVM S320/S325: 2792 is the verified variable-speed GP1 value. Point 1975
    # is deliberately not curated, and the former GP6 candidate 10895 is not
    # exposed because current device firmware returns "Point not found" for it.
    assert 1975 not in definitions
    assert 10895 not in definitions
    assert definitions[2792].key == "heating_circulation_pump_gp1"
    assert definitions[2792].platform == "sensor"


def test_standard_profile_uses_verified_vvm_s320_gp1_point() -> None:
    assert 1975 not in STANDARD_PROFILE_POINT_IDS
    assert 1975 not in KNOWN_POINT_IDS
    assert 10895 not in STANDARD_PROFILE_POINT_IDS
    assert 10895 not in KNOWN_POINT_IDS
    assert 2792 in STANDARD_PROFILE_POINT_IDS


def test_non_curated_discovered_point_can_still_be_selected_explicitly() -> None:
    # Unknown/discovered IDs are intentionally preserved for the Individual
    # profile, so model-specific REST points can still be exposed explicitly.
    assert normalize_selected_ids([1975]) == frozenset({1975})


def test_unset_individual_selection_defaults_to_curated_points() -> None:
    assert normalize_selected_ids(None) == KNOWN_POINT_IDS


def test_explicit_empty_individual_selection_stays_empty() -> None:
    assert normalize_selected_ids([]) == frozenset()
