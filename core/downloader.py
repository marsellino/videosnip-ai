import subprocess, os, glob

def download_youtube_video(url, output_dir="temp"):
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    # Try different strategies in order until one works
    strategies = [
        # Strategy 1: best mp4 with edge cookies
        [
            "yt-dlp",
            "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--cookies-from-browser", "edge",
            "-o", output_template,
            "--no-playlist", "--quiet", "--progress",
            url
        ],
        # Strategy 2: any best format, let yt-dlp decide
        [
            "yt-dlp",
            "-f", "best[height<=720]/best",
            "--cookies-from-browser", "edge",
            "-o", output_template,
            "--no-playlist", "--quiet", "--progress",
            url
        ],
        # Strategy 3: no cookies, just download whatever is available
        [
            "yt-dlp",
            "-f", "best",
            "--no-check-certificates",
            "-o", output_template,
            "--no-playlist", "--quiet", "--progress",
            url
        ],
    ]

    last_error = ""
    for i, cmd in enumerate(strategies, 1):
        print(f"    Trying strategy {i}/{len(strategies)}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            break
        last_error = result.stderr
        print(f"    Strategy {i} failed, trying next...")
    else:
        raise RuntimeError("All download strategies failed:\n" + last_error)

    # Find the downloaded file (could be .mp4 or .webm)
    for ext in ["mp4", "webm", "mkv"]:
        files = glob.glob(os.path.join(output_dir, f"*.{ext}"))
        if files:
            return max(files, key=os.path.getmtime)

    raise FileNotFoundError("Downloaded file not found.")