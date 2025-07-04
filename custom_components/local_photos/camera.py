"""Support for Local Photos Albums."""
from __future__ import annotations
import logging

import voluptuous as vol

from homeassistant.components.camera import (
    Camera,
    CameraEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_WRITEMETADATA,
    SETTING_IMAGESELECTION_MODE_OPTIONS,
    WRITEMETADATA_DEFAULT_OPTION,
    CONF_ALBUM_ID,
)
from .coordinator import Coordinator, CoordinatorManager

SERVICE_NEXT_MEDIA = "next_media"
ATTR_MODE = "mode"
CAMERA_NEXT_MEDIA_SCHEMA = {
    vol.Optional(ATTR_MODE): vol.In(SETTING_IMAGESELECTION_MODE_OPTIONS)
}

CAMERA_TYPE = CameraEntityDescription(
    key="album_image", name="Album image", icon="mdi:image"
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Local Photos camera."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator_manager: CoordinatorManager = entry_data.get("coordinator_manager")

    album_ids = entry.options[CONF_ALBUM_ID]
    entities = []
    for album_id in album_ids:
        coordinator = await coordinator_manager.get_coordinator(album_id)
        entities.append(LocalPhotosAlbumCamera(coordinator))

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_NEXT_MEDIA,
        CAMERA_NEXT_MEDIA_SCHEMA,
        "next_media",
    )

    async_add_entities(
        entities,
        False,
    )


class LocalPhotosBaseCamera(Camera):
    """Base class Local Photos Camera class. Implements methods from CoordinatorEntity"""

    coordinator: Coordinator
    _attr_has_entity_name = True
    _attr_icon = "mdi:image"

    def __init__(self, coordinator: Coordinator) -> None:
        """Initialize a Local Photos Base Camera class."""
        super().__init__()
        self.coordinator = coordinator
        self.entity_description = CAMERA_TYPE
        self._attr_native_value = "Cover photo"
        self._attr_frame_interval = 10
        self._attr_is_on = True
        self._attr_is_recording = False
        self._attr_is_streaming = False
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        # Ignore manual update requests if the entity is disabled
        if not self.enabled:
            return

        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        write_metadata = self.coordinator.get_config_option(
            CONF_WRITEMETADATA, WRITEMETADATA_DEFAULT_OPTION
        )
        media = self.coordinator.current_media
        media_secondary = self.coordinator.current_secondary_media
        if write_metadata and media is not None:
            self._attr_extra_state_attributes["media_filename"] = media.filename
            
            # MediaItem objects only have basic properties (no extended metadata)
            # So we'll just provide basic information
            self._attr_extra_state_attributes["media_metadata"] = {
                "path": media.path,
                "id": media.id
            }
            self._attr_extra_state_attributes["media_contributor_info"] = {}
            self._attr_extra_state_attributes["media_url"] = ""
            
            if media_secondary is not None:
                self._attr_extra_state_attributes["secondary_media_filename"] = media_secondary.filename
                self._attr_extra_state_attributes["secondary_media_metadata"] = {
                    "path": media_secondary.path,
                    "id": media_secondary.id
                }
                self._attr_extra_state_attributes["secondary_media_contributor_info"] = {}
                self._attr_extra_state_attributes["secondary_media_url"] = ""
            else:
                self._attr_extra_state_attributes.pop("secondary_media_filename", None)
                self._attr_extra_state_attributes.pop("secondary_media_metadata", None)
                self._attr_extra_state_attributes.pop("secondary_media_contributor_info", None)
                self._attr_extra_state_attributes.pop("secondary_media_url", None)
            
            self.async_write_ha_state()

    async def next_media(self, mode=None):
        """Load the next media."""
        await self.coordinator.select_next(mode)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        await self.coordinator.refresh_current_image()
        if self.coordinator.current_media is None:
            _LOGGER.warning("No media selected for %s", self.name)
            return None
        return await self.coordinator.get_media_data(width, height)


class LocalPhotosAlbumCamera(LocalPhotosBaseCamera):
    """Representation of a Local Photos Album camera."""

    def __init__(self, coordinator: Coordinator) -> None:
        """Initialize a Local Photos album."""
        super().__init__(coordinator)
        self._attr_name = None  # Use the album name as the entity name
        album_id = self.coordinator.album.id
        self._attr_unique_id = f"{album_id}"
        self._attr_device_info = self.coordinator.get_device_info()
