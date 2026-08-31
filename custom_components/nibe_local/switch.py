"""Writable binary settings for NIBE Local REST."""
from __future__ import annotations

import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import POINTS, POINT_BY_ID
from .coordinator import NibeCoordinator
from .entity import NibePointEntity, raw_value


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
    """Generic writable switch, with mode-dependent protection for 3920/3921."""

    def _operating_mode(self) -> int | None:
        value = raw_value(self.coordinator.point(3751) or {})
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _write_allowed(self) -> bool:
        point_id = self.definition.point_id
        if point_id not in {3920, 3921}:
            return True

        mode = self._operating_mode()
        if mode == 1:  # Manuell: Heizen und Kühlen schreibbar
            return True
        if mode == 2:  # Nur Zusatzheizung: nur Heizen schreibbar
            return point_id == 3920
        # Auto (0), unbekannter Wert oder fehlender Wert: sicher nur lesen.
        return False

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
        if self.definition.point_id in {3920, 3921}:
            mode = self._operating_mode()
            attrs["operating_mode_raw"] = mode
            attrs["write_allowed"] = self._write_allowed()
        return attrs

    async def _ensure_write_allowed(self) -> None:
        if self.definition.point_id not in {3920, 3921}:
            return

        # Vor jedem Schreibversuch den Betriebsmodus gezielt neu lesen, damit
        # eine kurz zuvor am Gerät oder in myUplink geänderte Einstellung gilt.
        await self.coordinator.async_refresh_point(3751)
        if self._write_allowed():
            return

        mode = self._operating_mode()
        mode_label = {0: "Auto", 1: "Manuell", 2: "Nur Zusatzheizung"}.get(
            mode, "Unbekannt"
        )
        point_label = "Heizung zulassen" if self.definition.point_id == 3920 else "Kühlung zulassen"
        raise HomeAssistantError(
            f"{point_label} ist im Betriebsmodus {mode_label} nur lesbar."
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._ensure_write_allowed()
        await self.coordinator.api.patch_point(self.definition.point_id, 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._ensure_write_allowed()
        await self.coordinator.api.patch_point(self.definition.point_id, 0)
        await self.coordinator.async_request_refresh()


class NibeMoreHotWaterSwitch(NibePointEntity, SwitchEntity):
    """Switch for the NIBE one-time hot-water increase."""

    _attr_icon = "mdi:water-boiler-alert"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator, POINT_BY_ID[4564])
        self._attr_unique_id = f"{coordinator.api.device_id}_more_hot_water"
        self._optimistic_state: bool | None = None

    @property
    def name(self) -> str:
        return "Mehr Brauchwasser"

    @property
    def is_on(self) -> bool | None:
        if self._optimistic_state is not None:
            return self._optimistic_state

        minutes_point = self.coordinator.point(4030)
        minutes = raw_value(minutes_point or {})
        if minutes is None:
            return None

        try:
            return float(minutes) > 0
        except (TypeError, ValueError):
            return False

    async def _refresh_hot_water_state(self) -> None:
        await self.coordinator.async_refresh_point(4564)
        await self.coordinator.async_refresh_point(4030)

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

            minutes = raw_value(self.coordinator.point(4030) or {})
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

            minutes = raw_value(self.coordinator.point(4030) or {})
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
        self._optimistic_state = True
        self.async_write_ha_state()

        try:
            await self.coordinator.api.patch_point(4564, 2)
            self.hass.async_create_task(self._verify_turn_on())
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise

    async def async_turn_off(self, **kwargs) -> None:
        self._optimistic_state = False
        self.async_write_ha_state()

        try:
            await self.coordinator.api.patch_point(4564, 0)
            self.hass.async_create_task(self._verify_turn_off())
        except Exception:
            self._optimistic_state = None
            self.async_write_ha_state()
            raise


class NibeVentilationPlusSwitch(NibePointEntity, SwitchEntity):
    """Dashboard switch synchronized with the ventilation level select."""

    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator, POINT_BY_ID[3830])
        self._attr_unique_id = f"{coordinator.api.device_id}_ventilation_plus"
        self._optimistic_state: bool | None = None
        self._expected_modes: set[int] | None = None

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

    async def _refresh_ventilation(self) -> int | None:
        await self.coordinator.async_refresh_ventilation_state()
        value = raw_value(self.coordinator.point(3830) or {})
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
        self._optimistic_state = optimistic_on
        self._expected_modes = expected_modes
        self.async_write_ha_state()

        try:
            await self.coordinator.api.patch_point(3830, mode)
            self.hass.async_create_task(self._verify_after_write())
        except Exception:
            self._optimistic_state = None
            self._expected_modes = None
            self.async_write_ha_state()
            raise

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_mode(3, True, {3, 4})

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_mode(0, False, {0})
