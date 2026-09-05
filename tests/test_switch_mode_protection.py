"""Regression tests for operating-mode dependent switch protection."""

from custom_components.nibe_local.const import (
    POINT_AUX_HEAT_ALLOWED_HEATING,
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
)
from custom_components.nibe_local.switch import write_allowed_for_mode


def test_mode_dependent_switches_are_locked_in_auto() -> None:
    assert not write_allowed_for_mode(POINT_AUX_HEAT_ALLOWED_HEATING, 0)
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, 0)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 0)


def test_mode_dependent_switches_are_writable_in_manual() -> None:
    assert write_allowed_for_mode(POINT_AUX_HEAT_ALLOWED_HEATING, 1)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 1)
    assert write_allowed_for_mode(POINT_COOLING_ALLOWED, 1)


def test_only_heating_allowed_is_writable_in_auxiliary_heat_only_mode() -> None:
    assert not write_allowed_for_mode(POINT_AUX_HEAT_ALLOWED_HEATING, 2)
    assert write_allowed_for_mode(POINT_HEATING_ALLOWED, 2)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, 2)


def test_mode_dependent_switches_fail_closed_when_mode_is_unknown() -> None:
    assert not write_allowed_for_mode(POINT_AUX_HEAT_ALLOWED_HEATING, None)
    assert not write_allowed_for_mode(POINT_HEATING_ALLOWED, None)
    assert not write_allowed_for_mode(POINT_COOLING_ALLOWED, None)
