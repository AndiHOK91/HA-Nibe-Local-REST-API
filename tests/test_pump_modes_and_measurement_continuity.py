"""Pump semantics and stable measurement entities across write selection."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.components.sensor import SensorDeviceClass
from custom_components.nibe_local import sensor, number
from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.select import NibePointSelect


def point(value, **metadata):
    return {'metadata': {'variableType': 'integer', 'variableSize': 's32',
                         'isWritable': True, 'divisor': 10,
                         'minValue': -30000, 'maxValue': 30000, **metadata},
            'value': {'integerValue': value, 'isOk': True}}


def coordinator(points, writable):
    return SimpleNamespace(
        point=lambda pid: points.get(pid), entity_enabled=lambda pid: pid in points,
        write_enabled=lambda pid: pid in writable, enabled_point_ids=set(points),
        selected_writable_point_ids=writable, data={}, last_update_success=True,
        entity_naming='home_assistant', instance_id='test', device_name='NIBE',
        api=SimpleNamespace(patch_point=AsyncMock()), async_refresh_point=AsyncMock(),
    )


def test_degree_minutes_sensor_survives_write_permission_changes():
    for writable in ({781}, set()):
        c = coordinator({781: point(-4247)}, writable)
        result = []
        asyncio.run(sensor.async_setup_entry(None, SimpleNamespace(runtime_data=c), result.extend))
        degree = [e for e in result if getattr(getattr(e, 'definition', None), 'point_id', None) == 781]
        assert len(degree) == 1
        assert degree[0].unique_id == 'test_781'
        writers = []
        asyncio.run(number.async_setup_entry(None, SimpleNamespace(runtime_data=c), writers.extend))
        assert len(writers) == bool(writable)


def test_pump_modes_round_trip():
    for pid in (4729, 4745, 4778):
        c = coordinator({pid: point(1, divisor=1, maxValue=1)}, {pid})
        definition = next(p for p in POINTS if p.point_id == pid)
        assert definition.platform == 'select'
        entity = NibePointSelect(c, definition)
        assert entity.options == ['manual', 'auto']
        assert entity.current_option == 'auto'
        asyncio.run(entity.async_select_option('manual'))
        c.api.patch_point.assert_awaited_once_with(pid, 0)
        c.async_refresh_point.assert_awaited_once_with(pid)


def test_defrost_preserves_all_three_states():
    definition = next(p for p in POINTS if p.point_id == 3098)
    for raw, expected in [(0, 'off'), (1, 'active'), (2, 'passive')]:
        entity = sensor.NibeSensor(coordinator({3098: point(raw)}, set()), definition)
        assert entity.device_class == SensorDeviceClass.ENUM
        assert entity.native_value == expected
        assert expected in entity.options


def test_defrost_duration_special_value_remains_unknown_and_explained():
    definition = next(p for p in POINTS if p.point_id == 840)
    c = coordinator({840: point(65535, variableSize='u16', divisor=1)}, set())
    entity = sensor.NibeSensor(c, definition)
    assert entity.available
    assert entity.native_value is None
    assert entity.extra_state_attributes['duration_status'] == 'not_provided_by_device'


def test_write_selection_preserves_degree_minutes_registry_entry(monkeypatch):
    from custom_components.nibe_local import config_flow
    registry = SimpleNamespace(async_remove=lambda eid: removed.append(eid))
    entries = [SimpleNamespace(unique_id="test_781", domain=domain, entity_id=f"{domain}.gm")
               for domain in ("sensor", "number")]
    monkeypatch.setattr(config_flow.er, "async_get", lambda hass: registry)
    monkeypatch.setattr(config_flow.er, "async_entries_for_config_entry", lambda reg, eid: entries)
    for selected, expected in [([781], []), ([], ["number.gm"])]:
        removed = []
        config_flow._remove_write_mode_registry_conflicts(
            None, SimpleNamespace(entry_id="test"), profile="individual",
            selected_ids=[781], selected_writable_ids=selected, equipment=None,
            points={"781": point(-4247)},
        )
        assert removed == expected


def test_upgrade_removes_only_obsolete_pump_and_defrost_domains(monkeypatch):
    import custom_components.nibe_local as integration
    removed = []
    registry = SimpleNamespace(
        async_get_entity_id=lambda domain, platform, uid: f"{domain}.{uid}",
        async_remove=removed.append,
    )
    monkeypatch.setattr(integration.er, "async_get", lambda hass: registry)
    integration._remove_replaced_point_entities(None, SimpleNamespace(entry_id="test"))
    assert set(removed) == {"binary_sensor.test_3098", "switch.test_4729",
                            "switch.test_4745", "switch.test_4778",
                            "switch.test_8060", "number.test_22070"}
