# APP_PLAN.md

## Objective

Refactor the archived `ha-google-photos` Home Assistant integration to work with local photos hosted in the `/config/www` directory, instead of using the Google Photos API. The goal is to maintain as much of the existing feature set and functionality as possible while replacing the source of the photos.

## Overview of Required Changes

### 1. Remove Google Photos API Integration
- Eliminate all logic related to Google authentication, tokens, and API usage.
- Remove dependencies related to Google Photos (e.g., `google-auth`, `gphoto`, `oauthlib`, etc.).
- Clean up configuration entries and setup flows that were tied to Google credentials.

### 2. Load Photos from Local Directory
- Implement logic to read photo files from a specified folder inside `/config/www` (e.g., `/config/www/photos/`).
- Support basic filtering to only include valid image files (e.g., `.jpg`, `.png`).
- Ensure that file paths are converted into Home Assistant accessible URLs using the `/local/` path.

### 3. Replace Media Fetching Logic
- Adapt the image update logic to work with local files instead of pulling from the Google Photos API.
- Maintain functionality to rotate through images, fetch current image, and update images at defined intervals.

### 4. Preserve Existing Entity Behavior
- Keep existing Home Assistant entities (e.g., `camera`, `media_source`, or similar) functioning using the new local image data.
- Ensure services and attributes related to photo selection, display, or cycling are preserved where possible.

### 5. Update Configuration and Setup
- Simplify the integration configuration to accept a local folder path for images.
- Remove setup flows or configuration UI specific to Google OAuth or account linking.

### 6. Update Documentation
- Rewrite the integration documentation to reflect the change from Google Photos to local photos.
- Describe how users should place images into `/config/www/photos/` and configure the integration to point to that folder.

## Outcome

This refactor will convert `ha-google-photos` into a new integration that works entirely with local image files, making it suitable for offline or privacy-focused use without reliance on external APIs.
