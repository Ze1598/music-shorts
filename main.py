# Global Parameters
IMAGE_PATH = "/Users/josecosta/Downloads/ChatGPT Image May 8, 2025, 11_03_35 PM.png"
IMAGE_PATH = "/Users/josecosta/Downloads/ChatGPT Image Apr 29, 2025, 07_20_12 PM.png"

AUDIO_PATH = "/Users/josecosta/Downloads/The Struggler, Pt. 3.wav"
AUDIO_PATH = "/Users/josecosta/Downloads/Beast of Destruction v2.wav"
AUDIO_START_TIME = 33  # Start time of the audio in seconds
AUDIO_END_TIME = 86  # End time of the audio in seconds (also dictates video duration)

VIDEO_FPS = 60
OUTPUT_VIDEO_FILENAME = "youtube_short_final_v6.mp4"

# Video dimensions (9:16 aspect ratio for YouTube Shorts)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Background Mode
BACKGROUND_MODE = "blur_image"  # Options: "solid", "blur_image"
BACKGROUND_BLUR_RADIUS = 50  # Blur radius if BACKGROUND_MODE is "blur_image"
BACKGROUND_IMAGE_FIT = "stretch" # Options: "stretch", "crop", "fill"

# Centered image properties
IMAGE_WIDTH_PERCENTAGE = 65
IMAGE_CORNER_RADIUS = 30 # Set to 0 for no rounding.
IMAGE_X_POSITION = -1 # Top-left corner X for the image (-1 for auto-center)
IMAGE_Y_POSITION = -1 # Top-left corner Y for the image (-1 for auto-center)

# Shadow properties (used for both main image and waveform if enabled)
SHADOW_OFFSET_X = 10
SHADOW_OFFSET_Y = 10
SHADOW_BLUR_RADIUS = 15
SHADOW_DARKNESS_FACTOR = 0.5 # For solid bg image shadow

# Waveform Animation Properties
WAVEFORM_ENABLED = True
WAVEFORM_ANALYSIS_MODE = "melspectrogram" # Options: "rms", "melspectrogram"
WAVEFORM_COLOR_MODE = "contrast"  # Options: "custom", "contrast", "white", "black"
WAVEFORM_COLOR = (255, 255, 255) # (R, G, B) - Used if WAVEFORM_COLOR_MODE is "custom"
WAVEFORM_HEIGHT_PERCENTAGE = 15
WAVEFORM_BAR_COUNT = 50 # If melspectrogram, this is n_mels
WAVEFORM_BAR_SPACING_RATIO = 0.2
WAVEFORM_SMOOTHING_FACTOR = 0.35 # Applied to final band values if melspectrogram, or RMS if rms mode
SPACING_IMAGE_WAVEFORM = 215 # Vertical spacing between image and waveform
WAVEFORM_MIN_DB = -80.0 # For melspectrogram normalization
WAVEFORM_MAX_DB = 0.0   # For melspectrogram normalization

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

def analyze_audio(audio_path, start_time, end_time, num_video_frames, video_fps):
    print(f"Analyzing audio ({WAVEFORM_ANALYSIS_MODE} mode): {audio_path} from {start_time}s to {end_time}s for {num_video_frames} frames at {video_fps} FPS")
    if not os.path.exists(audio_path):
        print("Audio file not found.")
        return np.zeros((num_video_frames, WAVEFORM_BAR_COUNT)) if WAVEFORM_ANALYSIS_MODE == "melspectrogram" else np.zeros(num_video_frames)
    try:
        y, sr = librosa.load(audio_path, sr=None, offset=start_time, duration=(end_time-start_time))
        if len(y) == 0:
            print("Warning: Loaded audio is empty.")
            return np.zeros((num_video_frames, WAVEFORM_BAR_COUNT)) if WAVEFORM_ANALYSIS_MODE == "melspectrogram" else np.zeros(num_video_frames)
        hop_length = int(sr / video_fps)
        if hop_length == 0: hop_length = int(sr / 24) if video_fps == 0 else 512 # fallback based on 24fps or fixed
        if WAVEFORM_ANALYSIS_MODE == "melspectrogram":
            n_fft = 2048 
            mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=WAVEFORM_BAR_COUNT)
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            mel_spec_normalized = (mel_spec_db - WAVEFORM_MIN_DB) / (WAVEFORM_MAX_DB - WAVEFORM_MIN_DB)
            mel_spec_normalized = np.clip(mel_spec_normalized, 0, 1)
            processed_audio_data = mel_spec_normalized.T 
            if WAVEFORM_SMOOTHING_FACTOR > 0 and processed_audio_data.shape[0] > 1:
                for i in range(processed_audio_data.shape[1]):
                    band_data = processed_audio_data[:, i]
                    smoothed_band = [band_data[0]]
                    for j in range(1, len(band_data)):
                        smoothed_band.append(smoothed_band[-1] * WAVEFORM_SMOOTHING_FACTOR + band_data[j] * (1 - WAVEFORM_SMOOTHING_FACTOR))
                    processed_audio_data[:, i] = np.array(smoothed_band)
        elif WAVEFORM_ANALYSIS_MODE == "rms":
            frame_length = hop_length * 2 
            if frame_length == 0 : frame_length = 1024 
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            rms_max = np.max(rms)
            rms_normalized = rms / rms_max if rms_max > 0 else np.zeros_like(rms)
            if WAVEFORM_SMOOTHING_FACTOR > 0 and len(rms_normalized) > 1:
                rms_smoothed = [rms_normalized[0]]
                for i in range(1, len(rms_normalized)):
                    rms_smoothed.append(rms_smoothed[-1] * WAVEFORM_SMOOTHING_FACTOR + rms_normalized[i] * (1 - WAVEFORM_SMOOTHING_FACTOR))
                rms_normalized = np.array(rms_smoothed)
            processed_audio_data = np.tile(rms_normalized[:, np.newaxis], (1, WAVEFORM_BAR_COUNT))
        else:
            print(f"Unknown WAVEFORM_ANALYSIS_MODE: {WAVEFORM_ANALYSIS_MODE}. Using zeros.")
            return np.zeros((num_video_frames, WAVEFORM_BAR_COUNT))
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
        return np.zeros((num_video_frames, WAVEFORM_BAR_COUNT)) if WAVEFORM_ANALYSIS_MODE == "melspectrogram" else np.zeros(num_video_frames)

def draw_waveform_bars(audio_frame_amplitudes, canvas_width, canvas_height, bar_color_tuple):
    num_bars = WAVEFORM_BAR_COUNT
    if num_bars <= 0 or len(audio_frame_amplitudes) != num_bars: return None
    bars_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0,0,0,0))
    draw_on_bars = ImageDraw.Draw(bars_canvas)
    total_slot_width = canvas_width / num_bars
    bar_width = int(total_slot_width / (1 + WAVEFORM_BAR_SPACING_RATIO))
    bar_spacing = int(bar_width * WAVEFORM_BAR_SPACING_RATIO)
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

BG_COLOR_SOLID_GLOBAL = (0,0,0)
BLURRED_BG_IMAGE_GLOBAL = None
CENTER_IMG_PROCESSED_GLOBAL = None
CENTER_IMG_SHADOW_GLOBAL = None # For rounded shadow
IMG_FINAL_WIDTH_GLOBAL, IMG_FINAL_HEIGHT_GLOBAL = 0, 0
IMG_ACTUAL_POS_X_GLOBAL, IMG_ACTUAL_POS_Y_GLOBAL = 0, 0
WAVEFORM_AREA_START_X_GLOBAL, WAVEFORM_AREA_TOP_Y_GLOBAL = 0,0
WAVEFORM_AREA_WIDTH_GLOBAL, WAVEFORM_MAX_BAR_H_GLOBAL = 0,0
AUDIO_AMPLITUDES_GLOBAL = None

def precompute_assets():
    global BG_COLOR_SOLID_GLOBAL, BLURRED_BG_IMAGE_GLOBAL, CENTER_IMG_PROCESSED_GLOBAL, CENTER_IMG_SHADOW_GLOBAL
    global IMG_FINAL_WIDTH_GLOBAL, IMG_FINAL_HEIGHT_GLOBAL, IMG_ACTUAL_POS_X_GLOBAL, IMG_ACTUAL_POS_Y_GLOBAL
    global WAVEFORM_AREA_START_X_GLOBAL, WAVEFORM_AREA_TOP_Y_GLOBAL, WAVEFORM_AREA_WIDTH_GLOBAL, WAVEFORM_MAX_BAR_H_GLOBAL
    global AUDIO_AMPLITUDES_GLOBAL
    print("\n--- Pre-computing assets ---")
    BG_COLOR_SOLID_GLOBAL = get_predominant_color(IMAGE_PATH)
    if BACKGROUND_MODE == "blur_image" and os.path.exists(IMAGE_PATH):
        try:
            img_to_blur = Image.open(IMAGE_PATH).convert("RGB")
            target_w, target_h = VIDEO_WIDTH, VIDEO_HEIGHT; img_w, img_h = img_to_blur.size
            if BACKGROUND_IMAGE_FIT == "stretch": BLURRED_BG_IMAGE_GLOBAL = img_to_blur.resize((target_w, target_h), Image.Resampling.LANCZOS)
            elif BACKGROUND_IMAGE_FIT == "fill" or BACKGROUND_IMAGE_FIT == "crop":
                img_aspect = img_w / img_h; target_aspect = target_w / target_h
                if img_aspect > target_aspect: new_h = target_h; new_w = int(new_h * img_aspect)
                else: new_w = target_w; new_h = int(new_w / img_aspect)
                resized_img = img_to_blur.resize((new_w, new_h), Image.Resampling.LANCZOS)
                crop_x = (new_w - target_w) / 2; crop_y = (new_h - target_h) / 2
                BLURRED_BG_IMAGE_GLOBAL = resized_img.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))
            else: BLURRED_BG_IMAGE_GLOBAL = img_to_blur.resize((target_w, target_h), Image.Resampling.LANCZOS)
            BLURRED_BG_IMAGE_GLOBAL = BLURRED_BG_IMAGE_GLOBAL.filter(ImageFilter.GaussianBlur(BACKGROUND_BLUR_RADIUS))
            print(f"Pre-computed blurred background: Fit='{BACKGROUND_IMAGE_FIT}', Radius={BACKGROUND_BLUR_RADIUS}")
        except Exception as e: print(f"Error pre-computing blurred background: {e}"); BLURRED_BG_IMAGE_GLOBAL = None
    if os.path.exists(IMAGE_PATH):
        try:
            img_orig = Image.open(IMAGE_PATH).convert("RGBA")
            IMG_FINAL_WIDTH_GLOBAL = int(VIDEO_WIDTH * (IMAGE_WIDTH_PERCENTAGE / 100.0))
            IMG_FINAL_HEIGHT_GLOBAL = int(IMG_FINAL_WIDTH_GLOBAL * (img_orig.height / img_orig.width))
            img_resized = img_orig.resize((IMG_FINAL_WIDTH_GLOBAL, IMG_FINAL_HEIGHT_GLOBAL), Image.Resampling.LANCZOS)
            CENTER_IMG_PROCESSED_GLOBAL = add_rounded_corners(img_resized, IMAGE_CORNER_RADIUS)
            # Create rounded shadow based on the processed image's alpha
            img_shadow_color_base = tuple(int(c * (1 - SHADOW_DARKNESS_FACTOR)) for c in BG_COLOR_SOLID_GLOBAL) if BACKGROUND_MODE == "solid" else (0,0,0)
            shadow_color_rgba = img_shadow_color_base + (255,)
            if 'A' in CENTER_IMG_PROCESSED_GLOBAL.getbands():
                alpha_mask = CENTER_IMG_PROCESSED_GLOBAL.split()[3]
                shadow_silhouette = Image.new("RGBA", CENTER_IMG_PROCESSED_GLOBAL.size, (0,0,0,0))
                solid_shadow_img = Image.new("RGBA", CENTER_IMG_PROCESSED_GLOBAL.size, shadow_color_rgba)
                shadow_silhouette.paste(solid_shadow_img, mask=alpha_mask)
                CENTER_IMG_SHADOW_GLOBAL = shadow_silhouette.filter(ImageFilter.GaussianBlur(SHADOW_BLUR_RADIUS))
            print(f"Pre-processed main image & shadow: Size=({IMG_FINAL_WIDTH_GLOBAL}x{IMG_FINAL_HEIGHT_GLOBAL}), Radius={IMAGE_CORNER_RADIUS}")
        except Exception as e: print(f"Error pre-processing main image/shadow: {e}"); CENTER_IMG_PROCESSED_GLOBAL = None; CENTER_IMG_SHADOW_GLOBAL = None
    else: print(f"Main image {IMAGE_PATH} not found.")
    IMG_ACTUAL_POS_X_GLOBAL = (VIDEO_WIDTH - IMG_FINAL_WIDTH_GLOBAL) // 2 if IMAGE_X_POSITION == -1 else IMAGE_X_POSITION
    WAVEFORM_MAX_BAR_H_GLOBAL = int(VIDEO_HEIGHT * (WAVEFORM_HEIGHT_PERCENTAGE / 100.0)) if WAVEFORM_ENABLED else 0
    total_content_height = IMG_FINAL_HEIGHT_GLOBAL + (SPACING_IMAGE_WAVEFORM + WAVEFORM_MAX_BAR_H_GLOBAL if WAVEFORM_ENABLED and WAVEFORM_MAX_BAR_H_GLOBAL > 0 else 0)
    IMG_ACTUAL_POS_Y_GLOBAL = (VIDEO_HEIGHT - total_content_height) // 2 if IMAGE_Y_POSITION == -1 else IMAGE_Y_POSITION
    WAVEFORM_AREA_TOP_Y_GLOBAL = IMG_ACTUAL_POS_Y_GLOBAL + IMG_FINAL_HEIGHT_GLOBAL + SPACING_IMAGE_WAVEFORM
    WAVEFORM_AREA_WIDTH_GLOBAL = IMG_FINAL_WIDTH_GLOBAL
    WAVEFORM_AREA_START_X_GLOBAL = IMG_ACTUAL_POS_X_GLOBAL
    print(f"Image pos: X={IMG_ACTUAL_POS_X_GLOBAL}, Y={IMG_ACTUAL_POS_Y_GLOBAL}. Waveform top Y: {WAVEFORM_AREA_TOP_Y_GLOBAL}, spacing: {SPACING_IMAGE_WAVEFORM}")
    video_duration = AUDIO_END_TIME - AUDIO_START_TIME; current_fps = VIDEO_FPS
    if video_duration <= 0: video_duration = 1
    num_total_frames = int(video_duration * current_fps)
    if WAVEFORM_ENABLED: AUDIO_AMPLITUDES_GLOBAL = analyze_audio(AUDIO_PATH, AUDIO_START_TIME, AUDIO_END_TIME, num_total_frames, current_fps)
    print("--- Pre-computation finished ---")

def make_frame_for_moviepy(t):
    current_fps = VIDEO_FPS; frame_idx = int(t * current_fps)
    if frame_idx % (current_fps * 5) == 0: print(f"Generating frame {frame_idx + 1} for time {t:.2f}s")
    current_frame_pil = None
    if BACKGROUND_MODE == "blur_image" and BLURRED_BG_IMAGE_GLOBAL: current_frame_pil = BLURRED_BG_IMAGE_GLOBAL.copy()
    else: current_frame_pil = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR_SOLID_GLOBAL)
    if CENTER_IMG_SHADOW_GLOBAL:
        shadow_rounded = add_rounded_corners(CENTER_IMG_SHADOW_GLOBAL, IMAGE_CORNER_RADIUS)
        current_frame_pil.paste(CENTER_IMG_SHADOW_GLOBAL, (IMG_ACTUAL_POS_X_GLOBAL + SHADOW_OFFSET_X, IMG_ACTUAL_POS_Y_GLOBAL + SHADOW_OFFSET_Y), shadow_rounded)
        # current_frame_pil.paste(CENTER_IMG_SHADOW_GLOBAL, (IMG_ACTUAL_POS_X_GLOBAL + SHADOW_OFFSET_X, IMG_ACTUAL_POS_Y_GLOBAL + SHADOW_OFFSET_Y), CENTER_IMG_SHADOW_GLOBAL)
    if CENTER_IMG_PROCESSED_GLOBAL:
        current_frame_pil.paste(CENTER_IMG_PROCESSED_GLOBAL, (IMG_ACTUAL_POS_X_GLOBAL, IMG_ACTUAL_POS_Y_GLOBAL), CENTER_IMG_PROCESSED_GLOBAL)
    if WAVEFORM_ENABLED and AUDIO_AMPLITUDES_GLOBAL is not None and frame_idx < AUDIO_AMPLITUDES_GLOBAL.shape[0]:
        current_audio_frame_data = AUDIO_AMPLITUDES_GLOBAL[frame_idx, :]
        actual_wave_color = WAVEFORM_COLOR
        if WAVEFORM_COLOR_MODE == "white": actual_wave_color = (255,255,255)
        elif WAVEFORM_COLOR_MODE == "black": actual_wave_color = (0,0,0)
        elif WAVEFORM_COLOR_MODE == "contrast":
            try:
                wave_bg_box = (WAVEFORM_AREA_START_X_GLOBAL, WAVEFORM_AREA_TOP_Y_GLOBAL, 
                               WAVEFORM_AREA_START_X_GLOBAL + WAVEFORM_AREA_WIDTH_GLOBAL, 
                               WAVEFORM_AREA_TOP_Y_GLOBAL + WAVEFORM_MAX_BAR_H_GLOBAL)
                wave_bg_box = (max(0, wave_bg_box[0]), max(0, wave_bg_box[1]), 
                               min(VIDEO_WIDTH, wave_bg_box[2]), min(VIDEO_HEIGHT, wave_bg_box[3]))
                if wave_bg_box[2] > wave_bg_box[0] and wave_bg_box[3] > wave_bg_box[1]:
                    waveform_bg_crop = current_frame_pil.crop(wave_bg_box).convert("RGB")
                    avg_color_bg = tuple(int(c) for c in ImageStat.Stat(waveform_bg_crop).mean)
                    actual_wave_color = get_waveform_contrast_color(avg_color_bg[0], avg_color_bg[1], avg_color_bg[2])
                    if frame_idx == 0: print(f"Waveform contrast color: {actual_wave_color} against bg avg: {avg_color_bg}")
                else: 
                    if frame_idx == 0: print("Warning: Invalid crop area for waveform contrast. Defaulting color.")
                    actual_wave_color = get_waveform_contrast_color(BG_COLOR_SOLID_GLOBAL[0],BG_COLOR_SOLID_GLOBAL[1],BG_COLOR_SOLID_GLOBAL[2])
            except Exception as e_contrast:
                if frame_idx == 0: print(f"Error in contrast color: {e_contrast}. Defaulting.")
                actual_wave_color = (255,255,255)
        bars_canvas = draw_waveform_bars(current_audio_frame_data, WAVEFORM_AREA_WIDTH_GLOBAL, WAVEFORM_MAX_BAR_H_GLOBAL, actual_wave_color)
        if bars_canvas:
            wave_shadow_color_rgba = (0,0,0, 180) 
            if 'A' in bars_canvas.getbands():
                bars_alpha_mask = bars_canvas.split()[3]
                wave_shadow_sil = Image.new("RGBA", bars_canvas.size, (0,0,0,0))
                wave_shadow_sil.paste(Image.new("RGBA", bars_canvas.size, wave_shadow_color_rgba), mask=bars_alpha_mask)
                wave_shadow_blur = wave_shadow_sil.filter(ImageFilter.GaussianBlur(SHADOW_BLUR_RADIUS))
                current_frame_pil.paste(wave_shadow_blur, (WAVEFORM_AREA_START_X_GLOBAL + SHADOW_OFFSET_X, WAVEFORM_AREA_TOP_Y_GLOBAL + SHADOW_OFFSET_Y), wave_shadow_blur)
            current_frame_pil.paste(bars_canvas, (WAVEFORM_AREA_START_X_GLOBAL, WAVEFORM_AREA_TOP_Y_GLOBAL), bars_canvas)
    return np.array(current_frame_pil)

if __name__ == "__main__":
    print(f"Starting YouTube Shorts script (v6 - User Prefs & New Contrast)...")
    precompute_assets()
    video_duration = AUDIO_END_TIME - AUDIO_START_TIME
    if video_duration <= 0: video_duration = 1
    current_fps = VIDEO_FPS
    print(f"Target video duration: {video_duration}s, FPS: {current_fps}")
    video_clip = mpe.VideoClip(make_frame_for_moviepy, duration=video_duration)
    if os.path.exists(AUDIO_PATH):
        print(f"Reading audio: {AUDIO_PATH}")
        try:
            main_audio_clip = mpe.AudioFileClip(AUDIO_PATH)
            actual_start = min(max(0, AUDIO_START_TIME), main_audio_clip.duration)
            actual_end = min(max(actual_start, AUDIO_END_TIME), main_audio_clip.duration)
            if actual_start >= actual_end: print("Warning: Invalid audio trim. No audio."); video_clip = video_clip.set_audio(None)
            else:
                trimmed_audio = main_audio_clip.subclip(actual_start, actual_end)
                if trimmed_audio.duration < video_clip.duration: video_clip = video_clip.set_duration(trimmed_audio.duration)
                elif trimmed_audio.duration > video_clip.duration: trimmed_audio = trimmed_audio.set_duration(video_clip.duration)
                video_clip = video_clip.set_audio(trimmed_audio)
                print(f"Audio set. Final duration: {video_clip.duration:.2f}s.")
        except Exception as e: print(f"Error processing audio {AUDIO_PATH}: {e}. No audio."); video_clip = video_clip.set_audio(None)
    else: print(f"Audio {AUDIO_PATH} not found. No audio."); video_clip = video_clip.set_audio(None)
    print(f"\nWriting video: {OUTPUT_VIDEO_FILENAME}")
    try:
        video_clip.write_videofile(OUTPUT_VIDEO_FILENAME, fps=current_fps, codec="libx264", audio_codec="aac", threads=4, logger='bar')
        print(f"Successfully created: {OUTPUT_VIDEO_FILENAME}")
    except Exception as e: print(f"Error writing video: {e}")
    print("\nScript finished.")

