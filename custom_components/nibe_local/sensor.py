"""Sensors for NIBE Local REST."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .alarms import normalize_alarms
from .const import (
    POINTS,
    POINT_DEFROST_REQUESTED,
    POINT_OPERATING_MODE_STATUS,
    POINT_OPERATING_PRIORITY,
    POINT_PERIODIC_HOT_WATER_DATE,
    POINT_TIME_TO_DEFROST,
)
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value, scaled_value

OPERATING_PRIORITY_MAP = {
    10: "Aus",
    20: "Brauchwasser",
    30: "Heizung",
    40: "Pool",
    60: "Kühlung",
}
OPERATING_MODE_MAP = {0: "Auto", 1: "Manuell", 2: "Nur Zusatzheizung"}
DEFROST_REQUESTED_MAP = {0: "Aus", 1: "Aktiv", 2: "Passiv"}
PERIODIC_HOT_WATER_DATE_EPOCH = date(2010, 1, 1)


def periodic_hot_water_date(raw: int | str | None) -> str | None:
    """Decode NIBE day count to DD.MM.YYYY."""
    try:
        days = int(raw)
        if days < 0:
            return None
        next_date = PERIODIC_HOT_WATER_DATE_EPOCH + timedelta(days=days)
        return next_date.strftime("%d.%m.%Y")
    except (TypeError, ValueError, OverflowError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    definitions = [
        definition
        for definition in POINTS
        if definition.platform == "sensor" and coordinator.point(definition.point_id)
    ]
    entities = [NibeSensor(coordinator, definition) for definition in definitions]
    entities.append(NibeNotificationSensor(coordinator))
    async_add_entities(entities)


class NibeSensor(NibePointEntity, SensorEntity):
    @property
    def native_value(self):
        if self.definition.point_id == POINT_OPERATING_PRIORITY:
            value = raw_value(self.point or {})
            return OPERATING_PRIORITY_MAP.get(value, value)

        if self.definition.point_id == POINT_OPERATING_MODE_STATUS:
            value = raw_value(self.point or {})
            try:
                return OPERATING_MODE_MAP.get(int(value), value)
            except (TypeError, ValueError):
                return value

        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return periodic_hot_water_date(raw_value(self.point or {}))

        if self.definition.point_id == POINT_DEFROST_REQUESTED:
            value = raw_value(self.point or {})
            try:
                return DEFROST_REQUESTED_MAP.get(int(value), "Unbekannt")
            except (TypeError, ValueError):
                return "Unbekannt"

        value = scaled_value(self.point or {})

        if self.definition.point_id == POINT_TIME_TO_DEFROST:
            try:
                if value is not None and float(value) > 720:
                    return 0
            except (TypeError, ValueError):
                pass

        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return None
        point = self.point or {}
        md = point.get("metadata") or {}
        return md.get("shortUnit") or md.get("unit") or None

    @property
    def device_class(self):
        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return None
        unit = self.native_unit_of_measurement
        if unit in {"°C", "°"}:
            return SensorDeviceClass.TEMPERATURE
        if unit == "A":
            return SensorDeviceClass.CURRENT
        if unit == "kW":
            return SensorDeviceClass.POWER
        if unit == "Hz":
            return SensorDeviceClass.FREQUENCY
        if unit == "%RH":
            return SensorDeviceClass.HUMIDITY
        if unit == "bar":
            return SensorDeviceClass.PRESSURE
        if unit in {"h", "min", "s"}:
            return SensorDeviceClass.DURATION
        return None

    @property
    def state_class(self):
        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return None
        unit = self.native_unit_of_measurement
        if self.definition.point_id in {599, 1755, 1865, 2505, 2506, 2507}:
            return SensorStateClass.TOTAL_INCREASING
        if unit in {
            "°C",
            "°",
            "%",
            "%RH",
            "Hz",
            "A",
            "bar",
            "kW",
            "l/min",
            "min",
            "h",
            "s",
            "GM",
            "rpm",
        }:
            return SensorStateClass.MEASUREMENT
        return None


class NibeNotificationSensor(CoordinatorEntity[NibeCoordinator], SensorEntity):
    """Read-only sensor for active NIBE alarms/notifications."""

    _attr_has_entity_name = True
    _attr_name = "Aktive Meldungen"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.device_id}_notifications"

    @property
    def alarms(self) -> list[dict[str, Any]]:
        payload = (self.coordinator.data or {}).get("notifications") or {"alarms": []}
        return normalize_alarms(payload)

    @property
    def native_value(self) -> int:
        return len(self.alarms)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        alarms = self.alarms
        alarm_ids = [
            alarm["alarm_id"]
            for alarm in alarms
            if alarm.get("alarm_id") is not None
        ]
        summary = [
            f'{alarm["alarm_id"]} - {alarm["text"]}'
            if alarm.get("alarm_id") is not None
            else str(alarm.get("text") or "Unbekannter Alarm")
            for alarm in alarms
        ]
        return {
            "alarm_ids": alarm_ids,
            "alarm_summary": summary,
            "alarms": alarms,
        }
