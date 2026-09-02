"""Sensors for NIBE Local REST."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .alarms import normalize_alarms
from .const import (
    DOMAIN,
    POINTS,
    POINT_DEFROST_REQUESTED,
    POINT_OPERATING_MODE_STATUS,
    POINT_OPERATING_PRIORITY,
    POINT_PERIODIC_HOT_WATER_DATE,
    POINT_TIME_TO_DEFROST,
)
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, coordinator_device_info, raw_value, scaled_value

OPERATING_PRIORITY_MAP = {
    10: "off",
    20: "hot_water",
    30: "heating",
    40: "pool",
    60: "cooling",
}
# Backward-compatible label map for external imports.
OPERATING_MODE_MAP = {0: "Auto", 1: "Manuell", 2: "Nur Zusatzheizung"}
OPERATING_MODE_STATE_MAP = {
    0: "auto",
    1: "manual",
    2: "auxiliary_heat_only",
}
DEFROST_REQUESTED_MAP = {
    0: "off",
    1: "active",
    2: "passive",
}
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

    # Remove the legacy standalone poll timestamp entity introduced in 0.7.0.
    # The same value is now exposed as an attribute of the API connectivity sensor.
    entity_registry = er.async_get(hass)
    legacy_unique_id = f"{coordinator.api.device_id}_last_successful_poll"
    legacy_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, legacy_unique_id
    )
    if legacy_entity_id is not None:
        entity_registry.async_remove(legacy_entity_id)

    definitions = [
        definition
        for definition in POINTS
        if definition.platform == "sensor" and coordinator.point(definition.point_id)
    ]
    entities: list[SensorEntity] = [
        NibeSensor(coordinator, definition) for definition in definitions
    ]
    entities.extend(
        [
            NibeNotificationSensor(coordinator),
            NibeLastConnectionErrorSensor(coordinator),
        ]
    )
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
                return OPERATING_MODE_STATE_MAP.get(int(value), value)
            except (TypeError, ValueError):
                return value

        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return periodic_hot_water_date(raw_value(self.point or {}))

        if self.definition.point_id == POINT_DEFROST_REQUESTED:
            value = raw_value(self.point or {})
            try:
                return DEFROST_REQUESTED_MAP.get(int(value), "unknown")
            except (TypeError, ValueError):
                return "unknown"

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
        if self.definition.point_id == 781:
            return "GM"
        point = self.point or {}
        md = point.get("metadata") or {}
        unit = md.get("unit")
        short_unit = md.get("shortUnit")
        if unit == "°C":
            return "°C"
        return short_unit or unit or None

    @property
    def device_class(self):
        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return None
        if self.definition.point_id == 829:
            return SensorDeviceClass.ENERGY
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
        if self.definition.point_id in {599, 829, 1755, 1865, 2505, 2506, 2507}:
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
    _attr_translation_key = "notifications"

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
            else str(alarm.get("text") or "Unknown alarm")
            for alarm in alarms
        ]
        return {
            "alarm_ids": alarm_ids,
            "alarm_summary": summary,
            "alarms": alarms,
        }


class _NibeHealthTimestampSensor(CoordinatorEntity[NibeCoordinator], SensorEntity):
    """Base class for coordinator health timestamps."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)


class NibeLastConnectionErrorSensor(_NibeHealthTimestampSensor):
    """Timestamp of the most recent REST API connection error."""

    _attr_translation_key = "last_connection_error"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.device_id}_last_connection_error"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_connection_error
