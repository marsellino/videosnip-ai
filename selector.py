"""
LLM Selector — routes to Claude, Gemini, Ollama, or OpenAI
and returns structured video segments to cut
"""

import json
import os
import re
from core.transcriber import format_transcript_for_llm


SEGMENT_PROMPT = """You are an expert video editor AI. Your job is to watch a video's transcript and select the MOST essential moments that create a compelling highlight reel.

TARGET DURATION: {target_duration} seconds total

TRANSCRIPT (with timestamps):
{transcript}

TASK:
Select the most important segments that:
1. Capture the core message or best moments
2. Flow naturally together
3. Total approximately {target_duration} seconds combined
4. Prioritize: key insights, interesting stories, emotional peaks, main points

RULES:
- Each segment must be at least 10 seconds long
- Leave a small buffer (add 1-2s padding around key moments)
- Do NOT select more than 6 segments
- Timestamps are in [MM:SS] format in the transcript

Respond ONLY with valid JSON (no markdown, no explanation):
{{
  "segments": [
    {{
      "start": 12.5,
      "end": 45.0,
      "reason": "Opening hook that establishes the main topic"
    }},
    {{
      "start": 123.0,
      "end": 167.0,
      "reason": "Key insight about X"
    }}
  ]
}}
"""


def get_segments(transcript: dict, llm: str, target_duration: int = 120, ollama_model: str = "mistral") -> list[dict]:
    """
    Send transcript to chosen LLM and get back selected segments.
    Returns list of {start, end, reason} dicts.
    """
    formatted = format_transcript_for_llm(transcript)
    prompt = SEGMENT_PROMPT.format(
        transcript=formatted,
        target_duration=target_duration
    )

    if llm == "claude":
        raw = _call_claude(prompt)
    elif llm == "gemini":
        raw = _call_gemini(prompt)
    elif llm == "ollama":
        raw = _call_ollama(prompt, model=ollama_model)
    elif llm == "openai":
        raw = _call_openai(prompt)
    else:
        raise ValueError(f"Unknown LLM: {llm}")

    return _parse_segments(raw, transcript)


def _parse_segments(raw: str, transcript: dict) -> list[dict]:
    """Parse LLM JSON output into validated segment list."""
    # Strip markdown fences if present
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        data = json.loads(raw)
        segments = data.get("segments", data) if isinstance(data, dict) else data
    except json.JSONDecodeError:
        # Try to extract JSON array from the text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            segments = data.get("segments", [])
        else:
            raise ValueError(f"LLM returned invalid JSON:\n{raw[:500]}")

    # Validate and clean
    total_duration = transcript["segments"][-1]["end"] if transcript["segments"] else 9999
    valid = []
    for seg in segments:
        start = float(seg.get("start", 0))
        end = float(seg.get("end", 0))
        if end > start and end <= total_duration + 5 and (end - start) >= 5:
            valid.append({
                "start": max(0, start),
                "end": min(end, total_duration),
                "reason": seg.get("reason", "")
            })

    if not valid:
        raise ValueError("LLM returned no valid segments. Try a different model or check API key.")

    # Sort by time
    valid.sort(key=lambda x: x["start"])
    return valid


# ─────────────────────────────────────────────
# LLM Backend Implementations
# ─────────────────────────────────────────────

def _call_claude(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Install anthropic SDK: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("Set ANTHROPIC_API_KEY environment variable")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def _call_gemini(prompt: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("Install google SDK: pip install google-generativeai")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("Set GEMINI_API_KEY environment variable")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text


def _call_ollama(prompt: str, model: str = "mistral") -> str:
    """Calls a locally running Ollama instance (fully offline)."""
    try:
        import requests
    except ImportError:
        raise ImportError("Install requests: pip install requests")

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        },
        timeout=120
    )
    if response.status_code != 200:
        raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")
    return response.json()["response"]


def _call_openai(prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Install openai SDK: pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("Set OPENAI_API_KEY environment variable")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
