import json, os, re
from core.transcriber import format_transcript_for_llm

PROMPT = """You are an expert video editor. Analyze this full transcript and extract ALL important moments, grouped into highlight clips of approximately {target_duration} seconds each.

TRANSCRIPT:
{transcript}

Rules:
- Find ALL key moments across the entire video, not just the best ones
- Group them into separate highlight clips, each approximately {target_duration} seconds total
- Each clip should be self-contained and make sense on its own
- Each segment inside a clip must be at least 8 seconds long
- Aim for 3-6 segments per clip
- Create as many clips as needed to cover all important parts

Respond ONLY with valid JSON, no markdown:
{{
  "clips": [
    {{
      "title": "Short title for this clip",
      "segments": [
        {{"start": 12.5, "end": 45.0, "reason": "Opening hook"}},
        {{"start": 78.0, "end": 110.0, "reason": "Key point about X"}}
      ]
    }},
    {{
      "title": "Second highlight clip",
      "segments": [
        {{"start": 200.0, "end": 240.0, "reason": "Another important moment"}}
      ]
    }}
  ]
}}"""


def get_segments(transcript, llm, target_duration=120, ollama_model="mistral"):
    """Returns a list of clips, each clip is a list of segments."""
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
    except:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m: data = json.loads(m.group())
        else: raise ValueError(f"Invalid JSON from LLM: {raw[:300]}")

    total_duration = transcript["segments"][-1]["end"] if transcript["segments"] else 9999
    clips_raw = data.get("clips", [])
    clips = []

    for clip in clips_raw:
        title = clip.get("title", f"clip_{len(clips)+1}")
        valid_segs = []
        for s in clip.get("segments", []):
            start = max(0, float(s["start"]))
            end = min(float(s["end"]), total_duration)
            if end - start >= 5:
                valid_segs.append({
                    "start": start,
                    "end": end,
                    "reason": s.get("reason", "")
                })
        if valid_segs:
            clips.append({
                "title": title,
                "segments": sorted(valid_segs, key=lambda x: x["start"])
            })

    if not clips:
        raise ValueError("LLM returned no valid clips.")

    return clips


def _gemini(prompt):
    from google import genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError("Set GEMINI_API_KEY environment variable")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


def _claude(prompt):
    try: import anthropic
    except: raise ImportError("Run: pip install anthropic")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: raise EnvironmentError("Set ANTHROPIC_API_KEY environment variable")
    c = anthropic.Anthropic(api_key=key)
    return c.messages.create(model="claude-opus-4-5", max_tokens=2048, messages=[{"role":"user","content":prompt}]).content[0].text


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