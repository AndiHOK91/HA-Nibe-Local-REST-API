"""Sensors for NIBE Local REST."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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
from .entity import (
    NibePointEntity,
    coordinator_device_info,
    local_api_point_name,
    entity_unique_id,
    raw_value,
    scaled_value,
)

PARALLEL_UPDATES = 0

OPERATING_PRIORITY_MAP = {
    10: "off",
    20: "hot_water",
    30: "heating",
    40: "pool",
    60: "cooling",
}
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
UNIT_NORMALIZATIONS = {
    "%RH": "%",
    "l/min": "L/min",
}


def normalize_unit(unit: str | None) -> str | None:
    """Normalize NIBE unit strings to Home Assistant canonical units."""
    if unit is None:
        return None
    return UNIT_NORMALIZATIONS.get(unit, unit)


def is_relative_humidity(point: dict[str, Any]) -> bool:
    """Return whether NIBE explicitly identifies the value as relative humidity."""
    metadata = point.get("metadata") or {}
    return "%RH" in {metadata.get("unit"), metadata.get("shortUnit")}


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
        if definition.platform == "sensor"
        and coordinator.entity_enabled(definition.point_id)
        and coordinator.point(definition.point_id)
    ]
    entities: list[SensorEntity] = [
        NibeSensor(coordinator, definition) for definition in definitions
    ]
    known_ids = {definition.point_id for definition in POINTS}
    entities.extend(
        NibeDiscoveredSensor(coordinator, point_id)
        for point_id in sorted(coordinator.enabled_point_ids - known_ids)
    )
    entities.extend(
        [
            NibeNotificationSensor(coordinator),
            NibeLastConnectionErrorSensor(coordinator),
        ]
    )
    async_add_entities(entities)


class NibeDiscoveredSensor(CoordinatorEntity[NibeCoordinator], SensorEntity):
    """Read-only sensor for a NIBE point not yet curated by the integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NibeCoordinator, point_id: int) -> None:
        super().__init__(coordinator)
        self.point_id = point_id
        self._attr_unique_id = entity_unique_id(coordinator, point_id)

    @property
    def point(self) -> dict[str, Any]:
        return self.coordinator.point(self.point_id) or {}

    @property
    def name(self) -> str:
        base = local_api_point_name(self.point) or f"Local API variable {self.point_id}"
        if self.coordinator.entity_naming == "technical":
            return f"{base} [ID {self.point_id}]"
        return base

    @property
    def native_value(self):
        return scaled_value(self.point)

    @property
    def native_unit_of_measurement(self) -> str | None:
        metadata = self.point.get("metadata") or {}
        return normalize_unit(metadata.get("shortUnit") or metadata.get("unit"))

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success or not self.point:
            return False
        return bool((self.point.get("value") or self.point.get("datavalue") or {}).get("isOk", True))

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        metadata = self.point.get("metadata") or {}
        return {
            "point_id": self.point_id,
            "description": str(self.point.get("description") or "").replace("\u00ad", "").strip(),
            "variable_type": metadata.get("variableType"),
            "is_writable": metadata.get("isWritable"),
            "discovered": True,
        }


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
        return normalize_unit(short_unit or unit or None)

    @property
    def device_class(self):
        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return None
        if self.definition.point_id == 829:
            return SensorDeviceClass.ENERGY
        point = self.point or {}
        unit = self.native_unit_of_measurement
        if unit in {"°C", "°"}:
            return SensorDeviceClass.TEMPERATURE
        if unit == "A":
            return SensorDeviceClass.CURRENT
        if unit == "kW":
            return SensorDeviceClass.POWER
        if unit == "Hz":
            return SensorDeviceClass.FREQUENCY
        if is_relative_humidity(point):
            return SensorDeviceClass.HUMIDITY
        if unit == "L/min":
            return SensorDeviceClass.VOLUME_FLOW_RATE
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
            "Hz",
            "A",
            "bar",
            "kW",
            "L/min",
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
        self._attr_unique_id = entity_unique_id(coordinator, "notifications")

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)

    @property
    def alarms(self) -> list[dict[str, Any]]:
        payload = (self.coordinator.data or {}).get("notifications") or {"alarms": []}
        return normalize_alarms(payload, self.coordinator.hass.config.language)

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
            else str(alarm.get("text") or "Alarm")
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
        self._attr_unique_id = entity_unique_id(coordinator, "last_connection_error")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_connection_error
