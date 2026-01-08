import os
import requests
import random
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips

# Configuration from environment variables
PIXABAY_KEY = os.getenv("PIXABAY_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def get_pixabay_video():
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=animals&per_page=10&video_type=film"
    response = requests.get(url).json()
    video_data = random.choice(response['hits'])
    # Pick the 'small' or 'medium' version for faster processing
    video_url = video_data['videos']['medium']['url']
    with open("raw_video.mp4", "wb") as f:
        f.write(requests.get(video_url).content)
    return "raw_video.mp4"

def get_freesound_audio():
    url = f"https://freesound.org/apiv2/search/text/?query=nature&token={FREESOUND_KEY}&fields=id,previews"
    response = requests.get(url).json()
    audio_data = random.choice(response['results'])
    audio_url = audio_data['previews']['preview-hq-mp3']
    with open("raw_audio.mp3", "wb") as f:
        f.write(requests.get(audio_url).content)
    return "raw_audio.mp3"

def merge_video_audio(video_path, audio_path):
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)
    
    # Loop audio if it's shorter than video
    if audio.duration < video.duration:
        audio = concatenate_audioclips([audio] * int(video.duration / audio.duration + 1))
    
    final_audio = audio.set_duration(video.duration)
    final_video = video.set_audio(final_audio)
    
    output_file = "final_short.mp4"
    # Preset 'ultrafast' helps GitHub Actions process quickly
    final_video.write_videofile(output_file, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
    return output_file

def upload_to_catbox(file_path):
    url = "https://catbox.moe/user/api.php"
    files = {'fileToUpload': open(file_path, 'rb')}
    data = {'reqtype': 'fileupload'}
    response = requests.post(url, data=data, files=files)
    return response.text # Returns the URL

def send_to_telegram(video_url, file_path):
    # Sending the link via Catbox
    msg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(msg_url, data={"chat_id": TELEGRAM_CHAT_ID, "text": f"New Wildlife Short: {video_url}"})
    
    # Optional: Send the actual video file as well
    video_url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(file_path, 'rb') as v:
        requests.post(video_url_api, data={"chat_id": TELEGRAM_CHAT_ID}, files={"video": v})

def send_to_webhook(video_url):
    requests.post(WEBHOOK_URL, json={"content": f"New Short Video Created: {video_url}"})

if __name__ == "__main__":
    print("Fetching media...")
    v_path = get_pixabay_video()
    a_path = get_freesound_audio()
    
    print("Merging...")
    final_path = merge_video_audio(v_path, a_path)
    
    print("Uploading to Catbox...")
    catbox_url = upload_to_catbox(final_path)
    
    print(f"Posting to Telegram and Webhook: {catbox_url}")
    send_to_telegram(catbox_url, final_path)
    send_to_webhook(catbox_url)
