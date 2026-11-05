from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.nibe_local.binary_sensor import NibeBinarySensor
from custom_components.nibe_local.const import PointDef, POINTS


def _entity_for(point_id: int) -> NibeBinarySensor:
    entity = object.__new__(NibeBinarySensor)
    entity.definition = PointDef(point_id, "test", "heat_pump", "binary_sensor")
    return entity


def test_defrost_is_one_status_sensor() -> None:
    definitions = [point for point in POINTS if point.point_id == 3098]
    assert len(definitions) == 1
    assert definitions[0].platform == "sensor"


def test_protection_mode_remains_problem_device_class() -> None:
    assert _entity_for(3097).device_class == BinarySensorDeviceClass.PROBLEM
