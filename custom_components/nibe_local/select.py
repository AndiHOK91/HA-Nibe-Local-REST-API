"""Select entities for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    POINTS,
    POINT_HOT_WATER_DEMAND,
    POINT_OPERATING_MODE_SETTING,
    POINT_VENTILATION_MODE,
)
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, coordinator_device_info, raw_value

PARALLEL_UPDATES = 1


def supports_smart_mode(device: dict | None) -> bool:
    """Return whether the NIBE device response exposes Smart Mode support."""
    return isinstance(device, dict) and "smartMode" in device


def mapped_option(value: int | str | None, mapping: dict[int, str]) -> str | None:
    """Map enum values robustly when firmware returns numeric strings."""
    if value is None:
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return str(value)
    return mapping.get(normalized, str(value))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    entities: list[SelectEntity] = []

    device = (coordinator.data or {}).get("device")
    if supports_smart_mode(device):
        entities.append(NibeSmartModeSelect(coordinator))

    for definition in POINTS:
        if definition.platform != "select":
            continue
        point = coordinator.point(definition.point_id)
        if not point:
            continue
        if not (point.get("metadata") or {}).get("isWritable", False):
            continue
        entities.append(NibePointSelect(coordinator, definition))

    async_add_entities(entities)


class NibePointSelect(NibePointEntity, SelectEntity):
    """Select for explicitly mapped NIBE enum points."""

    ENUM_OPTIONS: dict[int, dict[int, str]] = {
        POINT_OPERATING_MODE_SETTING: {
            0: "auto",
            1: "manual",
            2: "auxiliary_heat_only",
        },
        POINT_HOT_WATER_DEMAND: {
            0: "low",
            1: "medium",
            2: "high",
        },
        POINT_VENTILATION_MODE: {
            0: "normal",
            1: "off",
            2: "reduced",
            3: "increased",
            4: "maximum",
        },
    }

    @property
    def _mapping(self) -> dict[int, str]:
        return self.ENUM_OPTIONS[self.definition.point_id]

    @property
    def options(self) -> list[str]:
        return list(self._mapping.values())

    @property
    def current_option(self) -> str | None:
        return mapped_option(raw_value(self.point or {}), self._mapping)

    async def async_select_option(self, option: str) -> None:
        reverse = {state: raw for raw, state in self._mapping.items()}
        if option not in reverse:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="select_invalid_option",
                translation_placeholders={"option": option},
            )

        await self.coordinator.api.patch_point(
            self.definition.point_id,
            reverse[option],
        )
        await self.coordinator.async_refresh_point(self.definition.point_id)

    @property
    def extra_state_attributes(self):
        attrs = dict(super().extra_state_attributes or {})
        attrs["raw_to_state"] = self._mapping
        return attrs


class NibeSmartModeSelect(CoordinatorEntity[NibeCoordinator], SelectEntity):
    """NIBE Smart Mode select."""

    _attr_has_entity_name = True
    _attr_translation_key = "smart_mode"
    _attr_options = ["normal", "away"]

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.device_id}_smart_mode"

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)

    @property
    def current_option(self) -> str | None:
        return ((self.coordinator.data or {}).get("device") or {}).get("smartMode")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.set_smart_mode(option)
        await self.coordinator.async_request_refresh()
