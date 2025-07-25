"""Constants for Local Photos."""
from __future__ import annotations

DOMAIN = "local_photos"
MANUFACTURER = "Local Photos"

CONF_FOLDER_PATH = "folder_path"
CONF_ALBUM_ID = "album_id"  # Kept for compatibility
CONF_ALBUM_ID_FAVORITES = "ALL"  # Renamed from FAVORITES to ALL

SETTING_IMAGESELECTION_MODE_RANDOM = "Random"
SETTING_IMAGESELECTION_MODE_ALPHABETICAL = "Alphabetical order"
SETTING_IMAGESELECTION_MODE_OPTIONS = [
    SETTING_IMAGESELECTION_MODE_RANDOM,
    SETTING_IMAGESELECTION_MODE_ALPHABETICAL,
]
SETTING_IMAGESELECTION_MODE_DEFAULT_OPTION = SETTING_IMAGESELECTION_MODE_RANDOM

SETTING_INTERVAL_OPTION_NONE = "Never"
SETTING_INTERVAL_OPTION_10 = "10 seconds"
SETTING_INTERVAL_OPTION_20 = "20 seconds"
SETTING_INTERVAL_OPTION_30 = "30 seconds"
SETTING_INTERVAL_OPTION_60 = "60 seconds"
SETTING_INTERVAL_OPTION_120 = "120 seconds"
SETTING_INTERVAL_OPTION_300 = "300 seconds"
SETTING_INTERVAL_OPTIONS = [
    SETTING_INTERVAL_OPTION_NONE,
    SETTING_INTERVAL_OPTION_10,
    SETTING_INTERVAL_OPTION_20,
    SETTING_INTERVAL_OPTION_30,
    SETTING_INTERVAL_OPTION_60,
    SETTING_INTERVAL_OPTION_120,
    SETTING_INTERVAL_OPTION_300,
]
SETTING_INTERVAL_DEFAULT_OPTION = SETTING_INTERVAL_OPTION_60
SETTING_INTERVAL_MAP = dict(
    {
        SETTING_INTERVAL_OPTION_NONE: None,
        SETTING_INTERVAL_OPTION_10: 10,
        SETTING_INTERVAL_OPTION_20: 20,
        SETTING_INTERVAL_OPTION_30: 30,
        SETTING_INTERVAL_OPTION_60: 60,
        SETTING_INTERVAL_OPTION_120: 120,
        SETTING_INTERVAL_OPTION_300: 300,
    }
)

CONF_WRITEMETADATA = "attribute_metadata"
WRITEMETADATA_DEFAULT_OPTION = False

SETTING_CROP_MODE_ORIGINAL = "Original"
SETTING_CROP_MODE_CROP = "Crop"
SETTING_CROP_MODE_COMBINED = "Combine images"
SETTING_CROP_MODE_OPTIONS = [
    SETTING_CROP_MODE_ORIGINAL,
    SETTING_CROP_MODE_CROP,
    SETTING_CROP_MODE_COMBINED,
]
SETTING_CROP_MODE_DEFAULT_OPTION = SETTING_CROP_MODE_ORIGINAL

# Aspect ratio settings
CONF_ASPECT_RATIO = "aspect_ratio"
SETTING_ASPECT_RATIO_16_9 = "16:9"
SETTING_ASPECT_RATIO_16_10 = "16:10"
SETTING_ASPECT_RATIO_4_3 = "4:3"
SETTING_ASPECT_RATIO_1_1 = "1:1"
SETTING_ASPECT_RATIO_OPTIONS = [
    SETTING_ASPECT_RATIO_16_10,
    SETTING_ASPECT_RATIO_16_9,
    SETTING_ASPECT_RATIO_4_3,
    SETTING_ASPECT_RATIO_1_1,
]
SETTING_ASPECT_RATIO_DEFAULT_OPTION = SETTING_ASPECT_RATIO_16_10

# Aspect ratio values (width:height)
ASPECT_RATIO_VALUES = {
    SETTING_ASPECT_RATIO_16_9: (16, 9),
    SETTING_ASPECT_RATIO_16_10: (16, 10),
    SETTING_ASPECT_RATIO_4_3: (4, 3),
    SETTING_ASPECT_RATIO_1_1: (1, 1),
}
