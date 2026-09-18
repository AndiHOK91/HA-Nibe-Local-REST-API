"""Button entities for NIBE Local REST."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import NibeApiError
from .const import DOMAIN
from .coordinator import NibeCoordinator
from .entity import coordinator_device_info, entity_unique_id
from .profiles import alarm_reset_enabled

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NibeCoordinator = entry.runtime_data
    if not alarm_reset_enabled(coordinator.entity_profile):
        return
    async_add_entities([NibeAlarmResetButton(coordinator)])


class NibeAlarmResetButton(ButtonEntity):
    """Reset all active NIBE alarms/notifications through Local REST."""

    _attr_has_entity_name = True
    _attr_translation_key = "reset_alarms"
    _attr_icon = "mdi:alarm-light-off"

    def __init__(self, coordinator: NibeCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = entity_unique_id(coordinator, "reset_alarms")

    @property
    def device_info(self):
        return coordinator_device_info(self.coordinator)

    async def async_press(self) -> None:
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
