"""Power limitation points in the Extended installation profile."""
from types import SimpleNamespace
import pytest
from homeassistant.components.sensor import SensorDeviceClass
from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    PROFILE_EXTENDED, PROFILE_STANDARD, point_enabled,
)
from custom_components.nibe_local.sensor import NibeSensor


@pytest.mark.parametrize('pid', [22070, 22077, 27238])
def test_power_limits_are_selected_by_extended_profile(pid):
    assert point_enabled(PROFILE_EXTENDED, pid)
    assert not point_enabled(PROFILE_STANDARD, pid)
    assert next(p for p in POINTS if p.point_id == pid).platform == ('switch' if pid == 22077 else 'sensor')


def entity(pid, raw, **metadata):
    p = {'metadata': metadata, 'value': {'integerValue': raw}}
    c = SimpleNamespace(point=lambda _: p, entity_naming='home_assistant', instance_id='test')
    return NibeSensor(c, next(p for p in POINTS if p.point_id == pid))


@pytest.mark.parametrize('raw,expected', [(0, 'inactive'), (1, 'active'), ('1', 'active'), (2, 'unknown')])
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


@pytest.mark.parametrize('function', [66, '66', 3, None])
@pytest.mark.parametrize('raw,expected', [(0, 'off'), (1, 'on')])
def test_aux_status_name_is_stable_for_every_function(function, raw, expected):
    points = {22077: {'value': {'integerValue': raw}}}
    if function is not None:
        points[22070] = {'value': {'integerValue': function}}
    c = SimpleNamespace(point=lambda pid: points.get(pid),
        entity_naming='home_assistant', instance_id='test')
    e = NibeSensor(c, next(p for p in POINTS if p.point_id == 22077))
    assert e.translation_key == 'aux_via_modbus'
    assert e.native_value == expected
    assert e.device_class == SensorDeviceClass.ENUM
    assert e.unique_id == 'test_22077'


@pytest.mark.parametrize('raw,expected', [(66, 'external_power_limit'), ('66', 'external_power_limit'), (3, 'function_3')])
def test_aux_function_sensor_translates_confirmed_codes(raw, expected):
    e = entity(22070, raw)
    assert e.native_value == expected
    assert expected in e.options
    assert e.translation_key == 'aux_modbus_function'


def test_aux_switch_writes_zero_and_one():
    import asyncio
    from unittest.mock import AsyncMock
    from custom_components.nibe_local import switch, sensor
    points = {22070: {'value': {'integerValue': 66}},
              22077: {'metadata': {'isWritable': True}, 'value': {'integerValue': 0}}}
    c = SimpleNamespace(point=lambda pid: points.get(pid), entity_naming='home_assistant',
        instance_id='test', entity_enabled=lambda pid: pid == 22077,
        write_enabled=lambda pid: True, enabled_point_ids={22077}, selected_writable_point_ids={22077},
        data={}, last_update_success=True,
        api=SimpleNamespace(patch_point=AsyncMock()), async_refresh_point=AsyncMock())
    result = []
    asyncio.run(switch.async_setup_entry(None, SimpleNamespace(runtime_data=c), result.extend))
    assert len(result) == 1
    e = result[0]
    assert e.translation_key == 'aux_via_modbus'
    asyncio.run(e.async_turn_on())
    c.api.patch_point.assert_awaited_once_with(22077, 1)
    c.api.patch_point.reset_mock()
    asyncio.run(e.async_turn_off())
    c.api.patch_point.assert_awaited_once_with(22077, 0)
    result = []
    asyncio.run(sensor.async_setup_entry(None, SimpleNamespace(runtime_data=c), result.extend))
    assert not any(getattr(getattr(e, 'definition', None), 'point_id', None) == 22077 for e in result)


@pytest.mark.parametrize('code', range(70))
def test_all_aux_codes_have_valid_options_and_unknown_codes_stay_numeric(code):
    from custom_components.nibe_local.sensor import AUX_FUNCTION_STATES
    e = entity(22070, code)
    assert e.native_value == AUX_FUNCTION_STATES.get(code, str(code))
    assert e.native_value in e.options
    assert len(e.options) == len(set(e.options))


def test_aux_labels_exist_in_both_languages():
    import json
    from pathlib import Path
    from custom_components.nibe_local.sensor import AUX_FUNCTION_STATES
    for language in ['de', 'en']:
        d = json.loads((Path('custom_components/nibe_local/translations') / f'{language}.json').read_text())
        labels = d['entity']['sensor']['aux_modbus_function']['state']
        assert set(AUX_FUNCTION_STATES.values()) <= set(labels)
    assert labels['external_power_limit'] == 'Ext. power limitation'
    assert 49 not in AUX_FUNCTION_STATES
    assert 62 not in AUX_FUNCTION_STATES


def test_rest_power_limitation_activation_is_not_automatically_selected():
    from custom_components.nibe_local.profiles import PROFILE_COMPLETE, PROFILE_INDIVIDUAL
    assert not point_enabled(PROFILE_EXTENDED, 32824)
    assert not point_enabled(PROFILE_STANDARD, 32824)
    assert point_enabled(PROFILE_COMPLETE, 32824)
    assert point_enabled(PROFILE_INDIVIDUAL, 32824, [32824])
    import json
    from pathlib import Path
    translations = json.loads(Path('custom_components/nibe_local/translations/de.json').read_text())
    assert translations['entity']['sensor']['power_limitation_enabled']['name'] == 'Aktivierung der Leistungsbegrenzung'


def test_aux_status_localized_active_inactive_labels():
    import json
    from pathlib import Path
    root = Path(__file__).parents[1] / 'custom_components' / 'nibe_local' / 'translations'
    for language, name, inactive, active in (
        ('de', 'Aux von Modbus', 'Inaktiv', 'Aktiv'),
        ('en', 'AUX via Modbus', 'Inactive', 'Active'),
    ):
        data = json.loads((root / f'{language}.json').read_text(encoding='utf-8'))
        sensor = data['entity']['sensor']['aux_via_modbus']
        assert sensor['name'] == name
        assert sensor['state']['off'] == inactive
        assert sensor['state']['on'] == active
        assert data['entity']['switch']['aux_via_modbus']['name'] == name
