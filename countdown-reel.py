import asyncio
import os
import requests
import json
import re
import time
import shutil
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from dotenv import load_dotenv
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips, ColorClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.video.fx import FadeIn

load_dotenv() 

LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
BRAND_FETCH_API_KEY = os.getenv("BRAND_FETCH_API_KEY")
BRAND_FETCH_CLIENT_ID = os.getenv("BRAND_FETCH_CLIENT_ID")

# ==========================================
# 🚀 DEVELOPMENT TOGGLE & SOLID COLOR PALETTE
# ==========================================
TEST_MODE = True  # Set to False for Final 1080p Render

if TEST_MODE:
    WIDTH, HEIGHT = 540, 960  
    RENDER_FPS = 12           
    print("\n⚠️ RUNNING IN DRAFT/TEST MODE - FAST RENDER ⚠️\n")
else:
    WIDTH, HEIGHT = 1080, 1920 
    RENDER_FPS = 24            

# Standard Solid Colors (Removed Blue)
THEME_COLORS = [
    'red',
    'green',
    'orange',
    'purple',
    'magenta',
    'cyan',
    'yellow'
]
# ==========================================

USER_PATH = r"C:\Users\Amit.Rakhaiya\AppData\Local\Microsoft\Windows\Fonts"
FONT_PATH = os.path.join(USER_PATH, "NotoSans-VariableFont_wdth,wght.ttf")
IMPACT_PATH = r"C:\Windows\Fonts\impact.ttf"

BOLD_FONT = IMPACT_PATH if os.path.exists(IMPACT_PATH) else FONT_PATH

INPUT_JSON = "script.json"
TARGET_DIR = "target"
IMAGE_DIR = os.path.join(TARGET_DIR, "images")
VOICE_DIR = os.path.join(TARGET_DIR, "voice-over")
SFX_DIR = "sfx"
LOGOS_DIR = "logos"

MODEL_ID = "7b592283-e8a7-4c5a-9ba6-d18c31f258b9" 
first_image_id = None

# --- PIL Image Generators for flawless transparent graphics ---
def create_hollow_text(text, font_path, font_size, stroke_width, color_name):
    """Draws transparent text with a solid colored border using Python Native PIL"""
    try:
        font = ImageFont.truetype(font_path, font_size)
        dummy_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy_img)
        
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
            w = bbox[2] - bbox[0] + 40
            h = bbox[3] - bbox[1] + 40
            x_offset, y_offset = -bbox[0] + 20, -bbox[1] + 20
        else:
            w, h = draw.textsize(text, font=font, stroke_width=stroke_width)
            w, h = w + 40, h + 40
            x_offset, y_offset = 20, 20
            
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Fill is completely transparent (Alpha 0), Stroke uses the Theme Color
        draw.text((x_offset, y_offset), text, font=font, fill=(0, 0, 0, 0), stroke_width=stroke_width, stroke_fill=color_name)
        return np.array(img)
    except Exception as e:
        print(f"PIL Text Error: {e}")
        return None

def create_rounded_plate(w, h, radius, opacity=0.85):
    """Draws a white rounded rectangle with transparency"""
    try:
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=(255, 255, 255, int(255 * opacity)))
        return np.array(img)
    except Exception as e:
        print(f"PIL Plate Error: {e}")
        return None
# --------------------------------------------------------

def log_api_quotas():
    if TEST_MODE: return 
    print("\n" + "="*50 + "\n📋 API STATUS CHECK\n" + "="*50)
    try:
        res = requests.get("https://cloud.leonardo.ai/api/rest/v1/me", headers={"authorization": f"Bearer {LEONARDO_API_KEY}"})
        if res.status_code == 200:
            tokens = res.json().get('user_details', [{}])[0].get('user', {}).get('subscriptionTokensRemaining', 'N/A')
            print(f"✅ Leonardo.ai: {tokens} tokens remaining")
    except Exception as e: print(f"❌ Leonardo Error: {e}")
    print("="*50 + "\n")

def find_sfx_file(base_name):
    if not base_name: return None
    try:
        matches = [os.path.join(SFX_DIR, f) for f in os.listdir(SFX_DIR) if f.lower().startswith(base_name.lower())]
        if matches: return random.choice(matches) 
    except Exception: return None
    return None

def fetch_tool_logo(domain):
    if not domain: return None
    valid_extensions = ['.png', '.jpg', '.jpeg']
    for ext in valid_extensions:
        local_path = os.path.join(LOGOS_DIR, f"{domain}{ext}")
        if os.path.exists(local_path):
            return local_path
            
    logo_path_png = os.path.join(LOGOS_DIR, f"{domain}.png")
    try:
        if BRAND_FETCH_API_KEY:
            url = f"https://api.brandfetch.io/v2/brands/{domain}"
            headers = {"Authorization": f"Bearer {BRAND_FETCH_API_KEY}"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                image_url = None
                for logo in data.get('logos', []):
                    for fmt in logo.get('formats', []):
                        if fmt.get('format') == 'png':
                            image_url = fmt.get('src')
                            break
                    if image_url: break
                
                if image_url:
                    img_res = requests.get(image_url, timeout=10)
                    if img_res.status_code == 200:
                        with open(logo_path_png, 'wb') as f: f.write(img_res.content)
                        return logo_path_png

        if BRAND_FETCH_CLIENT_ID:
            cdn_url = f"https://cdn.brandfetch.io/{domain}?c={BRAND_FETCH_CLIENT_ID}"
            img_res = requests.get(cdn_url, timeout=10)
            if img_res.status_code == 200:
                with open(logo_path_png, 'wb') as f: f.write(img_res.content)
                return logo_path_png
    except Exception as e: pass 
    return None

def setup_workspace():
    if not TEST_MODE and os.path.exists(TARGET_DIR): 
        shutil.rmtree(TARGET_DIR)
    os.makedirs(IMAGE_DIR, exist_ok=True); os.makedirs(VOICE_DIR, exist_ok=True)
    os.makedirs(LOGOS_DIR, exist_ok=True)

def generate_murf_voiceover(text, filepath):
    if TEST_MODE and os.path.exists(filepath): return
    url = "https://api.murf.ai/v1/speech/generate"
    payload = {"voiceId": "hi-IN-amit", "text": text, "format": "mp3", "speed": 1.05}
    res = requests.post(url, json=payload, headers={"api-key": MURF_API_KEY, "Content-Type": "application/json"})
    if res.status_code != 200: raise Exception(f"Murf Error: {res.text}")
    with open(filepath, "wb") as f: f.write(requests.get(res.json()["audioFile"]).content)

def generate_leonardo_image(visual_prompt, filename, is_first_scene=False):
    global first_image_id
    path = os.path.abspath(os.path.join(IMAGE_DIR, filename))
    if TEST_MODE and os.path.exists(path): return path

    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {LEONARDO_API_KEY}"}
    payload = {
        "height": 768, "width": 512, "modelId": MODEL_ID,
        "prompt": f"Cinematic, hyper-realistic, 8k resolution, highly detailed, {visual_prompt}",
        "num_images": 1, "alchemy": False, "public": False
    }
    if not is_first_scene and first_image_id:
        payload["init_generation_image_id"] = first_image_id

    res = requests.post(url, json=payload, headers=headers)
    gen_id = res.json()['sdGenerationJob']['generationId']
    for _ in range(30):
        time.sleep(5)
        poll = requests.get(f"{url}/{gen_id}", headers=headers).json().get('generations_by_pk')
        if poll and poll.get('status') == 'COMPLETE':
            img = poll['generated_images'][0]
            if is_first_scene: first_image_id = img['id']
            with open(path, 'wb') as f: f.write(requests.get(img['url']).content)
            return path
    raise Exception(f"Leonardo Timeout for {filename}")

def create_scene(img_path, scene_data, voice_audio, scene_index, theme_color):
    meta = scene_data.get('tech_meta', {})
    pause_dur = meta.get('pause_after', 0.2)
    total_dur = voice_audio.duration + pause_dur
    audio_tracks = [voice_audio]
    
    # The whoosh is anchored exactly to the start (t=0.0) of this new scene
    if scene_index > 0:
        whoosh_path = find_sfx_file("whoosh")
        if whoosh_path:
            transition_sfx = AudioFileClip(whoosh_path).with_volume_scaled(1.5).with_start(0.0)
            audio_tracks.append(transition_sfx)
    
    sfx_path = find_sfx_file(meta.get('sfx'))
    if sfx_path and meta.get('sfx') != "whoosh": 
        sfx_clip = AudioFileClip(sfx_path).with_volume_scaled(1.0).with_start(voice_audio.duration)
        audio_tracks.append(sfx_clip)

    final_audio = CompositeAudioClip(audio_tracks).with_duration(total_dur)

    # 1. Background Image
    main_clip = ImageClip(img_path).with_duration(total_dur).resized(height=HEIGHT)
    if main_clip.w < WIDTH: main_clip = main_clip.resized(width=WIDTH)
    main_clip = main_clip.cropped(x_center=main_clip.w/2, y_center=main_clip.h/2, width=WIDTH, height=HEIGHT)

    def zoom_fn(t):
        if meta.get('zoom_style') == 'pan_right': return 1.1
        return 1.0 + (0.08 * t / total_dur) 
    main_clip = main_clip.resized(zoom_fn)

    # 2. Cinematic Dimmer
    dark_overlay = ColorClip(size=(WIDTH, HEIGHT), color=(0,0,0)).with_opacity(0.4).with_duration(total_dur)
    
    final_clips_array = [main_clip, dark_overlay]
    scale = 0.5 if TEST_MODE else 1.0

    # ==========================================
    # 3. FACT BADGE (Hollow Fill, Solid Theme Color Border via PIL)
    # ==========================================
    if scene_index > 0: 
        fact_num = 6 - scene_index 
        
        raw_str = f"FACT #{fact_num}"
        spaced_text = " ".join(raw_str).replace("  ", "   ") 

        font_size = int(100 * scale)
        stroke_width = int(4 * scale) if not TEST_MODE else 2

        hollow_text_img = create_hollow_text(spaced_text, BOLD_FONT, font_size, stroke_width, theme_color)
        if hollow_text_img is not None:
            badge_clip = ImageClip(hollow_text_img).with_duration(total_dur).with_position(('center', int(200 * scale)))
            final_clips_array.append(badge_clip)

    # ==========================================
    # 4. LOGO PLATE (Rounded Corners via PIL) & DYNAMIC URL
    # ==========================================
    domain = scene_data.get('tool_logo', '').lower()
    if domain:
        logo_path = fetch_tool_logo(domain)
        if logo_path:
            logo_img = ImageClip(logo_path).with_duration(total_dur)
            logo_img = logo_img.resized(height=int(350 * scale))
            if logo_img.w > int(800 * scale): logo_img = logo_img.resized(width=int(800 * scale))
            
            plate_w, plate_h = logo_img.w + int(80 * scale), logo_img.h + int(60 * scale)
            plate_y = int(500 * scale) 
            
            plate_img = create_rounded_plate(plate_w, plate_h, radius=int(40 * scale), opacity=0.85)
            if plate_img is not None:
                white_plate = ImageClip(plate_img).with_duration(total_dur).with_position(('center', plate_y))
                final_clips_array.append(white_plate)
            
            logo_img = logo_img.with_position(('center', plate_y + int(30 * scale))) 
            final_clips_array.append(logo_img)
            
        url_clip = TextClip(
            text=domain.upper(),
            font_size=int(55 * scale),
            color=theme_color, 
            stroke_color='black', stroke_width=int(2.5 * scale),
            font=BOLD_FONT,
            method='caption',
            size=(int(900 * scale), int(120 * scale)), 
            text_align='center'
        ).with_position(('center', int(930 * scale))).with_duration(total_dur)
        final_clips_array.append(url_clip)

    # ==========================================
    # 5. MAIN CAPTION (Dynamic Solid Color Highlight)
    # ==========================================
    caption = scene_data['caption']
    highlight = meta.get('highlight_word', '').upper()
    is_highlight = highlight in caption.upper() and highlight != ""
    
    txt_clip = TextClip(
        text=caption.upper() if is_highlight else caption,
        font_size=int(100 * scale), 
        color=theme_color if is_highlight else 'white', 
        stroke_color='black', stroke_width=int(4.0 * scale), 
        method='caption', font=BOLD_FONT, 
        size=(int(950 * scale), int(450 * scale)), 
        text_align='center'
    ).with_duration(total_dur)

    if scene_index == 0:
        txt_clip = txt_clip.with_position('center')
    else:
        txt_clip = txt_clip.with_position(('center', int(1250 * scale)))

    final_clips_array.append(txt_clip)

    return CompositeVideoClip(final_clips_array).with_audio(final_audio)

async def main():
    try:
        log_api_quotas()
        setup_workspace()
        with open(INPUT_JSON, "r", encoding="utf-8") as f: data = json.load(f)
        
        title_slug = re.sub(r'[^\w\s-]', '', data.get('title', 'reel')).strip().replace(' ', '-')

        current_theme_color = random.choice(THEME_COLORS)
        print(f"\n🎨 Selected Reel Theme Color: {current_theme_color.upper()}")

        pkg = data.get("marketing_package", {})
        metadata_file = os.path.join(TARGET_DIR, f"{title_slug}-metadata.txt")
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(f"{pkg.get('reel_caption', '')}\n\n.\n.\n{pkg.get('hashtags', '')}")

        print(f"🎬 Loaded Tech Script: '{data.get('title', 'Untitled')}'")

        final_clips = []
        for i, scene in enumerate(data['scenes']):
            img_filename = f"{title_slug}_scene_{i}.jpg"
            print(f"--- 🎥 Processing {title_slug} - Scene {i} ---")
            
            v_path = os.path.join(VOICE_DIR, f"voice_{i}.mp3")
            generate_murf_voiceover(scene['hindi_speech'], v_path)
            audio = AudioFileClip(v_path)
            
            img_path = generate_leonardo_image(scene['visual_prompt'], img_filename, i==0)
            
            # --- THE NEW TRANSITION LOGIC ---
            # Create a 0.1s 'Dip to Black' cut between scenes.
            if i > 0:
                black_dip = ColorClip(size=(WIDTH, HEIGHT), color=(0, 0, 0)).with_duration(0.1)
                final_clips.append(black_dip)
            
            # Add FadeIn(0.2) to the scene clip so it gently emerges from the black dip
            scene_clip = create_scene(img_path, scene, audio, i, current_theme_color).with_effects([FadeIn(0.2)])
            final_clips.append(scene_clip)

        output_file = os.path.join(TARGET_DIR, f"{title_slug}{'-TEST' if TEST_MODE else ''}.mp4")
        
        print(f"--- ⚙️ Finalizing Video: {WIDTH}x{HEIGHT}, {RENDER_FPS} FPS ---")
        concatenate_videoclips(final_clips, method="compose").write_videofile(
            output_file, fps=RENDER_FPS, codec="libx264", audio_codec="aac"
        )
        print(f"\n✅ VIRAL AI REEL GENERATED: {output_file}")

    except Exception as e:
        print(f"\n[FAIL FAST] HALTED: {e}"); exit(1)

if __name__ == "__main__":
    asyncio.run(main())