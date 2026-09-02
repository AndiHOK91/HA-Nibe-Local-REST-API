"""NIBE Local REST API integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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

_LOGGER = logging.getLogger(__name__)
_LEGACY_ENTITY_OBJECT_PREFIX = "nibe_vvm_s320_"
_ENTITY_OBJECT_PREFIX = "nibe_api_"


def _legacy_entity_id_target(entity_id: str) -> str | None:
    """Return the neutral replacement for a legacy VVM S320 entity ID."""
    domain, separator, object_id = entity_id.partition(".")
    if not separator or not object_id.startswith(_LEGACY_ENTITY_OBJECT_PREFIX):
        return None
    suffix = object_id.removeprefix(_LEGACY_ENTITY_OBJECT_PREFIX)
    if not suffix:
        return None
    return f"{domain}.{_ENTITY_OBJECT_PREFIX}{suffix}"


def _async_migrate_legacy_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rename automatically generated legacy VVM S320 entity IDs.

    Older releases used the hard-coded device fallback name ``NIBE VVM S320``.
    Home Assistant incorporated that device name into automatically generated
    entity IDs. The local REST API does not expose a model name on all systems,
    so migrate only matching legacy IDs owned by this config entry to the
    neutral ``nibe_api`` prefix. Unique IDs are intentionally left unchanged.
    """
    entity_registry = er.async_get(hass)

    for registry_entry in list(entity_registry.entities.values()):
        if (
            registry_entry.platform != DOMAIN
            or registry_entry.config_entry_id != entry.entry_id
        ):
            continue

        new_entity_id = _legacy_entity_id_target(registry_entry.entity_id)
        if new_entity_id is None or new_entity_id == registry_entry.entity_id:
            continue

        if entity_registry.async_get(new_entity_id) is not None:
            _LOGGER.warning(
                "Cannot migrate legacy entity ID %s to %s because the target already exists",
                registry_entry.entity_id,
                new_entity_id,
            )
            continue

        _LOGGER.info(
            "Migrating legacy entity ID %s to %s",
            registry_entry.entity_id,
            new_entity_id,
        )
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            new_entity_id=new_entity_id,
        )


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
        device_name=entry.title or "NIBE Local REST API",
    )
    await coordinator.async_config_entry_first_refresh()

    _async_migrate_legacy_entity_ids(hass, entry)

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
