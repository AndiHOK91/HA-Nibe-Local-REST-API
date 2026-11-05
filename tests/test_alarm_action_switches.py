"""Writable alarm-action preferences with a read-only fallback."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from custom_components.nibe_local import switch, sensor


def coordinator(pid, writable):
    point = {'metadata': {'isWritable': True, 'variableType': 'integer',
                        'minValue': 0, 'maxValue': 1, 'divisor': 1},
             'value': {'integerValue': 0}}
    return SimpleNamespace(point=lambda i: point if i == pid else None,
        entity_enabled=lambda i: i == pid, write_enabled=lambda i: writable,
        enabled_point_ids={pid}, selected_writable_point_ids={pid} if writable else set(),
        entity_naming='home_assistant', instance_id='test', data={},
        api=SimpleNamespace(patch_point=AsyncMock()), async_refresh_point=AsyncMock())


@pytest.mark.parametrize('pid', [3935, 3936])
def test_alarm_action_switch_sends_zero_and_one(pid):
    c = coordinator(pid, True)
    entities = []
    asyncio.run(switch.async_setup_entry(None, SimpleNamespace(runtime_data=c), entities.extend))
    assert len(entities) == 1
    e = entities[0]
    assert e.is_on is False
    asyncio.run(e.async_turn_on())
    c.api.patch_point.assert_awaited_once_with(pid, 1)
    c.api.patch_point.reset_mock()
    asyncio.run(e.async_turn_off())
    c.api.patch_point.assert_awaited_once_with(pid, 0)
    sensors = []
    asyncio.run(sensor.async_setup_entry(None, SimpleNamespace(runtime_data=c), sensors.extend))
    assert not any(getattr(getattr(e, 'definition', None), 'point_id', None) == pid for e in sensors)


@pytest.mark.parametrize('pid', [3935, 3936])
def test_alarm_action_without_permission_keeps_named_sensor(pid):
    c = coordinator(pid, False)
    entities = []
    asyncio.run(switch.async_setup_entry(None, SimpleNamespace(runtime_data=c), entities.extend))
    assert entities == []
    sensors = []
    asyncio.run(sensor.async_setup_entry(None, SimpleNamespace(runtime_data=c), sensors.extend))
    e = next(e for e in sensors if getattr(getattr(e, 'definition', None), 'point_id', None) == pid)
    assert e.native_value == 'off'
    assert e.translation_key.startswith('alarm_action_lower_')
    c.api.patch_point.assert_not_awaited()
