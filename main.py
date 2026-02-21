import asyncio
import os
import requests
import json
import re
import time
import shutil
import warnings
import random
import numpy as np
from datetime import datetime
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.video.fx import FadeIn

# Load the secret keys from the .env file
load_dotenv() 

# --- CONFIGURATION ---
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")

USER_PATH = r"C:\Users\Amit.Rakhaiya\AppData\Local\Microsoft\Windows\Fonts"
FONT_PATH = os.path.join(USER_PATH, "NotoSans-VariableFont_wdth,wght.ttf")
INPUT_JSON = "script.json"

TARGET_DIR = "target"
IMAGE_DIR = os.path.join(TARGET_DIR, "images")
VOICE_DIR = os.path.join(TARGET_DIR, "voice-over")
SFX_DIR = "sfx"

WIDTH, HEIGHT = 1080, 1920 
MODEL_ID = "7b592283-e8a7-4c5a-9ba6-d18c31f258b9" 
STYLE_UUID_3D = "debdf72a-91a4-467b-bf61-cc02bdeb69c6"
first_image_id = None

def log_api_quotas():
    """Fetches and displays remaining Leonardo tokens cleanly."""
    print("\n" + "="*50 + "\n📋 API STATUS CHECK\n" + "="*50)
    try:
        res = requests.get("https://cloud.leonardo.ai/api/rest/v1/me", 
                           headers={"authorization": f"Bearer {LEONARDO_API_KEY}"})
        if res.status_code == 200:
            tokens = res.json().get('user_details', [{}])[0].get('user', {}).get('subscriptionTokensRemaining', 'N/A')
            print(f"✅ Leonardo.ai: {tokens} tokens remaining")
        else: print(f"⚠️ Leonardo Status: {res.status_code}")
    except Exception as e: print(f"❌ Leonardo Error: {e}")
    print("="*50 + "\n")

def find_sfx_file(base_name):
    if not base_name: return None
    try:
        matches = []
        for file in os.listdir(SFX_DIR):
            if file.lower().startswith(base_name.lower()):
                matches.append(os.path.join(SFX_DIR, file))
        if matches:
            return random.choice(matches) 
    except Exception: return None
    return None

def setup_workspace():
    if os.path.exists(TARGET_DIR): shutil.rmtree(TARGET_DIR)
    os.makedirs(IMAGE_DIR, exist_ok=True); os.makedirs(VOICE_DIR, exist_ok=True)

def generate_murf_voiceover(text, filepath):
    url = "https://api.murf.ai/v1/speech/generate"
    payload = {"voiceId": "hi-IN-amit", "text": text, "format": "mp3", "speed": 1.12}
    res = requests.post(url, json=payload, headers={"api-key": MURF_API_KEY, "Content-Type": "application/json"})
    if res.status_code != 200: raise Exception(f"Murf Error: {res.text}")
    with open(filepath, "wb") as f: f.write(requests.get(res.json()["audioFile"]).content)

def generate_leonardo_image(visual_prompt, filename, is_first_scene=False):
    global first_image_id
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Bearer {LEONARDO_API_KEY}"}
    payload = {
        "height": 768, "width": 512, "modelId": MODEL_ID,
        "prompt": f"Indian professional character, {visual_prompt}, 3D Pixar style, cinematic office lighting",
        "num_images": 1, "alchemy": False, "styleUUID": STYLE_UUID_3D, "public": False
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
            path = os.path.abspath(os.path.join(IMAGE_DIR, filename))
            with open(path, 'wb') as f: f.write(requests.get(img['url']).content)
            return path
    raise Exception(f"Leonardo Timeout for {filename}")

def create_scene(img_path, scene_data, voice_audio):
    meta = scene_data.get('comedy_meta', {})
    beat_dur = meta.get('punchline_beat', 0.2)
    
    audio_tracks = [voice_audio]
    current_time = voice_audio.duration + beat_dur
    
    sfx_path = find_sfx_file(meta.get('sfx'))
    if sfx_path:
        sfx_clip = AudioFileClip(sfx_path).with_start(current_time)
        audio_tracks.append(sfx_clip)
        current_time += sfx_clip.duration
    
    laugh_intensity = meta.get('laugh_intensity')
    if laugh_intensity:
        laugh_path = find_sfx_file(f"laugh_{laugh_intensity}")
        if laugh_path:
            # Fixed for MoviePy 2.0
            laugh_clip = AudioFileClip(laugh_path).with_volume_scaled(0.7).with_start(current_time)
            audio_tracks.append(laugh_clip)
            current_time += (laugh_clip.duration * 0.5)

    final_audio = CompositeAudioClip(audio_tracks).with_duration(current_time)
    total_dur = current_time

    main_clip = ImageClip(img_path).with_duration(total_dur).resized(height=HEIGHT)
    if main_clip.w < WIDTH: main_clip = main_clip.resized(width=WIDTH)
    main_clip = main_clip.cropped(x_center=main_clip.w/2, y_center=main_clip.h/2, width=WIDTH, height=HEIGHT)

    def zoom_fn(t):
        if meta.get('zoom_style') == 'snap' and t > voice_audio.duration:
            return 1.15 
        return 1.0 + (0.04 * t / total_dur)

    main_clip = main_clip.resized(zoom_fn)

    caption = scene_data['caption']
    highlight = meta.get('highlight_word', '').upper()
    is_punchline = highlight in caption.upper() and highlight != ""
    
    txt_clip = TextClip(
        text=caption.upper() if is_punchline else caption,
        font_size=55 if is_punchline else 48,
        color='yellow' if is_punchline else 'white',
        stroke_color='black', stroke_width=2.0,
        method='caption', font=FONT_PATH, size=(850, 450), text_align='center'
    ).with_duration(total_dur).with_position(('center', 1300))

    return CompositeVideoClip([main_clip, txt_clip]).with_audio(final_audio)

async def main():
    try:
        log_api_quotas()
        setup_workspace()
        with open(INPUT_JSON, "r", encoding="utf-8") as f: data = json.load(f)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        title_slug = re.sub(r'[^\w\s-]', '', data.get('title', 'reel')).strip().replace(' ', '-')

        # Pre-execution logging
        print(f"🎬 Loaded Script: '{data.get('title', 'Untitled')}'")
        print(f"📁 Project Slug: {title_slug}")
        print(f"📦 Total Scenes: {len(data['scenes'])}\n")

        final_clips = []
        for i, scene in enumerate(data['scenes']):
            img_filename = f"title_scene_{i}.jpg" if i == 0 else f"scene_{i}.jpg"
            scene_name_clean = img_filename.replace('.jpg', '')
            
            # Rich Scene Logging
            print(f"--- 🎥 Processing {title_slug}_{scene_name_clean} ---")
            
            print("   🎙️ Generating voiceover...")
            v_path = os.path.join(VOICE_DIR, f"voice_{i}.mp3")
            generate_murf_voiceover(scene['hindi_speech'], v_path)
            audio = AudioFileClip(v_path)
            
            print(f"   🖼️ Generating image via Leonardo.ai ({img_filename})...")
            img_path = generate_leonardo_image(scene['visual_prompt'], img_filename, i==0)
            
            meta = scene.get('comedy_meta', {})
            sfx_log = meta.get('sfx', 'none') or 'none'
            laugh_log = meta.get('laugh_intensity', 'none') or 'none'
            
            print(f"   🎬 Compositing scene (SFX: {sfx_log}, Laugh: {laugh_log})...")
            final_clips.append(create_scene(img_path, scene, audio).with_effects([FadeIn(0.3)]))
            print("   ✅ Scene composited successfully.\n")

        output_file = os.path.join(TARGET_DIR, f"{title_slug}-{timestamp}.mp4")
        
        print("--- ⚙️ Finalizing Video: 1080p, 24 FPS, 1Mbps ---")
        concatenate_videoclips(final_clips, method="compose").write_videofile(
            output_file, fps=24, codec="libx264", bitrate="1000k"
        )
        print(f"\n✅ REEL GENERATED SUCCESSFULLY: {output_file}")

    except Exception as e:
        print(f"\n[FAIL FAST] HALTED: {e}"); exit(1)

if __name__ == "__main__":
    asyncio.run(main())