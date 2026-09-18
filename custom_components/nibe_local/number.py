"""Writable numeric settings for NIBE Local REST."""
from __future__ import annotations

import math

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, POINTS
from .coordinator import NibeCoordinator
from .entity import NibeDiscoveredPointEntity, NibePointEntity, scaled_value, to_raw
from .writable import writable_platform_for_point

PARALLEL_UPDATES = 1

# The current VVM S320 local REST metadata for point 3702 is malformed:
# minValue=55, maxValue=700, divisor=10. Generic scaling would expose 5.5 °C
# as the minimum although NIBE's actual range is 55.0–70.0 °C.
SAFE_NUMBER_LIMITS: dict[int, tuple[float, float]] = {
    3702: (55.0, 70.0),
}


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
        if not coordinator.entity_enabled(definition.point_id):
            continue
        if not coordinator.write_enabled(definition.point_id):
            continue
        point = coordinator.point(definition.point_id)
        if not point:
            continue
        if not (point.get("metadata") or {}).get("isWritable", False):
            continue
        entities.append(NibeNumber(coordinator, definition))

    curated_number_ids = {
        definition.point_id for definition in POINTS if definition.platform == "number"
    }
    for point_id in sorted(coordinator.enabled_point_ids):
        if (
            point_id in curated_number_ids
            or coordinator.selected_writable_point_ids is None
            or not coordinator.write_enabled(point_id)
        ):
            continue
        point = coordinator.point(point_id)
        if writable_platform_for_point(point_id, point) != "number":
            continue
        entities.append(NibeDiscoveredNumber(coordinator, point_id))

    async_add_entities(entities)


def _metadata_divisor(point: dict) -> int | float | None:
    """Return the raw metadata divisor without hiding invalid zero values."""
    md = point.get("metadata") or {}
    divisor = md.get("divisor", 1)
    return 1 if divisor is None else divisor


def metadata_limits(
    point: dict,
    current: float | None,
    point_id: int | None = None,
) -> tuple[float, float] | None:
    """Return trustworthy scaled limits or None when metadata is ambiguous."""
    if point_id in SAFE_NUMBER_LIMITS:
        return SAFE_NUMBER_LIMITS[point_id]

    md = point.get("metadata") or {}
    divisor = _metadata_divisor(point)
    minimum = md.get("minValue")
    maximum = md.get("maxValue")

    if not isinstance(divisor, (int, float)) or divisor <= 0:
        return None
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        return None
    if minimum > maximum:
        return None
    if minimum == 0 and maximum == 0:
        # Real Number entities always pass point_id and must never trust NIBE's
        # 0/0 convention as an actual writable range. Keep the historical helper
        # result only for callers without an entity/point context.
        if point_id is not None or current not in (None, 0):
            return None

    return float(minimum / divisor), float(maximum / divisor)


def value_is_representable(point: dict, value: float) -> bool:
    """Return whether a scaled value maps exactly to a NIBE integer raw value."""
    divisor = _metadata_divisor(point)
    if not isinstance(divisor, (int, float)) or divisor <= 0:
        return False
    raw_value = value * divisor
    return math.isclose(raw_value, round(raw_value), rel_tol=0.0, abs_tol=1e-9)


class NibeNumber(NibePointEntity, NumberEntity):
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
        limits = metadata_limits(
            self.point or {},
            current,
            self.definition.point_id,
        )
        if limits:
            return limits[0]
        return float(current if current is not None else 0)

    @property
    def native_max_value(self) -> float:
        current = self.native_value
        limits = metadata_limits(
            self.point or {},
            current,
            self.definition.point_id,
        )
        if limits:
            return limits[1]
        return float(current if current is not None else 0)

    @property
    def native_step(self) -> float:
        divisor = _metadata_divisor(self.point or {})
        return 1 / divisor if isinstance(divisor, (int, float)) and divisor > 0 else 1

    async def async_set_native_value(self, value: float) -> None:
        current = self.native_value
        limits = metadata_limits(
            self.point or {},
            current,
            self.definition.point_id,
        )
        if limits is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="number_limits_unavailable",
            )

        minimum, maximum = limits
        if not minimum <= value <= maximum:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="number_out_of_range",
                translation_placeholders={
                    "value": str(value),
                    "minimum": str(minimum),
                    "maximum": str(maximum),
                },
            )

        if not value_is_representable(self.point or {}, value):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="number_invalid_step",
                translation_placeholders={
                    "value": str(value),
                    "step": str(self.native_step),
                },
            )

        await self.coordinator.api.patch_point(
            self.definition.point_id,
            to_raw(self.point or {}, value),
        )
        await self.coordinator.async_refresh_point(self.definition.point_id)


class NibeDiscoveredNumber(NibeDiscoveredPointEntity, NumberEntity):
    """Generic numeric write entity selected explicitly in Individual mode."""

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
        limits = metadata_limits(self.point or {}, self.native_value, self.point_id)
        return limits[0] if limits else float(self.native_value or 0)

    @property
    def native_max_value(self) -> float:
        limits = metadata_limits(self.point or {}, self.native_value, self.point_id)
        return limits[1] if limits else float(self.native_value or 0)

    @property
    def native_step(self) -> float:
        divisor = _metadata_divisor(self.point or {})
        return 1 / divisor if isinstance(divisor, (int, float)) and divisor > 0 else 1

    async def async_set_native_value(self, value: float) -> None:
        limits = metadata_limits(self.point or {}, self.native_value, self.point_id)
        if limits is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="number_limits_unavailable",
            )

        minimum, maximum = limits
        if not minimum <= value <= maximum:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="number_out_of_range",
                translation_placeholders={
                    "value": str(value),
                    "minimum": str(minimum),
                    "maximum": str(maximum),
                },
            )

        if not value_is_representable(self.point or {}, value):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="number_invalid_step",
                translation_placeholders={
                    "value": str(value),
                    "step": str(self.native_step),
                },
            )

        await self.coordinator.api.patch_point(
            self.point_id,
            to_raw(self.point or {}, value),
        )
        await self.coordinator.async_refresh_point(self.point_id)
