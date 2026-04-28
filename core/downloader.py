import subprocess, os, glob, re

def download_youtube_video(url, output_dir="temp"):
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    cmd = ["yt-dlp", "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "--merge-output-format", "mp4", "-o", output_template, "--no-playlist", "--quiet", "--progress", url]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError("yt-dlp failed. Run: pip install yt-dlp")
    mp4_files = glob.glob(os.path.join(output_dir, "*.mp4"))
    if not mp4_files:
        raise FileNotFoundError("Downloaded file not found.")
    return max(mp4_files, key=os.path.getmtime)
