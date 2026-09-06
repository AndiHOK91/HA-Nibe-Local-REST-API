"""Read-only time values for NIBE Local REST."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value

SECONDS_PER_DAY = 24 * 60 * 60
PARALLEL_UPDATES = 1

# NIBE firmware / public-local-API limitation, verified on a VVM S320:
# - REST variableType="time" points 3708 and 7849 report isWritable=true but
#   PATCH /api/v1/devices/0/points returns HTTP 400 even when writing the
#   unchanged current value.
# - For point 3708 / Modbus holding register 67, normal Modbus access is also
#   rejected while neighbouring holding registers work: FC03 -> 0x83/0x01,
#   FC06 -> 0x86/0x01, FC16 -> 0x90/0x01 (Illegal Function).
# Therefore time values remain visible as Home Assistant time entities, but
# writes are blocked locally until NIBE provides a working/publicly documented
# write mechanism. This is not a seconds-since-midnight conversion error.
TIME_WRITE_LIMITATION = (
    "NIBE firmware/API limitation: time values are read-only through the "
    "currently verified public local interfaces"
)


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
    """Encode a time as seconds since midnight without performing a write."""
    return value.hour * 3600 + value.minute * 60 + value.second


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up read-only NIBE time entities."""
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
        entities.append(NibeTime(coordinator, definition))
    async_add_entities(entities)


class NibeTime(NibePointEntity, TimeEntity):
    """NIBE time stored as seconds since midnight and exposed read-only."""

    @property
    def native_value(self) -> time | None:
        return time_from_seconds(raw_value(self.point or {}))

    async def async_set_value(self, value: time) -> None:
        """Reject writes locally because NIBE time writes are not supported."""
        raise HomeAssistantError(TIME_WRITE_LIMITATION)
