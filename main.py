import os
import requests
import random
import sys
from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips

# GitHub Secrets se keys lena
PIXABAY_KEY = os.getenv("PIXABAY_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def get_pixabay_video():
    print("Fetching video from Pixabay...")
    if not PIXABAY_KEY:
        print("ERROR: PIXABAY_KEY is missing! Check GitHub Secrets.")
        sys.exit(1)

    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=animals&per_page=20&video_type=film"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Pixabay API Error: Status {response.status_code}")
        print(f"Response Content: {response.text}")
        sys.exit(1)

    try:
        data = response.json()
        if not data.get('hits'):
            print("No videos found for the query.")
            sys.exit(1)
        video_data = random.choice(data['hits'])
        video_url = video_data['videos']['medium']['url']
        
        print(f"Downloading video: {video_url}")
        with open("raw_video.mp4", "wb") as f:
            f.write(requests.get(video_url).content)
        return "raw_video.mp4"
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        print(f"Actual Response: {response.text}")
        sys.exit(1)

def get_freesound_audio():
    print("Fetching audio from Freesound...")
    if not FREESOUND_KEY:
        print("ERROR: FREESOUND_KEY is missing!")
        sys.exit(1)

    url = f"https://freesound.org/apiv2/search/text/?query=nature&token={FREESOUND_KEY}&fields=id,previews"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        audio_data = random.choice(data['results'])
        audio_url = audio_data['previews']['preview-hq-mp3']
        with open("raw_audio.mp3", "wb") as f:
            f.write(requests.get(audio_url).content)
        return "raw_audio.mp3"
    else:
        print(f"Freesound Error: {response.status_code}")
        sys.exit(1)

def merge_video_audio(v_path, a_path):
    print("Merging video and audio...")
    video = VideoFileClip(v_path)
    audio = AudioFileClip(a_path)
    
    if audio.duration < video.duration:
        audio = concatenate_audioclips([audio] * int(video.duration / audio.duration + 1))
    
    final_audio = audio.with_duration(video.duration)
    final_video = video.with_audio(final_audio)
    
    output = "final_output.mp4"
    final_video.write_videofile(output, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
    return output

def upload_to_catbox(file_path):
    print("Uploading to Catbox...")
    url = "https://catbox.moe/user/api.php"
    with open(file_path, 'rb') as f:
        response = requests.post(url, data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
    return response.text

def post_to_socials(catbox_url, file_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram keys missing. Skipping post.")
        return

    # Send Link
    tg_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(tg_msg, data={"chat_id": TELEGRAM_CHAT_ID, "text": f"New Short: {catbox_url}"})
    
    # Send File
    tg_vid = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(file_path, 'rb') as v:
        requests.post(tg_vid, data={"chat_id": TELEGRAM_CHAT_ID}, files={"video": v})
    
    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={"content": f"New Video: {catbox_url}"})

if __name__ == "__main__":
    v = get_pixabay_video()
    a = get_freesound_audio()
    out = merge_video_audio(v, a)
    link = upload_to_catbox(out)
    post_to_socials(link, out)
    print(f"Successfully posted: {link}")
