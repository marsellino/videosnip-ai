import whisper
import os
import json


def transcribe_video(video_path, model_size="base"):
    # Check for cached transcript first
    cached = _get_cache_path(video_path)
    if os.path.exists(cached):
        print("    Found cached transcript, skipping Whisper...")
        with open(cached, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"    Loading Whisper '{model_size}' model...")
    model = whisper.load_model(model_size)
    print(f"    Transcribing {os.path.basename(video_path)}...")
    result = model.transcribe(video_path, verbose=False)

    transcript = {
        "text": result["text"].strip(),
        "segments": [
            {
                "id": s["id"],
                "start": round(s["start"], 2),
                "end": round(s["end"], 2),
                "text": s["text"].strip(),
            }
            for s in result["segments"]
        ],
        "language": result.get("language", "en"),
    }

    # Save to cache
    with open(cached, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2)
    print(f"    Transcript cached: {os.path.basename(cached)}")

    return transcript


def _get_cache_path(video_path):
    base = os.path.splitext(video_path)[0]
    return base + "_transcript.json"


def format_transcript_for_llm(transcript, max_chars=12000):
    lines = []
    for seg in transcript["segments"]:
        m, s = int(seg["start"] // 60), int(seg["start"] % 60)
        lines.append(f"[{m:02d}:{s:02d}] {seg['text']}")
    full = "\n".join(lines)
    return full[:max_chars] + "\n...[truncated]" if len(full) > max_chars else full