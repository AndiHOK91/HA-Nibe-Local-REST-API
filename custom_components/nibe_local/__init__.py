"""NIBE Local REST API integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er

from .api import NibeLocalApi
from .const import (
    CONF_AUTH_HEADER,
    CONF_AUTH_METHOD,
    CONF_COMMAND_POLL_DELAY_MS,
    CONF_ENTITY_PROFILE,
    CONF_ENTITY_NAMING,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_POINT_IDS,
    CONF_VERIFY_SSL,
    DEFAULT_COMMAND_POLL_DELAY_MS,
    DEFAULT_ENTITY_NAMING,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
    DOMAIN,
)
from .coordinator import NibeCoordinator
from .equipment import CONF_EQUIPMENT
from .profiles import DEFAULT_ENTITY_PROFILE


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_migrate_entity_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Move legacy device-id unique IDs to a config-entry-scoped namespace."""
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    legacy_prefix = "0_"

    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        old_unique_id = registry_entry.unique_id
        if old_unique_id.startswith(prefix) or not old_unique_id.startswith(legacy_prefix):
            continue
        new_unique_id = f"{prefix}{old_unique_id[len(legacy_prefix):]}"
        existing_entity_id = registry.async_get_entity_id(
            registry_entry.domain, registry_entry.platform, new_unique_id
        )
        if existing_entity_id and existing_entity_id != registry_entry.entity_id:
            continue
        registry.async_update_entity(
            registry_entry.entity_id, new_unique_id=new_unique_id
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = {**entry.data, **entry.options}

    api = NibeLocalApi(
        async_get_clientsession(hass),
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
        auth_header=data.get(CONF_AUTH_HEADER),
        auth_method=data.get(CONF_AUTH_METHOD),
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
    )

    coordinator = NibeCoordinator(
        hass,
        api,
        data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        data.get(CONF_COMMAND_POLL_DELAY_MS, DEFAULT_COMMAND_POLL_DELAY_MS),
        device_name=entry.title or "NIBE Local REST API",
        instance_id=entry.entry_id,
        entity_profile=data.get(CONF_ENTITY_PROFILE, DEFAULT_ENTITY_PROFILE),
        selected_point_ids=data.get(CONF_SELECTED_POINT_IDS, ()),
        entity_naming=data.get(CONF_ENTITY_NAMING, DEFAULT_ENTITY_NAMING),
        equipment=data.get(CONF_EQUIPMENT),
    )
    await coordinator.async_config_entry_first_refresh()
    await _async_migrate_entity_unique_ids(hass, entry)

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
