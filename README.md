# Local Photos Integration for Home Assistant

> [!NOTE]
> This integration is a refactored version of the Google Photos integration, modified to work with local photos instead of the Google Photos API.

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

This integration allows you to add local photo albums from your Home Assistant `/config/www/photos` directory as a `camera` entity to your setup. The entity will be showing media from your local photo albums so you can add some personalization to your dashboards without relying on external services.

**This component will set up the following platforms.**

For each selected album:

Platform | Name | Description
-- | --  | --
`camera` | `media` | An image from the Google Photos Album.
`sensor` | `filename` | Filename of the currently selected media item.
`sensor` | `creation_timestamp` | Timestamp of the currently selected media item.
`sensor` | `media_count` | Counter showing the number of media items in the album (photo + video). It could take a while to populate all media items, to check if the integration is still loading an attribute `is_updating` is available.
`select` | `image_selection_mode` | Configuration setting on how to pick the next image.
`select` | `crop_mode` | Configuration setting on how to crop the image, either `Original`, `Crop` or `Combine images` [(explanation)](#crop-modes).
`select` | `update_interval` | Configuration setting on how often to update the image, if you have a lot of albums running on your instance it is adviseable to not set this to low.

![example][exampleimg]

## Installation

### HACS (Once available)
1. Find the integration as `Local Photos`
1. Click install.
1. Restart Home Assistant.

### Manual
1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `local_photos`.
1. Download _all_ the files from the `custom_components/local_photos/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant

## Configuration
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Local Photos".
2. Click on the integration and follow the setup process.
3. The integration will create a `/config/www/photos` directory if it doesn't already exist. This is where you'll store your photos.

### Adding Photos

1. Place your photos in the `/config/www/photos` directory. You can access this directory through the File Editor add-on or via SFTP/Samba depending on your Home Assistant setup.
2. You can organize photos into albums by creating subdirectories in the `/config/www/photos` directory. For example:
   - `/config/www/photos/vacation/` - For vacation photos
   - `/config/www/photos/family/` - For family photos
   - `/config/www/photos/holidays/` - For holiday photos
3. The integration will automatically detect these directories as albums.
4. Supported image formats include: JPG, JPEG, PNG, GIF, BMP, and WEBP.

### Adding Albums to Home Assistant

1. After adding photos to your directories, go to the Local Photos integration card in Home Assistant.
2. Click "Configure" on the integration card.
3. Select "Album Select" from the menu.
4. Choose the album you want to add from the dropdown menu and click "Submit".
5. The album will now be available as a camera entity in Home Assistant.

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
entity: camera.google_photos_library_favorites
aspect_ratio: '1:1'
tap_action:
  action: call-service
  service: google_photos.next_media
  data:
    mode: RANDOM
  target:
    entity_id: camera.google_photos_library_favorites
```

### Lovelace wall panel

You can combine this integration with the [lovelace-wallpanel](https://github.com/j-a-n/lovelace-wallpanel) (min version 4.8) extension by [j-a-n](https://github.com/j-a-n) to show your photos as a screensaver on your dashboards. For the best results set the crop mode of the album to [Crop](#crop) or [Combine images](#combine-images).

Home Assistant Dashboard configuration yaml (raw config):
```yaml
wallpanel:
  enabled: true
  hide_toolbar: true
  hide_sidebar: true
  fullscreen: true
  image_fit: cover
  image_url: media-entity://camera.google_photos_favorites_media,
  cards:
      # Note: For this markdown card to work you need to enable write metadata in the integration settings.
    - type: markdown
      content: >-
        {{states.camera.google_photos_favorites_media.attributes.media_metadata.photo.cameraMake}},
        {{states.camera.google_photos_favorites_media.attributes.media_metadata.photo.cameraModel}}
```

**Important** Make sure to align the image crop modes with the configuration of the wall panel, if not set correctly images might appear blurry. For crop mode [original](#original), set the `image_fit` property to `contain`.

## Service

It is possible to control the album using the service exposed by `google_photos`.

### Go to next media

#### Example
```
service: google_photos.next_media
data:
  entity_id: camera.google_photos_library_favorites
  mode: Random
```

#### Key Descriptions
| Key | Required | Default | Description |
| --- | --- | --- | --- |
| entity_id | Yes | | Entity name of a Google Photo album camera. |
| mode | No | `Random` | Selection mode next image, either `Random` or `Album order` |

## FAQ

### How do I add new photos to my albums?

Simply add new image files to the appropriate directories in your `/config/www/photos` folder. The integration will automatically detect new photos the next time it refreshes. You can access this directory through the File Editor add-on or via SFTP/Samba depending on your Home Assistant setup.

### Why aren't my photos showing up in the integration?

Check that your photos are in the correct directory (`/config/www/photos` or a subdirectory) and that they are in a supported format (JPG, JPEG, PNG, GIF, BMP, or WEBP). Also, make sure the files aren't too large - the integration has a 20MB file size limit for images.

### Can I use this integration offline?

Yes! That's one of the main benefits of this integration compared to the original Google Photos integration. Since all photos are stored locally, this integration works completely offline without any external API dependencies.

## Notes / Remarks / Limitations

- The integration scans the photo directories when you add an album, so if you add many new photos, you may need to restart Home Assistant or reconfigure the album to see them.
- Very large images (>20MB) are skipped to prevent performance issues.
- For best performance, keep your photo collection reasonably sized. Having thousands of high-resolution photos may impact performance.

## Future plans
- Support for videos
- Support for filtering images by file name or metadata
- Support for filtering images by date/time
- Custom photo carousel frontend component
- Add trigger on new media detection
- Add ability to rotate images
- Add support for image metadata extraction (EXIF data)

## Debug Logging
To enable debug log, add the following lines to your configuration.yaml and restart your HomeAssistant.

```yaml
logger:
  default: info
  logs:
    custom_components.google_photos: debug
    googleapiclient: debug
```

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

<!---->

***

[buymecoffee]: https://www.buymeacoffee.com/Daanoz
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/daanoz/ha-google-photos.svg?style=for-the-badge
[commits]: https://github.com/daanoz/ha-google-photos/commits/master
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.com/invite/home-assistant
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: https://raw.githubusercontent.com/daanoz/ha-google-photos/main/example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: https://github.com/daanoz/ha-google-photos/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/custom-components/integration_blueprint.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Daan%20Sieben%20%40Daanoz-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/daanoz/ha-google-photos.svg?style=for-the-badge
[releases]: https://github.com/daanoz/ha-google-photos/releases
[user_profile]: https://github.com/daanoz
