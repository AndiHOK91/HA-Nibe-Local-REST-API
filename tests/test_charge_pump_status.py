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
