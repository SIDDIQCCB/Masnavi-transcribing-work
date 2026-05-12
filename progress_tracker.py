"""
Progress tracker for playlist transcription.
Saves state to JSON so work can be resumed after interruption.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STATUS_PENDING    = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED  = "completed"
STATUS_FAILED     = "failed"


class ProgressTracker:
    """
    Persists transcription job state in a JSON file.

    Schema
    ------
    {
        "playlist_url": "https://...",
        "created_at": 1234567890,
        "updated_at": 1234567890,
        "total": 10,
        "videos": {
            "<video_id>": {
                "url": "https://...",
                "title": "...",
                "status": "pending|processing|completed|failed",
                "transcript_path": "transcripts/....txt",
                "error": null,
                "started_at": null,
                "completed_at": null
            },
            ...
        }
    }
    """

    def __init__(self, save_path: str = "progress.json"):
        self.save_path = Path(save_path)
        self._data: dict = {}
        if self.save_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Init / load
    # ------------------------------------------------------------------

    def init_playlist(self, playlist_url: str, videos: list) -> None:
        """
        Initialise tracker for a new playlist.
        Existing completed entries are preserved (resume support).
        """
        if not self._data:
            self._data = {
                "playlist_url": playlist_url,
                "created_at": time.time(),
                "updated_at": time.time(),
                "total": len(videos),
                "videos": {},
            }

        existing = self._data.get("videos", {})
        for v in videos:
            vid_id = v["id"]
            if vid_id not in existing:
                existing[vid_id] = {
                    "url": v["url"],
                    "title": v["title"],
                    "status": STATUS_PENDING,
                    "transcript_path": None,
                    "error": None,
                    "started_at": None,
                    "completed_at": None,
                }
        self._data["videos"] = existing
        self._data["total"] = len(videos)
        self._save()

    def _load(self) -> None:
        try:
            with open(self.save_path, encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info(f"Resumed from {self.save_path}")
        except Exception as e:
            logger.warning(f"Could not load progress file: {e}")
            self._data = {}

    def _save(self) -> None:
        self._data["updated_at"] = time.time()
        tmp = self.save_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.save_path)

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------

    def mark_processing(self, video_id: str) -> None:
        self._data["videos"][video_id]["status"] = STATUS_PROCESSING
        self._data["videos"][video_id]["started_at"] = time.time()
        self._data["videos"][video_id]["error"] = None
        self._save()

    def mark_completed(self, video_id: str, transcript_path: str) -> None:
        self._data["videos"][video_id]["status"] = STATUS_COMPLETED
        self._data["videos"][video_id]["transcript_path"] = transcript_path
        self._data["videos"][video_id]["completed_at"] = time.time()
        self._save()

    def mark_failed(self, video_id: str, error: str) -> None:
        self._data["videos"][video_id]["status"] = STATUS_FAILED
        self._data["videos"][video_id]["error"] = error
        self._data["videos"][video_id]["completed_at"] = time.time()
        self._save()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def total(self) -> int:
        return self._data.get("total", 0)

    @property
    def videos(self) -> dict:
        return self._data.get("videos", {})

    def pending_videos(self) -> list:
        """Return list of (video_id, info) for videos not yet completed."""
        return [
            (vid_id, info)
            for vid_id, info in self.videos.items()
            if info["status"] in (STATUS_PENDING, STATUS_PROCESSING, STATUS_FAILED)
        ]

    def completed_count(self) -> int:
        return sum(1 for v in self.videos.values() if v["status"] == STATUS_COMPLETED)

    def failed_count(self) -> int:
        return sum(1 for v in self.videos.values() if v["status"] == STATUS_FAILED)

    def pending_count(self) -> int:
        return sum(1 for v in self.videos.values() if v["status"] == STATUS_PENDING)

    def summary(self) -> dict:
        return {
            "total": self.total,
            "completed": self.completed_count(),
            "failed": self.failed_count(),
            "pending": self.pending_count(),
            "percent_done": round(self.completed_count() / max(self.total, 1) * 100, 1),
        }

    def is_all_done(self) -> bool:
        return self.completed_count() + self.failed_count() >= self.total

    def get_all_data(self) -> dict:
        return self._data
