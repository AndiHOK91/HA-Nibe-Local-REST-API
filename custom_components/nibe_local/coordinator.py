"""Coordinator for NIBE Local REST."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import time as time_module
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import NibeApiError, NibeAuthError, NibeLocalApi, async_resolve_host_ip
from .const import DOMAIN, POINTS, POINT_VENTILATION_MODE

_LOGGER = logging.getLogger(__name__)

FALLBACK_BACKOFF_STEPS_SECONDS = (30, 60, 120)
CONNECTION_NOTIFICATION_DELAY_SECONDS = 120

_NOTIFICATION_FALLBACK_MESSAGES = {
    "auth_rejected_notification": (
        "{label}: The stored credentials were rejected by the REST API. "
        "Please update the integration credentials."
    ),
    "connection_unreachable_notification": (
        "{label}: The local REST API has been unreachable for at least 2 minutes. "
        "Please check the network, NIBE device, and REST API."
    ),
}


def fallback_backoff_delay(failure_streak: int) -> int:
    """Return the fallback delay for a consecutive bulk failure streak."""
    step = min(max(failure_streak, 0), len(FALLBACK_BACKOFF_STEPS_SECONDS) - 1)
    return FALLBACK_BACKOFF_STEPS_SECONDS[step]


def should_skip_fallback_scan(
    *,
    now: float,
    next_attempt_at: float,
    has_previous_points: bool = True,
) -> bool:
    """Return whether the expensive individual-point fallback is still backed off."""
    return has_previous_points and now < next_attempt_at


def merge_point_updates(
    previous_points: dict[str, Any], fresh_points: dict[str, Any]
) -> dict[str, Any]:
    """Merge fresh fallback results while retaining previously known point values."""
    merged = dict(previous_points)
    merged.update(fresh_points)
    return merged


def connection_failure_notification_due(
    *,
    now: float,
    failure_started_at: float | None,
    delay: int = CONNECTION_NOTIFICATION_DELAY_SECONDS,
) -> bool:
    """Return whether a connection failure has lasted long enough to notify."""
    return failure_started_at is not None and now - failure_started_at >= delay


def auth_failure_notification_due(*, notification_active: bool) -> bool:
    """Return whether an authentication failure notification should be created."""
    return not notification_active


class NibeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: NibeLocalApi,
        interval: int,
        command_poll_delay_ms: int = 1000,
        device_name: str = "NIBE Local REST API",
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.api = api
        self.command_poll_delay_ms = command_poll_delay_ms
        self.device_name = device_name
        self._fallback_failure_streak = 0
        self._next_fallback_attempt = 0.0
        self._connection_failure_started_at: float | None = None
        self._connection_notification_active = False
        self._auth_notification_active = False
        self.bulk_fallback_active = False
        self.last_successful_poll: datetime | None = None
        self.last_connection_error: datetime | None = None

    @property
    def _auth_notification_id(self) -> str:
        return f"{DOMAIN}_{self.api.device_id}_auth"

    @property
    def _connection_notification_id(self) -> str:
        return f"{DOMAIN}_{self.api.device_id}_connection"

    async def _connection_label(self) -> str:
        """Return a device/host/IP label for user-facing messages."""
        ip_address = await async_resolve_host_ip(self.api.host)
        return f"{self.device_name} – Host: {self.api.host} – IP: {ip_address or '–'}"

    async def _translated_message(self, key: str, **placeholders: str) -> str:
        """Return a localized integration message with English fallback."""
        translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "exceptions",
            {DOMAIN},
        )
        translation_key = f"component.{DOMAIN}.exceptions.{key}.message"
        template = translations.get(
            translation_key,
            _NOTIFICATION_FALLBACK_MESSAGES.get(key, key),
        )
        try:
            return template.format(**placeholders)
        except KeyError:
            return template

    async def _notify_auth_failure(self) -> None:
        """Create the authentication failure notification once per outage."""
        if not auth_failure_notification_due(
            notification_active=self._auth_notification_active
        ):
            return

        label = await self._connection_label()
        message = await self._translated_message(
            "auth_rejected_notification",
            label=label,
        )
        persistent_notification.async_create(
            self.hass,
            message,
            title="NIBE Local REST API",
            notification_id=self._auth_notification_id,
        )
        self._auth_notification_active = True

    async def _record_connection_failure(self) -> None:
        """Notify only after the REST API has been unreachable for two minutes."""
        now = time_module.monotonic()
        self.last_connection_error = dt_util.utcnow()
        if self._connection_failure_started_at is None:
            self._connection_failure_started_at = now
            return

        if self._connection_notification_active or not connection_failure_notification_due(
            now=now,
            failure_started_at=self._connection_failure_started_at,
        ):
            return

        label = await self._connection_label()
        message = await self._translated_message(
            "connection_unreachable_notification",
            label=label,
        )
        persistent_notification.async_create(
            self.hass,
            message,
            title="NIBE Local REST API",
            notification_id=self._connection_notification_id,
        )
        self._connection_notification_active = True

    def _record_success(self) -> None:
        """Record a successful poll and clear stale connection/auth notifications."""
        self.last_successful_poll = dt_util.utcnow()
        self._connection_failure_started_at = None
        self._connection_notification_active = False
        self._auth_notification_active = False
        persistent_notification.async_dismiss(
            self.hass, self._connection_notification_id
        )
        persistent_notification.async_dismiss(self.hass, self._auth_notification_id)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            points = await self.api.get_points()
            if points:
                self.bulk_fallback_active = False
                if self._fallback_failure_streak:
                    _LOGGER.info("Bulk /points is available again; fallback backoff reset")
                self._fallback_failure_streak = 0
                self._next_fallback_attempt = 0.0
            else:
                self.bulk_fallback_active = True
                points = await self._get_points_with_backoff()

            device = await self.api.get_device()
            try:
                notifications = await self.api.get_notifications()
            except NibeAuthError:
                raise
            except NibeApiError as err:
                _LOGGER.debug("Notifications endpoint unavailable: %s", err)
                notifications = {"alarms": []}

            self._record_success()
            return {"points": points, "device": device, "notifications": notifications}
        except NibeAuthError as err:
            await self._notify_auth_failure()
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_rejected",
            ) from err
        except NibeApiError as err:
            await self._record_connection_failure()
            raise UpdateFailed(str(err)) from err

    async def _get_points_with_backoff(self) -> dict[str, Any]:
        """Fallback to individual point requests with a bounded retry backoff."""
        now = time_module.monotonic()
        previous_points = (self.data or {}).get("points") or {}

        if should_skip_fallback_scan(
            now=now,
            next_attempt_at=self._next_fallback_attempt,
            has_previous_points=bool(previous_points),
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
