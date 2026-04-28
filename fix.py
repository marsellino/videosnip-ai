f = open("agent.py", "w", encoding="utf-8")
f.write("""import argparse, os, shutil
from core.downloader import download_youtube_video
from core.transcriber import transcribe_video
from core.cutter import cut_video
from llm.selector import get_segments

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--llm", default="gemini")
    parser.add_argument("--duration", type=int, default=120)
    parser.add_argument("--ollama-model", default="mistral")
    parser.add_argument("--output", default="output/highlight.mp4")
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    print("VideoSnip AI Agent")
    print("=" * 50)

    print("[1/4] Downloading video...")
    video_path = download_youtube_video(args.url, output_dir="temp")
    print("    OK: " + video_path)

    print("[2/4] Transcribing with Whisper...")
    transcript = transcribe_video(video_path)
    print("    OK: " + str(len(transcript["segments"])) + " segments found")

    print("[3/4] Analyzing with " + args.llm.upper() + "...")
    segs = get_segments(
        transcript=transcript,
        llm=args.llm,
        target_duration=args.duration,
        ollama_model=args.ollama_model
    )
    total = sum(s["end"] - s["start"] for s in segs)
    print("    OK: " + str(len(segs)) + " segments, " + str(round(total)) + "s total")
    for i, s in enumerate(segs, 1):
        print("    [" + str(i) + "] " + str(s["start"]) + "s to " + str(s["end"]) + "s")

    print("[4/4] Cutting video with FFmpeg...")
    cut_video(video_path, segs, args.output)
    print("    OK: Saved to " + args.output)

    if not args.keep_temp:
        shutil.rmtree("temp", ignore_errors=True)

    print("Done! Video ready: " + args.output)

if __name__ == "__main__":
    main()
""")
f.close()
print("agent.py fixed successfully!")