"""Binary sensors for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    async_add_entities(
        NibeBinarySensor(coordinator, d)
        for d in POINTS
        if d.platform == "binary_sensor" and coordinator.point(d.point_id)
    )


class NibeBinarySensor(NibePointEntity, BinarySensorEntity):
    @property
    def device_class(self):
        if self.definition.point_id in {3097, 3098, 8060, 2683}:
            return BinarySensorDeviceClass.PROBLEM
        if self.definition.point_id in {2657, 2729, 3138, 1829}:
            return BinarySensorDeviceClass.RUNNING
        return None

    @property
    def is_on(self) -> bool | None:
        value = raw_value(self.point or {})
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower() not in {"", "0", "off", "false", "none"}
        return bool(value)
