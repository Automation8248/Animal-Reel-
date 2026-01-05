import requests
import random
import json
import os
import subprocess
from threading import Thread

# ================= ENV =================
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ================= CONSTANTS =================
ANIMALS = ["dog", "cat", "lion", "bird", "horse", "elephant"]

HASHTAGS = [
    "#animals", "#wildlife", "#nature",
    "#animalvideos", "#naturelovers",
    "#animalworld", "#earthlife", "#reels"
]

DEFAULT_TITLES = [
    "Nature at its best 🐾",
    "Wildlife moments you’ll love 🦁",
    "Animals living their best life 🐶",
    "Pure nature vibes 🌿",
    "Life in the wild 🦊"
]

DEFAULT_CAPTIONS = [
    "Nature never fails to amaze us 💚",
    "Wildlife is pure magic ✨",
    "Peaceful moments from nature 🍃",
    "Animals remind us how beautiful life is 🐾"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USED_FILE = os.path.join(BASE_DIR, "used_videos.json")

# ================= HELPERS =================
def load_used():
    if not os.path.exists(USED_FILE):
        return []
    return json.load(open(USED_FILE))

def save_used(video_id):
    used = load_used()
    used.append(video_id)
    json.dump(list(set(used)), open(USED_FILE, "w"))

# ================= PIXABAY UNIQUE VIDEO =================
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

# ================= FREESOUND MUSIC =================
def fetch_music():
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": "nature",
        "filter": "license:\"Creative Commons 0\"",
        "token": FREESOUND_KEY
    }

    sounds = requests.get(url, params=params).json()["results"]
    sound = random.choice(sounds)

    info = requests.get(
        f"https://freesound.org/apiv2/sounds/{sound['id']}/",
        params={"token": FREESOUND_KEY}
    ).json()

    audio_url = info["previews"]["preview-hq-mp3"]

    with open("music.mp3", "wb") as f:
        f.write(requests.get(audio_url).content)

# ================= MAKE REEL =================
def make_reel():
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", "video.mp4",
        "-i", "music.mp3",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "final_reel.mp4"
    ], check=True)

# ================= SAFE CAPTION BUILDER =================
def build_caption():
    titles = DEFAULT_TITLES
    captions = DEFAULT_CAPTIONS

    titles_path = os.path.join(BASE_DIR, "titles.json")
    captions_path = os.path.join(BASE_DIR, "captions.json")

    if os.path.exists(titles_path):
        titles = json.load(open(titles_path))
    if os.path.exists(captions_path):
        captions = json.load(open(captions_path))

    return f"""{random.choice(titles)}

{random.choice(captions)}

{' '.join(HASHTAGS)}
"""

# ================= CATBOX =================
def upload_catbox():
    res = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": open("final_reel.mp4", "rb")}
    )
    return res.text.strip()

# ================= SEND =================
def send_telegram(video_url, text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo",
        data={"chat_id": TELEGRAM_CHAT, "video": video_url, "caption": text}
    )

def send_webhook(video_url, text):
    requests.post(WEBHOOK_URL, json={"video_url": video_url, "caption": text})

# ================= MAIN =================
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

