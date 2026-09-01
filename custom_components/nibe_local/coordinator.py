"""Coordinator for NIBE Local REST."""
from __future__ import annotations

from datetime import timedelta
import logging
import time as time_module
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NibeApiError, NibeAuthError, NibeLocalApi
from .const import DOMAIN, POINTS, POINT_VENTILATION_MODE

_LOGGER = logging.getLogger(__name__)

FALLBACK_BACKOFF_STEPS_SECONDS = (30, 60, 120)


def fallback_backoff_delay(failure_streak: int) -> int:
    """Return the fallback delay for a consecutive bulk failure streak."""
    step = min(max(failure_streak, 0), len(FALLBACK_BACKOFF_STEPS_SECONDS) - 1)
    return FALLBACK_BACKOFF_STEPS_SECONDS[step]


def should_skip_fallback_scan(*, now: float, next_attempt_at: float) -> bool:
    """Return whether the expensive individual-point fallback is still backed off."""
    return now < next_attempt_at


def merge_point_updates(
    previous_points: dict[str, Any], fresh_points: dict[str, Any]
) -> dict[str, Any]:
    """Merge fresh fallback results while retaining previously known point values."""
    merged = dict(previous_points)
    merged.update(fresh_points)
    return merged


class NibeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: NibeLocalApi,
        interval: int,
        command_poll_delay_ms: int = 1000,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.api = api
        self.command_poll_delay_ms = command_poll_delay_ms
        self._fallback_failure_streak = 0
        self._next_fallback_attempt = 0.0

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            points = await self.api.get_points()
            if points:
                if self._fallback_failure_streak:
                    _LOGGER.info("Bulk /points is available again; fallback backoff reset")
                self._fallback_failure_streak = 0
                self._next_fallback_attempt = 0.0
            else:
                points = await self._get_points_with_backoff()

            device = await self.api.get_device()
            try:
                notifications = await self.api.get_notifications()
            except NibeAuthError:
                raise
            except NibeApiError as err:
                _LOGGER.debug("Notifications endpoint unavailable: %s", err)
                notifications = {"alarms": []}
            return {"points": points, "device": device, "notifications": notifications}
        except NibeAuthError as err:
            raise ConfigEntryAuthFailed(
                "NIBE API rejected the configured credentials"
            ) from err
        except NibeApiError as err:
            raise UpdateFailed(str(err)) from err

    async def _get_points_with_backoff(self) -> dict[str, Any]:
        """Fallback to individual point requests with a bounded retry backoff."""
        now = time_module.monotonic()
        previous_points = (self.data or {}).get("points") or {}

        if should_skip_fallback_scan(
            now=now, next_attempt_at=self._next_fallback_attempt
        ):
            _LOGGER.debug(
                "Bulk /points still returned no usable data; keeping previous values "
                "and delaying the next individual-point fallback for %.0f s",
                self._next_fallback_attempt - now,
            )
            return previous_points

        _LOGGER.warning(
            "Bulk /points response could not be normalized; falling back to "
            "individual point requests"
        )

        fresh_points: dict[str, Any] = {}
        for definition in POINTS:
            try:
                point = await self.api.get_point(definition.point_id)
            except NibeAuthError:
                raise
            except NibeApiError:
                continue
            metadata = point.get("metadata") if isinstance(point, dict) else None
            if isinstance(metadata, dict) and metadata.get("variableId") is not None:
                fresh_points[str(metadata["variableId"])] = point

        delay = fallback_backoff_delay(self._fallback_failure_streak)
        self._fallback_failure_streak += 1
        self._next_fallback_attempt = now + delay

        if fresh_points:
            _LOGGER.debug(
                "Individual-point fallback returned %d points; next full fallback "
                "scan in %d s if bulk /points stays unavailable",
                len(fresh_points),
                delay,
            )
        else:
            _LOGGER.warning(
                "Individual-point fallback returned no points; next full fallback "
                "scan in %d s",
                delay,
            )

        return merge_point_updates(previous_points, fresh_points)

    def point(self, point_id: int) -> dict[str, Any] | None:
        return (self.data or {}).get("points", {}).get(str(point_id))

    async def async_refresh_point(self, point_id: int) -> dict[str, Any] | None:
        """Refresh one NIBE point and publish it immediately."""
        try:
            point = await self.api.get_point(point_id)
        except NibeApiError as err:
            _LOGGER.debug("Targeted refresh of point %s failed: %s", point_id, err)
            return None

        metadata = point.get("metadata") if isinstance(point, dict) else None
        if not isinstance(metadata, dict) or metadata.get("variableId") is None:
            return None

        current = dict(self.data or {})
        points = dict(current.get("points") or {})
        points[str(metadata["variableId"])] = point
        current["points"] = points
        self.async_set_updated_data(current)
        return point

    async def async_refresh_ventilation_state(self) -> dict[str, Any] | None:
        """Refresh the ventilation mode once for all ventilation entities."""
        return await self.async_refresh_point(POINT_VENTILATION_MODE)
