"""
Transcriber — converts video audio to timestamped transcript using OpenAI Whisper (local)
"""

import whisper
import os


def transcribe_video(video_path: str, model_size: str = "base") -> dict:
    """
    Transcribe a video file using Whisper running locally.

    Args:
        video_path: Path to the video file
        model_size: Whisper model size — tiny, base, small, medium, large
                    (larger = more accurate but slower)
                    Recommended: 'base' for speed, 'small' for quality

    Returns:
        dict with keys:
            - text: full transcript string
            - segments: list of {id, start, end, text}
            - language: detected language
    """
    print(f"    Loading Whisper '{model_size}' model...")
    model = whisper.load_model(model_size)

    print(f"    Transcribing {os.path.basename(video_path)}...")
    result = model.transcribe(
        video_path,
        verbose=False,
        word_timestamps=False,
    )

    # Normalize segments
    segments = [
        {
            "id": seg["id"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        }
        for seg in result["segments"]
    ]

    return {
        "text": result["text"].strip(),
        "segments": segments,
        "language": result.get("language", "en"),
    }


def format_transcript_for_llm(transcript: dict, max_chars: int = 12000) -> str:
    """
    Format the transcript into a clean string for the LLM prompt.
    Includes timestamps in [MM:SS] format.
    """
    lines = []
    for seg in transcript["segments"]:
        start = seg["start"]
        minutes = int(start // 60)
        seconds = int(start % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg['text']}")

    full = "\n".join(lines)

    # Truncate if too long (very long videos)
    if len(full) > max_chars:
        full = full[:max_chars] + "\n... [transcript truncated]"

    return full
