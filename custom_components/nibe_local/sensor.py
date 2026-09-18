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
    POINT_CURRENT_STATUS,
    POINT_DEFROST_REQUESTED,
    POINT_OPERATING_MODE_STATUS,
    POINT_OPERATING_PRIORITY,
    POINT_PERIODIC_HOT_WATER_DATE,
    POINT_TIME_TO_DEFROST,
)
from .coordinator import NibeCoordinator
from .entity import (
    NibeDiscoveredPointEntity,
    NibePointEntity,
    coordinator_device_info,
    local_api_point_name,
    entity_unique_id,
    point_value,
    raw_value,
    raw_value_is_sentinel,
    scaled_value,
)
from .system_status import (
    CURRENT_STATUS_STATE_OPTIONS,
    current_status_attributes,
    decode_current_status,
)
from .writable import description_enum_map, writable_platform_for_point

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
AUX_HEAT_MODE_MAP = {
    0: "off",
    1: "on",
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
        and not (
            coordinator.selected_writable_point_ids is not None
            and coordinator.write_enabled(definition.point_id)
            and writable_platform_for_point(
                definition.point_id,
                coordinator.point(definition.point_id),
            )
            is not None
        )
    ]
    entities: list[SensorEntity] = [
        NibeSensor(coordinator, definition) for definition in definitions
    ]
    known_ids = {definition.point_id for definition in POINTS}
    write_platform_ids = {
        definition.point_id
        for definition in POINTS
        if definition.platform in {"number", "select", "switch"}
    }
    read_only_known_write_ids = {
        point_id
        for point_id in coordinator.enabled_point_ids & write_platform_ids
        if not coordinator.write_enabled(point_id)
        or not bool(
            ((coordinator.point(point_id) or {}).get("metadata") or {}).get(
                "isWritable", False
            )
        )
    }
    generic_writable_ids = {
        point_id
        for point_id in coordinator.enabled_point_ids
        if coordinator.selected_writable_point_ids is not None
        and coordinator.write_enabled(point_id)
        and writable_platform_for_point(point_id, coordinator.point(point_id)) is not None
    }
    read_only_sensor_ids = (
        (coordinator.enabled_point_ids - known_ids) | read_only_known_write_ids
    ) - generic_writable_ids
    entities.extend(
        NibeDiscoveredSensor(coordinator, point_id)
        for point_id in sorted(read_only_sensor_ids)
    )
    entities.extend(
        [
            NibeNotificationSensor(coordinator),
            NibeLastConnectionErrorSensor(coordinator),
        ]
    )
    async_add_entities(entities)


class NibeDiscoveredSensor(NibeDiscoveredPointEntity, SensorEntity):
    """Read-only sensor for a NIBE point not exposed through another platform."""

    @property
    def native_value(self):
        return scaled_value(self.point or {})

    @property
    def native_unit_of_measurement(self) -> str | None:
        metadata = (self.point or {}).get("metadata") or {}
        return normalize_unit(metadata.get("shortUnit") or metadata.get("unit"))


class NibeSensor(NibePointEntity, SensorEntity):
    @property
    def available(self) -> bool:
        point = self.point
        if not self.coordinator.last_update_success or not point:
            return False

        # Point 840 is a duration value whose u16 maximum is a device-provided
        # special state. Keep the entity reachable instead of reporting a
        # communication failure; native_value remains unknown for that state.
        if self.definition.point_id == POINT_TIME_TO_DEFROST and raw_value(point) == 65535:
            return bool(point_value(point).get("isOk", True))

        return super().available

    @property
    def native_value(self):
        point = self.point or {}

        # Do this before the generic sentinel check. For this REST point the
        # u16 maximum is a special state, not a duration in minutes.
        if self.definition.point_id == POINT_TIME_TO_DEFROST and raw_value(point) == 65535:
            return None

        if raw_value_is_sentinel(point):
            return None

        if self.definition.point_id == POINT_OPERATING_PRIORITY:
            value = raw_value(point)
            return OPERATING_PRIORITY_MAP.get(value, value)

        if self.definition.point_id == POINT_CURRENT_STATUS:
            return decode_current_status(raw_value(point))

        if self.definition.point_id == POINT_OPERATING_MODE_STATUS:
            value = raw_value(point)
            try:
                return OPERATING_MODE_STATE_MAP.get(int(value), value)
            except (TypeError, ValueError):
                return value

        if self.definition.point_id == 1760:
            value = raw_value(point)
            try:
                return AUX_HEAT_MODE_MAP.get(int(value), value)
            except (TypeError, ValueError):
                return value

        if self.definition.point_id == POINT_PERIODIC_HOT_WATER_DATE:
            return periodic_hot_water_date(raw_value(point))

        if self.definition.point_id == POINT_DEFROST_REQUESTED:
            value = raw_value(point)
            try:
                return DEFROST_REQUESTED_MAP.get(int(value), "unknown")
            except (TypeError, ValueError):
                return "unknown"

        if self.definition.point_id == 22268:
            value = raw_value(point)
            try:
                numeric_value = int(value)
            except (TypeError, ValueError):
                return value
            return description_enum_map(point).get(numeric_value, value)

        return scaled_value(point)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.definition.point_id in {
            POINT_CURRENT_STATUS,
            POINT_PERIODIC_HOT_WATER_DATE,
        }:
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
        if self.definition.point_id == POINT_CURRENT_STATUS:
            return SensorDeviceClass.ENUM
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
    def options(self) -> list[str] | None:
        if self.definition.point_id == POINT_CURRENT_STATUS:
            return list(CURRENT_STATUS_STATE_OPTIONS)
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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes = dict(super().extra_state_attributes)
        point = self.point or {}

        if self.definition.point_id == POINT_TIME_TO_DEFROST:
            raw = raw_value(point)
            if raw == 65535:
                attributes["nibe_special_value"] = raw
                label = description_enum_map(point).get(65535)
                if label:
                    attributes["nibe_special_state"] = label

        if self.definition.point_id == POINT_CURRENT_STATUS:
            attributes.update(current_status_attributes(raw_value(point)))

        return attributes


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
        latest = alarms[0] if alarms else {}
        return {
            "alarm_ids": alarm_ids,
            "alarm_summary": summary,
            "latest_alarm_id": latest.get("alarm_id"),
            "latest_alarm_text": latest.get("text"),
            "latest_alarm_description": latest.get("description"),
            "latest_alarm_severity": latest.get("severity"),
            "latest_alarm_time": latest.get("time"),
            "latest_alarm_equipment": latest.get("equipment"),
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
