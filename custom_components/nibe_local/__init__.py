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
    POINT_BY_ID,
)
from .coordinator import NibeCoordinator

_LOGGER = logging.getLogger(__name__)
_LEGACY_ENTITY_OBJECT_PREFIX = "nibe_vvm_s320_"
_ENTITY_OBJECT_PREFIX = "nibe_api_"
_SPECIAL_ENTITY_KEYS = {
    "api_reachable",
    "fallback_active",
    "notifications",
    "last_connection_error",
    "smart_mode",
}


def _canonical_entity_key(unique_id: str, device_id: str) -> str | None:
    """Return the stable language-neutral entity key for a registry unique ID."""
    prefix = f"{device_id}_"
    if not unique_id.startswith(prefix):
        return None

    suffix = unique_id.removeprefix(prefix)
    if suffix in _SPECIAL_ENTITY_KEYS:
        return suffix

    try:
        point_id = int(suffix)
    except ValueError:
        return None

    definition = POINT_BY_ID.get(point_id)
    return definition.key if definition is not None else None


def _canonical_entity_id_target(
    entity_id: str,
    unique_id: str,
    device_id: str,
) -> str | None:
    """Return the canonical NIBE API entity ID for an automatically named entity."""
    domain, separator, object_id = entity_id.partition(".")
    if not separator:
        return None

    if not object_id.startswith(
        (_LEGACY_ENTITY_OBJECT_PREFIX, _ENTITY_OBJECT_PREFIX)
    ):
        return None

    key = _canonical_entity_key(unique_id, device_id)
    if key is None:
        return None
    return f"{domain}.{_ENTITY_OBJECT_PREFIX}{key}"


def _async_migrate_entity_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device_id: str,
) -> None:
    """Migrate automatically generated entity IDs to stable canonical IDs.

    Older releases derived entity IDs from the hard-coded ``NIBE VVM S320``
    device fallback and from localized entity names. Canonical IDs now use the
    neutral ``nibe_api`` prefix plus the stable translation key. This keeps the
    technical entity ID independent from the Home Assistant UI language while
    preserving the existing unique ID and entity registry entry.

    Only IDs still using an integration-generated ``nibe_vvm_s320`` or
    ``nibe_api`` prefix are migrated. Custom entity IDs with another prefix are
    intentionally left untouched.
    """
    entity_registry = er.async_get(hass)

    for registry_entry in list(entity_registry.entities.values()):
        if (
            registry_entry.platform != DOMAIN
            or registry_entry.config_entry_id != entry.entry_id
        ):
            continue

        new_entity_id = _canonical_entity_id_target(
            registry_entry.entity_id,
            registry_entry.unique_id,
            device_id,
        )
        if new_entity_id is None or new_entity_id == registry_entry.entity_id:
            continue

        if entity_registry.async_get(new_entity_id) is not None:
            _LOGGER.warning(
                "Cannot migrate entity ID %s to %s because the target already exists",
                registry_entry.entity_id,
                new_entity_id,
            )
            continue

        _LOGGER.info(
            "Migrating entity ID %s to %s",
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

    _async_migrate_entity_ids(hass, entry, api.device_id)

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
