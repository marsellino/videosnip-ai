import argparse, os, shutil
from core.downloader import download_youtube_video
from core.transcriber import transcribe_video
from core.cutter import cut_video
from llm.selector import get_segments


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--llm", default="gemini")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--ollama-model", default="mistral")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
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
    clips = get_segments(
        transcript=transcript,
        llm=args.llm,
        target_duration=args.duration,
        ollama_model=args.ollama_model
    )
    print("    OK: " + str(len(clips)) + " highlight clips identified")

    print("[4/4] Cutting videos with FFmpeg...")
    for i, clip in enumerate(clips, 1):
        total = sum(s["end"] - s["start"] for s in clip["segments"])

        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in clip["title"])
        safe_title = safe_title.strip().replace(" ", "_")[:40]
        output_path = os.path.join(args.output_dir, f"clip_{i:02d}_{safe_title}.mp4")

        print(f"    Cutting clip {i}/{len(clips)}: {clip['title']} (~{round(total)}s)")
        for j, seg in enumerate(clip["segments"], 1):
            print(f"       [{j}] {seg['start']}s to {seg['end']}s | {seg.get('reason','')}")

        cut_video(video_path, clip["segments"], output_path)
        print(f"       Saved: {output_path}")

    if not args.keep_temp:
        shutil.rmtree("temp", ignore_errors=True)

    print("")
    print("Done! " + str(len(clips)) + " highlight clips saved to: " + args.output_dir)


if __name__ == "__main__":
    main()