"""Regression tests for NIBE point 1760 state mapping."""

from custom_components.nibe_local.sensor import AUX_HEAT_MODE_MAP


def test_aux_heat_mode_1760_binary_states() -> None:
    assert AUX_HEAT_MODE_MAP == {0: "off", 1: "on"}
