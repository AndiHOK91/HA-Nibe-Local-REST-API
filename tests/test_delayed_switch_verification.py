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
    from custom_components.nibe_local.const import POINTS
    assert DELAYED_VERIFY_SWITCHES == {
        definition.point_id for definition in POINTS if definition.platform == "switch"
    }
    assert {22077, 3706, POINT_HEATING_ALLOWED, POINT_COOLING_ALLOWED} <= DELAYED_VERIFY_SWITCHES


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


def test_aux_switch_avoids_transient_off_when_nibe_readback_is_delayed(monkeypatch) -> None:
    """The UI stays on while initial REST reads still return zero."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    import custom_components.nibe_local.switch as switch_module
    from custom_components.nibe_local.const import POINTS

    async def scenario() -> None:
        point = {"value": {"integerValue": 0}}
        read_count = 0

        async def refresh(point_id):
            nonlocal read_count
            assert point_id == 22077
            read_count += 1
            if read_count >= 3:
                point["value"]["integerValue"] = 1
            return {"metadata": {"variableId": 22077}, **point}

        async def no_delay(_seconds):
            return None

        monkeypatch.setattr(switch_module.asyncio, "sleep", no_delay)
        coordinator = SimpleNamespace(
            entity_naming="home_assistant",
            instance_id="test",
            point=lambda pid: point if pid == 22077 else None,
            api=SimpleNamespace(patch_point=AsyncMock()),
            async_refresh_point=refresh,
            command_poll_delay_ms=1000,
            last_update_success=True,
        )
        entity = NibeSwitch(coordinator, next(p for p in POINTS if p.point_id == 22077))
        entity.hass = SimpleNamespace(async_create_task=asyncio.create_task)
        entity.async_write_ha_state = MagicMock()

        await entity.async_turn_on()
        assert entity.is_on is True
        assert point["value"]["integerValue"] == 0
        coordinator.api.patch_point.assert_awaited_once_with(22077, 1)
        await entity._verify_task
        assert read_count == 3
        assert entity.is_on is True
        assert entity._optimistic_state is None

    asyncio.run(scenario())


def test_aux_delayed_readback_has_bounded_timeout() -> None:
    source = inspect.getsource(NibeSwitch._verify_after_write)
    assert "self.definition.point_id == 22077" in source
    assert "delays += (3.0, 5.0, 5.0)" in source
    assert "self._optimistic_state = None" in source
