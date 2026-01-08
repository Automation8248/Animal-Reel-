import os
import requests
import random
import sys
from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips, vfx

# API Keys
PIXABAY_KEY = os.getenv("PIXABAY_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def get_dynamic_metadata():
    """AI se Title, Caption aur 8 Hashtags lena"""
    print("Generating AI Metadata...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    
    prompt = "Generate a catchy title, 1-sentence emotional caption, and exactly 8 trending hashtags for a vertical animal short. Format: Title | Caption | Hashtags"
    
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload).json()
        content = response['choices'][0]['message']['content']
        parts = content.split('|')
        return {"title": parts[0].strip(), "caption": parts[1].strip(), "hashtags": parts[2].strip()}
    except:
        return {"title": "Wild Beauty", "caption": "Nature's wonders never cease to amaze.", "hashtags": "#animals #wildlife #shorts #nature #viral #trending #reels #explore"}

def get_pixabay_video():
    print("Fetching Vertical Video from Pixabay...")
    # 'orientation=vertical' specifically YouTube Shorts ke liye
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=animals&orientation=vertical&per_page=30"
    data = requests.get(url).json()
    
    if not data['hits']:
        print("No vertical videos found!")
        sys.exit(1)
        
    video_url = random.choice(data['hits'])['videos']['medium']['url']
    with open("raw_video.mp4", "wb") as f:
        f.write(requests.get(video_url).content)
    return "raw_video.mp4"

def get_freesound_audio():
    print("Fetching Nature Audio...")
    url = f"https://freesound.org/apiv2/search/text/?query=nature&token={FREESOUND_KEY}&fields=id,previews"
    data = requests.get(url).json()
    audio_url = random.choice(data['results'])['previews']['preview-hq-mp3']
    with open("raw_audio.mp3", "wb") as f:
        f.write(requests.get(audio_url).content)
    return "raw_audio.mp3"

def process_shorts_video(v_path, a_path):
    print("Converting to 9:16 Shorts format (7-8 seconds)...")
    video = VideoFileClip(v_path)
    audio = AudioFileClip(a_path)
    
    # 1. Duration Lock (7.5 seconds)
    duration = 7.5
    video = video.subclipped(0, min(video.duration, duration))
    
    # 2. Resize and Crop for 9:16 (YouTube Shorts Standard)
    # Target: 1080x1920
    w, h = video.size
    target_ratio = 9/16
    current_ratio = w/h
    
    if current_ratio > target_ratio:
        # Video zyada wide hai, sides crop karo
        new_w = h * target_ratio
        video = video.cropped(x1=(w-new_w)/2, x2=(w+new_w)/2)
    elif current_ratio < target_ratio:
        # Video zyada patla hai, top/bottom crop karo
        new_h = w / target_ratio
        video = video.cropped(y1=(h-new_h)/2, y2=(h+new_h)/2)
    
    final_video = video.resized(height=1920) # Standarize to 1080p height
    
    # 3. Audio Setup
    if audio.duration < duration:
        audio = concatenate_audioclips([audio] * 2)
    final_audio = audio.with_duration(duration)
    
    final_output = final_video.with_audio(final_audio)
    output_name = "yt_short_final.mp4"
    final_output.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=30, preset="ultrafast")
    return output_name

def upload_to_catbox(file_path):
    url = "https://catbox.moe/user/api.php"
    with open(file_path, 'rb') as f:
        response = requests.post(url, data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
    return response.text

def post_content(video_url, file_path, meta):
    # Telegram Caption with AI Text
    full_caption = f"🎥 *{meta['title']}*\n\n{meta['caption']}\n\n{meta['hashtags']}"
    
    # Send to Telegram
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(file_path, 'rb') as v:
        requests.post(tg_url, data={
            "chat_id": TELEGRAM_CHAT_ID, 
            "caption": full_caption, 
            "parse_mode": "Markdown"
        }, files={"video": v})
    
    # Send to Webhook
    if WEBHOOK_URL:
        payload = {
            "video_url": video_url,
            "title": meta['title'],
            "caption": meta['caption'],
            "hashtags": meta['hashtags'],
            "format": "YouTube Shorts (9:16)"
        }
        requests.post(WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    meta = get_dynamic_metadata()
    v_raw = get_pixabay_video()
    a_raw = get_freesound_audio()
    final_v = process_shorts_video(v_raw, a_raw)
    catbox_link = upload_to_catbox(final_v)
    post_content(catbox_link, final_v, meta)
    print(f"Shorts Uploaded: {catbox_link}")
