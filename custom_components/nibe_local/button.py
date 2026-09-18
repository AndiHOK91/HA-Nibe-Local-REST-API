"""Button entities for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .alarms import normalize_alarms
from .api import NibeApiError
from .const import DOMAIN
from .coordinator import NibeCoordinator
from .entity import coordinator_device_info, entity_unique_id
from .profiles import alarm_reset_enabled

PARALLEL_UPDATES = 1


def alarm_reset_available(coordinator: NibeCoordinator) -> bool:
    """Return whether the alarm reset action may currently be used."""
    if not coordinator.last_update_success:
        return False
    notifications = (coordinator.data or {}).get("notifications")
    return bool(normalize_alarms(notifications))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    if not alarm_reset_enabled(coordinator.entity_profile):
        return
    async_add_entities([NibeAlarmResetButton(coordinator)])


class NibeAlarmResetButton(CoordinatorEntity[NibeCoordinator], ButtonEntity):
    """Reset all active NIBE alarms/notifications through Local REST."""

    _attr_has_entity_name = True
    _attr_translation_key = "reset_alarms"
    _attr_icon = "mdi:alarm-light-off"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entity_unique_id(coordinator, "reset_alarms")

    @property
    def available(self) -> bool:
        """Only allow alarm reset while an active alarm is known."""
        return alarm_reset_available(self.coordinator)

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)

    async def async_press(self) -> None:
        if not self.available:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="alarm_reset_no_active_alarms",
            )

        try:
            await self.coordinator.api.reset_notifications()
        except NibeApiError as err:
            message = str(err)
            if "HTTP 405" in message:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="alarm_reset_not_supported",
                ) from err
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="alarm_reset_failed",
                translation_placeholders={"error": message},
            ) from err

        await self.coordinator.async_request_refresh()
