"""Writable numeric settings for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS, POINT_BWZ_OPERATING_TIME, POINT_BWZ_STANDSTILL_TIME
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, scaled_value, to_raw


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    entities = []
    for definition in POINTS:
        if definition.platform != "number":
            continue
        point = coordinator.point(definition.point_id)
        if not point:
            continue
        if not (point.get("metadata") or {}).get("isWritable", False):
            continue
        entities.append(NibeNumber(coordinator, definition))
    async_add_entities(entities)


def metadata_limits(point: dict, current: float | None) -> tuple[float, float] | None:
    """Return trustworthy scaled limits or None when metadata is ambiguous."""
    md = point.get("metadata") or {}
    divisor = md.get("divisor") or 1
    minimum = md.get("minValue")
    maximum = md.get("maxValue")

    if not isinstance(divisor, (int, float)) or divisor == 0:
        return None
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        return None
    if minimum > maximum:
        return None
    if minimum == 0 and maximum == 0 and current not in (None, 0):
        return None

    return float(minimum / divisor), float(maximum / divisor)


class NibeNumber(NibePointEntity, NumberEntity):
    @property
    def name(self) -> str:
        if self.definition.point_id == POINT_BWZ_OPERATING_TIME:
            return "BWZ Betriebszeit"
        if self.definition.point_id == POINT_BWZ_STANDSTILL_TIME:
            return "BWZ Stillstandszeit"
        return super().name

    @property
    def native_value(self) -> float | None:
        value = scaled_value(self.point or {})
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        md = (self.point or {}).get("metadata") or {}
        return md.get("shortUnit") or md.get("unit") or None

    @property
    def native_min_value(self) -> float:
        current = self.native_value
        limits = metadata_limits(self.point or {}, current)
        if limits:
            return limits[0]
        return float(current if current is not None else 0)

    @property
    def native_max_value(self) -> float:
        current = self.native_value
        limits = metadata_limits(self.point or {}, current)
        if limits:
            return limits[1]
        return float(current if current is not None else 0)

    @property
    def native_step(self) -> float:
        md = (self.point or {}).get("metadata") or {}
        divisor = md.get("divisor") or 1
        return 1 / divisor if isinstance(divisor, (int, float)) and divisor else 1

    async def async_set_native_value(self, value: float) -> None:
        current = self.native_value
        limits = metadata_limits(self.point or {}, current)
        if limits is None:
            raise HomeAssistantError(
                "NIBE liefert für diesen Wert keine verlässlichen Min-/Max-Grenzen; "
                "der Schreibvorgang wurde aus Sicherheitsgründen blockiert."
            )

        minimum, maximum = limits
        if not minimum <= value <= maximum:
            raise HomeAssistantError(
                f"Wert {value} liegt außerhalb des erlaubten Bereichs "
                f"{minimum} bis {maximum}."
            )

        await self.coordinator.api.patch_point(
            self.definition.point_id,
            to_raw(self.point or {}, value),
        )
        await self.coordinator.async_refresh_point(self.definition.point_id)
