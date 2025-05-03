"""Config flow for Local Photos integration."""
from __future__ import annotations

import logging
import os
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_WRITEMETADATA,
    WRITEMETADATA_DEFAULT_OPTION,
    CONF_ALBUM_ID,
    CONF_ALBUM_ID_FAVORITES,
    CONF_FOLDER_PATH,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Local Photos."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
            )

        # Create default options
        options = {}
        options[CONF_ALBUM_ID] = [CONF_ALBUM_ID_FAVORITES]
        options[CONF_WRITEMETADATA] = WRITEMETADATA_DEFAULT_OPTION

        return self.async_create_entry(
            title="Local Photos",
            data={},
            options=options,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for local photos."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def _get_albumselect_schema(self) -> vol.Schema:
        """Return album selection form"""
        # Scan the photos directory for subdirectories to use as albums
        photos_dir = os.path.join(self.hass.config.config_dir, "www", "photos")
        album_selection = {CONF_ALBUM_ID_FAVORITES: "All Photos"}
        
        try:
            # Define a function to run in the executor
            def scan_albums():
                albums_info = {}
                if not os.path.exists(photos_dir):
                    return albums_info
                    
                for item in os.listdir(photos_dir):
                    item_path = os.path.join(photos_dir, item)
                    if os.path.isdir(item_path):
                        # Count the number of image files in the directory
                        image_count = 0
                        for root, _, files in os.walk(item_path):
                            for file in files:
                                if file.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")):
                                    image_count += 1
                        albums_info[item] = f"{item} ({image_count} items)"
                return albums_info
                
            # Run the file operations in a separate thread
            albums = await self.hass.async_add_executor_job(scan_albums)
            album_selection.update(albums)
        except Exception as err:
            self.logger.error("Error scanning albums: %s", err)

        return vol.Schema(
            {
                vol.Required(CONF_ALBUM_ID): vol.In(album_selection),
            }
        )

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["albumselect", "settings"],
            description_placeholders={
                "model": "Local Photos",
            },
        )

    async def async_step_albumselect(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Set the album used."""
        self.logger.debug(
            "async_albumselect_confirm called with user_input: %s", user_input
        )

        # user input was not provided.
        if user_input is None:
            data_schema = await self._get_albumselect_schema()
            return self.async_show_form(step_id="albumselect", data_schema=data_schema)

        # user input was provided, store the album id
        options = dict(self.config_entry.options)
        album_id_list = options.get(CONF_ALBUM_ID, [])
        if not user_input[CONF_ALBUM_ID] in album_id_list:
            album_id_list.append(user_input[CONF_ALBUM_ID])
            options[CONF_ALBUM_ID] = album_id_list
            return self.async_create_entry(title="", data=options)
        return self.async_create_entry(title="", data=options)

    async def async_step_settings(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Set the settings used."""
        self.logger.debug("async_step_settings called with user_input: %s", user_input)

        # user input was not provided.
        if user_input is None:
            options = dict(self.config_entry.options)
            data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_WRITEMETADATA,
                        default=options.get(
                            CONF_WRITEMETADATA, WRITEMETADATA_DEFAULT_OPTION
                        ),
                    ): bool,
                }
            )
            return self.async_show_form(step_id="settings", data_schema=data_schema)

        # user input was provided, store the settings
        options = dict(self.config_entry.options)
        options[CONF_WRITEMETADATA] = user_input[CONF_WRITEMETADATA]
        return self.async_create_entry(title="", data=options)
