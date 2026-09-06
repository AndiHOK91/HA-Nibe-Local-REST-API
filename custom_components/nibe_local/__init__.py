"""NIBE Local REST API integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

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
from .diagnostics import (
    ALLOWED_HISTORY_DAYS,
    DEFAULT_HISTORY_DAYS,
    async_get_extended_config_entry_diagnostics,
)
from .equipment import CONF_EQUIPMENT
from .profiles import DEFAULT_ENTITY_PROFILE
from .statistics_migration import (
    async_import_statistics_migration,
    async_preview_statistics_migration,
)
from .statistics_restore import (
    async_list_statistics_backups,
    async_preview_statistics_restore,
)

SERVICE_EXPORT_EXTENDED_DIAGNOSTICS = "export_extended_diagnostics"
SERVICE_PREVIEW_STATISTICS_MIGRATION = "preview_statistics_migration"
SERVICE_IMPORT_STATISTICS_MIGRATION = "import_statistics_migration"
SERVICE_LIST_STATISTICS_BACKUPS = "list_statistics_backups"
SERVICE_PREVIEW_STATISTICS_RESTORE = "preview_statistics_restore"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_HISTORY_DAYS = "history_days"
ATTR_SOURCE_ENTITY_ID = "source_entity_id"
ATTR_TARGET_ENTITY_ID = "target_entity_id"
ATTR_CREATE_BACKUP = "create_backup"
ATTR_BACKUP_FILE = "backup_file"
SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional(ATTR_HISTORY_DAYS, default=DEFAULT_HISTORY_DAYS): vol.In(
            ALLOWED_HISTORY_DAYS
        ),
    }
)
SERVICE_PREVIEW_STATISTICS_MIGRATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SOURCE_ENTITY_ID): str,
        vol.Required(ATTR_TARGET_ENTITY_ID): str,
    }
)
SERVICE_IMPORT_STATISTICS_MIGRATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SOURCE_ENTITY_ID): str,
        vol.Required(ATTR_TARGET_ENTITY_ID): str,
        vol.Optional(ATTR_CREATE_BACKUP, default=True): bool,
    }
)
SERVICE_LIST_STATISTICS_BACKUPS_SCHEMA = vol.Schema({})
SERVICE_PREVIEW_STATISTICS_RESTORE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_BACKUP_FILE): str,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-level actions."""

    async def async_export_extended_diagnostics(call: ServiceCall) -> ServiceResponse:
        """Return explicitly requested diagnostics with current values and history."""
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError("NIBE Local REST API config entry not found")
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("NIBE Local REST API config entry is not loaded")
        return await async_get_extended_config_entry_diagnostics(
            hass,
            entry,
            history_days=call.data[ATTR_HISTORY_DAYS],
        )

    def validate_migration_entities(call: ServiceCall) -> tuple[str, str]:
        """Validate one source/target entity pair for a migration action."""
        source_entity_id = call.data[ATTR_SOURCE_ENTITY_ID]
        target_entity_id = call.data[ATTR_TARGET_ENTITY_ID]
        if source_entity_id == target_entity_id:
            raise ServiceValidationError("Source and target entity must be different")

        registry = er.async_get(hass)
        target_entry = registry.async_get(target_entity_id)
        if target_entry is None or target_entry.platform != DOMAIN:
            raise ServiceValidationError(
                "Target entity must belong to the NIBE Local REST API integration"
            )
        return source_entity_id, target_entity_id

    async def async_preview_migration(call: ServiceCall) -> ServiceResponse:
        """Return a read-only comparison of historical source and target statistics."""
        source_entity_id, target_entity_id = validate_migration_entities(call)
        return await async_preview_statistics_migration(
            hass,
            source_entity_id,
            target_entity_id,
        )

    async def async_import_migration(call: ServiceCall) -> ServiceResponse:
        """Import missing historical source statistics into a REST target sensor."""
        source_entity_id, target_entity_id = validate_migration_entities(call)
        return await async_import_statistics_migration(
            hass,
            source_entity_id,
            target_entity_id,
            create_backup=call.data[ATTR_CREATE_BACKUP],
        )

    async def async_list_backups(call: ServiceCall) -> ServiceResponse:
        """Return all integration-owned statistics migration backups."""
        return await async_list_statistics_backups(hass)

    async def async_preview_restore(call: ServiceCall) -> ServiceResponse:
        """Return a read-only restore preview for one selected backup."""
        result = await async_preview_statistics_restore(
            hass,
            call.data[ATTR_BACKUP_FILE],
        )
        target_entity_id = result["backup"]["target_entity_id"]
        registry = er.async_get(hass)
        target_entry = registry.async_get(target_entity_id)
        if target_entry is not None and target_entry.platform != DOMAIN:
            raise ServiceValidationError(
                "Backup target does not belong to the NIBE Local REST API integration"
            )
        return result

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_EXTENDED_DIAGNOSTICS,
        async_export_extended_diagnostics,
        schema=SERVICE_EXPORT_EXTENDED_DIAGNOSTICS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PREVIEW_STATISTICS_MIGRATION,
        async_preview_migration,
        schema=SERVICE_PREVIEW_STATISTICS_MIGRATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_STATISTICS_MIGRATION,
        async_import_migration,
        schema=SERVICE_IMPORT_STATISTICS_MIGRATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_STATISTICS_BACKUPS,
        async_list_backups,
        schema=SERVICE_LIST_STATISTICS_BACKUPS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PREVIEW_STATISTICS_RESTORE,
        async_preview_restore,
        schema=SERVICE_PREVIEW_STATISTICS_RESTORE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


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
