"""
Cutter — uses FFmpeg to cut and stitch video segments
"""

import subprocess
import os
import tempfile


def cut_video(video_path: str, segments: list[dict], output_path: str) -> str:
    """
    Cut a video into selected segments and merge them into one output file.

    Args:
        video_path: Path to the source video
        segments: List of {start, end} dicts with timestamps in seconds
        output_path: Path for the final output video

    Returns:
        Path to the output file
    """
    if not segments:
        raise ValueError("No segments provided to cut.")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # If only one segment, cut directly
    if len(segments) == 1:
        seg = segments[0]
        _cut_single(video_path, seg["start"], seg["end"], output_path)
        return output_path

    # Multiple segments: cut each, then concat
    temp_clips = []
    concat_list_path = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cut each segment
            for i, seg in enumerate(segments):
                clip_path = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
                _cut_single(video_path, seg["start"], seg["end"], clip_path)
                temp_clips.append(clip_path)

            # Write ffmpeg concat list
            concat_list_path = os.path.join(tmpdir, "concat.txt")
            with open(concat_list_path, "w") as f:
                for clip in temp_clips:
                    f.write(f"file '{clip}'\n")

            # Concatenate
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-movflags", "+faststart",
                "-preset", "fast",
                "-crf", "23",
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg concat failed:\n{result.stderr}")

    except Exception as e:
        raise RuntimeError(f"Video cutting failed: {e}")

    return output_path


def _cut_single(video_path: str, start: float, end: float, output_path: str):
    """Cut a single segment from a video file."""
    duration = end - start
    if duration <= 0:
        raise ValueError(f"Invalid segment: start={start}, end={end}")

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "fast",
        "-crf", "23",
        "-avoid_negative_ts", "make_zero",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg cut failed for segment {start}-{end}:\n{result.stderr}")


def get_video_duration(video_path: str) -> float:
    """Get total video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())
