"""Writable numeric settings for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, scaled_value, to_raw


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    entities = []
    for d in POINTS:
        if d.platform != "number":
            continue
        point = coordinator.point(d.point_id)
        if not point:
            continue
        if not (point.get("metadata") or {}).get("isWritable", False):
            continue
        entities.append(NibeNumber(coordinator, d))
    async_add_entities(entities)


class NibeNumber(NibePointEntity, NumberEntity):
    @property
    def native_value(self) -> float | None:
        value = scaled_value(self.point or {})
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        # Punkt 3845 ist laut Anlagen-/myUplink-Anzeige ein Intervall in Monaten.
        # Die NIBE-Punkteliste liefert für diesen Punkt jedoch keine Einheit,
        # deshalb wird die fachlich bestätigte Einheit hier explizit ergänzt.
        if self.definition.point_id == 3845:
            return "Monate"
        md = (self.point or {}).get("metadata") or {}
        return md.get("shortUnit") or md.get("unit") or None

    @property
    def native_min_value(self) -> float:
        md = (self.point or {}).get("metadata") or {}
        divisor = md.get("divisor") or 1
        value = md.get("minValue")
        current = self.native_value
        if isinstance(value, (int, float)) and not (
            value == 0 and md.get("maxValue") == 0 and current not in (None, 0)
        ):
            return float(value / divisor)
        return float(current - 100 if current is not None else -100)

    @property
    def native_max_value(self) -> float:
        md = (self.point or {}).get("metadata") or {}
        divisor = md.get("divisor") or 1
        value = md.get("maxValue")
        current = self.native_value
        if isinstance(value, (int, float)) and not (
            value == 0 and md.get("minValue") == 0 and current not in (None, 0)
        ):
            return float(value / divisor)
        return float(current + 100 if current is not None else 100)

    @property
    def native_step(self) -> float:
        md = (self.point or {}).get("metadata") or {}
        divisor = md.get("divisor") or 1
        return 1 / divisor if divisor else 1

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.patch_point(self.definition.point_id, to_raw(self.point or {}, value))
        await self.coordinator.async_request_refresh()
