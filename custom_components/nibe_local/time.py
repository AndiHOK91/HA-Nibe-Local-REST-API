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

SECONDS_PER_DAY = 24 * 60 * 60
PARALLEL_UPDATES = 1


def time_from_seconds(raw: int | str | None) -> time | None:
    """Decode NIBE seconds since midnight to a time value."""
    try:
        seconds = int(raw)
    except (TypeError, ValueError):
        return None

    if not 0 <= seconds < SECONDS_PER_DAY:
        return None

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return time(hour=hours, minute=minutes, second=seconds)


def seconds_from_time(value: time) -> int:
    """Encode a time value as NIBE seconds since midnight."""
    return value.hour * 3600 + value.minute * 60 + value.second


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
        if not coordinator.entity_enabled(definition.point_id):
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
        return time_from_seconds(raw_value(self.point or {}))

    async def async_set_value(self, value: time) -> None:
        await self.coordinator.api.patch_point(
            self.definition.point_id,
            seconds_from_time(value),
        )
        await self.coordinator.async_refresh_point(self.definition.point_id)
