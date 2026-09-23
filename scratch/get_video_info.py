import json
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

video_ids = [
    'u1bJrs-CLG8', # Nirvanaa
    '9R8kKCKVMqQ', # ASTRA 5
    'KxE6J0IZOdk', # Dronanetra
    'oXN3gUaqNHA', # Aetheris / Aeronex
    'NHvcTRt15CY', # Vikram Sharma / Aero Engine
    'F1uMvmKkdms'  # InnovativeX
]

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True
}

results = {}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for vid in video_ids:
        url = f'https://www.youtube.com/watch?v={vid}'
        try:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '')
            uploader = info.get('uploader', '')
            description = info.get('description', '')
            tags = info.get('tags', [])
            duration = info.get('duration', 0)
            
            transcript_text = ""
            try:
                # Try fetching transcript
                transcript = YouTubeTranscriptApi.get_transcript(vid)
                transcript_text = " ".join([entry['text'] for entry in transcript])
            except Exception as te:
                transcript_text = f"No transcript available: {te}"

            results[vid] = {
                'url': url,
                'title': title,
                'uploader': uploader,
                'duration_seconds': duration,
                'tags': tags,
                'description': description,
                'transcript': transcript_text[:2000] # First 2000 chars
            }
            print(f"Done {vid}: {title} by {uploader}")
        except Exception as e:
            print(f"Error {vid}: {e}")

with open('scratch/yt_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Saved to scratch/yt_analysis.json")
