# Local Photos Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]
[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![Buy me a coffee][buymecoffeebadge]][buymecoffee]

This integration allows you to add local photo albums from a directory of your choice as a `camera` entity to your setup. The entity will be showing media from your local photo albums so you can add some personalization to your dashboards without relying on external services.

**This component will set up the following platforms.**

For each selected album:

Platform | Name | Description
-- | --  | --
`camera` | `media` | An image from the Local Photos Album.
`sensor` | `filename` | Filename of the currently selected media item.
`sensor` | `creation_timestamp` | Timestamp of the currently selected media item.
`sensor` | `media_count` | Counter showing the number of media items in the album (photo + video).
`select` | `image_selection_mode` | Configuration setting on how to pick the next image.
`select` | `crop_mode` | Configuration setting on how to crop the image, either `Original`, `Crop` or `Combine images` [(explanation)](#crop-modes).
`select` | `update_interval` | Configuration setting on how often to update the image, if you have a lot of albums running on your instance it is adviseable to not set this to low.
`select` | `aspect_ratio` | Configuration setting for the target aspect ratio of displayed images (16:10, 16:9, 4:3, 1:1).

![example][exampleimg]

## Installation

### HACS (Not Currently In HACS)
1. Find the integration as `Local Photos`
1. Click install.
1. Restart Home Assistant.

### Manual
1. Using the tool of your choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `local_photos`.
1. Download _all_ the files from the `custom_components/local_photos/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant

## Configuration and Setup

### Setting Up Your Photo Directory

1. Create a directory for your photos and add your images to it. You can use any location accessible to Home Assistant and manage files via the File Editor add-on or SFTP/Samba.
2. You can organize photos into albums by creating subdirectories. For example:
   - `/config/www/images/vacation/` - For vacation photos
   - `/config/www/images/family/` - For family photos
   - `/config/www/images/holidays/` - For holiday photos
   - `/media/Photos/vacation/` - For vacation photos on external media
3. Supported image formats include: JPG, JPEG, PNG, GIF, BMP, and WEBP.

### Adding Albums to Home Assistant

1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Local Photos".
2. Click on the integration and enter the path to your photos directory.
3. If you're using a media source in Home Assistant OS (like a samba share), it will be mounted in the `/media` folder. For example, for a samba share called "Photos", you would set the path as `/media/Photos`.
4. After entering a valid directory path, you'll be presented with a list of available albums (subdirectories) in that location.
5. Select the album you want to display. If you want to display all photos, select "All Photos".
6. The album will be available as a camera entity in Home Assistant with a device name that reflects the selected album (e.g., "Local Photos Vacation").
7. To add another album, simply add the integration again and select a different album.

## Configuration

After installation, add the integration through the Home Assistant UI:

1. Go to **Settings** → **Devices & Services**
2. Click the **+ ADD INTEGRATION** button
3. Search for "Local Photos" and select it
4. Follow the configuration steps to specify your photos directory and select an album

The integration will scan the specified directory for subdirectories, each representing an album. Each album will be added as a separate camera entity.

### Settings

Each album has the following settings that can be configured through the entity settings:

#### Crop

This setting controls how images are displayed:

- **Original**: Maintains the original aspect ratio of the image, adding black bars if necessary
- **Crop**: Crops the image to fill the entire frame
- **Combine images**: For landscape displays showing portrait images (or vice versa), combines two similar images side by side

#### Aspect Ratio

Controls the target aspect ratio for displaying images:

- **16:10**: Default widescreen aspect ratio (1.6:1)
- **16:9**: Common TV/monitor widescreen format (1.78:1)
- **4:3**: Traditional monitor aspect ratio (1.33:1)
- **1:1**: Square aspect ratio

Note: When using the "Original" crop mode, the image will maintain its original aspect ratio but will be fitted within the selected aspect ratio frame. With "Crop" mode, images will be cropped to exactly match the selected aspect ratio.

#### Image Selection

Controls how the next image is selected:

- **Random**: Selects a random image from the album
- **Alphabetical order**: Cycles through images in alphabetical order

#### Update Interval

Controls how often the displayed image changes:

- Options range from 10 seconds to 1 day
- Set to "Manual" to disable automatic updates

## Crop modes

### Original

Provides scaled down images that would fit in the requested view in the original aspect ratio. If your dashboard configuration does not specify the aspect ratio, the card size could change for every image.

### Crop

Crop image to fit into the requested view.

### Combine images

In combine images mode, the integration will combine two images of the same orientation if it calculates that showing two images side by side would lead to a lower loss in square pixels than cropping a single image. For example; two portrait images on a landscape view.

## Examples

### Dashboard Picture card

```
show_state: false
show_name: false
camera_view: auto
type: picture-entity
entity: camera.local_photos_myalbum
aspect_ratio: '1:1'
tap_action:
  action: call-service
  service: local_photos.next_media
  data:
    mode: Random
  target:
    entity_id: camera.local_photos_myalbum
```

### Lovelace wall panel

You can combine this integration with the [lovelace-wallpanel](https://github.com/j-a-n/lovelace-wallpanel) (min version 4.8) extension by [j-a-n](https://github.com/j-a-n) to show your photos as a screensaver on your dashboards. For the best results set the crop mode of the album to [Crop](#crop) or [Combine images](#combine-images).

Home Assistant Dashboard configuration yaml (raw config):
```yaml
wallpanel:
  enabled: true
  image_url: media-entity://camera.local_photos_myalbum
  cards:
    - type: markdown
      content: >
        {{states.camera.local_photos_myalbum.attributes.media_metadata.path}}
```

## Service

It is possible to control the album using the service exposed by `local_photos`.

### Go to next media

#### Example
```
service: local_photos.next_media
data:
  entity_id: camera.local_photos_myalbum
  mode: Random
```

#### Key Descriptions
| Key | Required | Default | Description |
| --- | --- | --- | --- |
| entity_id | Yes | | Entity name of a Local Photos album camera. |
| mode | No | `Random` | Selection mode next image, either `Random` or `Alphabetical order` |

## FAQ

### How do I add new photos to my albums?

Simply add new image files to the appropriate directories in your photos folder. The integration will automatically detect new photos the next time it refreshes. You can access this directory through the File Editor add-on or via SFTP/Samba depending on your Home Assistant setup.

### Why aren't my photos showing up in the integration?

Check that your photos are in the correct directory (the one you specified during setup) and that they are in a supported format (JPG, JPEG, PNG, GIF, BMP, or WEBP). Also, make sure the files aren't too large - the integration has a 20MB file size limit for images.


## Notes / Remarks / Limitations

- The integration scans the photo directories when you add an album, so if you add many new photos, you may need to restart Home Assistant or reconfigure the album to see them.
- Very large images (>20MB) are skipped to prevent performance issues.
- For best performance, keep your photo collection reasonably sized. Having thousands of high-resolution photos may impact performance.
- The directory you specify must exist before you can set up the integration. The integration will not create directories for you.



## Debug Logging
To enable debug log, add the following lines to your configuration.yaml and restart your HomeAssistant.

```yaml
logger:
  default: info
  logs:
    custom_components.local_photos: debug
```

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Origin

This integration is a refactored version of the [Google Photos integration](https://github.com/Daanoz/ha-google-photos), modified to work with local photos instead of the Google Photos API as I really enjoyed the "Combine" mode of displaying photos.

The refactoring was done using AI assistance with Windsurf IDE, so while it has been tested, there may still be some issues to resolve.

<!---->


***

[buymecoffee]: https://www.buymeacoffee.com/Migz93
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/migz93/ha-local-photos.svg?style=for-the-badge
[commits]: https://github.com/migz93/ha-local-photos/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[exampleimg]: https://raw.githubusercontent.com/migz93/ha-local-photos/main/example.png
[license]: https://github.com/migz93/ha-local-photos/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/custom-components/integration_blueprint.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Migz93-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/migz93/ha-local-photos.svg?style=for-the-badge
[releases]: https://github.com/migz93/ha-local-photos/releases
[user_profile]: https://github.com/migz93
