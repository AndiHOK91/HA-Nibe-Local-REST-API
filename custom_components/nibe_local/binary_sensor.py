"""Binary sensors for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import POINTS
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, coordinator_device_info, entity_unique_id, raw_value

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        NibeApiReachableBinarySensor(coordinator),
        NibeFallbackActiveBinarySensor(coordinator),
    ]
    entities.extend(
        NibeBinarySensor(coordinator, definition)
        for definition in POINTS
        if definition.platform == "binary_sensor"
        and coordinator.entity_enabled(definition.point_id)
        and coordinator.point(definition.point_id)
    )
    async_add_entities(entities)


class NibeBinarySensor(NibePointEntity, BinarySensorEntity):
    @property
    def device_class(self):
        if self.definition.point_id in {3097, 3098, 2683}:
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


class NibeApiReachableBinarySensor(CoordinatorEntity[NibeCoordinator], BinarySensorEntity):
    """Show whether the most recent regular coordinator poll succeeded."""

    _attr_has_entity_name = True
    _attr_translation_key = "api_reachable"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entity_unique_id(coordinator, "api_reachable")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)


class NibeFallbackActiveBinarySensor(CoordinatorEntity[NibeCoordinator], BinarySensorEntity):
    """Show whether bulk /points currently requires the individual-point fallback."""

    _attr_has_entity_name = True
    _attr_translation_key = "fallback_active"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entity_unique_id(coordinator, "fallback_active")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.bulk_fallback_active

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)
