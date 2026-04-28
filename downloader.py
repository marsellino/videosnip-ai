"""
Downloader — fetches YouTube videos using yt-dlp
"""

import subprocess
import os
import glob
import re


def sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-_.]', '_', name)[:60]


def download_youtube_video(url: str, output_dir: str = "temp") -> str:
    """
    Download a YouTube video using yt-dlp.
    Returns the path to the downloaded file.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",
        "--quiet",
        "--progress",
        url
    ]

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed. Make sure yt-dlp is installed: pip install yt-dlp\n"
            f"Also ensure ffmpeg is installed on your system."
        )

    # Find the downloaded file
    mp4_files = glob.glob(os.path.join(output_dir, "*.mp4"))
    if not mp4_files:
        raise FileNotFoundError("Downloaded file not found. yt-dlp may have used a different format.")

    # Return the most recently modified file
    return max(mp4_files, key=os.path.getmtime)
