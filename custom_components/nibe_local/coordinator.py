"""Coordinator for NIBE Local REST."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NibeApiError, NibeLocalApi
from .const import DOMAIN, POINTS, POINT_VENTILATION_MODE

_LOGGER = logging.getLogger(__name__)


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

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            points = await self.api.get_points()
            if not points:
                _LOGGER.warning(
                    "Bulk /points response could not be normalized; "
                    "falling back to individual point requests"
                )
                points = {}
                for definition in POINTS:
                    try:
                        point = await self.api.get_point(definition.point_id)
                    except NibeApiError:
                        continue
                    metadata = point.get("metadata") if isinstance(point, dict) else None
                    if isinstance(metadata, dict) and metadata.get("variableId") is not None:
                        points[str(metadata["variableId"])] = point

            device = await self.api.get_device()
            try:
                notifications = await self.api.get_notifications()
            except NibeApiError as err:
                _LOGGER.debug("Notifications endpoint unavailable: %s", err)
                notifications = {"alarms": []}
            return {"points": points, "device": device, "notifications": notifications}
        except NibeApiError as err:
            raise UpdateFailed(str(err)) from err

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
