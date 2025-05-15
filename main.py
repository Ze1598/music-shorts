# --- Script Start --- #
from PIL import Image, ImageDraw, ImageFilter, ImageStat
import moviepy.editor as mpe
import numpy as np
import os
import librosa
import colorsys

def get_predominant_color(image_path):
    print(f"Reading image for predominant color: {image_path}")
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}. Using default black.")
        return (0,0,0)
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"Error opening image {image_path}: {e}. Using default black.")
        return (0,0,0)
    if 'A' in img.getbands():
        mask = img.split()[3]
        if ImageStat.Stat(mask).sum[0] == 0:
            print("Warning: Image is fully transparent. Using default black.")
            return (0,0,0)
        img_rgb = img.convert("RGB")
        stat = ImageStat.Stat(img_rgb, mask)
    else:
        img_rgb = img.convert("RGB")
        stat = ImageStat.Stat(img_rgb)
    avg_color = tuple(int(c) for c in stat.mean)
    print(f"Calculated average color (predominant): {avg_color}")
    return avg_color

def add_rounded_corners(img, radius):
    if radius <= 0: return img
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0) + img.size, radius=radius, fill=255)
    img_copy = img.copy()
    img_copy.putalpha(mask)
    return img_copy

def get_waveform_contrast_color(bg_r, bg_g, bg_b):
    # Calculate luminance of the background
    bg_lum = 0.299 * bg_r + 0.587 * bg_g + 0.114 * bg_b

    # Attempt 1: Inverted color
    inv_r, inv_g, inv_b = 255 - bg_r, 255 - bg_g, 255 - bg_b
    inv_lum = 0.299 * inv_r + 0.587 * inv_g + 0.114 * inv_b

    # Check if luminance difference is significant enough
    if abs(bg_lum - inv_lum) > 60: # Threshold for sufficient contrast
        # print(f"Using inverted color for waveform: ({inv_r}, {inv_g}, {inv_b}) against bg: ({bg_r}, {bg_g}, {bg_b})")
        return (inv_r, inv_g, inv_b)

    # Attempt 2: If inverted color is not contrasting enough, try shifting hue significantly
    # Convert RGB to HLS
    h, l, s = colorsys.rgb_to_hls(bg_r / 255.0, bg_g / 255.0, bg_b / 255.0)
    
    # Shift hue by 0.5 (180 degrees) for complementary
    comp_h = (h + 0.5) % 1.0
    
    # Adjust lightness for contrast: if background is dark, make complement light, and vice-versa
    comp_l = 0.8 if l < 0.5 else 0.2
    comp_s = max(0.5, s) # Ensure some saturation

    comp_r, comp_g, comp_b = colorsys.hls_to_rgb(comp_h, comp_l, comp_s)
    comp_r, comp_g, comp_b = int(comp_r * 255), int(comp_g * 255), int(comp_b * 255)
    comp_lum = 0.299 * comp_r + 0.587 * comp_g + 0.114 * comp_b

    if abs(bg_lum - comp_lum) > 60:
        print(f"Using complementary-like color for waveform: ({comp_r}, {comp_g}, {comp_b})")
        return (comp_r, comp_g, comp_b)

    # Fallback: Pure black or white based on background luminance
    fallback_color = (0, 0, 0) if bg_lum > 128 else (255, 255, 255)
    print(f"Using fallback black/white for waveform: {fallback_color}")
    return fallback_color

def analyze_audio(audio_path, start_time, end_time, num_video_frames, video_fps, waveform_analysis_mode, waveform_bar_count, waveform_smoothing_factor, waveform_min_db, waveform_max_db):
    print(f"Analyzing audio ({waveform_analysis_mode} mode): {audio_path} from {start_time}s to {end_time}s for {num_video_frames} frames at {video_fps} FPS")
    if not os.path.exists(audio_path):
        print("Audio file not found.")
        return np.zeros((num_video_frames, waveform_bar_count)) if waveform_analysis_mode == "melspectrogram" else np.zeros(num_video_frames)
    try:
        y, sr = librosa.load(audio_path, sr=None, offset=start_time, duration=(end_time-start_time))
        if len(y) == 0:
            print("Warning: Loaded audio is empty.")
            return np.zeros((num_video_frames, waveform_bar_count)) if waveform_analysis_mode == "melspectrogram" else np.zeros(num_video_frames)
        hop_length = int(sr / video_fps)
        if hop_length == 0: hop_length = int(sr / 24) if video_fps == 0 else 512 # fallback based on 24fps or fixed
        if waveform_analysis_mode == "melspectrogram":
            n_fft = 2048 
            mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=waveform_bar_count)
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            mel_spec_normalized = (mel_spec_db - waveform_min_db) / (waveform_max_db - waveform_min_db)
            mel_spec_normalized = np.clip(mel_spec_normalized, 0, 1)
            processed_audio_data = mel_spec_normalized.T 
            if waveform_smoothing_factor > 0 and processed_audio_data.shape[0] > 1:
                for i in range(processed_audio_data.shape[1]):
                    band_data = processed_audio_data[:, i]
                    smoothed_band = [band_data[0]]
                    for j in range(1, len(band_data)):
                        smoothed_band.append(smoothed_band[-1] * waveform_smoothing_factor + band_data[j] * (1 - waveform_smoothing_factor))
                    processed_audio_data[:, i] = np.array(smoothed_band)
        elif waveform_analysis_mode == "rms":
            frame_length = hop_length * 2 
            if frame_length == 0 : frame_length = 1024 
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            rms_max = np.max(rms)
            rms_normalized = rms / rms_max if rms_max > 0 else np.zeros_like(rms)
            if waveform_smoothing_factor > 0 and len(rms_normalized) > 1:
                rms_smoothed = [rms_normalized[0]]
                for i in range(1, len(rms_normalized)):
                    rms_smoothed.append(rms_smoothed[-1] * waveform_smoothing_factor + rms_normalized[i] * (1 - waveform_smoothing_factor))
                rms_normalized = np.array(rms_smoothed)
            processed_audio_data = np.tile(rms_normalized[:, np.newaxis], (1, waveform_bar_count))
        else:
            print(f"Unknown waveform_analysis_mode: {waveform_analysis_mode}. Using zeros.")
            return np.zeros((num_video_frames, waveform_bar_count))
        if processed_audio_data.shape[0] < num_video_frames:
            padding_shape = (num_video_frames - processed_audio_data.shape[0], processed_audio_data.shape[1])
            padding = np.zeros(padding_shape)
            final_audio_data = np.concatenate((processed_audio_data, padding), axis=0)
        else:
            final_audio_data = processed_audio_data[:num_video_frames, :]
        print(f"Audio analysis complete. Output shape: {final_audio_data.shape}")
        return final_audio_data
    except Exception as e:
        print(f"Error analyzing audio: {e}")
        return np.zeros((num_video_frames, waveform_bar_count)) if waveform_analysis_mode == "melspectrogram" else np.zeros(num_video_frames)

def draw_waveform_bars(audio_frame_amplitudes, canvas_width, canvas_height, bar_color_tuple, waveform_bar_count, waveform_bar_spacing_ratio):
    num_bars = waveform_bar_count
    if num_bars <= 0 or len(audio_frame_amplitudes) != num_bars: return None
    bars_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0,0,0,0))
    draw_on_bars = ImageDraw.Draw(bars_canvas)
    total_slot_width = canvas_width / num_bars
    bar_width = int(total_slot_width / (1 + waveform_bar_spacing_ratio))
    bar_spacing = int(bar_width * waveform_bar_spacing_ratio)
    if bar_width < 1: bar_width = 1
    if bar_spacing < 0: bar_spacing = 0
    actual_waveform_width = num_bars * bar_width + max(0, num_bars - 1) * bar_spacing
    current_x = (canvas_width - actual_waveform_width) // 2
    for i in range(num_bars):
        rms_value_for_bar = audio_frame_amplitudes[i]
        bar_height = int(canvas_height * rms_value_for_bar)
        if bar_height < 1: bar_height = 0
        x0 = current_x; y0 = canvas_height - bar_height
        x1 = x0 + bar_width; y1 = canvas_height
        if bar_height > 0: draw_on_bars.rectangle([x0, y0, x1, y1], fill=bar_color_tuple)
        current_x += (bar_width + bar_spacing)
    return bars_canvas

# Asset storage class to replace global variables
class VideoAssets:
    def __init__(self):
        self.bg_color_solid = (0,0,0)
        self.blurred_bg_image = None
        self.center_img_processed = None
        self.center_img_shadow = None  # For rounded shadow
        self.img_final_width, self.img_final_height = 0, 0
        self.img_actual_pos_x, self.img_actual_pos_y = 0, 0
        self.waveform_area_start_x, self.waveform_area_top_y = 0, 0
        self.waveform_area_width, self.waveform_max_bar_h = 0, 0
        self.audio_amplitudes = None

def precompute_assets(image_path, video_width, video_height, background_mode, background_image_fit, background_blur_radius,
                   image_width_percentage, image_corner_radius, image_x_position, image_y_position,
                   shadow_darkness_factor, shadow_blur_radius, waveform_enabled, waveform_height_percentage,
                   spacing_image_waveform, audio_path, audio_start_time, audio_end_time, video_fps,
                   waveform_analysis_mode, waveform_bar_count, waveform_smoothing_factor, waveform_min_db, waveform_max_db):
    assets = VideoAssets()
    print("\n--- Pre-computing assets ---")
    assets.bg_color_solid = get_predominant_color(image_path)
    if background_mode == "blur_image" and os.path.exists(image_path):
        try:
            img_to_blur = Image.open(image_path).convert("RGB")
            target_w, target_h = video_width, video_height; img_w, img_h = img_to_blur.size
            if background_image_fit == "stretch": assets.blurred_bg_image = img_to_blur.resize((target_w, target_h), Image.Resampling.LANCZOS)
            elif background_image_fit == "fill" or background_image_fit == "crop":
                img_aspect = img_w / img_h; target_aspect = target_w / target_h
                if img_aspect > target_aspect: new_h = target_h; new_w = int(new_h * img_aspect)
                else: new_w = target_w; new_h = int(new_w / img_aspect)
                resized_img = img_to_blur.resize((new_w, new_h), Image.Resampling.LANCZOS)
                crop_x = (new_w - target_w) / 2; crop_y = (new_h - target_h) / 2
                assets.blurred_bg_image = resized_img.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))
            else: assets.blurred_bg_image = img_to_blur.resize((target_w, target_h), Image.Resampling.LANCZOS)
            assets.blurred_bg_image = assets.blurred_bg_image.filter(ImageFilter.GaussianBlur(background_blur_radius))
            print(f"Pre-computed blurred background: Fit='{background_image_fit}', Radius={background_blur_radius}")
        except Exception as e: print(f"Error pre-computing blurred background: {e}"); assets.blurred_bg_image = None
    if os.path.exists(image_path):
        try:
            img_orig = Image.open(image_path).convert("RGBA")
            assets.img_final_width = int(video_width * (image_width_percentage / 100.0))
            assets.img_final_height = int(assets.img_final_width * (img_orig.height / img_orig.width))
            img_resized = img_orig.resize((assets.img_final_width, assets.img_final_height), Image.Resampling.LANCZOS)
            assets.center_img_processed = add_rounded_corners(img_resized, image_corner_radius)
            # Create rounded shadow based on the processed image's alpha
            img_shadow_color_base = tuple(int(c * (1 - shadow_darkness_factor)) for c in assets.bg_color_solid) if background_mode == "solid" else (0,0,0)
            shadow_color_rgba = img_shadow_color_base + (255,)
            if 'A' in assets.center_img_processed.getbands():
                alpha_mask = assets.center_img_processed.split()[3]
                shadow_silhouette = Image.new("RGBA", assets.center_img_processed.size, (0,0,0,0))
                solid_shadow_img = Image.new("RGBA", assets.center_img_processed.size, shadow_color_rgba)
                shadow_silhouette.paste(solid_shadow_img, mask=alpha_mask)
                assets.center_img_shadow = shadow_silhouette.filter(ImageFilter.GaussianBlur(shadow_blur_radius))
            print(f"Pre-processed main image & shadow: Size=({assets.img_final_width}x{assets.img_final_height}), Radius={image_corner_radius}")
        except Exception as e: print(f"Error pre-processing main image/shadow: {e}"); assets.center_img_processed = None; assets.center_img_shadow = None
    else: print(f"Main image {image_path} not found.")
    assets.img_actual_pos_x = (video_width - assets.img_final_width) // 2 if image_x_position == -1 else image_x_position
    assets.waveform_max_bar_h = int(video_height * (waveform_height_percentage / 100.0)) if waveform_enabled else 0
    total_content_height = assets.img_final_height + (spacing_image_waveform + assets.waveform_max_bar_h if waveform_enabled and assets.waveform_max_bar_h > 0 else 0)
    assets.img_actual_pos_y = (video_height - total_content_height) // 2 if image_y_position == -1 else image_y_position
    assets.waveform_area_top_y = assets.img_actual_pos_y + assets.img_final_height + spacing_image_waveform
    assets.waveform_area_width = assets.img_final_width
    assets.waveform_area_start_x = assets.img_actual_pos_x
    print(f"Image pos: X={assets.img_actual_pos_x}, Y={assets.img_actual_pos_y}. Waveform top Y: {assets.waveform_area_top_y}, spacing: {spacing_image_waveform}")
    video_duration = audio_end_time - audio_start_time; current_fps = video_fps
    if video_duration <= 0: video_duration = 1
    num_total_frames = int(video_duration * current_fps)
    if waveform_enabled: 
        assets.audio_amplitudes = analyze_audio(audio_path, audio_start_time, audio_end_time, num_total_frames, current_fps,
                                             waveform_analysis_mode, waveform_bar_count, waveform_smoothing_factor, 
                                             waveform_min_db, waveform_max_db)
    print("--- Pre-computation finished ---")
    return assets

def make_frame_for_moviepy(t, assets, video_fps, video_width, video_height, background_mode, image_corner_radius,
                         shadow_offset_x, shadow_offset_y, shadow_blur_radius, waveform_enabled, waveform_color_mode,
                         waveform_color, waveform_bar_count, waveform_bar_spacing_ratio):
    current_fps = video_fps; frame_idx = int(t * current_fps)
    if frame_idx % (current_fps * 5) == 0: print(f"Generating frame {frame_idx + 1} for time {t:.2f}s")
    current_frame_pil = None
    if background_mode == "blur_image" and assets.blurred_bg_image: current_frame_pil = assets.blurred_bg_image.copy()
    else: current_frame_pil = Image.new("RGB", (video_width, video_height), assets.bg_color_solid)
    if assets.center_img_shadow:
        shadow_rounded = add_rounded_corners(assets.center_img_shadow, image_corner_radius)
        current_frame_pil.paste(assets.center_img_shadow, (assets.img_actual_pos_x + shadow_offset_x, assets.img_actual_pos_y + shadow_offset_y), shadow_rounded)
    if assets.center_img_processed:
        current_frame_pil.paste(assets.center_img_processed, (assets.img_actual_pos_x, assets.img_actual_pos_y), assets.center_img_processed)
    if waveform_enabled and assets.audio_amplitudes is not None and frame_idx < assets.audio_amplitudes.shape[0]:
        current_audio_frame_data = assets.audio_amplitudes[frame_idx, :]
        actual_wave_color = waveform_color
        if waveform_color_mode == "white": actual_wave_color = (255,255,255)
        elif waveform_color_mode == "black": actual_wave_color = (0,0,0)
        elif waveform_color_mode == "contrast":
            try:
                wave_bg_box = (assets.waveform_area_start_x, assets.waveform_area_top_y, 
                               assets.waveform_area_start_x + assets.waveform_area_width, 
                               assets.waveform_area_top_y + assets.waveform_max_bar_h)
                wave_bg_box = (max(0, wave_bg_box[0]), max(0, wave_bg_box[1]), 
                               min(video_width, wave_bg_box[2]), min(video_height, wave_bg_box[3]))
                if wave_bg_box[2] > wave_bg_box[0] and wave_bg_box[3] > wave_bg_box[1]:
                    waveform_bg_crop = current_frame_pil.crop(wave_bg_box).convert("RGB")
                    avg_color_bg = tuple(int(c) for c in ImageStat.Stat(waveform_bg_crop).mean)
                    actual_wave_color = get_waveform_contrast_color(avg_color_bg[0], avg_color_bg[1], avg_color_bg[2])
                    if frame_idx == 0: print(f"Waveform contrast color: {actual_wave_color} against bg avg: {avg_color_bg}")
                else: 
                    if frame_idx == 0: print("Warning: Invalid crop area for waveform contrast. Defaulting color.")
                    actual_wave_color = get_waveform_contrast_color(assets.bg_color_solid[0], assets.bg_color_solid[1], assets.bg_color_solid[2])
            except Exception as e_contrast:
                if frame_idx == 0: print(f"Error in contrast color: {e_contrast}. Defaulting.")
                actual_wave_color = (255,255,255)
        bars_canvas = draw_waveform_bars(current_audio_frame_data, assets.waveform_area_width, assets.waveform_max_bar_h, 
                                       actual_wave_color, waveform_bar_count, waveform_bar_spacing_ratio)
        if bars_canvas:
            wave_shadow_color_rgba = (0,0,0, 180) 
            if 'A' in bars_canvas.getbands():
                bars_alpha_mask = bars_canvas.split()[3]
                wave_shadow_sil = Image.new("RGBA", bars_canvas.size, (0,0,0,0))
                wave_shadow_sil.paste(Image.new("RGBA", bars_canvas.size, wave_shadow_color_rgba), mask=bars_alpha_mask)
                wave_shadow_blur = wave_shadow_sil.filter(ImageFilter.GaussianBlur(shadow_blur_radius))
                current_frame_pil.paste(wave_shadow_blur, (assets.waveform_area_start_x + shadow_offset_x, assets.waveform_area_top_y + shadow_offset_y), wave_shadow_blur)
            current_frame_pil.paste(bars_canvas, (assets.waveform_area_start_x, assets.waveform_area_top_y), bars_canvas)
    return np.array(current_frame_pil)

if __name__ == "__main__":
    # Sample configuration for creating a YouTube Short
    # Image settings
    IMAGE_PATH = "/Users/josecosta/Downloads/ChatGPT Image Apr 29, 2025, 07_20_12 PM.png"
    IMAGE_WIDTH_PERCENTAGE = 65
    IMAGE_CORNER_RADIUS = 30  # Set to 0 for no rounding
    IMAGE_X_POSITION = -1  # -1 for auto-center
    IMAGE_Y_POSITION = -1  # -1 for auto-center
    
    # Audio settings
    AUDIO_PATH = "/Users/josecosta/Downloads/Beast of Destruction v2.wav"
    AUDIO_START_TIME = 33  # Start time of the audio in seconds
    AUDIO_END_TIME = 86  # End time of the audio in seconds (also dictates video duration)
    
    # Video settings
    VIDEO_FPS = 60
    OUTPUT_VIDEO_FILENAME = "youtube_short_final_v6.mp4"
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920
    
    # Background settings
    BACKGROUND_MODE = "blur_image"  # Options: "solid", "blur_image"
    BACKGROUND_BLUR_RADIUS = 50  # Blur radius if BACKGROUND_MODE is "blur_image"
    BACKGROUND_IMAGE_FIT = "stretch"  # Options: "stretch", "crop", "fill"
    
    # Shadow properties
    SHADOW_OFFSET_X = 10
    SHADOW_OFFSET_Y = 10
    SHADOW_BLUR_RADIUS = 15
    SHADOW_DARKNESS_FACTOR = 0.5  # For solid bg image shadow
    
    # Waveform Animation Properties
    WAVEFORM_ENABLED = True
    WAVEFORM_ANALYSIS_MODE = "melspectrogram"  # Options: "rms", "melspectrogram"
    WAVEFORM_COLOR_MODE = "contrast"  # Options: "custom", "contrast", "white", "black"
    WAVEFORM_COLOR = (255, 255, 255)  # (R, G, B) - Used if WAVEFORM_COLOR_MODE is "custom"
    WAVEFORM_HEIGHT_PERCENTAGE = 15
    WAVEFORM_BAR_COUNT = 50  # If melspectrogram, this is n_mels
    WAVEFORM_BAR_SPACING_RATIO = 0.2
    WAVEFORM_SMOOTHING_FACTOR = 0.35  # Applied to final band values if melspectrogram, or RMS if rms mode
    SPACING_IMAGE_WAVEFORM = 215  # Vertical spacing between image and waveform
    WAVEFORM_MIN_DB = -80.0  # For melspectrogram normalization
    WAVEFORM_MAX_DB = 0.0  # For melspectrogram normalization
    
    print(f"Starting YouTube Shorts script (v6 - User Prefs & New Contrast)...")
    
    # Precompute all assets
    assets = precompute_assets(
        image_path=IMAGE_PATH,
        video_width=VIDEO_WIDTH,
        video_height=VIDEO_HEIGHT,
        background_mode=BACKGROUND_MODE,
        background_image_fit=BACKGROUND_IMAGE_FIT,
        background_blur_radius=BACKGROUND_BLUR_RADIUS,
        image_width_percentage=IMAGE_WIDTH_PERCENTAGE,
        image_corner_radius=IMAGE_CORNER_RADIUS,
        image_x_position=IMAGE_X_POSITION,
        image_y_position=IMAGE_Y_POSITION,
        shadow_darkness_factor=SHADOW_DARKNESS_FACTOR,
        shadow_blur_radius=SHADOW_BLUR_RADIUS,
        waveform_enabled=WAVEFORM_ENABLED,
        waveform_height_percentage=WAVEFORM_HEIGHT_PERCENTAGE,
        spacing_image_waveform=SPACING_IMAGE_WAVEFORM,
        audio_path=AUDIO_PATH,
        audio_start_time=AUDIO_START_TIME,
        audio_end_time=AUDIO_END_TIME,
        video_fps=VIDEO_FPS,
        waveform_analysis_mode=WAVEFORM_ANALYSIS_MODE,
        waveform_bar_count=WAVEFORM_BAR_COUNT,
        waveform_smoothing_factor=WAVEFORM_SMOOTHING_FACTOR,
        waveform_min_db=WAVEFORM_MIN_DB,
        waveform_max_db=WAVEFORM_MAX_DB
    )
    
    # Create frame maker function with closure for all parameters
    def frame_maker(t):
        return make_frame_for_moviepy(
            t=t,
            assets=assets,
            video_fps=VIDEO_FPS,
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            background_mode=BACKGROUND_MODE,
            image_corner_radius=IMAGE_CORNER_RADIUS,
            shadow_offset_x=SHADOW_OFFSET_X,
            shadow_offset_y=SHADOW_OFFSET_Y,
            shadow_blur_radius=SHADOW_BLUR_RADIUS,
            waveform_enabled=WAVEFORM_ENABLED,
            waveform_color_mode=WAVEFORM_COLOR_MODE,
            waveform_color=WAVEFORM_COLOR,
            waveform_bar_count=WAVEFORM_BAR_COUNT,
            waveform_bar_spacing_ratio=WAVEFORM_BAR_SPACING_RATIO
        )
    
    video_duration = AUDIO_END_TIME - AUDIO_START_TIME
    if video_duration <= 0: video_duration = 1
    print(f"Target video duration: {video_duration}s, FPS: {VIDEO_FPS}")
    
    # Create video clip with our frame maker function
    video_clip = mpe.VideoClip(frame_maker, duration=video_duration)
    
    # Add audio if available
    if os.path.exists(AUDIO_PATH):
        print(f"Reading audio: {AUDIO_PATH}")
        try:
            main_audio_clip = mpe.AudioFileClip(AUDIO_PATH)
            actual_start = min(max(0, AUDIO_START_TIME), main_audio_clip.duration)
            actual_end = min(max(actual_start, AUDIO_END_TIME), main_audio_clip.duration)
            if actual_start >= actual_end: 
                print("Warning: Invalid audio trim. No audio.")
                video_clip = video_clip.set_audio(None)
            else:
                trimmed_audio = main_audio_clip.subclip(actual_start, actual_end)
                if trimmed_audio.duration < video_clip.duration:
                    video_clip = video_clip.set_duration(trimmed_audio.duration)
                elif trimmed_audio.duration > video_clip.duration:
                    trimmed_audio = trimmed_audio.set_duration(video_clip.duration)
                video_clip = video_clip.set_audio(trimmed_audio)
                print(f"Audio set. Final duration: {video_clip.duration:.2f}s.")
        except Exception as e: 
            print(f"Error processing audio {AUDIO_PATH}: {e}. No audio.")
            video_clip = video_clip.set_audio(None)
    else: 
        print(f"Audio {AUDIO_PATH} not found. No audio.")
        video_clip = video_clip.set_audio(None)
    
    # Write the final video file
    print(f"\nWriting video: {OUTPUT_VIDEO_FILENAME}")
    try:
        video_clip.write_videofile(
            OUTPUT_VIDEO_FILENAME, 
            fps=VIDEO_FPS, 
            codec="libx264", 
            audio_codec="aac", 
            threads=4, 
            logger='bar'
        )
        print(f"Successfully created: {OUTPUT_VIDEO_FILENAME}")
    except Exception as e: 
        print(f"Error writing video: {e}")
    
    print("\nScript finished.")

