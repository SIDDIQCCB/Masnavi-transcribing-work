"""
CLI runner for batch playlist transcription.
Supports single video URL or full playlist with resume capability.

Usage
-----
# Single video
python run_transcription.py --url "https://youtube.com/watch?v=..."

# Full playlist
python run_transcription.py --playlist "https://youtube.com/playlist?list=..."

# Resume interrupted playlist (auto-detected)
python run_transcription.py --playlist "..." --resume

Options
-------
--model       Whisper model size: tiny / base / small / medium (default: medium)
--language    Primary language code (default: ur for Urdu)
--output      Output folder for transcripts (default: transcripts)
--progress    JSON file to track progress (default: progress.json)
--audio-dir   Temp folder for downloaded audio (default: audio_cache)
--keep-audio  Do not delete audio files after transcription
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from transcriber import (
    download_audio,
    get_playlist_videos,
    transcribe_audio,
    save_transcript,
)
from progress_tracker import ProgressTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progress callback (CLI)
# ---------------------------------------------------------------------------

def make_cli_progress(video_title: str):
    """Returns a callback that prints progress to stdout."""
    bar_width = 30

    def cb(stage: str, pct: float):
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        label = {
            "downloading": "Downloading",
            "loading_model": "Loading model",
            "transcribing": "Transcribing ",
        }.get(stage, stage.capitalize())
        print(f"\r  {label} [{bar}] {pct:5.1f}%", end="", flush=True)
        if pct >= 100:
            print()

    return cb


# ---------------------------------------------------------------------------
# Process a single video
# ---------------------------------------------------------------------------

def process_video(
    video_id: str,
    url: str,
    title: str,
    tracker: ProgressTracker,
    args: argparse.Namespace,
) -> bool:
    """
    Download + transcribe one video.
    Updates tracker state throughout.
    Returns True on success.
    """
    tracker.mark_processing(video_id)
    logger.info(f"{'='*60}")
    logger.info(f"Processing: {title}")
    logger.info(f"URL       : {url}")

    progress_cb = make_cli_progress(title)

    # 1. Download
    logger.info("Step 1/2 — Downloading audio…")
    result = download_audio(url, args.audio_dir, progress_cb=progress_cb)
    if result is None or result[0] is None:
        err = "Audio download failed"
        logger.error(err)
        tracker.mark_failed(video_id, err)
        return False
    audio_path, _ = result

    # 2. Transcribe
    logger.info("Step 2/2 — Transcribing…")
    transcript = transcribe_audio(
        audio_path,
        language=args.language,
        model_size=args.model,
        progress_cb=progress_cb,
        device="cpu",
        compute_type="int8",
    )

    # Clean up audio unless --keep-audio
    if not args.keep_audio and os.path.exists(audio_path):
        os.remove(audio_path)
        logger.info("Audio file removed.")

    if transcript is None:
        err = "Transcription returned None"
        logger.error(err)
        tracker.mark_failed(video_id, err)
        return False

    # 3. Save
    saved_path = save_transcript(title, transcript, args.output)
    tracker.mark_completed(video_id, saved_path)

    summary = tracker.summary()
    logger.info(
        f"✓ Saved → {saved_path}  "
        f"[{summary['completed']}/{summary['total']} done, "
        f"{summary['percent_done']}%]"
    )
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Masnavi Lecture Transcription System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url",      help="Single YouTube video URL")
    group.add_argument("--playlist", help="YouTube playlist URL")

    parser.add_argument("--model",      default="medium",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: medium)")
    parser.add_argument("--language",   default="ur",
                        help="Primary language code (default: ur)")
    parser.add_argument("--output",     default="transcripts",
                        help="Output folder (default: transcripts)")
    parser.add_argument("--progress",   default="progress.json",
                        help="Progress JSON file (default: progress.json)")
    parser.add_argument("--audio-dir",  default="audio_cache",
                        help="Temp audio folder (default: audio_cache)")
    parser.add_argument("--keep-audio", action="store_true",
                        help="Keep downloaded audio files")
    parser.add_argument("--resume",     action="store_true",
                        help="Resume from saved progress (default: auto)")

    args = parser.parse_args()

    tracker = ProgressTracker(save_path=args.progress)

    # ---- Single video mode ------------------------------------------------
    if args.url:
        from transcriber import get_video_title
        title = get_video_title(args.url) or "video"
        videos = [{"id": title[:40], "url": args.url, "title": title}]
        tracker.init_playlist(args.url, videos)
        process_video(list(tracker.videos.keys())[0], args.url, title, tracker, args)
        return

    # ---- Playlist mode ----------------------------------------------------
    logger.info(f"Fetching playlist: {args.playlist}")
    videos = get_playlist_videos(args.playlist)
    if not videos:
        logger.error("No videos found in playlist.")
        sys.exit(1)

    logger.info(f"Found {len(videos)} videos.")
    tracker.init_playlist(args.playlist, videos)

    pending = tracker.pending_videos()
    if not pending:
        logger.info("All videos already completed. Nothing to do.")
        return

    logger.info(
        f"Resuming: {tracker.completed_count()} done, "
        f"{len(pending)} remaining."
    )

    success = fail = 0
    for video_id, info in pending:
        ok = process_video(video_id, info["url"], info["title"], tracker, args)
        if ok:
            success += 1
        else:
            fail += 1

    logger.info("=" * 60)
    logger.info(f"Batch complete — {success} succeeded, {fail} failed.")
    s = tracker.summary()
    logger.info(
        f"Overall: {s['completed']}/{s['total']} transcribed "
        f"({s['percent_done']}%)"
    )


if __name__ == "__main__":
    main()
