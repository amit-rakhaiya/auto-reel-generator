import os
import subprocess
# This package comes with MoviePy and has a bundled FFmpeg executable!
import imageio_ffmpeg 

SFX_DIR = "sfx"

def clean_audio_files():
    print("🧹 Starting SFX Metadata Cleaner...")
    
    # Locate the hidden FFmpeg installed with MoviePy
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    for filename in os.listdir(SFX_DIR):
        if filename.lower().endswith((".wav", ".mp3")):
            filepath = os.path.join(SFX_DIR, filename)
            temp_filepath = os.path.join(SFX_DIR, "temp_" + filename)
            
            print(f"Processing: {filename}")
            
            # Use the absolute path to ffmpeg
            command = [
                ffmpeg_path, "-y", "-i", filepath, 
                "-map_metadata", "-1", "-map_chapters", "-1", 
                temp_filepath
            ]
            
            try:
                # Run ffmpeg silently
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                # Replace the original file with the clean one
                os.replace(temp_filepath, filepath)
                print(f"  ✅ Cleaned and replaced!")
            except Exception as e:
                print(f"  ❌ Failed to clean {filename}: {e}")
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)

    print("\n🎉 All SFX files are clean! You can now run main.py safely.")

if __name__ == "__main__":
    clean_audio_files()