"""Sensors for NIBE Local REST."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value, scaled_value

OPERATING_PRIORITY_MAP = {10: "Aus", 20: "Brauchwasser", 30: "Heizung", 40: "Pool", 60: "Kühlung"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    defs = [d for d in POINTS if d.platform == "sensor" and coordinator.point(d.point_id)]
    entities = [NibeSensor(coordinator, d) for d in defs]
    entities.append(NibeNotificationSensor(coordinator))
    async_add_entities(entities)


class NibeSensor(NibePointEntity, SensorEntity):
    @property
    def native_value(self):
        if self.definition.point_id == 1758:
            value = raw_value(self.point or {})
            return OPERATING_PRIORITY_MAP.get(value, value)

        value = scaled_value(self.point or {})
        if self.definition.point_id == 840 and value is not None:
            try:
                return 0 if float(value) > 720 else value
            except (TypeError, ValueError):
                return value
        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        point = self.point or {}
        md = point.get("metadata") or {}
        return md.get("shortUnit") or md.get("unit") or None

    @property
    def device_class(self):
        unit = self.native_unit_of_measurement
        if unit in {"°C", "°"}:
            return SensorDeviceClass.TEMPERATURE
        if unit == "A":
            return SensorDeviceClass.CURRENT
        if unit == "kW":
            return SensorDeviceClass.POWER
        if unit == "Hz":
            return SensorDeviceClass.FREQUENCY
        if unit in {"%RH"}:
            return SensorDeviceClass.HUMIDITY
        if unit == "bar":
            return SensorDeviceClass.PRESSURE
        if unit in {"h", "min", "s"}:
            return SensorDeviceClass.DURATION
        return None

    @property
    def state_class(self):
        unit = self.native_unit_of_measurement
        if self.definition.point_id in {1755, 2505, 2506, 2507}:
            return SensorStateClass.TOTAL_INCREASING
        if unit in {"°C", "°", "%", "%RH", "Hz", "A", "bar", "kW", "l/min", "min", "h", "s", "GM", "rpm"}:
            return SensorStateClass.MEASUREMENT
        return None


class NibeNotificationSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Aktive Meldungen"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.api.device_id}_notifications"

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> int:
        return len(((self.coordinator.data or {}).get("notifications") or {}).get("alarms", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"alarms": ((self.coordinator.data or {}).get("notifications") or {}).get("alarms", [])}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
