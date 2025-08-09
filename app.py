# Updated with enhanced scheduling - v4 (fixed privacy + timing requirements)
import streamlit as st
import os
import tempfile
from pathlib import Path
import shutil
import sys
import importlib
import yaml

# Import main module and its functions
import video_generation
import moviepy.editor as mpe

# Import YouTube integration modules
from youtube_service import YouTubeService, VideoMetadata

st.set_page_config(
    page_title="YouTube Shorts Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("YouTube Shorts Generator")
st.markdown("Create beautiful music visualization videos for YouTube Shorts")

# Load video profiles
@st.cache_data
def load_video_profiles():
    try:
        with open('video_profiles.yaml', 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        st.error("video_profiles.yaml not found")
        return {}
    except yaml.YAMLError as e:
        st.error(f"Error loading video profiles: {e}")
        return {}

profiles = load_video_profiles()

# Helper function to get profile values
def get_profile_value(profile_key, path, default=None):
    """Get a value from the selected profile using dot notation path"""
    if not profiles or profile_key not in profiles:
        return default
    
    profile = profiles[profile_key]
    keys = path.split('.')
    value = profile
    
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

# Create tabs for different sections
tab_input, tab_video, tab_background, tab_image, tab_waveform, tab_generate, tab_youtube = st.tabs([
    "Input/Output", "Video Settings", "Background", "Image", "Waveform", "Generate", "YouTube"
])

# Function to run the main script with the provided parameters
def generate_video(params):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(os.path.join(script_dir, params["OUTPUT_VIDEO_FILENAME"]))
        os.makedirs(output_dir, exist_ok=True)
        
        # Ensure audio times are valid numbers
        audio_start_time_sec = max(0, params["AUDIO_START_TIME"])
        audio_end_time_sec = max(audio_start_time_sec + 1, params["AUDIO_END_TIME"])
        
        # Call the precompute_assets function from main.py with all necessary parameters
        assets = video_generation.precompute_assets(
            image_path=params["IMAGE_PATH"],
            video_width=params["VIDEO_WIDTH"],
            video_height=params["VIDEO_HEIGHT"],
            background_mode=params["BACKGROUND_MODE"],
            background_image_fit=params["BACKGROUND_IMAGE_FIT"],
            background_blur_radius=params["BACKGROUND_BLUR_RADIUS"],
            image_width_percentage=params["IMAGE_WIDTH_PERCENTAGE"],
            image_corner_radius=params["IMAGE_CORNER_RADIUS"],
            image_x_position=params["IMAGE_X_POSITION"],
            image_y_position=params["IMAGE_Y_POSITION"],
            shadow_darkness_factor=params["SHADOW_DARKNESS_FACTOR"],
            shadow_blur_radius=params["SHADOW_BLUR_RADIUS"],
            waveform_enabled=params["WAVEFORM_ENABLED"],
            waveform_height_percentage=params["WAVEFORM_HEIGHT_PERCENTAGE"],
            spacing_image_waveform=params["SPACING_IMAGE_WAVEFORM"],
            audio_path=params["AUDIO_PATH"],
            audio_start_time=audio_start_time_sec,
            audio_end_time=audio_end_time_sec,
            video_fps=params["VIDEO_FPS"],
            waveform_analysis_mode=params["WAVEFORM_ANALYSIS_MODE"],
            waveform_bar_count=params["WAVEFORM_BAR_COUNT"],
            waveform_smoothing_factor=params["WAVEFORM_SMOOTHING_FACTOR"],
            waveform_min_db=params["WAVEFORM_MIN_DB"],
            waveform_max_db=params["WAVEFORM_MAX_DB"]
        )
        
        # Calculate video duration
        video_duration = params["AUDIO_END_TIME"] - params["AUDIO_START_TIME"]
        if video_duration <= 0: video_duration = 1
        
        # Create a frame maker function that uses the assets and parameters
        def frame_maker(t):
            return video_generation.make_frame_for_moviepy(
                t=t,
                assets=assets,
                video_fps=params["VIDEO_FPS"],
                video_width=params["VIDEO_WIDTH"],
                video_height=params["VIDEO_HEIGHT"],
                background_mode=params["BACKGROUND_MODE"],
                image_corner_radius=params["IMAGE_CORNER_RADIUS"],
                shadow_offset_x=params["SHADOW_OFFSET_X"],
                shadow_offset_y=params["SHADOW_OFFSET_Y"],
                shadow_blur_radius=params["SHADOW_BLUR_RADIUS"],
                waveform_enabled=params["WAVEFORM_ENABLED"],
                waveform_color_mode=params["WAVEFORM_COLOR_MODE"],
                waveform_color=params["WAVEFORM_COLOR"],
                waveform_bar_count=params["WAVEFORM_BAR_COUNT"],
                waveform_bar_spacing_ratio=params["WAVEFORM_BAR_SPACING_RATIO"]
            )
        
        # Create the video clip using the frame maker function
        video_clip = mpe.VideoClip(frame_maker, duration=video_duration)
        
        # Add audio if available
        if os.path.exists(params["AUDIO_PATH"]):
            audio_clip = mpe.AudioFileClip(params["AUDIO_PATH"])
            actual_start = min(max(0, params["AUDIO_START_TIME"]), audio_clip.duration)
            actual_end = min(max(actual_start, params["AUDIO_END_TIME"]), audio_clip.duration)
            
            if actual_start >= actual_end:
                video_clip = video_clip.set_audio(None)
            else:
                trimmed_audio = audio_clip.subclip(actual_start, actual_end)
                if trimmed_audio.duration < video_clip.duration:
                    video_clip = video_clip.set_duration(trimmed_audio.duration)
                elif trimmed_audio.duration > video_clip.duration:
                    trimmed_audio = trimmed_audio.set_duration(video_clip.duration)
                video_clip = video_clip.set_audio(trimmed_audio)
        
        # Write the result to a file
        video_clip.write_videofile(
            params["OUTPUT_VIDEO_FILENAME"],
            fps=params["VIDEO_FPS"],
            codec="libx264",
            audio_codec="aac",
            threads=4
        )
        
        success = True
        message = f"Video generated successfully: {params['OUTPUT_VIDEO_FILENAME']}"
    except Exception as e:
        success = False
        message = f"Error generating video: {str(e)}"
    
    class Result:
        def __init__(self, success, message):
            self.returncode = 0 if success else 1
            self.stdout = message if success else ""
            self.stderr = "" if success else message
    
    return Result(success, message)

# Input and Output settings
with tab_input:
    st.header("Input and Output Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_image = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], 
                                         help="The image to be displayed in the video")
        
        if uploaded_image:
            # Save the uploaded image to a temporary file
            temp_image = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_image.write(uploaded_image.getvalue())
            temp_image_path = temp_image.name
            temp_image.close()
            
            st.image(uploaded_image, caption="Uploaded Image", width=300)
            image_path = temp_image_path
        else:
            image_path = ""
    
    with col2:
        uploaded_audio = st.file_uploader("Upload Audio", type=["wav", "mp3"], 
                                         help="The audio file to be used in the video")
        
        if uploaded_audio:
            # Save the uploaded audio to a temporary file
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_audio.write(uploaded_audio.getvalue())
            temp_audio_path = temp_audio.name
            temp_audio.close()
            
            st.audio(uploaded_audio, format="audio/wav")
            audio_path = temp_audio_path
        else:
            audio_path = ""
    
    # Profile selection dropdown
    st.subheader("Video Profile")
    profile_options = []
    profile_keys = []
    
    if profiles:
        for key, profile in profiles.items():
            if 'display_name' in profile:
                profile_options.append(profile['display_name'])
                profile_keys.append(key)
    
    # Default to "Shorts with waveform" (default_profile)
    default_index = 0
    if 'default_profile' in profile_keys:
        default_index = profile_keys.index('default_profile')
    
    selected_profile_display = st.selectbox(
        "Choose a video profile",
        profile_options,
        index=default_index,
        help="Select a pre-configured profile to populate settings automatically"
    )
    
    # Get the selected profile key
    selected_profile_key = None
    if selected_profile_display in profile_options:
        selected_profile_key = profile_keys[profile_options.index(selected_profile_display)]
    
    # Auto-calculate video length checkbox
    default_use_audio_duration = get_profile_value(selected_profile_key, 'input_output.use_audio_duration', False)
    use_audio_duration = st.checkbox("Auto-calculate video length from audio duration", default_use_audio_duration,
                                    help="When enabled, automatically sets start time to 0 and end time to the full audio duration")
    
    # Time input in MM:SS format
    default_start_time = get_profile_value(selected_profile_key, 'input_output.audio_start_time', "00:33")
    default_end_time = get_profile_value(selected_profile_key, 'input_output.audio_end_time', "01:26")
    
    # Initialize session state for time values if not exists
    if 'audio_start_time_str' not in st.session_state:
        st.session_state.audio_start_time_str = default_start_time
    if 'audio_end_time_str' not in st.session_state:
        st.session_state.audio_end_time_str = default_end_time
    
    # Update session state when profile changes (only if profile selection actually changed)
    current_profile_key = f"profile_{selected_profile_key}"
    if current_profile_key not in st.session_state or st.session_state[current_profile_key] != selected_profile_key:
        st.session_state[current_profile_key] = selected_profile_key
        st.session_state.audio_start_time_str = default_start_time
        st.session_state.audio_end_time_str = default_end_time
    
    # Calculate auto duration if enabled and audio is uploaded
    if use_audio_duration and uploaded_audio and audio_path:
        try:
            import librosa
            audio_duration = librosa.get_duration(path=audio_path)
            minutes = int(audio_duration // 60)
            seconds = int(audio_duration % 60)
            calculated_start_time = "00:00"
            calculated_end_time = f"{minutes:02d}:{seconds:02d}"
            st.info(f"Auto-calculated duration: {calculated_end_time} (from audio file)")
            # Update session state with calculated values
            st.session_state.audio_start_time_str = calculated_start_time
            st.session_state.audio_end_time_str = calculated_end_time
        except Exception as e:
            st.warning(f"Could not calculate audio duration: {e}")
    
    # Always show editable time input fields using session state values
    audio_start_time_str = st.text_input("Audio Start Time (MM:SS)", st.session_state.audio_start_time_str, 
                                      help="Start time of the audio in MM:SS format")
    
    audio_end_time_str = st.text_input("Audio End Time (MM:SS)", st.session_state.audio_end_time_str, 
                                    help="End time of the audio in MM:SS format (also dictates video duration)")
    
    # Update session state with any manual changes
    st.session_state.audio_start_time_str = audio_start_time_str
    st.session_state.audio_end_time_str = audio_end_time_str
    
    # Convert MM:SS to seconds
    def time_str_to_seconds(time_str):
        try:
            # Handle different formats
            if ":" in time_str:
                parts = time_str.split(":")
                if len(parts) == 2:  # MM:SS
                    minutes, seconds = parts
                    return int(minutes) * 60 + int(seconds)
                elif len(parts) == 3:  # HH:MM:SS
                    hours, minutes, seconds = parts
                    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            # Handle direct seconds input
            return int(time_str)
        except ValueError:
            return 0  # Default to 0 if parsing fails
    
    # Convert input strings to seconds
    audio_start_time = time_str_to_seconds(audio_start_time_str)
    audio_end_time = time_str_to_seconds(audio_end_time_str)
    
    # Display the converted values
    st.caption(f"Start time in seconds: {audio_start_time}")
    st.caption(f"End time in seconds: {audio_end_time}")
    
    default_output_filename = get_profile_value(selected_profile_key, 'input_output.output_filename', "youtube_short.mp4")
    output_filename = st.text_input("Output Video Filename", default_output_filename, 
                                  help="Name of the output video file")

# Video settings
with tab_video:
    st.header("Video Settings")
    
    # Single column layout for better vertical alignment
    default_fps = get_profile_value(selected_profile_key, 'video.fps', 60)
    video_fps = st.number_input("Video FPS", 24, 60, default_fps, 
                        help="Frames per second for the output video")
    
    st.markdown("Video Dimensions (9:16 aspect ratio for YouTube Shorts)")
    default_width = get_profile_value(selected_profile_key, 'video.width', 1080)
    default_height = get_profile_value(selected_profile_key, 'video.height', 1920)
    video_width = st.number_input("Video Width", 360, 1920, default_width, 
                                help="Width of the output video")
    video_height = st.number_input("Video Height", 640, 3840, default_height, 
                                 help="Height of the output video")

# Background settings
with tab_background:
    st.header("Background Settings")
    
    default_bg_mode = get_profile_value(selected_profile_key, 'background.mode', "blur_image")
    bg_modes = ["blur_image", "solid"]
    bg_mode_index = bg_modes.index(default_bg_mode) if default_bg_mode in bg_modes else 0
    background_mode = st.selectbox("Background Mode", 
                                 bg_modes, 
                                 index=bg_mode_index,
                                 help="Options: 'solid', 'blur_image'")
    
    # Initialize all background variables to avoid NameError
    default_blur_radius = get_profile_value(selected_profile_key, 'background.blur_radius', 50)
    default_image_fit = get_profile_value(selected_profile_key, 'background.image_fit', "stretch")
    default_bg_color = get_profile_value(selected_profile_key, 'background.color', "#000000")
    
    if background_mode == "blur_image":
        background_blur_radius = st.number_input("Background Blur Radius", 10, 100, default_blur_radius, 
                                          help="Blur radius if BACKGROUND_MODE is 'blur_image'")
        
        fit_options = ["stretch", "crop", "fill"]
        fit_index = fit_options.index(default_image_fit) if default_image_fit in fit_options else 0
        background_image_fit = st.selectbox("Background Image Fit", 
                                          fit_options,
                                          index=fit_index, 
                                          help="Options: 'stretch', 'crop', 'fill'")
        # Set defaults for variables not shown in this mode
        background_color = default_bg_color
    else:
        background_color = st.color_picker("Background Color", default_bg_color, 
                                         help="Background color if BACKGROUND_MODE is 'solid'")
        # Set defaults for variables not shown in this mode
        background_blur_radius = default_blur_radius
        background_image_fit = default_image_fit

# Image settings
with tab_image:
    st.header("Image Settings")
    
    default_img_width_pct = get_profile_value(selected_profile_key, 'image.width_percentage', 65)
    image_width_percentage = st.number_input("Image Width Percentage", 10, 100, default_img_width_pct, 
                                      help="Width of the image as a percentage of the video width")
    
    default_corner_radius = get_profile_value(selected_profile_key, 'image.corner_radius', 30)
    image_corner_radius = st.number_input("Image Corner Radius", 0, 100, default_corner_radius, 
                                   help="Set to 0 for no rounding")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_x_pos = get_profile_value(selected_profile_key, 'image.x_position', -1)
        image_x_position = st.number_input("Image X Position", -1, 1920, default_x_pos, 
                                         help="Top-left corner X for the image (-1 for auto-center)")
    
    with col2:
        default_y_pos = get_profile_value(selected_profile_key, 'image.y_position', -1)
        image_y_position = st.number_input("Image Y Position", -1, 3840, default_y_pos, 
                                         help="Top-left corner Y for the image (-1 for auto-center)")
    
    st.subheader("Shadow Properties")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        default_shadow_x = get_profile_value(selected_profile_key, 'shadow.offset_x', 10)
        shadow_offset_x = st.number_input("Shadow Offset X", 0, 50, default_shadow_x, 
                                        help="Horizontal offset for shadow")
    
    with col2:
        default_shadow_y = get_profile_value(selected_profile_key, 'shadow.offset_y', 10)
        shadow_offset_y = st.number_input("Shadow Offset Y", 0, 50, default_shadow_y, 
                                        help="Vertical offset for shadow")
    
    with col3:
        default_shadow_blur = get_profile_value(selected_profile_key, 'shadow.blur_radius', 15)
        shadow_blur_radius = st.number_input("Shadow Blur Radius", 0, 50, default_shadow_blur, 
                                           help="Blur radius for shadow")
    
    default_shadow_darkness = get_profile_value(selected_profile_key, 'shadow.darkness_factor', 0.5)
    shadow_darkness_factor = st.number_input("Shadow Darkness Factor", 0.0, 1.0, default_shadow_darkness, step=0.01, 
                                      help="For solid bg image shadow")

# Waveform settings
with tab_waveform:
    st.header("Waveform Animation Settings")
    
    default_waveform_enabled = get_profile_value(selected_profile_key, 'waveform.enabled', True)
    waveform_enabled = st.checkbox("Enable Waveform", default_waveform_enabled, 
                                  help="Whether to show the audio waveform visualization")
    
    # Initialize default values for waveform-related variables from profile
    waveform_analysis_mode = get_profile_value(selected_profile_key, 'waveform.analysis_mode', "melspectrogram")
    waveform_color_mode = get_profile_value(selected_profile_key, 'waveform.color_mode', "contrast")
    waveform_color = get_profile_value(selected_profile_key, 'waveform.color', "#FFFFFF")
    waveform_height_percentage = get_profile_value(selected_profile_key, 'waveform.height_percentage', 15)
    waveform_bar_count = get_profile_value(selected_profile_key, 'waveform.bar_count', 50)
    waveform_bar_spacing_ratio = get_profile_value(selected_profile_key, 'waveform.bar_spacing_ratio', 0.2)
    waveform_smoothing_factor = get_profile_value(selected_profile_key, 'waveform.smoothing_factor', 0.35)
    spacing_image_waveform = get_profile_value(selected_profile_key, 'waveform.spacing_from_image', 215)
    waveform_min_db = get_profile_value(selected_profile_key, 'waveform.min_db', -80.0)
    waveform_max_db = get_profile_value(selected_profile_key, 'waveform.max_db', 0.0)
    
    if waveform_enabled:
        analysis_modes = ["melspectrogram", "rms"]
        analysis_index = analysis_modes.index(waveform_analysis_mode) if waveform_analysis_mode in analysis_modes else 0
        waveform_analysis_mode = st.selectbox("Waveform Analysis Mode", 
                                             analysis_modes,
                                             index=analysis_index, 
                                             help="Options: 'rms', 'melspectrogram'")
        
        color_modes = ["contrast", "custom", "white", "black"]
        color_index = color_modes.index(waveform_color_mode) if waveform_color_mode in color_modes else 0
        waveform_color_mode = st.selectbox("Waveform Color Mode", 
                                          color_modes,
                                          index=color_index, 
                                          help="Options: 'custom', 'contrast', 'white', 'black'")
        
        if waveform_color_mode == "custom":
            waveform_color = st.color_picker("Waveform Color", waveform_color, 
                                            help="(R, G, B) - Used if WAVEFORM_COLOR_MODE is 'custom'")
        
        waveform_height_percentage = st.number_input("Waveform Height Percentage", 5, 50, waveform_height_percentage, 
                                              help="Height of the waveform as a percentage of the video height")
        
        waveform_bar_count = st.number_input("Waveform Bar Count", 10, 100, waveform_bar_count, 
                                      help="If melspectrogram, this is n_mels")
        
        waveform_bar_spacing_ratio = st.number_input("Waveform Bar Spacing Ratio", 0.0, 1.0, waveform_bar_spacing_ratio, step=0.01, 
                                              help="Spacing between waveform bars")
        
        waveform_smoothing_factor = st.number_input("Waveform Smoothing Factor", 0.0, 1.0, waveform_smoothing_factor, step=0.01, 
                                             help="Applied to final band values if melspectrogram, or RMS if rms mode")
        
        spacing_image_waveform = st.number_input("Spacing Between Image and Waveform", 50, 500, spacing_image_waveform, 
                                          help="Vertical spacing between image and waveform")
        
        col1, col2 = st.columns(2)
        
        with col1:
            waveform_min_db = st.number_input("Waveform Min dB", -100.0, 0.0, waveform_min_db, step=0.1, 
                                       help="For melspectrogram normalization")
        
        with col2:
            waveform_max_db = st.number_input("Waveform Max dB", -50.0, 0.0, waveform_max_db, step=0.1, 
                                       help="For melspectrogram normalization")

# Generate video
with tab_generate:
    st.header("Generate Video")
    
    if st.button("Generate YouTube Short", type="primary"):
        if not uploaded_image:
            st.error("Please upload an image")
        elif not uploaded_audio:
            st.error("Please upload an audio file")
        else:
            # Convert color picker hex to RGB tuple if needed
            if background_mode == "solid":
                bg_color = tuple(int(background_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            else:
                bg_color = (0, 0, 0)  # Default
                
            # Process waveform color
            waveform_color_tuple = (255, 255, 255)  # Default
            if waveform_enabled and waveform_color_mode == "custom":
                waveform_color_tuple = tuple(int(waveform_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                
            # Prepare parameters for the main script
            params = {
                "IMAGE_PATH": image_path,
                "AUDIO_PATH": audio_path,
                "AUDIO_START_TIME": audio_start_time,
                "AUDIO_END_TIME": audio_end_time,
                "OUTPUT_VIDEO_FILENAME": output_filename,
                "VIDEO_FPS": video_fps,
                "VIDEO_WIDTH": video_width,
                "VIDEO_HEIGHT": video_height,
                "BACKGROUND_MODE": background_mode,
                "BACKGROUND_BLUR_RADIUS": background_blur_radius if background_mode == "blur_image" else 0,
                "BACKGROUND_IMAGE_FIT": background_image_fit if background_mode == "blur_image" else "stretch",
                "BACKGROUND_COLOR": bg_color,
                "IMAGE_WIDTH_PERCENTAGE": image_width_percentage,
                "IMAGE_CORNER_RADIUS": image_corner_radius,
                "IMAGE_X_POSITION": image_x_position,
                "IMAGE_Y_POSITION": image_y_position,
                "SHADOW_OFFSET_X": shadow_offset_x,
                "SHADOW_OFFSET_Y": shadow_offset_y,
                "SHADOW_BLUR_RADIUS": shadow_blur_radius,
                "SHADOW_DARKNESS_FACTOR": shadow_darkness_factor,
                "WAVEFORM_ENABLED": waveform_enabled,
                "WAVEFORM_ANALYSIS_MODE": waveform_analysis_mode,
                "WAVEFORM_COLOR_MODE": waveform_color_mode,
                "WAVEFORM_COLOR": waveform_color_tuple,
                "WAVEFORM_HEIGHT_PERCENTAGE": waveform_height_percentage,
                "WAVEFORM_BAR_COUNT": waveform_bar_count,
                "WAVEFORM_BAR_SPACING_RATIO": waveform_bar_spacing_ratio,
                "WAVEFORM_SMOOTHING_FACTOR": waveform_smoothing_factor,
                "SPACING_IMAGE_WAVEFORM": spacing_image_waveform,
                "WAVEFORM_MIN_DB": waveform_min_db,
                "WAVEFORM_MAX_DB": waveform_max_db
            }
            
            with st.spinner("Generating YouTube Short..."):
                # Generate the video using main.py functions directly
                result = generate_video(params)
                
                if result.returncode == 0:
                    st.success(result.stdout)
                    
                    # Get the absolute path of the output video
                    output_video_path = os.path.abspath(output_filename)
                    
                    # Display the video
                    st.video(output_video_path)
                    
                    # Store generated video path for YouTube upload
                    st.session_state.generated_video_path = output_video_path
                    
                    # Provide a download button
                    with open(output_video_path, "rb") as file:
                        st.download_button(
                            label="Download Video",
                            data=file,
                            file_name=os.path.basename(output_filename),
                            mime="video/mp4"
                        )
                else:
                    st.error(result.stderr)

# YouTube Upload and Scheduling
with tab_youtube:
    st.header("YouTube Upload & Scheduling")
    
    # Check for OAuth code in URL parameters first
    query_params = st.query_params
    oauth_code = query_params.get('code')
    
    # If there's a code, try to authenticate (recreate flow if needed)
    if oauth_code:
        try:
            # Recreate the flow since session state might be cleared
            from google_auth_oauthlib.flow import Flow
            import json
            
            # Determine redirect URI based on environment
            if os.path.exists('client_secrets.json'):
                redirect_uri = 'http://localhost:8501'
                flow = Flow.from_client_secrets_file(
                    'client_secrets.json',
                    scopes=['https://www.googleapis.com/auth/youtube'],
                    redirect_uri=redirect_uri
                )
            else:
                redirect_uri = os.getenv('STREAMLIT_APP_URL', 'https://music-shorts.streamlit.app/')
                if not redirect_uri.endswith('/'):
                    redirect_uri += '/'
                
                client_config = {
                    "web": {
                        "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                        "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri]
                    }
                }
                
                flow = Flow.from_client_config(
                    client_config,
                    scopes=['https://www.googleapis.com/auth/youtube'],
                    redirect_uri=redirect_uri
                )
            
            # Get the token using the code
            flow.fetch_token(code=oauth_code)
            st.session_state.youtube_credentials = flow.credentials
            
            # Clear URL and refresh
            st.query_params.clear()
            st.success("🎉 Successfully authenticated with YouTube!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
            st.query_params.clear()
    
    # Check if authenticated
    youtube_authenticated = 'youtube_credentials' in st.session_state
    
    if not youtube_authenticated:
        st.subheader("🔐 Connect to YouTube")
        
        if st.button("🔗 Get Authorization Code", type="primary"):
            from google_auth_oauthlib.flow import Flow
            import json
            
            # Try to load client secrets from file first, then env variables
            try:
                # Determine redirect URI based on environment
                if os.path.exists('client_secrets.json'):
                    # Local development
                    redirect_uri = 'http://localhost:8501'
                else:
                    # Cloud deployment - use the actual app URL (with trailing slash to match browser behavior)
                    redirect_uri = os.getenv('STREAMLIT_APP_URL', 'https://music-shorts.streamlit.app/')
                    # Ensure trailing slash for consistency
                    if not redirect_uri.endswith('/'):
                        redirect_uri += '/'
                
                if os.path.exists('client_secrets.json'):
                    # Load from file (local development)
                    flow = Flow.from_client_secrets_file(
                        'client_secrets.json',
                        scopes=['https://www.googleapis.com/auth/youtube'],
                        redirect_uri=redirect_uri
                    )
                else:
                    # Load from environment variables (cloud deployment)
                    client_config = {
                        "web": {
                            "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                            "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": [redirect_uri]
                        }
                    }
                    
                    # Validate required environment variables
                    if not client_config["web"]["client_id"] or not client_config["web"]["client_secret"]:
                        st.error("❌ Missing Google OAuth credentials. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")
                        st.stop()
                    
                    flow = Flow.from_client_config(
                        client_config,
                        scopes=['https://www.googleapis.com/auth/youtube'],
                        redirect_uri=redirect_uri
                    )
                    
            except Exception as e:
                st.error(f"❌ Error setting up OAuth flow: {e}")
                st.info("💡 Make sure you have either:")
                st.markdown("- `client_secrets.json` file in your project directory, OR")
                st.markdown("- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` environment variables set")
                st.stop()
            
            auth_url, _ = flow.authorization_url()
            st.session_state.oauth_flow = flow
            st.session_state.auth_url = auth_url
        
        if 'auth_url' in st.session_state:
            st.markdown(f"""
            ### 🚀 Click to Authorize
            
            [**👆 CLICK HERE TO AUTHORIZE**]({st.session_state.auth_url})
            
            You'll be redirected back to this app automatically after authorization.
            """)
    
    else:
        # User is authenticated
        st.success("✅ Connected to YouTube")
        
        try:
            credentials = st.session_state.youtube_credentials
            youtube_service = YouTubeService(credentials)
            
            # Get channel info
            try:
                channel_info = youtube_service.get_channel_info()
                if channel_info:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Channel:** {channel_info['title']}")
                        st.write(f"**Subscribers:** {channel_info['subscriber_count']}")
                    with col2:
                        if st.button("Disconnect"):
                            del st.session_state.youtube_credentials
                            st.rerun()
            except Exception as e:
                st.warning(f"Could not fetch channel info: {e}")
            
            # Upload Form Section
            if 'generated_video_path' in st.session_state and os.path.exists(st.session_state.generated_video_path):
                st.subheader("📤 Upload Video")
                
                # Video detection and analysis
                try:
                    video_analysis = youtube_service.detect_shorts_format(st.session_state.generated_video_path)
                    
                    if video_analysis:
                        if video_analysis['is_shorts']:
                            st.success("✅ Video detected as YouTube Short")
                            st.write(f"Duration: {video_analysis['duration']:.1f}s, "
                                   f"Resolution: {video_analysis['width']}×{video_analysis['height']}")
                        else:
                            st.info("ℹ️ Video does not meet YouTube Shorts criteria")
                except Exception as e:
                    st.warning(f"Could not analyze video: {e}")
                    video_analysis = None
                
                # Upload form
                st.subheader("Video Details")
                
                # Basic Information
                title = st.text_input("Title *", max_chars=100, help="Maximum 100 characters")
                description = st.text_area("Description", max_chars=5000, height=100, help="Maximum 5000 characters")
                tags = st.text_input("Tags (comma-separated)", help="Separate tags with commas, max 500 characters total")
                
                # Privacy & Scheduling (moved outside form for interactivity)
                schedule_option = st.radio("Publishing", ["Upload now", "Schedule for later"])
                
                if schedule_option == "Schedule for later":
                    st.info("📋 **Note:** Scheduled videos must be set to 'private' privacy status")
                    privacy = "private"  # Force private for scheduling
                    st.write(f"**Privacy Status:** {privacy} (required for scheduling)")
                else:
                    privacy = st.selectbox("Privacy", ["private", "unlisted", "public"], index=2)
                
                publish_at = None
                if schedule_option == "Schedule for later":
                        st.info("📅 Schedule your video for future publication")
                        
                        # Date and time selection with better validation
                        from datetime import datetime, timezone, timedelta
                        import pytz
                        
                        # Common timezones list
                        common_timezones = [
                            'UTC',
                            'America/New_York',      # Eastern
                            'America/Chicago',       # Central  
                            'America/Denver',        # Mountain
                            'America/Los_Angeles',   # Pacific
                            'Europe/London',
                            'Europe/Paris',
                            'Europe/Berlin',
                            'Asia/Tokyo',
                            'Asia/Shanghai',
                            'Australia/Sydney',
                            'US/Eastern',
                            'US/Central',
                            'US/Mountain', 
                            'US/Pacific'
                        ]
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Set minimum date to today  
                            min_date = datetime.now().date()
                            max_date = min_date + timedelta(days=365)
                            
                            schedule_date = st.date_input(
                                "📅 Publish Date",
                                min_value=min_date,
                                max_value=max_date,
                                value=min_date,
                                help="Select the date when you want the video to be published"
                            )
                        
                        with col2:
                            # Default to current time + 60 minutes in HH:MM format
                            default_datetime = datetime.now() + timedelta(hours=1)
                            default_time_str = default_datetime.strftime("%H:%M")
                            
                            schedule_time_str = st.text_input(
                                "🕒 Publish Time (HH:MM)",
                                value=default_time_str,
                                help="Enter time in 24-hour format (e.g., 14:30)"
                            )
                            
                            # Convert HH:MM to time object (reuse the existing function)
                            def time_str_to_time(time_str):
                                try:
                                    if ":" in time_str:
                                        parts = time_str.split(":")
                                        if len(parts) == 2:
                                            hours, minutes = int(parts[0]), int(parts[1])
                                            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                                                from datetime import time
                                                return time(hours, minutes)
                                    return None
                                except (ValueError, IndexError):
                                    return None
                            
                            schedule_time = time_str_to_time(schedule_time_str)
                            if not schedule_time:
                                st.error("⚠️ Invalid time format. Use HH:MM (e.g., 14:30)")
                                schedule_time = default_datetime.time()
                        
                        with col3:
                            selected_tz = st.selectbox(
                                "🌍 Timezone",
                                common_timezones,
                                index=0,  # UTC default
                                help="Select your timezone for accurate scheduling"
                            )
                        
                        # Combine date, time, and timezone
                        try:
                            from datetime import datetime as dt
                            tz = pytz.timezone(selected_tz)
                            local_datetime = dt.combine(schedule_date, schedule_time)
                            localized_datetime = tz.localize(local_datetime)
                            utc_datetime = localized_datetime.astimezone(pytz.UTC)
                            
                            # YouTube API expects RFC 3339 format (ISO 8601 with Z suffix for UTC)
                            publish_at = utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                            
                            # Validation: ensure scheduled time meets YouTube requirements
                            now_utc = datetime.now(pytz.UTC)
                            min_future = now_utc + timedelta(minutes=60)  # Conservative 60-minute minimum
                            
                            if utc_datetime <= now_utc:
                                st.error("⚠️ Scheduled time must be in the future")
                                publish_at = None
                            elif utc_datetime < min_future:
                                st.error("⚠️ YouTube requires scheduling at least 60 minutes in the future (recommended)")
                                publish_at = None
                            else:
                                # Show confirmation of scheduled time
                                time_until = utc_datetime - now_utc
                                if time_until.days > 0:
                                    time_str = f"{time_until.days} days, {time_until.seconds // 3600} hours"
                                else:
                                    hours = time_until.seconds // 3600
                                    minutes = (time_until.seconds % 3600) // 60
                                    time_str = f"{hours}h {minutes}m"
                                
                                st.success(f"✅ Video will be published in {time_str}")
                                st.caption(f"UTC time: {utc_datetime.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                                
                        except Exception as e:
                            st.error(f"Error processing scheduled time: {e}")
                            publish_at = None
                
                # YouTube Shorts handling (moved outside form)
                auto_detect_shorts = st.checkbox("Auto-detect as YouTube Short", value=True)
                is_shorts = False
                if auto_detect_shorts and video_analysis and video_analysis['is_shorts']:
                    is_shorts = True
                    st.info("Will be tagged as YouTube Short (#Shorts)")
                
                # Upload button (now in a separate form for submission)
                with st.form("upload_submit_form"):
                    submitted = st.form_submit_button("🚀 Upload to YouTube", type="primary")
                    
                    if submitted:
                        # Validation
                        validation_errors = []
                        
                        if not title.strip():
                            validation_errors.append("Please provide a video title")
                            
                        if schedule_option == "Schedule for later" and not publish_at:
                            validation_errors.append("Please select a valid future date and time for scheduling")
                        
                        if validation_errors:
                            for error in validation_errors:
                                st.error(error)
                        else:
                            # Prepare metadata
                            metadata = VideoMetadata()
                            metadata.title = title.strip()
                            metadata.description = description.strip()
                            metadata.tags = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
                            metadata.privacy_status = privacy
                            metadata.publish_at = publish_at
                            metadata.shorts_format = is_shorts
                            
                            # Upload video
                            with st.spinner("Uploading video to YouTube..."):
                                try:
                                    result = youtube_service.upload_video(st.session_state.generated_video_path, metadata)
                                    
                                    if result:
                                        # Show success message based on scheduling
                                        if result.get('publish_at'):
                                            st.success("🎉 Video uploaded and scheduled successfully!")
                                            st.balloons()
                                        else:
                                            st.success("🎉 Video uploaded successfully!")
                                            st.balloons()
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.write(f"**Title:** {result['title']}")
                                            st.write(f"**Privacy:** {result['status'].title()}")
                                            st.write(f"**Upload Status:** {result.get('upload_status', 'N/A').title()}")
                                            
                                            if result.get('publish_at'):
                                                from datetime import datetime
                                                try:
                                                    # Parse and format the scheduled time
                                                    scheduled_dt = datetime.fromisoformat(result['publish_at'].replace('Z', '+00:00'))
                                                    formatted_time = scheduled_dt.strftime('%Y-%m-%d at %H:%M UTC')
                                                    st.write(f"**📅 Scheduled for:** {formatted_time}")
                                                    
                                                    # Show time until publication
                                                    from datetime import timezone
                                                    now_utc = datetime.now(timezone.utc)
                                                    time_diff = scheduled_dt - now_utc
                                                    
                                                    if time_diff.days > 0:
                                                        st.info(f"⏰ Will be published in {time_diff.days} days and {time_diff.seconds // 3600} hours")
                                                    else:
                                                        hours = time_diff.seconds // 3600
                                                        minutes = (time_diff.seconds % 3600) // 60
                                                        st.info(f"⏰ Will be published in {hours}h {minutes}m")
                                                        
                                                except Exception:
                                                    st.write(f"**📅 Scheduled for:** {result['publish_at']}")
                                            else:
                                                st.write("**Status:** Published immediately")
                                        
                                        with col2:
                                            st.markdown(f"[🔗 View on YouTube]({result['video_url']})")
                                            st.code(result['video_url'], language=None)
                                            
                                            # Additional info for scheduled videos
                                            if result.get('publish_at'):
                                                st.info("💡 Video is uploaded but won't be visible until the scheduled time")
                                    
                                    else:
                                        st.error("Upload failed. Please check the error messages above.")
                                        
                                except Exception as e:
                                    st.error(f"Upload error: {e}")
            
            else:
                st.info("📹 Generate a video first to enable YouTube upload")
                
        except Exception as e:
            st.error(f"YouTube service error: {e}")
            if st.button("🔄 Clear Credentials"):
                del st.session_state.youtube_credentials
                st.rerun()

# Removed sidebar
