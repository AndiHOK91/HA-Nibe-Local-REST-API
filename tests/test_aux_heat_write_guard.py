"""Regression tests for AUX heat switch write protection."""

from custom_components.nibe_local.const import (
    POINT_AUX_HEAT_ALLOWED_HEATING,
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
)
from custom_components.nibe_local.switch import (
    MODE_DEPENDENT_SWITCHES,
    write_allowed_for_mode,
)


def test_aux_heat_allowed_heating_is_not_operating_mode_dependent() -> None:
    assert POINT_AUX_HEAT_ALLOWED_HEATING not in MODE_DEPENDENT_SWITCHES
    for mode in (0, 1, 2, None):
        assert write_allowed_for_mode(POINT_AUX_HEAT_ALLOWED_HEATING, mode)


def test_heating_and_cooling_permissions_keep_mode_guard() -> None:
    assert MODE_DEPENDENT_SWITCHES == {
        POINT_HEATING_ALLOWED,
        POINT_COOLING_ALLOWED,
    }
