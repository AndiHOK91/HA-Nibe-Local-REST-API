"""Shared delayed REST write verification for writable NIBE point entities."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .entity import raw_value

_LOGGER = logging.getLogger(__name__)

# Verification remains bounded even if NIBE never applies the requested value.
VERIFY_DELAYS_SECONDS = (1.0, 1.0, 1.5, 2.0, 3.0, 3.0, 5.0, 5.0)


def raw_values_equal(actual: Any, expected: Any) -> bool:
    """Compare numeric REST values even if firmware serializes them as strings."""
    if actual is None:
        return False
    if isinstance(actual, bool) or isinstance(expected, bool):
        return actual == expected
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError, OverflowError):
        return actual == expected


class DelayedPointWriteMixin:
    """Keep a successfully requested value visible until confirmed or timed out.

    The optimistic value affects only Home Assistant presentation. The NIBE
    coordinator retains the actual last-read value at all times.
    """

    _pending_display_value: Any = None
    _pending_raw_value: Any = None
    _pending_verify_task: asyncio.Task[None] | None = None
    _verification_generation: int = 0

    async def _async_patch_and_verify(
        self, point_id: int, raw: int | str, display_value: Any
    ) -> None:
        """Write a REST point then verify readback without a transient UI reset."""
        self._verification_generation += 1
        generation = self._verification_generation
        self._cancel_pending_verification()
        self._pending_display_value = None
        self._pending_raw_value = None

        # Never present a rejected command as an accepted value.
        await self.coordinator.api.patch_point(point_id, raw)

        if getattr(self, "hass", None) is None:
            # Allows detached entity usage in migrations and platform tests.
            await self.coordinator.async_refresh_point(point_id)
            return

        self._pending_display_value = display_value
        self._pending_raw_value = raw
        self.async_write_ha_state()
        self._pending_verify_task = self.hass.async_create_task(
            self._async_verify_point_value(point_id, raw, generation)
        )

    async def _async_verify_point_value(
        self, point_id: int, expected: int | str, generation: int
    ) -> None:
        try:
            first_delay = getattr(self.coordinator, "command_poll_delay_ms", 1000) / 1000
            for delay in (first_delay, *VERIFY_DELAYS_SECONDS[1:]):
                await asyncio.sleep(delay)
                refreshed = await self.coordinator.async_refresh_point(point_id)
                if refreshed is None:
                    continue
                if raw_values_equal(raw_value(refreshed), expected):
                    return
            _LOGGER.warning(
                "NIBE point %s did not confirm written value within the readback window",
                point_id,
            )
        except asyncio.CancelledError:
            raise
        finally:
            # A newer command owns this entity's pending optimistic display.
            if self._verification_generation == generation:
                self._pending_display_value = None
                self._pending_raw_value = None
                if getattr(self, "hass", None) is not None:
                    self.async_write_ha_state()

    def _cancel_pending_verification(self) -> None:
        task = self._pending_verify_task
        if task is not None and not task.done():
            task.cancel()
        self._pending_verify_task = None

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_pending_verification()
        await super().async_will_remove_from_hass()
