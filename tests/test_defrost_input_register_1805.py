"""Defrost Input Register 1805 remains exposed as a non-writable status switch."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import json
from pathlib import Path

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.profiles import (
    PROFILE_STANDARD, PROFILE_EXTENDED, PROFILE_COMPLETE, PROFILE_INDIVIDUAL,
    point_enabled,
)
from custom_components.nibe_local.switch import NibeDefrostStatusSwitch, async_setup_entry
from custom_components.nibe_local.sensor import NibeSensor
from custom_components.nibe_local.writable import writable_platform_for_point


def point(value, writable=False):
    return {
        "metadata": {
            "variableId": 3098, "variableType": "integer", "variableSize": "u8",
            "modbusRegisterType": "MODBUS_INPUT_REGISTER",
            "modbusRegisterID": 1805, "isWritable": writable,
            "minValue": 0, "maxValue": 2, "divisor": 1,
        },
        "value": {"integerValue": value, "isOk": True},
    }


def coordinator(value=0):
    return SimpleNamespace(
        point=lambda pid: point(value) if pid == 3098 else None,
        entity_enabled=lambda pid: pid == 3098,
        write_enabled=lambda pid: False,
        enabled_point_ids={3098},
        selected_writable_point_ids=None,
        entity_naming="home_assistant",
        instance_id="test",
        data={},
        last_update_success=True,
        api=SimpleNamespace(patch_point=AsyncMock()),
        async_refresh_point=AsyncMock(),
    )


@pytest.mark.parametrize("value,expected", [(0, False), (1, True), (2, True), (3, None)])
def test_read_only_defrost_switch_state_and_register(value, expected):
    c = coordinator(value)
    entity = NibeDefrostStatusSwitch(c)
    assert entity.is_on is expected
    assert entity.extra_state_attributes["modbus_input_register"] == 1805
    assert entity.extra_state_attributes["read_only"] is True
    assert entity.unique_id == "test_3098_defrost_status_switch"


def test_input_register_cannot_be_operated():
    c = coordinator(1)
    entity = NibeDefrostStatusSwitch(c)
    with pytest.raises(HomeAssistantError, match="schreibgeschütztes"):
        asyncio.run(entity.async_turn_on())
    with pytest.raises(HomeAssistantError, match="schreibgeschütztes"):
        asyncio.run(entity.async_turn_off())
    c.api.patch_point.assert_not_awaited()


@pytest.mark.parametrize("profile,selected,expected", [
    (PROFILE_STANDARD, None, False),
    (PROFILE_EXTENDED, None, True),
    (PROFILE_COMPLETE, None, True),
    (PROFILE_INDIVIDUAL, (3098,), True),
    (PROFILE_INDIVIDUAL, (4,), False),
])
def test_defrost_status_kept_across_profiles(profile, selected, expected):
    assert point_enabled(profile, 3098, selected) is expected


def test_switch_setup_includes_status_without_write_permission():
    c = coordinator(1)
    entities = []
    asyncio.run(async_setup_entry(None, SimpleNamespace(runtime_data=c), entities.extend))
    assert len([e for e in entities if isinstance(e, NibeDefrostStatusSwitch)]) == 1


def test_defrost_enum_sensor_still_distinguishes_passive_and_active():
    definition = next(d for d in POINTS if d.point_id == 3098)
    c = coordinator(2)
    assert NibeSensor(c, definition).native_value == "passive"
    assert NibeDefrostStatusSwitch(c).is_on is True


def test_no_inferred_write_platform_even_with_bad_metadata():
    for maximum in (1, 2):
        p = point(1, writable=True)
        p["metadata"]["maxValue"] = maximum
        assert writable_platform_for_point(3098, p) is None


@pytest.mark.parametrize("lang,expected", [
    ("de", "Enteisung aktiv (EB101) – nur Anzeige"),
    ("en", "Defrost active (EB101) – read-only"),
])
def test_defrost_status_switch_translation(lang, expected):
    path = Path(__file__).resolve().parents[1] / "custom_components/nibe_local/translations" / f"{lang}.json"
    translations = json.loads(path.read_text(encoding="utf-8"))
    assert translations["entity"]["switch"]["defrost_status_switch"]["name"] == expected
