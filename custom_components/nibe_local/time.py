"""Writable time settings for NIBE Local REST."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up writable NIBE time entities."""
    coordinator: NibeCoordinator = entry.runtime_data
    entities = []
    for definition in POINTS:
        if definition.platform != "time":
            continue
        point = coordinator.point(definition.point_id)
        if not point:
            continue
        if not (point.get("metadata") or {}).get("isWritable", False):
            continue
        entities.append(NibeTime(coordinator, definition))
    async_add_entities(entities)


class NibeTime(NibePointEntity, TimeEntity):
    """NIBE time stored as seconds since midnight."""

    @property
    def native_value(self) -> time | None:
        """Return the NIBE value as a Home Assistant time."""
        value = raw_value(self.point or {})
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return None

        if not 0 <= seconds < 24 * 60 * 60:
            return None

        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return time(hour=hours, minute=minutes, second=seconds)

    async def async_set_value(self, value: time) -> None:
        """Write a Home Assistant time as seconds since midnight."""
        seconds = value.hour * 3600 + value.minute * 60 + value.second
        await self.coordinator.api.patch_point(self.definition.point_id, seconds)
        await self.coordinator.async_request_refresh()
