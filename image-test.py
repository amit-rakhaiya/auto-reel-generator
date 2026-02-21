import requests
import time
import os

# --- CONFIGURATION ---
API_KEY = "05976a70-9c98-4d6d-8b59-43f21a1626ce"
SAVE_DIR = r"D:\Amit\dream-works\auto-reel\images"

# Ensure the directory exists
os.makedirs(SAVE_DIR, exist_ok=True)

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {API_KEY}"
}

def generate_image(user_prompt):
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    
    # 2:3 Aspect Ratio for Reels (Standard HD resolution for Fast Mode)
    # 512x768 is the most cost-effective "Fast" resolution for 2:3
    payload = {
        "height": 768,
        "width": 512,
        "modelId": "7b592283-e8a7-4c5a-9ba6-d18c31f258b9", # Lucid Origin
        "prompt": user_prompt,
        "num_images": 1,
        "alchemy": False,      # FALSE = "Fast" mode / Minimum Token Cost
        "photoReal": False,    # FALSE = Minimum Cost
        "presetStyle": "ILLUSTRATION",
        "public": False        # Keep your reel assets private
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()['sdGenerationJob']['generationId']
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def download_ready_image(gen_id):
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}"
    print("Generating your reel asset...")
    
    for _ in range(10): # Try for 50 seconds max
        time.sleep(5)
        response = requests.get(url, headers=headers)
        data = response.json().get('generations_by_pk')
        
        if data and data.get('status') == 'COMPLETE':
            image_url = data['generated_images'][0]['url']
            img_data = requests.get(image_url).content
            
            # Save with timestamp to D: drive
            filename = f"reel_img_{int(time.time())}.jpg"
            filepath = os.path.join(SAVE_DIR, filename)
            
            with open(filepath, 'wb') as f:
                f.write(img_data)
            print(f"✅ Downloaded: {filepath}")
            return
    print("Timeout: Image took too long to generate.")

if __name__ == "__main__":
    prompt = input("Describe the Reel frame: ")
    if prompt.strip():
        gid = generate_image(prompt)
        if gid:
            download_ready_image(gid)