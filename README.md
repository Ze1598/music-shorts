# YouTube Shorts Generator

## Overview

This application automates the creation of YouTube Shorts videos with integrated YouTube upload and scheduling capabilities. It takes a square input image and an audio file, and generates a 9:16 aspect ratio video (defaulting to 60 FPS). The video features the input image centered with rounded corners, and its shadow also has rounded corners for a cohesive look. Users can choose between a solid background color (derived from the image's predominant color) or a blurred version of the input image as the background.

A key feature is an optional, highly customizable audio-reactive waveform animation displayed below the centered image, with configurable vertical spacing between the image and the waveform. The application now includes full YouTube integration for direct upload and advanced scheduling of videos.

All key aspects like input file paths, audio timings, image placement, visual effects, output filename, and YouTube publishing settings are configurable through an intuitive web interface.

## Features

### 🎬 Video Generation
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

### 📺 YouTube Integration
-   **Direct Upload**: Upload generated videos directly to YouTube without leaving the app
-   **Advanced Scheduling**: Schedule videos for future publication with timezone support
-   **Automatic YouTube Shorts Detection**: Automatically tags qualifying videos as YouTube Shorts
-   **Privacy Controls**: Set video privacy (private, unlisted, public) with automatic requirements for scheduled uploads
-   **Metadata Management**: Add titles, descriptions, tags, and custom thumbnails
-   **OAuth Authentication**: Secure Google OAuth integration with automatic redirect handling
-   **Upload Progress Tracking**: Real-time upload progress with retry logic for failed uploads
-   **Multi-Environment Support**: Works both locally and when deployed to cloud platforms

### ⚙️ Technical Features
-   **Custom Audio & FPS**: Uses user-provided audio (WAV/MP3) and allows setting video FPS (default 60).
-   **Audio Trimming**: Specifies start/end times for audio, dictating video duration.
-   **Fully Customizable**: All settings remain editable regardless of profile selection - profiles only provide convenient starting points.
-   **Multiple Output Formats**: Standard Shorts format (9:16) and landscape format (16:9) supported.
-   **Responsive Web Interface**: Clean, tabbed interface with real-time validation and preview.

## Dependencies

### Core Dependencies
-   **Streamlit** (for the web interface)
-   **Pillow (PIL)** (for image processing)
-   **MoviePy** (version 1.0.3 recommended)
-   **NumPy**
-   **Librosa** (for audio analysis)
-   **PyYAML** (for video profiles configuration)

### YouTube Integration Dependencies
-   **google-auth** (≥2.15.0)
-   **google-auth-oauthlib** (≥0.7.1)
-   **google-auth-httplib2** (≥0.1.0)
-   **google-api-python-client** (≥2.70.0)
-   **pytz** (≥2023.3) - for timezone support

Install all dependencies using pip:
```bash
pip install -r requirements.txt
```

## YouTube Integration Setup

### Required Google Cloud Setup

To use the YouTube upload and scheduling features, you need to set up Google OAuth credentials:

#### 1. Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the **YouTube Data API v3**:
   - Go to APIs & Services → Library
   - Search for "YouTube Data API v3"
   - Click "Enable"

#### 2. Create OAuth 2.0 Credentials
1. Go to APIs & Services → Credentials
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Configure the OAuth consent screen if prompted
4. Choose "Web application" as application type
5. Add these **Authorized redirect URIs**:
   - `http://localhost:8501` (for local development)
   - `https://your-app-url.streamlit.app/` (for deployed version)
6. Download the credentials JSON file

#### 3. Required OAuth Scopes
The application requires the following Google OAuth scope:
- `https://www.googleapis.com/auth/youtube` - Full access to YouTube account for uploading and managing videos

**Note**: This scope requires Google verification if you plan to make the app available to other users. For personal use, you can run in testing mode.

#### 4. YouTube Channel Requirements
- You must have a YouTube channel associated with your Google account
- The channel must be in good standing (no strikes or restrictions)
- For scheduled uploads, videos must be set to "private" privacy status (YouTube API requirement)

### Credentials Configuration

The app supports two methods for providing OAuth credentials:

#### Local Development (Recommended)
1. Download your OAuth credentials JSON from Google Cloud Console
2. Rename it to `client_secrets.json` 
3. Place it in the project root directory
4. The app will automatically use this file

#### Cloud Deployment (Streamlit Cloud, etc.)
Set these environment variables in your deployment platform:
- `GOOGLE_CLIENT_ID` - Your OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Your OAuth client secret
- `STREAMLIT_APP_URL` - Your app's URL (e.g., `https://your-app.streamlit.app`)

The app automatically detects the environment and uses the appropriate method.

### Authentication Flow
1. Click "Get Authorization Code" in the YouTube tab
2. You'll be redirected to Google for authorization
3. After granting permissions, you'll be redirected back to the app
4. Authentication completes automatically - no manual code copying required!

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

### Streamlit Interface (Recommended)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup YouTube Credentials** (Optional):
   - Follow the [YouTube Integration Setup](#youtube-integration-setup) section above
   - Place `client_secrets.json` in project directory for local use
   - Or set environment variables for cloud deployment

3. **Run the Streamlit App**:
   ```bash
   streamlit run app.py
   ```

4. **Generate Videos**:
   - **Input/Output Tab**: Upload your image and audio files
   - **Video Settings Tab**: Configure video dimensions, FPS, and format
   - **Background Tab**: Choose between solid color or blurred image background
   - **Image Tab**: Adjust image size, position, corner radius, and shadow effects
   - **Waveform Tab**: Configure audio-reactive waveform animation (optional)
   - **Generate Tab**: Create your video with a single click
   - Download the resulting video directly from the app

5. **Upload to YouTube** (Optional):
   - **YouTube Tab**: Connect your YouTube account with OAuth
   - **Direct Upload**: Upload generated videos immediately with metadata
   - **Advanced Scheduling**: Schedule videos for future publication
     - Set publish date and time with timezone support
     - Videos are automatically set to "private" for scheduling (YouTube requirement)
     - Minimum 60 minutes in the future (YouTube requirement)
   - **Metadata Management**: Add titles, descriptions, tags
   - **Auto-Detection**: Automatically tags qualifying videos as YouTube Shorts

### Direct Script Usage (Legacy)

For advanced users who prefer command-line usage:

1. **Install Dependencies**
2. **Prepare Inputs**: Square image and audio file
3. **Configure Parameters**: Update `IMAGE_PATH` and `AUDIO_PATH` in `video_generation.py`
4. **Run Script**: `python video_generation.py`
5. **Output**: Video file (e.g., `youtube_short.mp4`)

*Note: The Streamlit interface is recommended as it provides a much more user-friendly experience with all the latest features.*

## Security & Privacy

### Data Handling
- **Local Processing**: All video generation happens locally on your machine
- **No Data Storage**: The app doesn't store your media files or personal data
- **Temporary Files**: Uploaded files are temporarily stored during processing and cleaned up afterward

### YouTube Integration Security
- **OAuth 2.0**: Uses industry-standard Google OAuth for secure authentication
- **Limited Scope**: Only requests YouTube upload permissions, no access to other Google services
- **Credential Storage**: 
  - Local: Credentials stored in browser session only
  - Cloud: Environment variables stored securely by hosting platform
- **No Persistent Storage**: Authentication tokens are not permanently stored

### Recommended Security Practices
- Use a dedicated Google account for API access if sharing the app
- Regularly review authorized apps in your Google account settings
- Keep your `client_secrets.json` file secure and never commit it to version control
- For production deployments, consider implementing additional access controls

## Troubleshooting

### Common YouTube Integration Issues

**"Invalid redirect URI" error:**
- Ensure your Google Cloud Console has the correct redirect URIs
- Local: `http://localhost:8501`
- Deployed: `https://your-app-url.streamlit.app/`

**"The request metadata specifies an invalid scheduled publishing time":**
- Ensure scheduled time is at least 60 minutes in the future
- Verify timezone settings are correct
- Check that the video privacy is set to "private" for scheduling

**Authentication not working:**
- Clear browser cache and try again
- Verify your Google Cloud project has YouTube Data API v3 enabled
- Check that your OAuth consent screen is configured properly

### Video Generation Issues

**Out of memory errors:**
- Reduce video resolution or FPS
- Use shorter audio clips
- Close other applications to free up RAM

**Audio not syncing:**
- Ensure audio file is not corrupted
- Try converting audio to WAV format
- Check that start/end times are within the audio file duration

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly, especially YouTube integration if modified
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.