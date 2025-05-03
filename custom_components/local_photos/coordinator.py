"""Coordinators to fetch data for all entities"""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta

import logging
import math
import random
from typing import Dict, List, Tuple, Optional
import io
import os
import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)
from homeassistant.helpers.entity import DeviceInfo

from PIL import Image

from .local_photos import LocalPhotosManager, Album, MediaItem
from .const import (
    CONF_ALBUM_ID_FAVORITES,
    CONF_FOLDER_PATH,
    DOMAIN,
    MANUFACTURER,
    SETTING_CROP_MODE_COMBINED,
    SETTING_CROP_MODE_CROP,
    SETTING_CROP_MODE_DEFAULT_OPTION,
    SETTING_IMAGESELECTION_MODE_ALPHABETICAL,
    SETTING_IMAGESELECTION_MODE_DEFAULT_OPTION,
    SETTING_INTERVAL_DEFAULT_OPTION,
    SETTING_INTERVAL_MAP,
)

_LOGGER = logging.getLogger(__name__)
FIFTY_MINUTES = 60 * 50


class CoordinatorManager:
    """Manages all coordinators used by integration (one per album)"""

    hass: HomeAssistant
    _config: ConfigEntry
    _photos_manager: LocalPhotosManager
    coordinators: dict[str, Coordinator] = dict()
    coordinator_first_refresh: dict[str, asyncio.Task] = dict()

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
    ) -> None:
        self.hass = hass
        self._config = config
        self._photos_manager = None
        
    async def initialize(self):
        """Initialize the photos manager asynchronously"""
        if self._photos_manager is None:
            self._photos_manager = LocalPhotosManager(self.hass, self._config.options)
            await self._photos_manager.scan_albums()

    async def get_coordinator(self, album_id: str) -> Coordinator:
        """Get a unique coordinator for specific album_id"""
        # Initialize the photos manager if it hasn't been initialized yet
        if self._photos_manager is None:
            await self.initialize()
            
        if album_id in self.coordinators:
            await self.coordinator_first_refresh.get(album_id)
            return self.coordinators.get(album_id)
            
        self.coordinators[album_id] = Coordinator(
            self.hass, self._photos_manager, self._config, album_id
        )
        first_refresh = asyncio.create_task(
            self.coordinators[album_id].async_config_entry_first_refresh()
        )
        self.coordinator_first_refresh[album_id] = first_refresh
        await first_refresh
        return self.coordinators[album_id]

    def remove_coordinator(self, album_id: str):
        """Remove coordinator instance"""
        if album_id not in self.coordinators:
            return
        self.coordinators.pop(album_id)
        self.coordinator_first_refresh.pop(album_id)


class Coordinator(DataUpdateCoordinator):
    """Coordinates data retrieval and selection from Local Photos"""

    _photos_manager: LocalPhotosManager
    _config: ConfigEntry

    album: Album = None
    album_id: str
    current_media_primary: MediaItem | None = None
    current_media_secondary: MediaItem | None = None
    current_media_cache: Dict[str, bytes] = {}

    # Media selection timestamp, when was this image selected to be shown,
    # used to calculate when to move to the next one
    current_media_selected_timestamp = datetime.fromtimestamp(0)

    crop_mode = SETTING_CROP_MODE_DEFAULT_OPTION
    image_selection_mode = SETTING_IMAGESELECTION_MODE_DEFAULT_OPTION
    interval = SETTING_INTERVAL_DEFAULT_OPTION

    def __init__(
        self,
        hass: HomeAssistant,
        photos_manager: LocalPhotosManager,
        config: ConfigEntry,
        album_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=None,
        )
        self._photos_manager = photos_manager
        self._config = config
        self.album_id = album_id

        # Get the album from the photos manager
        self.album = self._photos_manager.get_album(album_id)
        if not self.album:
            _LOGGER.warning("Album not found: %s, using default", album_id)
            self.album = self._photos_manager.get_album(CONF_ALBUM_ID_FAVORITES)

    @property
    def current_media(self) -> MediaItem | None:
        """Get current media item"""
        return self.current_media_primary
    
    @property
    def current_secondary_media(self) -> MediaItem | None:
        """Get current secondary media item"""
        return self.current_media_secondary

    def get_device_info(self) -> DeviceInfo:
        """Fetches device info for coordinator instance"""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self._config.entry_id,
                    self.album_id,
                )
            },
            manufacturer=MANUFACTURER,
            name=self.album.title,
            configuration_url=None,
        )

    def set_crop_mode(self, crop_mode: str):
        """Set crop mode"""
        self.current_media_cache = {}
        self.crop_mode = crop_mode

    def set_image_selection_mode(self, image_selection_mode: str):
        """Set image selection mode"""
        self.image_selection_mode = image_selection_mode

    def set_interval(self, interval: str):
        """Set interval"""
        self.interval = interval

    def get_config_option(self, prop, default) -> ConfigEntry:
        """Get config option."""
        if self._config.options is not None and prop in self._config.options:
            return self._config.options[prop]
        return default

    def current_media_id(self) -> str | None:
        """Id of current media"""
        media = self.current_media
        if media is None:
            return None
        return media.id

    async def set_current_media_with_id(self, media_id: str | None):
        """Sets current selected media using only the id"""
        if media_id is None:
            return
        try:
            self.current_media_selected_timestamp = datetime.now()
            media = await self._get_media_by_id(media_id)
            self.current_media_primary = media
            self.current_media_secondary = None
            self.current_media_cache = {}
        except Exception as err:
            _LOGGER.error("Error setting current media: %s", err)
            raise UpdateFailed(f"Error setting current media: {err}") from err

    async def _get_media_by_id(self, media_id: str) -> MediaItem:
        """Get media by id"""
        try:
            # Get the media item from the photos manager
            media = await self._photos_manager.get_media_item(self.album_id, media_id)
            if media is None:
                _LOGGER.warning(
                    "Media %s not found in album %s", media_id, self.album_id
                )
                return await self._get_random_media()
            return media
        except Exception as err:
            _LOGGER.error("Error getting media by id: %s", err)
            raise UpdateFailed(f"Error getting media by id: {err}") from err

    async def refresh_current_image(self) -> bool:
        """Selects next image if interval has passed"""
        interval = SETTING_INTERVAL_MAP.get(self.interval)
        if interval is None:
            return False

        time_delta = (
            datetime.now() - self.current_media_selected_timestamp
        ).total_seconds()
        if time_delta > interval or self.current_media is None:
            await self.select_next()
            return True
        return False

    async def select_next(self, mode=None):
        """Select next media based on config"""
        mode = mode or self.image_selection_mode
        if mode.lower() == SETTING_IMAGESELECTION_MODE_ALPHABETICAL.lower():
            await self._select_sequential_media()
        else:
            await self._select_random_media()

    async def _select_random_media(self):
        """Selects a random media item from the list"""
        try:
            media = await self._photos_manager.get_random_media_item(self.album_id)
            if media:
                await self.set_current_media_with_id(media.id)
            else:
                _LOGGER.warning("No media found in album %s", self.album_id)
        except Exception as err:
            _LOGGER.error("Error selecting random media: %s", err)

    async def _select_sequential_media(self):
        """Finds the current photo in the alphabetically sorted list, and moves to the next"""
        try:
            current_media_id = self.current_media_id()
            media = await self._photos_manager.get_next_media_item(self.album_id, current_media_id)
            if media:
                await self.set_current_media_with_id(media.id)
            else:
                _LOGGER.warning("No media found in album %s", self.album_id)
        except Exception as err:
            _LOGGER.error("Error selecting sequential media: %s", err)
            
    async def _get_random_media(self):
        """Get a random media item"""
        media = await self._photos_manager.get_random_media_item(self.album_id)
        if not media:
            _LOGGER.warning("No media found in album %s", self.album_id)
            return None
        return media

    async def get_media_data(self, width: int | None = None, height: int | None = None):
        """Get a binary image data for the current media"""
        width = width or 1024
        height = height or 512

        cache_key = f"w{width}h{height}{self.crop_mode}"
        if cache_key in self.current_media_cache:
            return self.current_media_cache[cache_key]

        if self.current_media_primary is None:
            _LOGGER.warning("No media selected")
            return None

        if self.crop_mode == SETTING_CROP_MODE_COMBINED:
            result = await self._get_combined_media_data(width, height)
            if result is not None:
                self.async_update_listeners()
                self.current_media_cache[cache_key] = result
                return self.current_media_cache[cache_key]
        
        # Process the image from the local file
        try:
            # Use async_add_executor_job for file operations
            def read_and_process_image():
                with open(self.current_media_primary.path, "rb") as f:
                    image_data = f.read()
                    
                # Process the image with PIL to resize/crop as needed
                with Image.open(io.BytesIO(image_data)) as img:
                    # Apply EXIF orientation first
                    img = self._apply_exif_orientation(img)
                    
                    # Get original dimensions (after orientation correction)
                    original_width, original_height = img.size
                    
                    # Calculate new dimensions while maintaining aspect ratio
                    if self.crop_mode == SETTING_CROP_MODE_CROP:
                        # Crop mode - resize to fill the target dimensions, may crop parts of the image
                        img_resized = self._resize_and_crop_image(img, width, height)
                    else:  # Default to SETTING_CROP_MODE_ORIGINAL
                        # Original mode - resize to fit within the target dimensions, may have letterboxing
                        img_resized = self._resize_to_fit(img, width, height)
                    
                    # Convert the resized image back to bytes
                    img_byte_arr = io.BytesIO()
                    # Preserve the original format if possible
                    img_format = img.format if img.format else 'JPEG'
                    img_resized.save(img_byte_arr, format=img_format, quality=95)
                    return img_byte_arr.getvalue()
            
            # Run the file operations in a separate thread
            result = await self.hass.async_add_executor_job(read_and_process_image)
            self.current_media_cache[cache_key] = result
            self.async_update_listeners()
            return result
        except Exception as err:
            _LOGGER.error("Error processing image %s: %s", self.current_media_primary.path, err)
            return None

    async def _get_combined_media_data(self, width: int, height: int):
        """Get a binary image data for the current media"""
        requested_dimensions = (float(width), float(height))
        media_dimensions = await self._get_media_dimensions()
        if media_dimensions is None:
            return None
            
        media_is_portrait = self._is_portrait(media_dimensions)
        if self._is_portrait(requested_dimensions) is media_is_portrait:
            # Requested orientation matches media orientation
            return None

        combined_image_dimensions = self._calculate_combined_image_dimensions(
            requested_dimensions, media_dimensions
        )
        cut_loss_single = self._calculate_cut_loss(
            requested_dimensions, media_dimensions
        )
        cut_loss_combined = self._calculate_cut_loss(
            combined_image_dimensions, media_dimensions
        )
        if cut_loss_single < cut_loss_combined:
            # Bigger part of the image would be lost with combined images
            return None

        if self.current_media_secondary is None:
            # Find another image with similar orientation
            try:
                all_media = await self._photos_manager.get_media_items(self.album_id)
                current_id = self.current_media_id()
                
                # Filter media with the same orientation
                similar_orientation_media = []
                for media_item in all_media:
                    if media_item.id == current_id:
                        continue
                            
                    # Get dimensions of this media item asynchronously
                    try:
                        # Define a function to run in the executor
                        def get_item_dimensions(path):
                            with Image.open(path) as img:
                                return img.size
                                
                        # Run the file operation in a separate thread
                        item_dimensions = await self.hass.async_add_executor_job(get_item_dimensions, media_item.path)
                        is_portrait = self._is_portrait(item_dimensions)
                        if is_portrait == media_is_portrait:
                            similar_orientation_media.append(media_item)
                    except Exception:
                        continue
                
                if not similar_orientation_media:
                    return None
                    
                # Choose a random media item with similar orientation
                self.current_media_secondary = random.choice(similar_orientation_media)
            except Exception as err:
                _LOGGER.error("Error finding secondary image: %s", err)
                return None

        # Process both images
        try:
            # Define a function to run in the executor
            def process_combined_images():
                # Load and resize primary image
                with open(self.current_media_primary.path, "rb") as f:
                    primary_data = f.read()
                    
                # Load and resize secondary image
                with open(self.current_media_secondary.path, "rb") as f:
                    secondary_data = f.read()
                    
                # Create the combined image
                with Image.new("RGB", (width, height), "white") as output:
                    # Process primary image
                    with Image.open(io.BytesIO(primary_data)) as img1:
                        # Apply EXIF orientation
                        img1 = self._apply_exif_orientation(img1)
                        
                        # Get original dimensions
                        orig_width, orig_height = img1.size
                        
                        # Calculate target dimensions while maintaining aspect ratio
                        target_width = math.ceil(combined_image_dimensions[0])
                        target_height = math.ceil(combined_image_dimensions[1])
                        
                        # Resize and crop to fit the combined dimensions (maintain aspect ratio)
                        img1 = self._resize_and_crop_image(img1, target_width, target_height)
                        output.paste(img1, (0, 0))
                    
                    # Process secondary image
                    with Image.open(io.BytesIO(secondary_data)) as img2:
                        # Apply EXIF orientation
                        img2 = self._apply_exif_orientation(img2)
                        
                        # Get original dimensions
                        orig_width, orig_height = img2.size
                        
                        # Calculate target dimensions while maintaining aspect ratio
                        target_width = math.ceil(combined_image_dimensions[0])
                        target_height = math.ceil(combined_image_dimensions[1])
                        
                        # Resize and crop to fit the combined dimensions (maintain aspect ratio)
                        img2 = self._resize_and_crop_image(img2, target_width, target_height)
                        
                        # Position the second image
                        if combined_image_dimensions[0] < requested_dimensions[0]:
                            # Side by side
                            output.paste(img2, (math.floor(combined_image_dimensions[0]), 0))
                        else:
                            # One above the other
                            output.paste(img2, (0, math.floor(combined_image_dimensions[1])))
                    
                    # Save the combined image
                    with io.BytesIO() as result:
                        output.save(result, "JPEG")
                        return result.getvalue()
            
            # Run the file operations in a separate thread
            return await self.hass.async_add_executor_job(process_combined_images)
        except Exception as err:
            _LOGGER.error("Error creating combined image: %s", err)
            return None

    async def update_data(self):
        """Check if media list or current image needs to be refreshed"""
        # If no media is selected yet, select one
        if self.current_media is None and self.album is not None:
            await self.select_next(None)

    def _is_portrait(self, dimensions: Tuple[float, float]) -> bool:
        """Returns if the given dimension represent a portrait media item"""
        return dimensions[0] < dimensions[1]

    def _calculate_combined_image_dimensions(
        self, target: Tuple[float, float], src: Tuple[float, float]
    ) -> Tuple[float, float]:
        multiplier_width = target[0] / src[0]
        multiplier_height = target[1] / src[1]
        if multiplier_height > multiplier_width:
            return (target[0], target[1] / 2)
        else:
            return (target[0] / 2, target[1])

    def _calculate_cut_loss(
        self, target: Tuple[float, float], src: Tuple[float, float]
    ) -> float:
        multiplier = max(target[0] / src[0], target[1] / src[1])
        return 1 - (
            (target[0] * target[1]) / ((src[0] * multiplier) * (src[1] * multiplier))
        )
        
    def _resize_and_crop_image(self, img, target_width, target_height):
        """Resize and crop the image to fill the target dimensions."""
        # Apply EXIF orientation
        img = self._apply_exif_orientation(img)
        
        # Get original dimensions
        original_width, original_height = img.size
        
        # Calculate aspect ratios
        original_ratio = original_width / original_height
        target_ratio = target_width / target_height
        
        # Determine which dimension to fit
        if original_ratio > target_ratio:  # Image is wider
            # Resize to match target height, then crop width
            resize_height = target_height
            resize_width = int(original_width * (resize_height / original_height))
            img_resized = img.resize((resize_width, resize_height), Image.LANCZOS)
            
            # Crop to target width
            left = (resize_width - target_width) // 2
            img_cropped = img_resized.crop((left, 0, left + target_width, target_height))
            return img_cropped
        else:  # Image is taller or same ratio
            # Resize to match target width, then crop height
            resize_width = target_width
            resize_height = int(original_height * (resize_width / original_width))
            img_resized = img.resize((resize_width, resize_height), Image.LANCZOS)
            
            # Crop to target height
            top = (resize_height - target_height) // 2
            img_cropped = img_resized.crop((0, top, target_width, top + target_height))
            return img_cropped
    
    def _resize_to_fit(self, img, target_width, target_height):
        """Resize the image to fit within the target dimensions while maintaining aspect ratio."""
        # Apply EXIF orientation
        img = self._apply_exif_orientation(img)
        
        # Get original dimensions
        original_width, original_height = img.size
        
        # Calculate aspect ratios
        original_ratio = original_width / original_height
        target_ratio = target_width / target_height
        
        # Create a blank canvas with the target dimensions
        canvas = Image.new('RGB', (target_width, target_height), (0, 0, 0))
        
        # Calculate new dimensions while maintaining aspect ratio
        if original_ratio > target_ratio:  # Image is wider
            # Fit to width
            new_width = target_width
            new_height = int(original_height * (new_width / original_width))
        else:  # Image is taller or same ratio
            # Fit to height
            new_height = target_height
            new_width = int(original_width * (new_height / original_height))
        
        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Center the image on the canvas
        paste_x = (target_width - new_width) // 2
        paste_y = (target_height - new_height) // 2
        canvas.paste(img_resized, (paste_x, paste_y))
        
        return canvas

    def _apply_exif_orientation(self, img):
        """Apply the EXIF orientation to the image."""
        try:
            # Check if the image has EXIF data
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = dict(img._getexif().items())
                orientation = exif.get(0x0112, 1)  # 0x0112 is the orientation tag
                
                # Apply the appropriate rotation/flip based on EXIF orientation
                if orientation == 1:  # Normal
                    return img
                elif orientation == 2:  # Mirrored horizontally
                    return img.transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 3:  # Rotated 180 degrees
                    return img.transpose(Image.ROTATE_180)
                elif orientation == 4:  # Mirrored vertically
                    return img.transpose(Image.FLIP_TOP_BOTTOM)
                elif orientation == 5:  # Mirrored horizontally and rotated 90 degrees counter-clockwise
                    return img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
                elif orientation == 6:  # Rotated 90 degrees counter-clockwise
                    return img.transpose(Image.ROTATE_270)
                elif orientation == 7:  # Mirrored horizontally and rotated 90 degrees clockwise
                    return img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
                elif orientation == 8:  # Rotated 90 degrees clockwise
                    return img.transpose(Image.ROTATE_90)
        except Exception as err:
            _LOGGER.debug("Error applying EXIF orientation: %s", err)
        
        # Return the original image if there's no EXIF data or if there was an error
        return img
    
    async def _get_media_dimensions(
        self, media: MediaItem | None = None
    ) -> Tuple[float, float] | None:
        """Get the dimensions of the media item"""
        media = media or self.current_media
        if media is None:
            return None
            
        try:
            # Define a function to run in the executor
            def get_dimensions():
                with Image.open(media.path) as img:
                    # Apply EXIF orientation to get the correct dimensions
                    img = self._apply_exif_orientation(img)
                    return img.size
                    
            # Run the file operation in a separate thread
            return await self.hass.async_add_executor_job(get_dimensions)
        except Exception as err:
            _LOGGER.error("Error getting image dimensions for %s: %s", media.path, err)
            return None

    async def _async_update_data(self):
        """Fetch album data"""
        try:
            # Refresh the album from the photos manager
            self.album = self._photos_manager.get_album(self.album_id)
            if not self.album:
                _LOGGER.warning("Album not found: %s, using default", self.album_id)
                self.album = self._photos_manager.get_album(CONF_ALBUM_ID_FAVORITES)
                
            await self.update_data()
            return True
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}") from err
