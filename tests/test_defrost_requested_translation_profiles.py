"""Regression coverage for translated defrost request across entity profiles."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.nibe_local.const import POINTS, POINT_DEFROST_REQUESTED
from custom_components.nibe_local.profiles import (
    PROFILE_COMPLETE,
    PROFILE_EXTENDED,
    PROFILE_INDIVIDUAL,
    PROFILE_STANDARD,
    point_enabled,
)
from custom_components.nibe_local.sensor import NibeSensor, async_setup_entry
from custom_components.nibe_local.writable import writable_platform_for_point


TRANSLATIONS = (
    Path(__file__).resolve().parents[1]
    / "custom_components" / "nibe_local" / "translations"
)


def defrost_point(value: int, *, writable: bool = False) -> dict:
    return {
        "metadata": {
            "variableId": POINT_DEFROST_REQUESTED,
            "variableType": "integer",
            "isWritable": writable,
            "divisor": 1,
            "minValue": 0,
            "maxValue": 2,
        },
        "value": {"integerValue": value, "isOk": True},
    }


@pytest.mark.parametrize("raw,expected", [(0, "off"), (1, "active"), (2, "passive"), (3, "unknown")])
def test_defrost_request_8060_is_enum(raw, expected):
    point = defrost_point(raw)
    coordinator = SimpleNamespace(
        point=lambda pid: point if pid == POINT_DEFROST_REQUESTED else None,
        entity_naming="home_assistant",
        instance_id="test",
    )
    definition = next(p for p in POINTS if p.point_id == POINT_DEFROST_REQUESTED)
    entity = NibeSensor(coordinator, definition)
    assert entity.device_class == SensorDeviceClass.ENUM
    assert entity.native_value == expected
    assert expected in entity.options
    assert entity.translation_key == "defrost_requested"


@pytest.mark.parametrize("language,off,active,passive", [
    ("de", "Aus", "Aktiv", "Passiv"),
    ("en", "Off", "Active", "Passive"),
])
def test_defrost_requested_translations(language, off, active, passive):
    translations = json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
    states = translations["entity"]["sensor"]["defrost_requested"]["state"]
    assert (states["off"], states["active"], states["passive"]) == (off, active, passive)


@pytest.mark.parametrize("profile,selected,expected", [
    (PROFILE_STANDARD, None, False),
    (PROFILE_EXTENDED, None, True),
    (PROFILE_COMPLETE, None, True),
    (PROFILE_INDIVIDUAL, [8060], True),
    (PROFILE_INDIVIDUAL, [4], False),
])
def test_defrost_request_profile_selection(profile, selected, expected):
    assert point_enabled(profile, POINT_DEFROST_REQUESTED, selected) is expected


def test_defrost_request_cannot_be_mistaken_for_a_write_switch():
    for max_value in (1, 2):
        point = defrost_point(1, writable=True)
        point["metadata"]["maxValue"] = max_value
        assert writable_platform_for_point(POINT_DEFROST_REQUESTED, point) is None


def test_defrost_requested_remains_read_only_even_if_selected_for_writing():
    point = defrost_point(1, writable=True)
    coordinator = SimpleNamespace(
        point=lambda pid: point if pid == POINT_DEFROST_REQUESTED else None,
        entity_enabled=lambda pid: pid == POINT_DEFROST_REQUESTED,
        write_enabled=lambda pid: pid == POINT_DEFROST_REQUESTED,
        selected_writable_point_ids=(POINT_DEFROST_REQUESTED,),
        enabled_point_ids={POINT_DEFROST_REQUESTED},
        entity_naming="home_assistant",
        instance_id="test",
        last_update_success=True,
    )
    entities = []
    asyncio.run(async_setup_entry(None, SimpleNamespace(runtime_data=coordinator), entities.extend))
    target = [
        e for e in entities
        if getattr(getattr(e, "definition", None), "point_id", None)
        == POINT_DEFROST_REQUESTED
    ]
    assert len(target) == 1
    assert target[0].device_class == SensorDeviceClass.ENUM
