"""Regression tests for NIBE switches with delayed REST state updates."""

import inspect

from custom_components.nibe_local.const import (
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
)
from custom_components.nibe_local.switch import (
    DELAYED_VERIFY_SWITCHES,
    NibeSwitch,
    _switch_state,
)


def _point(value):
    return {"value": {"integerValue": value, "stringValue": ""}}


def test_known_delayed_switches_are_verified_asynchronously() -> None:
    assert DELAYED_VERIFY_SWITCHES == {
        3706,  # Periodic hot water
        POINT_HEATING_ALLOWED,
        POINT_COOLING_ALLOWED,
    }


def test_switch_state_normalization() -> None:
    assert _switch_state(_point(1)) is True
    assert _switch_state(_point(0)) is False
    assert _switch_state({"value": {"integerValue": None, "stringValue": "off"}}) is False
    assert _switch_state({"value": {"integerValue": None, "stringValue": "on"}}) is True
    assert _switch_state(None) is None


def test_delayed_verification_uses_configured_command_poll_delay() -> None:
    source = inspect.getsource(NibeSwitch._verify_after_write)
    assert "command_poll_delay_ms" in source
    assert "async_refresh_point" in source
    assert "_optimistic_state = None" in source
    assert "_expected_state = None" in source


def test_delayed_switch_write_is_optimistic_but_other_switches_still_refresh_immediately() -> None:
    source = inspect.getsource(NibeSwitch._set_state)
    assert "not in DELAYED_VERIFY_SWITCHES" in source
    assert "self._optimistic_state = state" in source
    assert "self._expected_state = state" in source
    assert "self._start_verify_task()" in source
    assert "await self.coordinator.async_refresh_point(self.definition.point_id)" in source


def test_pending_verification_is_cancelled_when_entity_is_removed() -> None:
    source = inspect.getsource(NibeSwitch.async_will_remove_from_hass)
    assert "_cancel_verify_task()" in source
