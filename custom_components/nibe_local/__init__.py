"""NIBE Local REST integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NibeLocalApi
from .const import (
    CONF_AUTH_HEADER,
    CONF_COMMAND_POLL_DELAY_MS,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_COMMAND_POLL_DELAY_MS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import NibeCoordinator


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = {**entry.data, **entry.options}

    api = NibeLocalApi(
        async_get_clientsession(hass),
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        device_id=data.get(CONF_DEVICE_ID, "0"),
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
        auth_header=data.get(CONF_AUTH_HEADER),
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
    )

    coordinator = NibeCoordinator(
        hass,
        api,
        data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        data.get(CONF_COMMAND_POLL_DELAY_MS, DEFAULT_COMMAND_POLL_DELAY_MS),
        device_name=entry.title or "NIBE Local REST",
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
