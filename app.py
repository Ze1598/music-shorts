import streamlit as st
import os
import tempfile
from pathlib import Path
import shutil
import sys
import importlib.util
import importlib

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
def run_main_script(params):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script_path = os.path.join(script_dir, "main.py")
    
    # Store original values to restore later
    import main
    original_values = {}
    for key in params.keys():
        if hasattr(main, key):
            original_values[key] = getattr(main, key)
    
    # Set the new parameter values in the main module
    for key, value in params.items():
        setattr(main, key, value)
    
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(os.path.join(script_dir, params["OUTPUT_VIDEO_FILENAME"]))
        os.makedirs(output_dir, exist_ok=True)
        
        # Call the main functions directly
        main.precompute_assets()
        video_duration = params["AUDIO_END_TIME"] - params["AUDIO_START_TIME"]
        
        # Create the clip using the make_frame_for_moviepy function
        import moviepy.editor as mpe
        clip = mpe.VideoClip(main.make_frame_for_moviepy, duration=video_duration)
        
        # Set audio
        if os.path.exists(params["AUDIO_PATH"]):
            audio = mpe.AudioFileClip(params["AUDIO_PATH"]).subclip(params["AUDIO_START_TIME"], params["AUDIO_END_TIME"])
            clip = clip.set_audio(audio)
        
        # Write the result to a file
        clip.write_videofile(
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
    finally:
        # Restore original values
        for key, value in original_values.items():
            setattr(main, key, value)
    
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
    
    audio_start_time = st.slider("Audio Start Time (seconds)", 0, 300, 33, 
                               help="Start time of the audio in seconds")
    
    audio_end_time = st.slider("Audio End Time (seconds)", 1, 300, 86, 
                             help="End time of the audio in seconds (also dictates video duration)")
    
    output_filename = st.text_input("Output Video Filename", "youtube_short.mp4", 
                                  help="Name of the output video file")

# Video settings
with tab_video:
    st.header("Video Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        video_fps = st.slider("Video FPS", 24, 60, 60, 
                            help="Frames per second for the output video")
    
    with col2:
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
        background_blur_radius = st.slider("Background Blur Radius", 10, 100, 50, 
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
    
    image_width_percentage = st.slider("Image Width Percentage", 10, 100, 65, 
                                     help="Width of the image as a percentage of the video width")
    
    image_corner_radius = st.slider("Image Corner Radius", 0, 100, 30, 
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
    
    shadow_darkness_factor = st.slider("Shadow Darkness Factor", 0.0, 1.0, 0.5, 
                                     help="For solid bg image shadow")

# Waveform settings
with tab_waveform:
    st.header("Waveform Animation Settings")
    
    waveform_enabled = st.checkbox("Enable Waveform", True, 
                                 help="Whether to show the audio waveform visualization")
    
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
        
        waveform_height_percentage = st.slider("Waveform Height Percentage", 5, 50, 15, 
                                             help="Height of the waveform as a percentage of the video height")
        
        waveform_bar_count = st.slider("Waveform Bar Count", 10, 100, 50, 
                                     help="If melspectrogram, this is n_mels")
        
        waveform_bar_spacing_ratio = st.slider("Waveform Bar Spacing Ratio", 0.0, 1.0, 0.2, 
                                             help="Spacing between waveform bars")
        
        waveform_smoothing_factor = st.slider("Waveform Smoothing Factor", 0.0, 1.0, 0.35, 
                                            help="Applied to final band values if melspectrogram, or RMS if rms mode")
        
        spacing_image_waveform = st.slider("Spacing Between Image and Waveform", 50, 500, 215, 
                                         help="Vertical spacing between image and waveform")
        
        col1, col2 = st.columns(2)
        
        with col1:
            waveform_min_db = st.slider("Waveform Min dB", -100.0, 0.0, -80.0, 
                                      help="For melspectrogram normalization")
        
        with col2:
            waveform_max_db = st.slider("Waveform Max dB", -50.0, 0.0, 0.0, 
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
            st.info("Generating video... This may take a while.")
            
            # Convert color picker hex to RGB tuple if needed
            if background_mode == "solid":
                bg_color = tuple(int(background_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            if waveform_color_mode == "custom":
                wave_color = tuple(int(waveform_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            else:
                wave_color = (255, 255, 255)  # Default
            
            # Prepare parameters
            params = {
                "IMAGE_PATH": image_path,
                "AUDIO_PATH": audio_path,
                "AUDIO_START_TIME": audio_start_time,
                "AUDIO_END_TIME": audio_end_time,
                "VIDEO_FPS": video_fps,
                "OUTPUT_VIDEO_FILENAME": output_filename,
                "VIDEO_WIDTH": video_width,
                "VIDEO_HEIGHT": video_height,
                "BACKGROUND_MODE": background_mode,
                "BACKGROUND_BLUR_RADIUS": background_blur_radius if background_mode == "blur_image" else 50,
                "BACKGROUND_IMAGE_FIT": background_image_fit if background_mode == "blur_image" else "stretch",
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
                "WAVEFORM_COLOR": wave_color,
                "WAVEFORM_HEIGHT_PERCENTAGE": waveform_height_percentage,
                "WAVEFORM_BAR_COUNT": waveform_bar_count,
                "WAVEFORM_BAR_SPACING_RATIO": waveform_bar_spacing_ratio,
                "WAVEFORM_SMOOTHING_FACTOR": waveform_smoothing_factor,
                "SPACING_IMAGE_WAVEFORM": spacing_image_waveform,
                "WAVEFORM_MIN_DB": waveform_min_db,
                "WAVEFORM_MAX_DB": waveform_max_db
            }
            
            # Add BG_COLOR_SOLID_GLOBAL if solid background mode
            if background_mode == "solid":
                params["BG_COLOR_SOLID_GLOBAL"] = bg_color
            
            # Run script with parameters
            try:
                with st.spinner("Generating video..."):
                    result = run_main_script(params)
                
                if result.returncode == 0:
                    # Get the path to the output video
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    output_path = os.path.join(script_dir, output_filename)
                    
                    if os.path.exists(output_path):
                        # Read the video file
                        with open(output_path, "rb") as file:
                            video_bytes = file.read()
                        
                        # Display success message and video
                        st.success(f"Video generated successfully: {output_filename}")
                        st.video(video_bytes)
                        
                        # Provide download button
                        st.download_button(
                            label="Download Video",
                            data=video_bytes,
                            file_name=output_filename,
                            mime="video/mp4"
                        )
                    else:
                        st.error(f"Video file not found at {output_path}")
                        st.code(result.stdout)
                        st.code(result.stderr)
                else:
                    st.error("Error generating video")
                    st.code(result.stdout)
                    st.code(result.stderr)
                
                # No temporary files to clean up with direct import approach
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

st.sidebar.title("About")
st.sidebar.info(
    """
    This app allows you to create YouTube Shorts videos with audio visualization.
    
    Upload an image and audio file, configure the settings, and generate your video!
    
    Based on the YouTube Shorts Generator script.
    """
)

# Requirements note
st.sidebar.title("Requirements")
st.sidebar.markdown(
    """
    This app requires the following Python packages:
    - streamlit
    - PIL (Pillow)
    - moviepy
    - numpy
    - librosa
    
    Make sure they are installed in your environment.
    """
)
