"""Support for Local Photos."""
from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import CoordinatorManager
from .const import CONF_ALBUM_ID, CONF_FOLDER_PATH, DOMAIN

PLATFORMS = [Platform.CAMERA, Platform.SENSOR, Platform.SELECT]
_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(_, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        _LOGGER.error("Migration failed, please remove / add integration.")
        return False

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Local Photos from a config entry."""
    
    # Get the configured folder path or use the default
    folder_path = entry.options.get(CONF_FOLDER_PATH)
    if folder_path:
        # If the path is not absolute, make it relative to the config directory
        if not os.path.isabs(folder_path):
            folder_path = os.path.join(hass.config.config_dir, folder_path)
    else:
        # Use the default path if not specified
        folder_path = os.path.join(hass.config.config_dir, "www", "images")
    
    # Check if the photos directory exists
    if not os.path.exists(folder_path):
        _LOGGER.error("Photos directory does not exist: %s", folder_path)
        raise ConfigEntryNotReady(f"Directory does not exist: {folder_path}")
    
    # Ensure metadata is always enabled
    options = dict(entry.options)
    options["write_metadata"] = True
    
    # Initialize the coordinator manager
    coordinator_manager = CoordinatorManager(hass, entry)
    # Initialize the coordinator manager asynchronously
    await coordinator_manager.initialize()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dict(
        {
            "coordinator_manager": coordinator_manager,
            "loaded_options": options,
        }
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, updated_entry: ConfigEntry):
    """Handle an options update.

    Only reload integration if the optons are changed, skip if for example the auth token has been updated
    """
    current_options = hass.data.setdefault(DOMAIN, {})[updated_entry.entry_id].get(
        "loaded_options"
    )
    updated_options = {**updated_entry.options}
    if updated_options == current_options:
        _LOGGER.debug("update_listener triggered (no option change)")
        return
    _LOGGER.debug("update_listener triggered (options changed)")
    await hass.config_entries.async_reload(updated_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    loaded_entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state == ConfigEntryState.LOADED
    ]
    # Only remove services when there are no more loaded entries
    if len(loaded_entries) == 0:
        for service_name in hass.services.async_services().get(DOMAIN, []):
            hass.services.async_remove(DOMAIN, service_name)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    identifier = next((id for id in device_entry.identifiers if id[0] == DOMAIN), None)
    if identifier is None:
        return False
    coordinator_manager: CoordinatorManager = hass.data.get(DOMAIN)[
        config_entry.entry_id
    ].get("coordinator_manager")
    album_id = identifier[len(identifier) - 1]
    options = config_entry.options.copy()
    albums = options.get(CONF_ALBUM_ID, []).copy()
    if album_id in albums:
        albums.remove(album_id)
        options.update({CONF_ALBUM_ID: albums})
        hass.data.setdefault(DOMAIN, {})[config_entry.entry_id].update(
            {
                "loaded_options": {**options},
            }
        )
        hass.config_entries.async_update_entry(config_entry, options=options)

    coordinator_manager.remove_coordinator(album_id)
    return True
