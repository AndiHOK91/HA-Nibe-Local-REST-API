"""AUX function 22070 must display its translated enum, never a numeric slider."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.nibe_local import number, sensor
from custom_components.nibe_local.const import POINTS
from custom_components.nibe_local.writable import writable_platform_for_point


def _coordinator(profile="individual"):
    point = {
        "metadata": {"variableId": 22070, "variableType": "integer",
                     "variableSize": "u8", "isWritable": True,
                     "minValue": 0, "maxValue": 69, "divisor": 1},
        "value": {"integerValue": 66, "isOk": True},
    }
    return SimpleNamespace(
        point=lambda pid: point if pid == 22070 else None,
        entity_enabled=lambda pid: pid == 22070,
        write_enabled=lambda pid: True,
        enabled_point_ids={22070},
        selected_writable_point_ids={22070} if profile == "individual" else None,
        entity_naming="home_assistant", instance_id="test", data={},
        last_update_success=True,
        api=SimpleNamespace(patch_point=AsyncMock()),
        async_refresh_point=AsyncMock(return_value=point),
    )


@pytest.mark.parametrize("profile", ["individual", "extended", "complete"])
def test_aux_function_66_is_a_named_enum_sensor_in_all_profiles(profile):
    coordinator = _coordinator(profile)
    numbers = []
    asyncio.run(number.async_setup_entry(None, SimpleNamespace(runtime_data=coordinator), numbers.extend))
    assert numbers == []
    sensors = []
    asyncio.run(sensor.async_setup_entry(None, SimpleNamespace(runtime_data=coordinator), sensors.extend))
    selected = [s for s in sensors if getattr(getattr(s, "definition", None), "point_id", None) == 22070]
    assert len(selected) == 1
    assert selected[0].native_value == "external_power_limit"
    assert selected[0].translation_key == "aux_modbus_function"
    assert selected[0].unique_id == "test_22070"
    coordinator.api.patch_point.assert_not_awaited()


def test_aux_function_number_classification_is_disabled():
    assert writable_platform_for_point(
        22070, _coordinator().point(22070)
    ) is None


def test_aux_function_translation_labels_are_distinct_from_aux_switch():
    for lang, label in [("de", "Aux von Modbus – Funktion"),
                        ("en", "AUX via Modbus – function")]:
        data = json.loads(
            (Path(__file__).resolve().parents[1]
             / "custom_components" / "nibe_local"
             / "translations" / f"{lang}.json").read_text(encoding="utf-8")
        )
        assert data["entity"]["sensor"]["aux_modbus_function"]["name"] == label
        assert "external_power_limit" in data["entity"]["sensor"]["aux_modbus_function"]["state"]


def test_old_number_entity_is_migrated_without_removing_sensor(monkeypatch):
    import custom_components.nibe_local as integration

    registry = MagicMock()
    registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique:
        "number.aux_function" if domain == "number" and unique == "entry_22070"
        else None
    )
    monkeypatch.setattr(integration.er, "async_get", lambda hass: registry)
    integration._remove_replaced_point_entities(None, SimpleNamespace(entry_id="entry"))
    registry.async_remove.assert_called_once_with("number.aux_function")
    assert all(
        call.args[0] != "sensor.aux_function"
        for call in registry.async_remove.call_args_list
    )
