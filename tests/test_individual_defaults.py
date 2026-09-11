"""Regression tests for Individual profile preselection."""

from custom_components.nibe_local import _individual_default_point_ids
from custom_components.nibe_local.const import CONF_ENTITY_PROFILE
from custom_components.nibe_local.profiles import (
    PROFILE_EXTENDED,
    PROFILE_INDIVIDUAL,
    PROFILE_STANDARD,
)


def test_extended_profile_becomes_individual_default_selection() -> None:
    points = {
        "2792": {"value": {"integerValue": 21}},
        "10895": {"value": {"integerValue": 1}},
        "999999": {"value": {"integerValue": 1}},
    }

    selected = _individual_default_point_ids(
        {CONF_ENTITY_PROFILE: PROFILE_EXTENDED},
        points,
    )

    assert selected == [2792, 10895]


def test_standard_profile_includes_verified_gp6_default() -> None:
    points = {
        "2792": {"value": {"integerValue": 21}},
        "10895": {"value": {"integerValue": 1}},
    }

    selected = _individual_default_point_ids(
        {CONF_ENTITY_PROFILE: PROFILE_STANDARD},
        points,
    )

    assert selected == [2792, 10895]


def test_existing_individual_selection_is_not_overwritten() -> None:
    selected = _individual_default_point_ids(
        {CONF_ENTITY_PROFILE: PROFILE_INDIVIDUAL},
        {"2792": {}, "10895": {}},
    )

    assert selected is None
