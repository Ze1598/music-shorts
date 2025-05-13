# YouTube Shorts Automation Script

## Overview

This Python script automates the creation of YouTube Shorts videos. It takes a square input image and an audio file, and generates a 9:16 aspect ratio video (defaulting to 60 FPS). The video features the input image centered with rounded corners, and its shadow also has rounded corners for a cohesive look. Users can choose between a solid background color (derived from the image's predominant color) or a blurred version of the input image as the background.

A key feature is an optional, highly customizable audio-reactive waveform animation displayed below the centered image, with configurable vertical spacing between the image and the waveform. This version (v6) incorporates user-preferred default parameter values, implements a more sophisticated "contrast" mode for waveform color selection (aiming for legible inverted or complementary-like colors before falling back to black/white), and ensures the shadow for both the main image and the waveform respects rounded corners.

All key aspects like input file paths, audio timings, image placement, visual effects, and output filename are configurable through global variables within the script.

## Features

-   **Input Image**: Uses a user-provided square image (PNG or JPG).
-   **Rounded Corners**: Both the centered image and its shadow are processed to have rounded corners. Radius is configurable.
-   **Selectable Background Mode**: `"solid"` (predominant color) or `"blur_image"`. Blur intensity and image fit (`"stretch"`, `"crop"`, `"fill"`) are configurable.
-   **Unified Shadow Effect**: The centered image and its waveform (if enabled) receive a shadow using the same offset, blur, and color derivation logic.
-   **Advanced Audio-Reactive Waveform Animation**:
    *   **Enabled/Disabled**: Can be turned on or off.
    *   **Analysis Modes**: `"rms"` (overall intensity) or `"melspectrogram"` (dynamic frequency band reaction).
    *   **Advanced Color Modes**: For waveform bars:
        *   `"custom"`: Uses `WAVEFORM_COLOR` RGB tuple.
        *   `"contrast"`: Automatically selects a legible contrasting color (attempts inverted, then complementary-like, then black/white) against the background area behind the waveform or the predominant image color.
        *   `"white"`: Forces waveform to be white.
        *   `"black"`: Forces waveform to be black.
    *   **Shadow**: Waveform bars have a shadow, using shared parameters.
    *   **Customizable Appearance**: Waveform height, bar count (`n_mels` for melspectrogram), bar spacing, smoothing, and vertical spacing from the main image (`SPACING_IMAGE_WAVEFORM`) are configurable.
-   **Custom Audio & FPS**: Uses user-provided audio (WAV/MP3) and allows setting video FPS (default 60).
-   **Audio Trimming**: Specifies start/end times for audio, dictating video duration.
-   **Parameterized Configuration**: All settings via global variables, with user-preferred defaults integrated.
-   **Standard Shorts Format**: Outputs 1080x1920 video.

## Dependencies

-   **Pillow (PIL)**
-   **MoviePy** (version 1.0.3 recommended)
-   **NumPy**
-   **Librosa**
-   **colorsys** (Python built-in)

Install using pip:
```bash
pip install Pillow moviepy==1.0.3 numpy librosa
```

## Script Parameters (Global Variables)

Located at the beginning of `youtube_shorts_script_v6.py`. Key additions/changes from v5:

-   `VIDEO_FPS` (int): Frames per second for the output video (default: `60`).
-   `SPACING_IMAGE_WAVEFORM` (int): Vertical spacing in pixels between the bottom of the centered image and the top of the waveform area (default: `20`, functionality confirmed).
-   **Default Values**: Many parameters now reflect user-preferred defaults (e.g., `BACKGROUND_MODE = "blur_image"`, `IMAGE_WIDTH_PERCENTAGE = 55`, `WAVEFORM_COLOR_MODE = "contrast"`, specific audio timings).
-   The `get_waveform_contrast_color` function now implements more sophisticated logic for choosing a contrasting color beyond simple black/white.

**(Other parameters like `IMAGE_PATH`, `AUDIO_PATH`, `BACKGROUND_MODE`, `SHADOW_OFFSET_X/Y`, `WAVEFORM_ANALYSIS_MODE`, etc., are still present as described in previous README versions, with their behavior enhanced by the new logic where applicable).**

## How to Use

1.  **Install Dependencies**.
2.  **Prepare Inputs**: Square image and audio file.
3.  **Configure Parameters**: Update placeholders for `IMAGE_PATH` and `AUDIO_PATH` in `youtube_shorts_script_v6.py`. Adjust other global variables as needed.
4.  **Run Script**: `python3 youtube_shorts_script_v6.py` (or `python3.11`).
5.  **Output**: Video file (e.g., `youtube_short_final_v6.mp4`).

## Script Execution Steps (Internal Logic Changes from v5)

1.  **Pre-computation (`precompute_assets`)**:
    *   The shadow for the main image (`CENTER_IMG_SHADOW_GLOBAL`) is now created by applying rounded corners to a solid color silhouette derived from the image's alpha, then blurring. This ensures the shadow shape matches the rounded image.
    *   `SPACING_IMAGE_WAVEFORM` is explicitly used in calculating `WAVEFORM_AREA_TOP_Y_GLOBAL`.
2.  **Frame Generation (`make_frame_for_moviepy`)**:
    *   **Waveform Color**: If `WAVEFORM_COLOR_MODE` is `"contrast"`, the `get_waveform_contrast_color` function is called. This function first tries an inverted color. If contrast isn't sufficient, it attempts a complementary-like color with adjusted lightness. If still not sufficiently contrasting, it falls back to black or white based on the background luminance.
    *   The pre-computed rounded shadow (`CENTER_IMG_SHADOW_GLOBAL`) is pasted before the main image.

**(Other core logic for background, image processing, audio analysis (RMS/Mel Spectrogram), waveform bar drawing, and video assembly remains similar to v5 but incorporates the user's default parameters and the specific enhancements mentioned).**

## Output

The script produces a video file with the features described, incorporating the user's settings, the refined waveform contrast color logic, and correct image-to-waveform spacing.