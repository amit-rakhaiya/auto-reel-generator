import requests

API_KEY = "ap2_24ed601e-c810-4dc8-8aa7-6f0ef7277885"

url = "https://api.murf.ai/v1/speech/generate"

text = (
    "Kya aapko bhi lagta hai ki leave mangna ek crime hai? "
    "Chaliye corporate ki asli language samajhte hain. "
    "Jab aap kehte hain: Sir, family function ke liye chutti chahiye thi. "
    "Toh uska asli matlab hota hai: Sir, burnout ho chuka hoon, bas sona chahta hoon."
)

payload = {
    "voiceId": "hi-IN-amit",
    "text": text,
    "format": "mp3",
    "speed": 1.09,
    "pitch": 0
}

headers = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

# Step 1 — generate voice
response = requests.post(url, json=payload, headers=headers)
data = response.json()

# Step 2 — download real mp3
audio_url = data["audioFile"]

audio_data = requests.get(audio_url).content

with open("murf_bollywood.mp3", "wb") as f:
    f.write(audio_data)

print("🎧 Murf Bollywood voice downloaded & playable!")
