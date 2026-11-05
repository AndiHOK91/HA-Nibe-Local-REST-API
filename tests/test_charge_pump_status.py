"""Verified periodic/auto status of the charge pump."""
from types import SimpleNamespace
import pytest
from homeassistant.components.sensor import SensorDeviceClass
from custom_components.nibe_local.sensor import NibeSensor
from custom_components.nibe_local.const import POINTS


@pytest.mark.parametrize('pid', [4651, 4821])
@pytest.mark.parametrize('raw,expected', [(0, 'periodic'), (1, 'auto'), ('1', 'auto'), (2, 'unknown')])
def test_charge_pump_status(pid, raw, expected):
    p = {'metadata': {'variableSize': 'u8'}, 'value': {'integerValue': raw}}
    c = SimpleNamespace(point=lambda _: p, entity_naming='home_assistant', instance_id='test')
    definition = next(p for p in POINTS if p.point_id == pid)
    entity = NibeSensor(c, definition)
    assert entity.unique_id == f'test_{pid}'
    assert entity.device_class == SensorDeviceClass.ENUM
    assert entity.native_value == expected
    assert expected in entity.options


@pytest.mark.parametrize('pid', [4651, 4821])
def test_charge_pump_mode_select_writes_verified_values(pid):
    import asyncio
    from unittest.mock import AsyncMock
    from custom_components.nibe_local.select import NibePointSelect
    definition = next(p for p in POINTS if p.point_id == pid)
    assert definition.platform == 'select'
    point = {'metadata': {'isWritable': True}, 'value': {'integerValue': 1}}
    c = SimpleNamespace(point=lambda _: point, entity_naming='home_assistant',
        instance_id='test', api=SimpleNamespace(patch_point=AsyncMock()),
        async_refresh_point=AsyncMock())
    e = NibePointSelect(c, definition)
    assert e.current_option == 'auto'
    assert e.options == ['periodic', 'auto']
    asyncio.run(e.async_select_option('periodic'))
    c.api.patch_point.assert_awaited_once_with(pid, 0)
    c.api.patch_point.reset_mock()
    asyncio.run(e.async_select_option('auto'))
    c.api.patch_point.assert_awaited_once_with(pid, 1)


@pytest.mark.parametrize('pid', [4651, 4821])
@pytest.mark.parametrize('raw,expected', [(0, 'periodic'), (1, 'auto')])
def test_read_only_setup_keeps_named_enum_sensor_and_no_writer(pid, raw, expected):
    import asyncio
    from custom_components.nibe_local import sensor, select
    point = {'metadata': {'isWritable': True, 'variableType': 'integer',
                         'divisor': 1, 'minValue': 0, 'maxValue': 1},
             'value': {'integerValue': raw}}
    c = SimpleNamespace(point=lambda _: point, entity_enabled=lambda point_id: point_id == pid,
        enabled_point_ids={pid}, write_enabled=lambda _: False,
        selected_writable_point_ids=set(), data={}, entity_naming='home_assistant',
        instance_id='test')
    entry = SimpleNamespace(runtime_data=c)
    sensors = []
    asyncio.run(sensor.async_setup_entry(None, entry, sensors.extend))
    result = [e for e in sensors if getattr(getattr(e, 'definition', None), 'point_id', None) == pid]
    assert len(result) == 1
    e = result[0]
    assert e.unique_id == f'test_{pid}'
    assert e.translation_key == ('charge_pump_operating_mode' if pid == 4651
                                  else 'charge_pump_cooling_operating_mode')
    assert e.native_value == expected
    assert e.device_class == SensorDeviceClass.ENUM
    writers = []
    asyncio.run(select.async_setup_entry(None, entry, writers.extend))
    assert writers == []
