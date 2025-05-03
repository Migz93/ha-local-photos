"""Local Photos API for Home Assistant."""
from __future__ import annotations

import logging
import os
import random
from datetime import datetime
from typing import Dict, List, Optional
import mimetypes

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_ALBUM_ID_FAVORITES

_LOGGER = logging.getLogger(__name__)

# Supported image file extensions
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

class Album:
    """Representation of a local photo album (folder)."""

    def __init__(self, id: str, title: str, path: str) -> None:
        """Initialize a local album."""
        self.id = id
        self.title = title
        self.path = path
        self.is_writeable = False  # Local albums are read-only for now
        self.media_items_count = 0
        self.product_url = None

    def get(self, key, default=None):
        """Get album attribute."""
        if key == "id":
            return self.id
        elif key == "title":
            return self.title
        elif key == "isWriteable":
            return self.is_writeable
        elif key == "mediaItemsCount":
            return self.media_items_count
        elif key == "productUrl":
            return self.product_url
        return default


class MediaItem:
    """Representation of a local media item (photo)."""

    def __init__(self, id: str, filename: str, path: str) -> None:
        """Initialize a local media item."""
        self.id = id
        self.filename = filename
        self.path = path
        self.creation_time = self._get_creation_time()
        self.media_metadata = self._get_media_metadata()
        self.product_url = None
        self.contributor_info = None

    def _get_creation_time(self) -> datetime:
        """Get creation time from file metadata."""
        try:
            stat = os.stat(self.path)
            # Use the earliest time available (either creation or modification time)
            ctime = datetime.fromtimestamp(stat.st_ctime)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            return min(ctime, mtime)
        except Exception as ex:
            _LOGGER.error("Error getting creation time for %s: %s", self.path, ex)
            return datetime.now()

    def _get_media_metadata(self) -> Dict:
        """Get basic media metadata."""
        # In a real implementation, we could use PIL or other libraries to extract EXIF data
        # For now, we'll just provide basic file info
        return {
            "photo": {
                "cameraMake": "Local Photos",
                "cameraModel": "File System",
                "focalLength": 0,
                "apertureFNumber": 0,
                "isoEquivalent": 0,
                "exposureTime": "0s",
            },
            "creationTime": self.creation_time.isoformat(),
        }

    def get(self, key, default=None):
        """Get media item attribute."""
        if key == "id":
            return self.id
        elif key == "filename":
            return self.filename
        elif key == "mediaMetadata":
            return self.media_metadata
        elif key == "productUrl":
            return self.product_url
        elif key == "contributorInfo":
            return self.contributor_info
        return default


class LocalPhotosManager:
    """Manager for local photos."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        """Initialize the local photos manager."""
        self.hass = hass
        self.config = config
        self.base_path = os.path.join(hass.config.config_dir, "www")
        self.albums = {}

    async def scan_albums(self) -> None:
        """Scan for local photo albums (folders)."""
        photos_dir = os.path.join(self.base_path, "photos")
        
        # Create the photos directory if it doesn't exist
        dir_exists = await self.hass.async_add_executor_job(os.path.exists, photos_dir)
        if not dir_exists:
            try:
                await self.hass.async_add_executor_job(os.makedirs, photos_dir)
                _LOGGER.info("Created photos directory: %s", photos_dir)
            except Exception as ex:
                _LOGGER.error("Error creating photos directory: %s", ex)
                return

        # Add the main "ALL" album that includes all photos
        all_album = Album(
            id=self.config.get(CONF_ALBUM_ID_FAVORITES, "ALL"),
            title="All",
            path=photos_dir
        )
        self.albums[all_album.id] = all_album

        # Scan for subdirectories to use as albums
        try:
            dir_items = await self.hass.async_add_executor_job(os.listdir, photos_dir)
            for item in dir_items:
                item_path = os.path.join(photos_dir, item)
                is_dir = await self.hass.async_add_executor_job(os.path.isdir, item_path)
                if is_dir:
                    album = Album(
                        id=item,
                        title=item,
                        path=item_path
                    )
                    self.albums[album.id] = album
                    _LOGGER.debug("Found album: %s at %s", album.title, album.path)
        except Exception as ex:
            _LOGGER.error("Error scanning for albums: %s", ex)

    def get_albums(self) -> List[Album]:
        """Get all available albums."""
        return list(self.albums.values())

    def get_album(self, album_id: str) -> Optional[Album]:
        """Get album by ID."""
        return self.albums.get(album_id)

    async def get_media_items(self, album_id: str) -> List[MediaItem]:
        """Get all media items in an album."""
        album = self.get_album(album_id)
        if not album:
            _LOGGER.error("Album not found: %s", album_id)
            return []

        media_items = []
        
        # For the ALL album, scan all subdirectories too
        if album_id == self.config.get(CONF_ALBUM_ID_FAVORITES, "ALL"):
            # Use async_add_executor_job to run the walk operation in a separate thread
            def walk_directory():
                result = []
                for root, _, files in os.walk(album.path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        result.append((file, file_path))
                return result
                
            file_paths = await self.hass.async_add_executor_job(walk_directory)
            
            for file, file_path in file_paths:
                is_valid = await self.hass.async_add_executor_job(self._is_valid_image, file_path)
                if is_valid:
                    media_item = MediaItem(
                        id=file,
                        filename=file,
                        path=file_path
                    )
                    media_items.append(media_item)
        else:
            # For regular albums, just scan the directory
            try:
                dir_files = await self.hass.async_add_executor_job(os.listdir, album.path)
                for file in dir_files:
                    file_path = os.path.join(album.path, file)
                    is_file = await self.hass.async_add_executor_job(os.path.isfile, file_path)
                    is_valid = False
                    if is_file:
                        is_valid = await self.hass.async_add_executor_job(self._is_valid_image, file_path)
                    if is_file and is_valid:
                        media_item = MediaItem(
                            id=file,
                            filename=file,
                            path=file_path
                        )
                        media_items.append(media_item)
            except Exception as ex:
                _LOGGER.error("Error getting media items for album %s: %s", album_id, ex)

        # Update the media count for the album
        album.media_items_count = len(media_items)
        
        # Sort media items alphabetically by filename
        media_items.sort(key=lambda item: item.filename.lower())
        
        return media_items

    async def get_media_item(self, album_id: str, media_id: str) -> Optional[MediaItem]:
        """Get a specific media item by ID."""
        media_items = await self.get_media_items(album_id)
        for item in media_items:
            if item.id == media_id:
                return item
        return None

    async def get_random_media_item(self, album_id: str) -> Optional[MediaItem]:
        """Get a random media item from an album."""
        media_items = await self.get_media_items(album_id)
        if not media_items:
            return None
        return random.choice(media_items)

    async def get_next_media_item(self, album_id: str, current_media_id: str) -> Optional[MediaItem]:
        """Get the next media item in alphabetical order."""
        media_items = await self.get_media_items(album_id)
        if not media_items:
            return None
            
        # If no current media, return the first one
        if not current_media_id:
            return media_items[0]
            
        # Find the current media in the list
        current_index = -1
        for i, item in enumerate(media_items):
            if item.id == current_media_id:
                current_index = i
                break
                
        # If found, return the next one (or loop back to the first)
        if current_index >= 0:
            next_index = (current_index + 1) % len(media_items)
            return media_items[next_index]
        
        # If not found, return the first one
        return media_items[0]

    def get_media_url(self, media_item: MediaItem) -> str:
        """Get the URL for a media item that can be used in Home Assistant."""
        # Convert the file path to a URL that Home Assistant can access
        # Format: /local/photos/[album]/filename.jpg
        rel_path = os.path.relpath(media_item.path, self.base_path)
        return f"/local/{rel_path}"

    def _is_valid_image(self, file_path: str) -> bool:
        """Check if a file is a valid image.
        
        This is a synchronous method that should be called using async_add_executor_job
        """
        # Check file extension
        _, ext = os.path.splitext(file_path.lower())
        if ext not in SUPPORTED_EXTENSIONS:
            return False
            
        # Verify it's a file and not too large (limit to 20MB)
        try:
            if not os.path.isfile(file_path):
                return False
                
            file_size = os.path.getsize(file_path)
            if file_size > 20 * 1024 * 1024:  # 20MB
                _LOGGER.warning("File too large (>20MB): %s", file_path)
                return False
                
            # Additional check using mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type or not mime_type.startswith('image/'):
                return False
                
            return True
        except Exception as ex:
            _LOGGER.error("Error checking image file %s: %s", file_path, ex)
            return False
