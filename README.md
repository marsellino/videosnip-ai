# 🎬 VideoSnip AI Agent

Cut any YouTube video into a short highlight reel using local AI.
Paste a URL → Whisper transcribes it → LLM picks the best moments → FFmpeg cuts it.

---

## ⚡ Quick Start

```bash
# 1. Clone / copy this folder
cd video-agent

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install FFmpeg (system-level)
# macOS:   brew install ffmpeg
# Ubuntu:  sudo apt install ffmpeg
# Windows: https://ffmpeg.org/download.html (add to PATH)

# 4. Set your API key (skip if using Ollama)
export ANTHROPIC_API_KEY="sk-ant-..."   # Claude
export GEMINI_API_KEY="AIza..."         # Gemini
export OPENAI_API_KEY="sk-..."          # OpenAI

# 5. Run!
python agent.py "https://youtube.com/watch?v=XXXXX" --llm claude
```

Output saved to: `output/highlight.mp4`

---

## 🧰 Options

```
python agent.py <youtube_url> [options]

Options:
  --llm         claude | gemini | ollama | openai  (default: claude)
  --duration    Target seconds for output video     (default: 120)
  --ollama-model  Model name if using Ollama        (default: mistral)
  --output      Output file path                    (default: output/highlight.mp4)
  --keep-temp   Don't delete temp files after run
```

### Examples

```bash
# Claude (default) - 90 second highlight
python agent.py "https://youtube.com/watch?v=xxx" --llm claude --duration 90

# Gemini - 2 minute highlight
python agent.py "https://youtube.com/watch?v=xxx" --llm gemini --duration 120

# Fully offline with Ollama + Mistral (no API key needed!)
python agent.py "https://youtube.com/watch?v=xxx" --llm ollama --ollama-model mistral

# Ollama with LLaMA 3
python agent.py "https://youtube.com/watch?v=xxx" --llm ollama --ollama-model llama3
```

---

## 🏗️ How It Works

```
YouTube URL
    ↓
yt-dlp          Downloads video (720p MP4)
    ↓
Whisper         Transcribes audio with timestamps (runs locally)
    ↓
LLM             Reads transcript, selects the most essential segments
    ↓
FFmpeg          Cuts those segments and stitches into one clean video
    ↓
output/highlight.mp4
```

### What the LLM actually does

The agent sends the full timestamped transcript to the LLM with a prompt asking it to identify the 3-6 most essential moments. It returns a JSON list of `{start, end, reason}` objects. The agent validates these, then passes them to FFmpeg.

---

## 🤖 LLM Backends

| Backend | Needs | Quality | Speed | Cost |
|---------|-------|---------|-------|------|
| **Claude** | `ANTHROPIC_API_KEY` | ⭐⭐⭐⭐⭐ | Fast | ~$0.01/video |
| **Gemini** | `GEMINI_API_KEY` | ⭐⭐⭐⭐ | Fast | Free tier available |
| **OpenAI** | `OPENAI_API_KEY` | ⭐⭐⭐⭐ | Fast | ~$0.01/video |
| **Ollama** | Ollama installed | ⭐⭐⭐ | Slower | 100% free & offline |

### Using Ollama (fully local, no API key)

```bash
# Install Ollama from https://ollama.ai
ollama pull mistral     # or: llama3, gemma2, phi3
ollama serve            # start the local server

python agent.py "..." --llm ollama --ollama-model mistral
```

---

## 🎙️ Whisper Model Sizes

Edit `core/transcriber.py` to change the model:

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | 75MB | ⚡⚡⚡ | Good |
| `base` | 145MB | ⚡⚡ | Better (default) |
| `small` | 465MB | ⚡ | Great |
| `medium` | 1.5GB | 🐢 | Excellent |
| `large` | 3GB | 🐢🐢 | Best |

---

## 📁 Project Structure

```
video-agent/
├── agent.py              ← Main entry point (CLI)
├── requirements.txt
├── core/
│   ├── downloader.py     ← YouTube download via yt-dlp
│   ├── transcriber.py    ← Whisper transcription
│   └── cutter.py         ← FFmpeg video cutting & merging
├── llm/
│   └── selector.py       ← LLM routing + prompt + JSON parsing
├── temp/                 ← Downloaded videos (auto-cleaned)
└── output/               ← Your highlight videos go here
```

---

## 🛠️ Requirements

- **Python** 3.10+
- **FFmpeg** installed on your system
- **yt-dlp** (Python package, installs via pip)
- **Whisper** (runs on CPU — no GPU needed, just slower)
- One LLM API key (or Ollama for fully local)

---

## 💡 Tips

- **Long videos (1hr+)**: Use `--llm gemini` (largest context window) or `small`/`medium` Whisper
- **Non-English videos**: Whisper auto-detects language; all LLMs handle multilingual transcripts
- **GPU acceleration**: Install `torch` with CUDA support for much faster Whisper transcription
- **Batch processing**: Wrap `agent.py` in a shell loop for multiple URLs
