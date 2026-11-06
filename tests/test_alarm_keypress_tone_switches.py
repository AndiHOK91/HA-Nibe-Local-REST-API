"""The NIBE alarm and keypress tones are writable 0/1 options, not generic numbers."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.nibe_local import sensor, switch
from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    PROFILE_COMPLETE, PROFILE_EXTENDED, PROFILE_INDIVIDUAL, PROFILE_STANDARD, point_enabled,
)


@pytest.mark.parametrize("point_id,register,name", [
    (9659, 5326, "Tonsignal bei Alarm"),
    (9663, 5327, "Ton bei Tastendruck"),
])
def test_tone_points_curated_as_binary_switches(point_id, register, name):
    definition = next(p for p in POINTS if p.point_id == point_id)
    assert definition.platform == "switch"
    assert point_enabled(PROFILE_EXTENDED, point_id)
    assert point_enabled(PROFILE_COMPLETE, point_id)
    assert point_enabled(PROFILE_INDIVIDUAL, point_id, [point_id])
    assert not point_enabled(PROFILE_STANDARD, point_id)
    translations = json.loads(
        (Path(__file__).resolve().parents[1]
         / "custom_components" / "nibe_local" / "translations" / "de.json").read_text(encoding="utf-8")
    )
    assert translations["entity"]["switch"][definition.key]["name"] == name
    assert translations["entity"]["sensor"][definition.key]["state"] == {
        "off": "Aus", "on": "Ein", "unknown": "Unbekannt"
    }


def _coordinator(point_id, writable_permission=True, rest_writable=True, value=1):
    point = {
        "metadata": {"variableId": point_id, "variableType": "integer",
                     "variableSize": "u8", "modbusRegisterType": "MODBUS_HOLDING_REGISTER",
                     "modbusRegisterID": 5326 if point_id == 9659 else 5327,
                     "isWritable": rest_writable, "minValue": 0, "maxValue": 1,
                     "divisor": 1},
        "value": {"integerValue": value, "isOk": True},
    }
    return SimpleNamespace(
        point=lambda pid: point if pid == point_id else None,
        entity_enabled=lambda pid: pid == point_id,
        write_enabled=lambda pid: writable_permission,
        enabled_point_ids={point_id},
        selected_writable_point_ids={point_id} if writable_permission else set(),
        entity_naming="home_assistant", instance_id="test", data={},
        last_update_success=True,
        api=SimpleNamespace(patch_point=AsyncMock()),
        async_refresh_point=AsyncMock(return_value=point),
    )


@pytest.mark.parametrize("point_id", [9659, 9663])
def test_binary_tone_switch_writes_zero_one(point_id):
    c = _coordinator(point_id)
    switches = []
    asyncio.run(switch.async_setup_entry(None, SimpleNamespace(runtime_data=c), switches.extend))
    target = [e for e in switches if getattr(getattr(e, "definition", None), "point_id", None) == point_id]
    assert len(target) == 1
    e = target[0]
    assert e.is_on is True
    asyncio.run(e.async_turn_off())
    c.api.patch_point.assert_awaited_with(point_id, 0)
    asyncio.run(e.async_turn_on())
    c.api.patch_point.assert_awaited_with(point_id, 1)


@pytest.mark.parametrize("point_id", [9659, 9663])
@pytest.mark.parametrize("writable_permission,rest_writable", [(False, True), (True, False)])
def test_tone_read_only_fallback_is_named_enum(point_id, writable_permission, rest_writable):
    c = _coordinator(point_id, writable_permission, rest_writable, value=1)
    switches = []
    asyncio.run(switch.async_setup_entry(None, SimpleNamespace(runtime_data=c), switches.extend))
    assert switches == []
    sensors = []
    asyncio.run(sensor.async_setup_entry(None, SimpleNamespace(runtime_data=c), sensors.extend))
    target = [e for e in sensors if getattr(getattr(e, "definition", None), "point_id", None) == point_id]
    assert len(target) == 1
    assert target[0].device_class == SensorDeviceClass.ENUM
    assert target[0].native_value == "on"
    assert target[0].options == ["off", "on", "unknown"]
    assert target[0].translation_key in {"alarm_acoustic_signal", "key_press_tone"}


def test_tone_switch_upgrade_removes_old_sensor_registry_entry(monkeypatch):
    import custom_components.nibe_local as integration
    removed = []
    registry = SimpleNamespace(
        async_get_entity_id=lambda domain, platform, uid: (
            f"sensor.{uid}" if domain == "sensor" and uid in ("test_9659", "test_9663") else None
        ),
        async_remove=removed.append,
    )
    monkeypatch.setattr(integration.er, "async_get", lambda _: registry)

    class C:
        def point(self, pid):
            return {"metadata": {"isWritable": True}}

        def entity_enabled(self, pid):
            return pid in (9659, 9663)

        def write_enabled(self, pid):
            return pid in (9659, 9663)

    integration._remove_replaced_point_entities(None, SimpleNamespace(entry_id="test"), C())
    assert set(removed) == {"sensor.test_9659", "sensor.test_9663"}
