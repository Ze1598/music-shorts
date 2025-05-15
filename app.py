import streamlit as st
import os
import tempfile
from pathlib import Path
import shutil
import sys
import importlib

# Import main module and its functions
import video_generation
import moviepy.editor as mpe

st.set_page_config(
    page_title="YouTube Shorts Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("YouTube Shorts Generator")
st.markdown("Create beautiful music visualization videos for YouTube Shorts")

# Create tabs for different sections
tab_input, tab_video, tab_background, tab_image, tab_waveform, tab_generate = st.tabs([
    "Input/Output", "Video Settings", "Background", "Image", "Waveform", "Generate"
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
    
    # Time input in MM:SS format
    audio_start_time_str = st.text_input("Audio Start Time (MM:SS)", "00:33", 
                                      help="Start time of the audio in MM:SS format")
    
    audio_end_time_str = st.text_input("Audio End Time (MM:SS)", "01:26", 
                                    help="End time of the audio in MM:SS format (also dictates video duration)")
    
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
    
    output_filename = st.text_input("Output Video Filename", "youtube_short.mp4", 
                                  help="Name of the output video file")

# Video settings
with tab_video:
    st.header("Video Settings")
    
    # Single column layout for better vertical alignment
    video_fps = st.number_input("Video FPS", 24, 60, 60, 
                        help="Frames per second for the output video")
    
    st.markdown("Video Dimensions (9:16 aspect ratio for YouTube Shorts)")
    video_width = st.number_input("Video Width", 360, 1920, 1080, 
                                help="Width of the output video")
    video_height = st.number_input("Video Height", 640, 3840, 1920, 
                                 help="Height of the output video")

# Background settings
with tab_background:
    st.header("Background Settings")
    
    background_mode = st.selectbox("Background Mode", 
                                 ["blur_image", "solid"], 
                                 help="Options: 'solid', 'blur_image'")
    
    if background_mode == "blur_image":
        background_blur_radius = st.number_input("Background Blur Radius", 10, 100, 50, 
                                          help="Blur radius if BACKGROUND_MODE is 'blur_image'")
        
        background_image_fit = st.selectbox("Background Image Fit", 
                                          ["stretch", "crop", "fill"], 
                                          help="Options: 'stretch', 'crop', 'fill'")
    else:
        background_color = st.color_picker("Background Color", "#000000", 
                                         help="Background color if BACKGROUND_MODE is 'solid'")

# Image settings
with tab_image:
    st.header("Image Settings")
    
    image_width_percentage = st.number_input("Image Width Percentage", 10, 100, 65, 
                                      help="Width of the image as a percentage of the video width")
    
    image_corner_radius = st.number_input("Image Corner Radius", 0, 100, 30, 
                                   help="Set to 0 for no rounding")
    
    col1, col2 = st.columns(2)
    
    with col1:
        image_x_position = st.number_input("Image X Position", -1, 1920, -1, 
                                         help="Top-left corner X for the image (-1 for auto-center)")
    
    with col2:
        image_y_position = st.number_input("Image Y Position", -1, 3840, -1, 
                                         help="Top-left corner Y for the image (-1 for auto-center)")
    
    st.subheader("Shadow Properties")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        shadow_offset_x = st.number_input("Shadow Offset X", 0, 50, 10, 
                                        help="Horizontal offset for shadow")
    
    with col2:
        shadow_offset_y = st.number_input("Shadow Offset Y", 0, 50, 10, 
                                        help="Vertical offset for shadow")
    
    with col3:
        shadow_blur_radius = st.number_input("Shadow Blur Radius", 0, 50, 15, 
                                           help="Blur radius for shadow")
    
    shadow_darkness_factor = st.number_input("Shadow Darkness Factor", 0.0, 1.0, 0.5, step=0.01, 
                                      help="For solid bg image shadow")

# Waveform settings
with tab_waveform:
    st.header("Waveform Animation Settings")
    
    waveform_enabled = st.checkbox("Enable Waveform", True, 
                                  help="Whether to show the audio waveform visualization")
    
    # Initialize default values for waveform-related variables
    waveform_analysis_mode = "melspectrogram"
    waveform_color_mode = "contrast"
    waveform_color = "#FFFFFF"
    waveform_height_percentage = 15
    waveform_bar_count = 50
    waveform_bar_spacing_ratio = 0.2
    waveform_smoothing_factor = 0.35
    spacing_image_waveform = 215
    waveform_min_db = -80.0
    waveform_max_db = 0.0
    
    if waveform_enabled:
        waveform_analysis_mode = st.selectbox("Waveform Analysis Mode", 
                                             ["melspectrogram", "rms"], 
                                             help="Options: 'rms', 'melspectrogram'")
        
        waveform_color_mode = st.selectbox("Waveform Color Mode", 
                                          ["contrast", "custom", "white", "black"], 
                                          help="Options: 'custom', 'contrast', 'white', 'black'")
        
        if waveform_color_mode == "custom":
            waveform_color = st.color_picker("Waveform Color", "#FFFFFF", 
                                            help="(R, G, B) - Used if WAVEFORM_COLOR_MODE is 'custom'")
        
        waveform_height_percentage = st.number_input("Waveform Height Percentage", 5, 50, 15, 
                                              help="Height of the waveform as a percentage of the video height")
        
        waveform_bar_count = st.number_input("Waveform Bar Count", 10, 100, 50, 
                                      help="If melspectrogram, this is n_mels")
        
        waveform_bar_spacing_ratio = st.number_input("Waveform Bar Spacing Ratio", 0.0, 1.0, 0.2, step=0.01, 
                                              help="Spacing between waveform bars")
        
        waveform_smoothing_factor = st.number_input("Waveform Smoothing Factor", 0.0, 1.0, 0.35, step=0.01, 
                                             help="Applied to final band values if melspectrogram, or RMS if rms mode")
        
        spacing_image_waveform = st.number_input("Spacing Between Image and Waveform", 50, 500, 215, 
                                          help="Vertical spacing between image and waveform")
        
        col1, col2 = st.columns(2)
        
        with col1:
            waveform_min_db = st.number_input("Waveform Min dB", -100.0, 0.0, -80.0, step=0.1, 
                                       help="For melspectrogram normalization")
        
        with col2:
            waveform_max_db = st.number_input("Waveform Max dB", -50.0, 0.0, 0.0, step=0.1, 
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

# Removed sidebar
