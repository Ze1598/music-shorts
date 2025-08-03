# YouTube Shorts Generator

## Overview

This application automates the creation of YouTube Shorts videos. It takes a square input image and an audio file, and generates a 9:16 aspect ratio video (defaulting to 60 FPS). The video features the input image centered with rounded corners, and its shadow also has rounded corners for a cohesive look. Users can choose between a solid background color (derived from the image's predominant color) or a blurred version of the input image as the background.

A key feature is an optional, highly customizable audio-reactive waveform animation displayed below the centered image, with configurable vertical spacing between the image and the waveform. This version (v6) incorporates user-preferred default parameter values, implements a more sophisticated "contrast" mode for waveform color selection (aiming for legible inverted or complementary-like colors before falling back to black/white), and ensures the shadow for both the main image and the waveform respects rounded corners.

All key aspects like input file paths, audio timings, image placement, visual effects, and output filename are configurable through global variables within the script.

## Features

-   **Input Image**: Uses a user-provided square image (PNG or JPG).
-   **Rounded Corners**: Both the centered image and its shadow are processed to have rounded corners. Radius is configurable.
-   **Selectable Background Mode**: `"solid"` (predominant color) or `"blur_image"`. Blur intensity and image fit (`"stretch"`, `"crop"`, `"fill"`) are configurable.
-   **Unified Shadow Effect**: The centered image and its waveform (if enabled) receive a shadow using the same offset, blur, and color derivation logic.
-   **Video Profiles System**: Pre-configured settings profiles for different video types:
    *   **Shorts with waveform**: 9:16 aspect ratio (1080x1920) optimized for YouTube Shorts
    *   **Visualizer with waveform**: 16:9 aspect ratio (1920x1080) for landscape music visualizations
    *   **Custom profiles**: Easily extensible through `video_profiles.yaml` configuration
-   **Smart Audio Duration Management**: 
    *   **Auto-calculate video length**: Automatically sets video duration to match audio file length
    *   **Editable time controls**: Start/end times remain fully editable even with auto-calculation enabled
    *   **Persistent values**: Manual adjustments are preserved when toggling between auto/manual modes
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
-   **Fully Customizable**: All settings remain editable regardless of profile selection - profiles only provide convenient starting points.
-   **Multiple Output Formats**: Standard Shorts format (9:16) and landscape format (16:9) supported.

## Dependencies

-   **Streamlit** (for the web interface)
-   **Pillow (PIL)** (for image processing)
-   **MoviePy** (version 1.0.3 recommended)
-   **NumPy**
-   **Librosa** (for audio analysis)
-   **PyYAML** (for video profiles configuration)
-   **colorsys** (Python built-in)

Install all dependencies using pip:
```bash
pip install -r requirements.txt
```

## Video Profiles

The application now includes a flexible video profiles system via `video_profiles.yaml`:

### Available Profiles

1. **Shorts with waveform** (default):
   - 9:16 aspect ratio (1080x1920)
   - 65% image width
   - Optimized for YouTube Shorts format

2. **Visualizer with waveform**:
   - 16:9 aspect ratio (1920x1080) 
   - 25% image width (smaller, more focus on waveform)
   - Ideal for landscape music visualizations

### Profile Configuration

All profiles are defined in `video_profiles.yaml` with the following structure:
- **Input/Output**: Audio timing, output filename, auto-duration settings
- **Video**: Dimensions, FPS, aspect ratio
- **Background**: Mode (blur/solid), blur radius, image fit options
- **Image**: Size, positioning, corner radius
- **Shadow**: Offsets, blur radius, darkness
- **Waveform**: All animation parameters, colors, spacing

### Adding Custom Profiles

Simply extend `video_profiles.yaml` with new profile definitions. Each profile requires a `display_name` attribute for the UI dropdown.

## Parameters

All parameters can be configured through the Streamlit interface, with profile-based defaults or manual customization:

-   **Video Profiles**: Choose from pre-configured settings or customize any parameter
-   **Auto-Duration**: Automatically set video length to match audio file duration
-   **Real-time Editing**: All fields remain editable regardless of profile selection
-   **Session Persistence**: Manual changes are preserved when switching between auto/manual modes
-   **Advanced Waveform**: Sophisticated contrast color selection and audio analysis options

**(All original parameters remain available and are now organized in an intuitive tabbed interface across Input/Output, Video Settings, Background, Image, and Waveform sections.)**

## How to Use

### Option 1: Streamlit Interface (Recommended)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Streamlit App**:
   ```bash
   streamlit run app.py
   ```

3. **Use the Interface**:
   - Upload your image and audio files
   - Select a video profile (or keep the default "Shorts with waveform")
   - Optionally enable auto-calculate video length to match audio duration
   - Configure all parameters using the intuitive tabbed interface
   - Generate your video with a single click
   - Download the resulting video directly from the app

### Option 2: Direct Script Usage

1. **Install Dependencies**.
2. **Prepare Inputs**: Square image and audio file.
3. **Configure Parameters**: Update placeholders for `IMAGE_PATH` and `AUDIO_PATH` in `main.py`. Adjust other global variables as needed.
4. **Run Script**: `python main.py`.
5. **Output**: Video file (e.g., `youtube_short_final_v6.mp4`).

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