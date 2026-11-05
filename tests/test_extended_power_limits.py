"""Power limitation points in the Extended installation profile."""
from types import SimpleNamespace
import pytest
from homeassistant.components.sensor import SensorDeviceClass
from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    PROFILE_EXTENDED, PROFILE_STANDARD, point_enabled,
)
from custom_components.nibe_local.sensor import NibeSensor


@pytest.mark.parametrize('pid', [22077, 27238, 32824])
def test_power_limits_are_selected_by_extended_profile(pid):
    assert point_enabled(PROFILE_EXTENDED, pid)
    assert not point_enabled(PROFILE_STANDARD, pid)
    assert next(p for p in POINTS if p.point_id == pid).platform == 'sensor'


def entity(pid, raw, **metadata):
    p = {'metadata': metadata, 'value': {'integerValue': raw}}
    c = SimpleNamespace(point=lambda _: p, entity_naming='home_assistant', instance_id='test')
    return NibeSensor(c, next(p for p in POINTS if p.point_id == pid))


@pytest.mark.parametrize('raw,expected', [(0, 'off'), (1, 'on'), ('1', 'on'), (2, 'unknown')])
def test_power_limitation_sensor_states(raw, expected):
    e = entity(32824, raw)
    assert e.native_value == expected
    assert e.device_class == SensorDeviceClass.ENUM
    assert expected in e.options
    assert e.unique_id == 'test_32824'


def test_external_power_limit_preserves_scaling_and_unit():
    e = entity(27238, 42, divisor=10, decimal=1, unit='kW')
    assert e.native_value == 4.2
    assert e.native_unit_of_measurement == 'kW'
    assert e.device_class == SensorDeviceClass.POWER


@pytest.mark.parametrize('function,key', [(66, 'external_power_limit_request'), ('66', 'external_power_limit_request'), (3, 'aux_via_modbus'), (None, 'aux_via_modbus')])
@pytest.mark.parametrize('raw,expected', [(0, 'off'), (1, 'on')])
def test_aux_status_name_depends_on_selected_function(function, key, raw, expected):
    points = {22077: {'value': {'integerValue': raw}}}
    if function is not None:
        points[22070] = {'value': {'integerValue': function}}
    c = SimpleNamespace(point=lambda pid: points.get(pid),
        entity_naming='home_assistant', instance_id='test')
    e = NibeSensor(c, next(p for p in POINTS if p.point_id == 22077))
    assert e.translation_key == key
    assert e.native_value == expected
    assert e.device_class == SensorDeviceClass.ENUM
    assert e.unique_id == 'test_22077'
