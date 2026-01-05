import requests
import random
import json
import os
import subprocess
from threading import Thread

# =============== ENV =================
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# =============== CONSTANTS =================
ANIMALS = ["dog", "cat", "lion", "bird", "horse", "elephant"]

HASHTAGS = [
    "#animals", "#wildlife", "#nature",
    "#animalvideos", "#naturelovers",
    "#animalworld", "#earthlife", "#reels"
]

USED_FILE = "used_videos.json"

# =============== HELPERS =================
def load_used():
    if not os.path.exists(USED_FILE):
        return []
    return json.load(open(USED_FILE))

def save_used(video_id):
    used = load_used()
    used.append(video_id)
    json.dump(list(set(used)), open(USED_FILE, "w"))

# =============== 1. FETCH UNIQUE PIXABAY VIDEO =================
def fetch_video():
    used_ids = load_used()
    random.shuffle(ANIMALS)

    for animal in ANIMALS:
        url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={animal}&per_page=20"
        data = requests.get(url).json()

        for hit in data.get("hits", []):
            if hit["id"] not in used_ids:
                video_url = hit["videos"]["large"]["url"]

                with open("video.mp4", "wb") as f:
                    f.write(requests.get(video_url).content)

                save_used(hit["id"])
                print(f"✅ New video used: {hit['id']}")
                return

    raise Exception("❌ No new Pixabay videos found")

# =============== 2. FETCH FREESOUND MUSIC =================
def fetch_music():
    search_url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": "nature",
        "filter": "license:\"Creative Commons 0\"",
        "token": FREESOUND_KEY
    }
    sounds = requests.get(search_url, params=params).json()["results"]
    sound = random.choice(sounds)

    sound_data = requests.get(
        f"https://freesound.org/apiv2/sounds/{sound['id']}/",
        params={"token": FREESOUND_KEY}
    ).json()

    audio_url = sound_data["previews"]["preview-hq-mp3"]

    with open("music.mp3", "wb") as f:
        f.write(requests.get(audio_url).content)

# =============== 3. MAKE REEL / SHORT =================
def make_reel():
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", "video.mp4",
        "-i", "music.mp3",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=cover",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        "final_reel.mp4"
    ], check=True)

# =============== 4. RANDOM CAPTION =================
def build_caption():
    title = random.choice(json.load(open("titles.json")))
    caption = random.choice(json.load(open("captions.json")))
    return f"""{title}

{caption}

{' '.join(HASHTAGS)}
"""

# =============== 5. UPLOAD CATBOX =================
def upload_catbox():
    res = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": open("final_reel.mp4", "rb")}
    )
    return res.text.strip()

# =============== 6. SEND TELEGRAM =================
def send_telegram(video_url, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
    requests.post(url, data={
        "chat_id": TELEGRAM_CHAT,
        "video": video_url,
        "caption": text
    })

# =============== 7. SEND WEBHOOK =================
def send_webhook(video_url, text):
    requests.post(WEBHOOK_URL, json={
        "video_url": video_url,
        "caption": text
    })

# =============== MAIN =================
def main():
    fetch_video()
    fetch_music()
    make_reel()

    caption = build_caption()
    video_url = upload_catbox()

    Thread(target=send_telegram, args=(video_url, caption)).start()
    Thread(target=send_webhook, args=(video_url, caption)).start()

if __name__ == "__main__":
    main()
          
