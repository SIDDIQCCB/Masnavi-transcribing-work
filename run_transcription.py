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
import time
from datetime import datetime
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

def _format_eta(eta_seconds: float) -> str:
    """Format seconds remaining as 'Xh Ym' or 'Ym'."""
    total_min = int(eta_seconds // 60)
    hours, minutes = divmod(total_min, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def make_cli_progress(video_title: str):
    """Returns a callback that prints progress to stdout, with ETA when available."""
    bar_width = 30

    def cb(stage: str, pct: float, eta_seconds: float = None, finish_time: float = None):
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        label = {
            "downloading": "Downloading",
            "loading_model": "Loading model",
            "transcribing": "Transcribing ",
        }.get(stage, stage.capitalize())

        eta_str = ""
        if eta_seconds is not None and finish_time is not None:
            clock = datetime.fromtimestamp(finish_time).strftime("%I:%M %p").lstrip("0")
            eta_str = f"  ~{_format_eta(eta_seconds)} left, done ~{clock}"

        print(f"\r  {label} [{bar}] {pct:5.1f}%{eta_str}   ", end="", flush=True)
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
    job_start = time.monotonic()

    console_cb = make_cli_progress(title)

    def progress_cb(stage: str, pct: float, eta_seconds: float = None, finish_time: float = None):
        console_cb(stage, pct, eta_seconds=eta_seconds, finish_time=finish_time)
        if stage == "transcribing":
            tracker.update_eta(video_id, pct, eta_seconds=eta_seconds, finish_time=finish_time)

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
        device=args.device,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
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
    elapsed = time.monotonic() - job_start
    mins, secs = divmod(int(elapsed), 60)
    hrs, mins = divmod(mins, 60)
    time_str = f"{hrs}h {mins}m {secs}s" if hrs else f"{mins}m {secs}s"
    logger.info(
        f"✓ Saved → {saved_path}  (took {time_str})  "
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
                        choices=["tiny", "base", "small", "medium",
                                 "large-v2", "large-v3"],
                        help="Whisper model size (default: medium). "
                             "On an NVIDIA GPU, large-v3 gives the best "
                             "accuracy and is fast enough to be practical; "
                             "on CPU-only machines stick to small/medium.")
    parser.add_argument("--beam-size",  type=int, default=None, dest="beam_size",
                        help="Beam search width. Default: auto — 5 on GPU, "
                             "3 on CPU (higher = more accurate, slower)")
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
    parser.add_argument("--device",     default="auto",
                        choices=["auto", "cpu", "cuda"],
                        help="Compute device: auto-detects NVIDIA GPU, "
                             "else CPU (default: auto)")
    parser.add_argument("--compute-type", default="auto", dest="compute_type",
                        help="Precision: auto picks float16 (GPU) or int8 "
                             "(CPU) automatically (default: auto)")

    args = parser.parse_args()

    if args.device == "auto":
        from transcriber import _auto_device
        detected_device, detected_compute = _auto_device()
        gpu_note = " (NVIDIA GPU found)" if detected_device == "cuda" else " (no usable NVIDIA GPU — using CPU)"
        logger.info(f"Device auto-detect: {detected_device}/{detected_compute}{gpu_note}")

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
