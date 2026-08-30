"""Writable binary settings for NIBE Local REST."""
from __future__ import annotations

import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS, POINT_BY_ID
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value, scaled_value


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    entities = []
    for d in POINTS:
        if d.platform != "switch":
            continue
        point = coordinator.point(d.point_id)
        if not point or not (point.get("metadata") or {}).get("isWritable", False):
            continue

        if d.point_id == 4564:
            entities.append(NibeMoreHotWaterSwitch(coordinator))
        else:
            entities.append(NibeSwitch(coordinator, d))

    ventilation_point = coordinator.point(3830)
    if (
        ventilation_point
        and (ventilation_point.get("metadata") or {}).get("isWritable", False)
        and 3830 in POINT_BY_ID
    ):
        entities.append(NibeVentilationPlusSwitch(coordinator))

    async_add_entities(entities)


class NibeSwitch(NibePointEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        value = raw_value(self.point or {})
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower() not in {"", "0", "off", "false", "none"}
        return bool(value)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.api.patch_point(self.definition.point_id, 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api.patch_point(self.definition.point_id, 0)
        await self.coordinator.async_request_refresh()


class NibeMoreHotWaterSwitch(NibePointEntity, SwitchEntity):
    """Switch for NIBE one-time hot-water increase.

    Point 4564 is the command point. The actual active state is derived from
    point 4030 (remaining minutes for "Mehr Brauchwasser"). This avoids a
    short OFF flicker while the VVM applies the command asynchronously.
    """

    _attr_icon = "mdi:water-boiler-alert"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator, POINT_BY_ID[4564])
        self._optimistic_state: bool | None = None

    @property
    def name(self) -> str:
        return "Mehr Brauchwasser"

    @property
    def is_on(self) -> bool | None:
        minutes_point = self.coordinator.point(4030)
        minutes = scaled_value(minutes_point or {}) if minutes_point else None

        if minutes is not None:
            try:
                active = float(minutes) > 0
            except (TypeError, ValueError):
                active = False

            if active:
                return True

            if self._optimistic_state is True:
                return True

            return False

        return self._optimistic_state

    async def _verify_until_confirmed(self, turning_on: bool) -> None:
        await asyncio.sleep(self.coordinator.command_poll_delay_ms / 1000)

        for _ in range(10):
            await self.coordinator.async_refresh_point(4564)
            await self.coordinator.async_refresh_point(4030)

            minutes_point = self.coordinator.point(4030)
            minutes = scaled_value(minutes_point or {}) if minutes_point else None
            try:
                active = minutes is not None and float(minutes) > 0
            except (TypeError, ValueError):
                active = False

            if (turning_on and active) or (not turning_on and not active):
                self._optimistic_state = None
                self.async_write_ha_state()
                return

            await asyncio.sleep(1)

        self._optimistic_state = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        self._optimistic_state = True
        self.async_write_ha_state()
        try:
            await self.coordinator.api.patch_point(4564, 2)
            self.hass.async_create_task(self._verify_until_confirmed(True))
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api.patch_point(4564, 0)
        self.hass.async_create_task(self._verify_until_confirmed(False))


class NibeVentilationPlusSwitch(NibePointEntity, SwitchEntity):
    """Dashboard switch synchronized with the ventilation level select."""

    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator, POINT_BY_ID[3830])
        self._attr_unique_id = f"{coordinator.api.device_id}_ventilation_plus"
        self._optimistic_state: bool | None = None

    @property
    def name(self) -> str:
        return "Lüftung +"

    @property
    def is_on(self) -> bool | None:
        if self._optimistic_state is not None:
            return self._optimistic_state

        value = raw_value(self.point or {})
        if value is None:
            return None
        try:
            return int(value) in {3, 4}
        except (TypeError, ValueError):
            return False

    async def _refresh_both_ventilation_entities(self) -> None:
        await self.coordinator.async_refresh_ventilation_state()
        self._optimistic_state = None
        self.async_write_ha_state()

    async def _verify_after_configured_delay(self) -> None:
        await asyncio.sleep(self.coordinator.command_poll_delay_ms / 1000)
        await self._refresh_both_ventilation_entities()
        await asyncio.sleep(1)
        await self._refresh_both_ventilation_entities()

    async def _set_mode(self, mode: int, optimistic_on: bool) -> None:
        self._optimistic_state = optimistic_on
        self.async_write_ha_state()

        try:
            await self.coordinator.api.patch_point(3830, mode)
            self.hass.async_create_task(self._verify_after_configured_delay())
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_mode(3, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_mode(0, False)
