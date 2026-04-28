import subprocess, os, tempfile

def cut_video(video_path, segments, output_path):
    if not segments:
        raise ValueError("No segments provided.")
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    if len(segments) == 1:
        _cut_single(video_path, segments[0]["start"], segments[0]["end"], output_path)
        return output_path
    with tempfile.TemporaryDirectory() as tmpdir:
        clips = []
        for i, seg in enumerate(segments):
            p = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
            _cut_single(video_path, seg["start"], seg["end"], p)
            clips.append(p)
        concat = os.path.join(tmpdir, "concat.txt")
        with open(concat, "w") as f:
            for c in clips: f.write(f"file '{c}'\n")
        cmd = ["ffmpeg","-y","-f","concat","-safe","0","-i",concat,"-c:v","libx264","-c:a","aac","-movflags","+faststart","-preset","fast","-crf","23",output_path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError(f"FFmpeg failed: {r.stderr}")
    return output_path

def _cut_single(video_path, start, end, output_path):
    cmd = ["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(end-start),"-c:v","libx264","-c:a","aac","-preset","fast","-crf","23","-avoid_negative_ts","make_zero",output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"FFmpeg cut failed: {r.stderr}")
