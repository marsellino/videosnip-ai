import os

files = {
"core/downloader.py": '''import subprocess, os, glob, re

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
''',

"core/transcriber.py": '''import whisper, os

def transcribe_video(video_path, model_size="base"):
    print(f"    Loading Whisper '{model_size}' model...")
    model = whisper.load_model(model_size)
    print(f"    Transcribing {os.path.basename(video_path)}...")
    result = model.transcribe(video_path, verbose=False)
    segments = [{"id": s["id"], "start": round(s["start"],2), "end": round(s["end"],2), "text": s["text"].strip()} for s in result["segments"]]
    return {"text": result["text"].strip(), "segments": segments, "language": result.get("language","en")}

def format_transcript_for_llm(transcript, max_chars=12000):
    lines = []
    for seg in transcript["segments"]:
        m, s = int(seg["start"]//60), int(seg["start"]%60)
        lines.append(f"[{m:02d}:{s:02d}] {seg['text']}")
    full = "\\n".join(lines)
    return full[:max_chars] + "\\n...[truncated]" if len(full) > max_chars else full
''',

"core/cutter.py": '''import subprocess, os, tempfile

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
            for c in clips: f.write(f"file \'{c}\'\\n")
        cmd = ["ffmpeg","-y","-f","concat","-safe","0","-i",concat,"-c:v","libx264","-c:a","aac","-movflags","+faststart","-preset","fast","-crf","23",output_path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError(f"FFmpeg failed: {r.stderr}")
    return output_path

def _cut_single(video_path, start, end, output_path):
    cmd = ["ffmpeg","-y","-ss",str(start),"-i",video_path,"-t",str(end-start),"-c:v","libx264","-c:a","aac","-preset","fast","-crf","23","-avoid_negative_ts","make_zero",output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"FFmpeg cut failed: {r.stderr}")
''',

"llm/selector.py": '''import json, os, re
from core.transcriber import format_transcript_for_llm

PROMPT = """You are an expert video editor. Select the most essential moments from this transcript to create a highlight reel of approximately {target_duration} seconds.

TRANSCRIPT:
{transcript}

Rules:
- Select 3-6 segments, each at least 10 seconds long
- Total duration should be approximately {target_duration} seconds
- Pick the most interesting, informative, or engaging moments

Respond ONLY with valid JSON, no markdown:
{{"segments": [{{"start": 12.5, "end": 45.0, "reason": "Opening hook"}}]}}"""

def get_segments(transcript, llm, target_duration=120, ollama_model="mistral"):
    formatted = format_transcript_for_llm(transcript)
    prompt = PROMPT.format(transcript=formatted, target_duration=target_duration)
    if llm == "claude":   raw = _claude(prompt)
    elif llm == "gemini": raw = _gemini(prompt)
    elif llm == "ollama": raw = _ollama(prompt, ollama_model)
    elif llm == "openai": raw = _openai(prompt)
    else: raise ValueError(f"Unknown LLM: {llm}")
    return _parse(raw, transcript)

def _parse(raw, transcript):
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        data = json.loads(raw)
        segs = data.get("segments", data) if isinstance(data, dict) else data
    except:
        m = re.search(r"\\{.*\\}", raw, re.DOTALL)
        if m: segs = json.loads(m.group()).get("segments", [])
        else: raise ValueError(f"Invalid JSON from LLM: {raw[:300]}")
    total = transcript["segments"][-1]["end"] if transcript["segments"] else 9999
    valid = [{"start": max(0,float(s["start"])), "end": min(float(s["end"]),total), "reason": s.get("reason","")} for s in segs if float(s["end"]) > float(s["start"]) + 5]
    if not valid: raise ValueError("No valid segments returned by LLM.")
    return sorted(valid, key=lambda x: x["start"])

def _gemini(prompt):
    try: import google.generativeai as genai
    except: raise ImportError("Run: pip install google-generativeai")
    key = os.environ.get("GEMINI_API_KEY")
    if not key: raise EnvironmentError("Set GEMINI_API_KEY environment variable")
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt).text

def _claude(prompt):
    try: import anthropic
    except: raise ImportError("Run: pip install anthropic")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: raise EnvironmentError("Set ANTHROPIC_API_KEY environment variable")
    c = anthropic.Anthropic(api_key=key)
    return c.messages.create(model="claude-opus-4-5", max_tokens=1024, messages=[{"role":"user","content":prompt}]).content[0].text

def _ollama(prompt, model):
    import requests
    r = requests.post("http://localhost:11434/api/generate", json={"model":model,"prompt":prompt,"stream":False,"format":"json"}, timeout=120)
    return r.json()["response"]

def _openai(prompt):
    try: from openai import OpenAI
    except: raise ImportError("Run: pip install openai")
    key = os.environ.get("OPENAI_API_KEY")
    if not key: raise EnvironmentError("Set OPENAI_API_KEY environment variable")
    c = OpenAI(api_key=key)
    return c.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}).choices[0].message.content
''',
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Created: {path}")

print("\n✅ All files created! Run: python agent.py <url> --llm gemini")