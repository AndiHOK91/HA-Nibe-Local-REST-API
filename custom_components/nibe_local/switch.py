"""Writable binary settings for NIBE Local REST."""
from __future__ import annotations

import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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

    # Virtual dashboard switch backed by ventilation mode point 3830:
    # ON -> 3 (Erhöht), OFF -> 0 (Normal).
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
    """Switch for the NIBE one-time hot-water increase.

    Point 4030 (remaining minutes) is the authoritative state:
    the switch stays ON while the remaining time is greater than zero.
    """

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
        """Refresh both the trigger point and remaining-minutes point."""
        await self.coordinator.async_refresh_point(4564)
        await self.coordinator.async_refresh_point(4030)

    async def _verify_turn_on(self) -> None:
        """Keep the optimistic ON state until NIBE exposes remaining minutes."""
        # NIBE applies "one-time increase" asynchronously. Reading too early can
        # still return zero minutes, which previously made the switch jump back.
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

        # After the grace period, fall back to the actual remaining-minutes
        # value even if NIBE never accepted the command.
        self._optimistic_state = None
        self.async_write_ha_state()

    async def _verify_turn_off(self) -> None:
        """Keep the switch visually OFF until NIBE confirms 0 remaining minutes.

        Point 4030 may still report the old remaining time for a few seconds
        after point 4564 was set to 0. Clearing the optimistic state too early
        made the switch jump back to ON. While shutdown is pending, the
        optimistic OFF state has priority over normal coordinator polls.
        """
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

        # Safety fallback: if NIBE has still not confirmed the shutdown after
        # the grace period, stop forcing OFF and show the actual reported state.
        self._optimistic_state = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        # 2 = Einmalige Erhöhung. Keep the UI ON until point 4030 confirms
        # that remaining hot-water boost minutes are greater than zero.
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
        # Deactivate the one-time hot-water increase via its writable command
        # point. Point 4030 is treated as read-only state/remaining time:
        # attempting to PATCH it causes HTTP 400 on the tested NIBE firmware.
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
        """Refresh point 3830 and return its current raw mode."""
        await self.coordinator.async_refresh_ventilation_state()
        value = raw_value(self.coordinator.point(3830) or {})
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    async def _verify_after_write(self) -> None:
        """Keep optimistic state until NIBE confirms the requested mode.

        NIBE can expose the old ventilation value briefly after the PATCH.
        Clearing the optimistic state on that first stale read caused the
        dashboard switch to jump back. We now keep it until a matching mode
        is actually read, or until the grace period expires.
        """
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

        # If NIBE did not confirm within the grace period, stop forcing the
        # optimistic state and show the actually reported ventilation mode.
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
        # 3 = Erhöht. 4 = Maximal is also considered an active Lüftung+ state.
        await self._set_mode(3, True, {3, 4})

    async def async_turn_off(self, **kwargs) -> None:
        # Off explicitly requests 0 = Normal.
        await self._set_mode(0, False, {0})

