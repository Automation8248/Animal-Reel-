import requests
import random
import json
import os
import subprocess
import time
from threading import Thread

# ================= TIME LIMIT =================
START_TIME = time.time()
MAX_RUNTIME = 30  # seconds

def check_timeout():
    if time.time() - START_TIME > MAX_RUNTIME:
        print("⏰ 30 second limit reached. Exiting safely.")
        exit(0)

# ================= ENV =================
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ================= CONSTANTS =================
ANIMALS = ["dog", "cat", "lion", "horse", "elephant", "tiger", "cow", "goat"]

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

def video_hash(url):
    return str(abs(hash(url)))

# ================= PIXABAY UNIQUE VIDEO =================
def fetch_video():
    check_timeout()
    used_ids = load_used()
    random.shuffle(ANIMALS)

    for animal in ANIMALS:
        check_timeout()
        url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={animal}&per_page=10&safesearch=true"
        data = requests.get(url, timeout=5).json()

        for hit in data.get("hits", []):
            check_timeout()

            video_url = hit["videos"]["large"]["url"]
            vid_hash = video_hash(video_url)

            if vid_hash in used_ids:
                continue

            if "bird" in hit.get("tags", "").lower():
                continue

            duration = hit.get("duration", 0)
            if duration < 8 or duration > 10:
                continue

            with open("video.mp4", "wb") as f:
                f.write(requests.get(video_url, timeout=5).content)

            save_used(vid_hash)
            print(f"✅ Unique animal video used: {vid_hash}")
            return

    raise Exception("❌ No valid animal video found")

# ================= FREESOUND MUSIC =================
def fetch_music():
    check_timeout()
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": "nature",
        "filter": "license:\"Creative Commons 0\"",
        "token": FREESOUND_KEY
    }

    sounds = requests.get(url, params=params, timeout=5).json()["results"]
    sound = random.choice(sounds)

    info = requests.get(
        f"https://freesound.org/apiv2/sounds/{sound['id']}/",
        params={"token": FREESOUND_KEY},
        timeout=5
    ).json()

    audio_url = info["previews"]["preview-hq-mp3"]

    with open("music.mp3", "wb") as f:
        f.write(requests.get(audio_url, timeout=5).content)

# ================= MAKE REEL (FAST) =================
def make_reel():
    check_timeout()
    start = random.randint(0, 2)
    duration = random.randint(8, 10)

    subprocess.run([
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", "video.mp4",
        "-i", "music.mp3",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "final_reel.mp4"
    ], check=True)

# ================= CAPTION =================
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
    check_timeout()
    res = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": open("final_reel.mp4", "rb")},
        timeout=5
    )
    return res.text.strip()

# ================= SEND =================
def send_telegram(video_url, text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo",
        data={"chat_id": TELEGRAM_CHAT, "video": video_url, "caption": text},
        timeout=5
    )

def send_webhook(video_url, text):
    requests.post(
        WEBHOOK_URL,
        json={"video_url": video_url, "caption": text},
        timeout=5
    )

# ================= MAIN =================
def main():
    check_timeout()
    fetch_video()

    check_timeout()
    fetch_music()

    check_timeout()
    make_reel()

    caption = build_caption()
    video_url = upload_catbox()

    Thread(target=send_telegram, args=(video_url, caption)).start()
    Thread(target=send_webhook, args=(video_url, caption)).start()

if __name__ == "__main__":
    main()

