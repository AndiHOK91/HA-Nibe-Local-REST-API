"""Select entities for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    coordinator: NibeCoordinator = entry.runtime_data
    entities: list[SelectEntity] = [NibeSmartModeSelect(coordinator)]

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
    ENUM_LABELS: dict[int, dict[int, str]] = {
        3830: {
            0: "Normal",
            1: "Aus",
            2: "Reduziert",
            3: "Erhöht",
            4: "Maximal",
        },
        4729: {0: "Auto", 1: "Manuell"},
        4745: {0: "Auto", 1: "Manuell"},
        4778: {0: "Auto", 1: "Manuell"},
        4821: {0: "Auto", 1: "Manuell"},
    }

    HOT_WATER_DEMAND_LABELS = {
        0: "Niedrig",
        1: "Mittel",
        2: "Hoch",
    }

    def _mapping(self) -> dict[int, str] | None:
        point_id = self.definition.point_id
        if point_id == 3697:
            return self.HOT_WATER_DEMAND_LABELS
        return self.ENUM_LABELS.get(point_id)

    @property
    def options(self) -> list[str]:
        mapping = self._mapping()
        if mapping:
            return list(mapping.values())

        point = self.point or {}
        md = point.get("metadata") or {}
        minimum = md.get("minValue")
        maximum = md.get("maxValue")
        current = raw_value(point)

        if isinstance(minimum, int) and isinstance(maximum, int):
            if minimum <= maximum and (maximum - minimum) <= 50:
                return [str(value) for value in range(minimum, maximum + 1)]

        if isinstance(current, int):
            return [str(current)]
        if isinstance(current, str) and current:
            return [current]
        return []

    @property
    def current_option(self) -> str | None:
        value = raw_value(self.point or {})
        if value is None:
            return None

        mapping = self._mapping()
        if mapping and isinstance(value, int):
            return mapping.get(value, str(value))
        return str(value)

    async def async_select_option(self, option: str) -> None:
        mapping = self._mapping()
        if mapping:
            reverse = {label: raw for raw, label in mapping.items()}
            if option not in reverse:
                raise ValueError(f"Unknown option {option!r}")
            value: int | str = reverse[option]
        else:
            try:
                value = int(option)
            except ValueError:
                value = option

        await self.coordinator.api.patch_point(self.definition.point_id, value)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self):
        attrs = dict(super().extra_state_attributes or {})
        mapping = self._mapping()
        if mapping:
            attrs["raw_to_label"] = mapping
        return attrs


class NibeSmartModeSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Smart Mode"
    _attr_options = ["normal", "away"]

    def __init__(self, coordinator: NibeCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.api.device_id}_smart_mode"

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        return ((self.coordinator.data or {}).get("device") or {}).get("smartMode")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.set_smart_mode(option)
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
