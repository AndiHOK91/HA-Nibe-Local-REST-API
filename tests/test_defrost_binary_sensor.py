from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.nibe_local.binary_sensor import NibeBinarySensor
from custom_components.nibe_local.const import PointDef


def _entity_for(point_id: int) -> NibeBinarySensor:
    entity = object.__new__(NibeBinarySensor)
    entity.definition = PointDef(point_id, "test", "heat_pump", "binary_sensor")
    return entity


def test_defrost_uses_running_device_class() -> None:
    assert _entity_for(3098).device_class == BinarySensorDeviceClass.RUNNING


def test_protection_mode_remains_problem_device_class() -> None:
    assert _entity_for(3097).device_class == BinarySensorDeviceClass.PROBLEM
