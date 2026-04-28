"""
VideoSnip AI - Web Server
Bridges the browser UI to the local Python agent
Run with: python server.py
Then open: http://localhost:5000
"""

from flask import Flask, request, Response, send_from_directory
import subprocess
import sys
import os
import json

app = Flask(__name__, static_folder=".")

# ── Serve the UI ──────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "ui.html")

# ── Run the agent & stream logs back to browser ───────────
@app.route("/run", methods=["POST"])
def run_agent():
    data = request.get_json()
    url      = data.get("url", "").strip()
    llm      = data.get("llm", "gemini")
    duration = str(data.get("duration", 90))
    ollama_model = data.get("ollamaModel", "mistral")

    if not url:
        return {"error": "No URL provided"}, 400

    # Build the command
    cmd = [
        sys.executable, "agent.py",
        url,
        "--llm", llm,
        "--duration", duration,
    ]
    if llm == "ollama":
        cmd += ["--ollama-model", ollama_model]

    def generate():
        """Stream agent output line-by-line to the browser."""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=os.environ.copy()
        )
        for line in process.stdout:
            # Send each line as a Server-Sent Event
            yield f"data: {json.dumps(line.rstrip())}\n\n"

        process.wait()
        if process.returncode == 0:
            yield f"data: {json.dumps('__DONE__')}\n\n"
        else:
            yield f"data: {json.dumps('__ERROR__')}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    print("\n🎬 VideoSnip AI Server")
    print("=" * 40)
    print("   Open in browser: http://localhost:5000")
    print("   Press Ctrl+C to stop\n")
    app.run(debug=False, port=5000, threaded=True)
