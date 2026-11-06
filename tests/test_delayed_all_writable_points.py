"""Regression: writable REST points keep their requested value during NIBE readback lag."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.number import NibeNumber
from custom_components.nibe_local.select import NibePointSelect
from custom_components.nibe_local.switch import NibeDiscoveredSwitch
from custom_components.nibe_local.write_verification import raw_values_equal


def _point(raw, *, point_id, min_value=0, max_value=100, divisor=1):
    return {
        "metadata": {
            "variableId": point_id,
            "variableType": "integer",
            "isWritable": True,
            "minValue": min_value,
            "maxValue": max_value,
            "divisor": divisor,
        },
        "value": {"integerValue": raw, "isOk": True},
    }


def test_numeric_and_string_readbacks_compare_correctly():
    assert raw_values_equal("1", 1)
    assert raw_values_equal(0, "0")
    assert not raw_values_equal(0, 1)
    assert not raw_values_equal(None, 1)


@pytest.mark.parametrize("point_id", [4729, 4745, 4778])
def test_pump_select_stays_on_requested_option_until_confirmed(monkeypatch, point_id):
    async def scenario():
        import custom_components.nibe_local.write_verification as module

        current = _point(1, point_id=point_id, max_value=1)
        reads = 0

        async def refresh(pid):
            nonlocal reads
            assert pid == point_id
            reads += 1
            if reads >= 3:
                current["value"]["integerValue"] = 0
            return current

        async def no_sleep(delay):
            return None

        monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
        coordinator = SimpleNamespace(
            point=lambda pid: current if pid == point_id else None,
            api=SimpleNamespace(patch_point=AsyncMock()),
            async_refresh_point=refresh,
            command_poll_delay_ms=1000,
            entity_naming="home_assistant",
            instance_id="test",
            last_update_success=True,
        )
        definition = next(p for p in POINTS if p.point_id == point_id)
        entity = NibePointSelect(coordinator, definition)
        entity.hass = SimpleNamespace(async_create_task=asyncio.create_task)
        entity.async_write_ha_state = MagicMock()

        await entity.async_select_option("manual")
        assert entity.current_option == "manual"
        assert current["value"]["integerValue"] == 1
        await entity._pending_verify_task
        assert entity.current_option == "manual"
        assert entity._pending_display_value is None
        assert reads == 3
        coordinator.api.patch_point.assert_awaited_once_with(point_id, 0)

    asyncio.run(scenario())


def test_number_retains_requested_value_during_old_readback(monkeypatch):
    async def scenario():
        import custom_components.nibe_local.write_verification as module

        point_id = 3700
        current = _point(400, point_id=point_id, min_value=100, max_value=700, divisor=10)
        reads = 0

        async def refresh(_):
            nonlocal reads
            reads += 1
            if reads >= 3:
                current["value"]["integerValue"] = 450
            return current

        async def no_sleep(delay):
            return None

        monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
        coordinator = SimpleNamespace(
            point=lambda pid: current if pid == point_id else None,
            api=SimpleNamespace(patch_point=AsyncMock()),
            async_refresh_point=refresh,
            command_poll_delay_ms=1000,
            entity_naming="home_assistant",
            instance_id="test",
            last_update_success=True,
        )
        entity = NibeNumber(coordinator, next(p for p in POINTS if p.point_id == point_id))
        entity.hass = SimpleNamespace(async_create_task=asyncio.create_task)
        entity.async_write_ha_state = MagicMock()

        await entity.async_set_native_value(45.0)
        assert entity.native_value == 45.0
        assert current["value"]["integerValue"] == 400
        await entity._pending_verify_task
        assert entity.native_value == 45.0
        coordinator.api.patch_point.assert_awaited_once_with(point_id, 450)

    asyncio.run(scenario())


def test_discovered_switch_rolls_back_when_readback_never_confirms(monkeypatch):
    async def scenario():
        import custom_components.nibe_local.write_verification as module
        point_id = 999997
        current = _point(0, point_id=point_id, max_value=1)

        async def no_sleep(_):
            return None

        monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
        coordinator = SimpleNamespace(
            point=lambda pid: current if pid == point_id else None,
            api=SimpleNamespace(patch_point=AsyncMock()),
            async_refresh_point=AsyncMock(return_value=current),
            command_poll_delay_ms=1000,
            entity_naming="home_assistant",
            instance_id="test",
            last_update_success=True,
        )
        entity = NibeDiscoveredSwitch(coordinator, point_id)
        entity.hass = SimpleNamespace(async_create_task=asyncio.create_task)
        entity.async_write_ha_state = MagicMock()

        await entity.async_turn_on()
        assert entity.is_on is True
        await entity._pending_verify_task
        assert entity.is_on is False
        assert entity._pending_display_value is None

    asyncio.run(scenario())


def test_rejected_write_never_leaves_optimistic_state(monkeypatch):
    from custom_components.nibe_local.api import NibeApiError

    async def scenario():
        point_id = 4729
        current = _point(1, point_id=point_id, max_value=1)
        coordinator = SimpleNamespace(
            point=lambda pid: current,
            api=SimpleNamespace(patch_point=AsyncMock(side_effect=NibeApiError("rejected"))),
            async_refresh_point=AsyncMock(),
            command_poll_delay_ms=1000,
            entity_naming="home_assistant",
            instance_id="test",
            last_update_success=True,
        )
        entity = NibePointSelect(coordinator, next(p for p in POINTS if p.point_id == point_id))
        entity.hass = SimpleNamespace(async_create_task=asyncio.create_task)
        entity.async_write_ha_state = MagicMock()
        with pytest.raises(NibeApiError):
            await entity.async_select_option("manual")
        assert entity.current_option == "auto"
        assert entity._pending_display_value is None

    asyncio.run(scenario())
