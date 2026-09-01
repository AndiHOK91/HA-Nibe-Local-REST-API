"""Writable binary settings for NIBE Local REST."""
from __future__ import annotations

import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    POINTS,
    POINT_BY_ID,
    POINT_COOLING_ALLOWED,
    POINT_HEATING_ALLOWED,
    POINT_MORE_HOT_WATER,
    POINT_MORE_HOT_WATER_MINUTES,
    POINT_OPERATING_MODE_SETTING,
    POINT_VENTILATION_MODE,
)
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    entities = []
    for definition in POINTS:
        if definition.platform != "switch":
            continue
        point = coordinator.point(definition.point_id)
        if not point or not (point.get("metadata") or {}).get("isWritable", False):
            continue

        if definition.point_id == POINT_MORE_HOT_WATER:
            entities.append(NibeMoreHotWaterSwitch(coordinator))
        else:
            entities.append(NibeSwitch(coordinator, definition))

    ventilation_point = coordinator.point(POINT_VENTILATION_MODE)
    if (
        ventilation_point
        and (ventilation_point.get("metadata") or {}).get("isWritable", False)
        and POINT_VENTILATION_MODE in POINT_BY_ID
    ):
        entities.append(NibeVentilationPlusSwitch(coordinator))

    async_add_entities(entities)


def write_allowed_for_mode(point_id: int, mode: int | None) -> bool:
    """Return whether a mode-dependent heating/cooling point may be written."""
    if point_id not in {POINT_HEATING_ALLOWED, POINT_COOLING_ALLOWED}:
        return True
    if mode == 1:  # Manuell
        return True
    if mode == 2:  # Nur Zusatzheizung
        return point_id == POINT_HEATING_ALLOWED
    return False


def write_allowed_after_mode_refresh(
    point_id: int,
    mode: int | None,
    *,
    refresh_succeeded: bool,
) -> bool:
    """Return whether a protected write may proceed after refreshing the mode."""
    if point_id not in {POINT_HEATING_ALLOWED, POINT_COOLING_ALLOWED}:
        return True
    return refresh_succeeded and write_allowed_for_mode(point_id, mode)


class NibeSwitch(NibePointEntity, SwitchEntity):
    """Generic writable switch, with mode-dependent protection."""

    def _operating_mode(self) -> int | None:
        value = raw_value(self.coordinator.point(POINT_OPERATING_MODE_SETTING) or {})
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _write_allowed(self) -> bool:
        return write_allowed_for_mode(self.definition.point_id, self._operating_mode())

    @property
    def is_on(self) -> bool | None:
        value = raw_value(self.point or {})
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower() not in {"", "0", "off", "false", "none"}
        return bool(value)

    @property
    def extra_state_attributes(self):
        attrs = dict(super().extra_state_attributes or {})
        if self.definition.point_id in {POINT_HEATING_ALLOWED, POINT_COOLING_ALLOWED}:
            mode = self._operating_mode()
            attrs["operating_mode_raw"] = mode
            attrs["write_allowed"] = self._write_allowed()
        return attrs

    async def _ensure_write_allowed(self) -> None:
        if self.definition.point_id not in {POINT_HEATING_ALLOWED, POINT_COOLING_ALLOWED}:
            return

        refreshed = await self.coordinator.async_refresh_point(
            POINT_OPERATING_MODE_SETTING
        )
        if refreshed is None:
            raise HomeAssistantError(
                "Der aktuelle NIBE-Betriebsmodus konnte nicht geprüft werden. "
                "Die Änderung wurde vorsorglich nicht gesendet."
            )

        mode = self._operating_mode()
        if write_allowed_after_mode_refresh(
            self.definition.point_id,
            mode,
            refresh_succeeded=True,
        ):
            return

        mode_label = {0: "Auto", 1: "Manuell", 2: "Nur Zusatzheizung"}.get(
            mode, "Unbekannt"
        )
        point_label = (
            "Heizung zulassen"
            if self.definition.point_id == POINT_HEATING_ALLOWED
            else "Kühlung zulassen"
        )
        raise HomeAssistantError(
            f"{point_label} ist im Betriebsmodus {mode_label} nur lesbar."
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._ensure_write_allowed()
        await self.coordinator.api.patch_point(self.definition.point_id, 1)
        await self.coordinator.async_refresh_point(self.definition.point_id)

    async def async_turn_off(self, **kwargs) -> None:
        await self._ensure_write_allowed()
        await self.coordinator.api.patch_point(self.definition.point_id, 0)
        await self.coordinator.async_refresh_point(self.definition.point_id)


class NibeMoreHotWaterSwitch(NibePointEntity, SwitchEntity):
    """Switch for the NIBE one-time hot-water increase."""

    _attr_icon = "mdi:water-boiler-alert"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator, POINT_BY_ID[POINT_MORE_HOT_WATER])
        self._attr_unique_id = f"{coordinator.api.device_id}_more_hot_water"
        self._optimistic_state: bool | None = None
        self._verify_task: asyncio.Task[None] | None = None

    @property
    def name(self) -> str:
        return "Mehr Brauchwasser"

    @property
    def is_on(self) -> bool | None:
        if self._optimistic_state is not None:
            return self._optimistic_state

        minutes_point = self.coordinator.point(POINT_MORE_HOT_WATER_MINUTES)
        minutes = raw_value(minutes_point or {})
        if minutes is None:
            return None

        try:
            return float(minutes) > 0
        except (TypeError, ValueError):
            return False

    def _cancel_verify_task(self) -> None:
        if self._verify_task and not self._verify_task.done():
            self._verify_task.cancel()
        self._verify_task = None

    def _start_verify_task(self, coroutine) -> None:
        self._cancel_verify_task()
        self._verify_task = self.hass.async_create_task(coroutine)

    async def _refresh_hot_water_state(self) -> None:
        await self.coordinator.async_refresh_point(POINT_MORE_HOT_WATER)
        await self.coordinator.async_refresh_point(POINT_MORE_HOT_WATER_MINUTES)

    async def _verify_turn_on(self) -> None:
        delays = (
            self.coordinator.command_poll_delay_ms / 1000,
            1.0,
            2.0,
            3.0,
        )
        for delay in delays:
            await asyncio.sleep(delay)
            await self._refresh_hot_water_state()
            minutes = raw_value(
                self.coordinator.point(POINT_MORE_HOT_WATER_MINUTES) or {}
            )
            try:
                if minutes is not None and float(minutes) > 0:
                    self._optimistic_state = None
                    self.async_write_ha_state()
                    return
            except (TypeError, ValueError):
                pass
        self._optimistic_state = None
        self.async_write_ha_state()

    async def _verify_turn_off(self) -> None:
        delays = (
            self.coordinator.command_poll_delay_ms / 1000,
            1.0,
            1.5,
            2.0,
            3.0,
            5.0,
        )
        for delay in delays:
            await asyncio.sleep(delay)
            await self._refresh_hot_water_state()
            minutes = raw_value(
                self.coordinator.point(POINT_MORE_HOT_WATER_MINUTES) or {}
            )
            try:
                if minutes is not None and float(minutes) <= 0:
                    self._optimistic_state = None
                    self.async_write_ha_state()
                    return
            except (TypeError, ValueError):
                pass
        self._optimistic_state = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        self._cancel_verify_task()
        self._optimistic_state = True
        self.async_write_ha_state()
        try:
            await self.coordinator.api.patch_point(POINT_MORE_HOT_WATER, 2)
            self._start_verify_task(self._verify_turn_on())
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise

    async def async_turn_off(self, **kwargs) -> None:
        self._cancel_verify_task()
        self._optimistic_state = False
        self.async_write_ha_state()
        try:
            await self.coordinator.api.patch_point(POINT_MORE_HOT_WATER, 0)
            self._start_verify_task(self._verify_turn_off())
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_verify_task()
        await super().async_will_remove_from_hass()


class NibeVentilationPlusSwitch(NibePointEntity, SwitchEntity):
    """Dashboard switch synchronized with the ventilation level select."""

    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator, POINT_BY_ID[POINT_VENTILATION_MODE])
        self._attr_unique_id = f"{coordinator.api.device_id}_ventilation_plus"
        self._optimistic_state: bool | None = None
        self._expected_modes: set[int] | None = None
        self._verify_task: asyncio.Task[None] | None = None

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

    def _cancel_verify_task(self) -> None:
        if self._verify_task and not self._verify_task.done():
            self._verify_task.cancel()
        self._verify_task = None

    def _start_verify_task(self) -> None:
        self._cancel_verify_task()
        self._verify_task = self.hass.async_create_task(self._verify_after_write())

    async def _refresh_ventilation(self) -> int | None:
        await self.coordinator.async_refresh_ventilation_state()
        value = raw_value(self.coordinator.point(POINT_VENTILATION_MODE) or {})
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    async def _verify_after_write(self) -> None:
        delays = (
            self.coordinator.command_poll_delay_ms / 1000,
            1.0,
            1.5,
            2.0,
        )
        expected = set(self._expected_modes or ())
        for delay in delays:
            await asyncio.sleep(delay)
            mode = await self._refresh_ventilation()
            if mode is not None and mode in expected:
                self._optimistic_state = None
                self._expected_modes = None
                self.async_write_ha_state()
                return
        self._optimistic_state = None
        self._expected_modes = None
        self.async_write_ha_state()

    async def _set_mode(
        self,
        mode: int,
        optimistic_on: bool,
        expected_modes: set[int],
    ) -> None:
        self._cancel_verify_task()
        self._optimistic_state = optimistic_on
        self._expected_modes = expected_modes
        self.async_write_ha_state()
        try:
            await self.coordinator.api.patch_point(POINT_VENTILATION_MODE, mode)
            self._start_verify_task()
        except Exception:
            self._optimistic_state = None
            self._expected_modes = None
            self.async_write_ha_state()
            raise

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_mode(3, True, {3, 4})

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_mode(0, False, {0})

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_verify_task()
        await super().async_will_remove_from_hass()
