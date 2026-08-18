from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from backend.config import DATA_DIR

logger = logging.getLogger(__name__)

MEMORY_DIR = DATA_DIR / "remy" / "memory"
PROFILE_PATH = MEMORY_DIR / "profile.json"
RUNS_INDEX_PATH = MEMORY_DIR / "runs_index.json"
CV_HISTORY_DIR = MEMORY_DIR / "cv_history"
CV_HISTORY_INDEX_PATH = MEMORY_DIR / "cv_history.index.json"

MAX_RUNS_INDEX = 200
MAX_TOP_SKILLS = 25
MAX_CV_HISTORY = 100

_memory: Optional["RemyMemory"] = None


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_remy_memory() -> "RemyMemory":
    global _memory
    if _memory is None:
        _memory = RemyMemory()
    return _memory


class RemyMemory:
    """Persistent memory for Remy: run index + candidate profile signals.

    Lightweight JSON implementation of the Phase 1 memory plan. The full
    CV snapshot/delta history (`cv_history/`, `cv_deltas.jsonl`) lands with
    the `cv-chronicler` in the agent phase; this module covers the
    Phase 4 requirement of remembering reports and market signals.
    """

    def __init__(self) -> None:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        CV_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    # --- low-level file helpers ---

    @staticmethod
    def _read_json(path, default):
        if not path.exists():
            return default
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def _write_json(path, data) -> None:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # --- profile ---

    async def get_profile(self) -> dict:
        return self._read_json(
            PROFILE_PATH,
            {
                "role": "",
                "skills_timeline": [],
                "preferences": {},
                "market_signals": {"top_skills": [], "updated_at": ""},
            },
        )

    async def _save_profile(self, profile: dict) -> None:
        self._write_json(PROFILE_PATH, profile)

    async def update_market_signals(self, top_skills: list[str]) -> None:
        """Merge newly observed top skills into the profile's market signals."""
        if not top_skills:
            return
        profile = await self.get_profile()
        current = profile.get("market_signals", {}).get("top_skills", [])
        merged: list[str] = []
        for skill in [*top_skills, *current]:
            key = skill.strip().lower()
            if key and key not in {s.strip().lower() for s in merged}:
                merged.append(skill.strip())
        profile["market_signals"] = {
            "top_skills": merged[:MAX_TOP_SKILLS],
            "updated_at": _now(),
        }
        await self._save_profile(profile)
        logger.info("Updated profile market signals (%d skills)", len(merged[:MAX_TOP_SKILLS]))

    # --- runs index ---

    async def record_run(
        self,
        run_id: str,
        report_id: str,
        report_type: str,
        query_id: str,
        top_listing_ids: list[str],
        top_skills: Optional[list[str]] = None,
    ) -> None:
        index = self._read_json(RUNS_INDEX_PATH, [])
        index.insert(
            0,
            {
                "run_id": run_id,
                "report_id": report_id,
                "report_type": report_type,
                "query_id": query_id,
                "top_listing_ids": top_listing_ids[:10],
                "recorded_at": _now(),
            },
        )
        self._write_json(RUNS_INDEX_PATH, index[:MAX_RUNS_INDEX])
        await self.update_market_signals(top_skills or [])

    async def list_recent_runs(self, limit: int = 50) -> list[dict]:
        index = self._read_json(RUNS_INDEX_PATH, [])
        return index[: max(1, min(limit, MAX_RUNS_INDEX))]

    async def clear(self) -> None:
        self._write_json(RUNS_INDEX_PATH, [])
        self._write_json(
            PROFILE_PATH,
            {
                "role": "",
                "skills_timeline": [],
                "preferences": {},
                "market_signals": {"top_skills": [], "updated_at": _now()},
            },
        )
        for path in CV_HISTORY_DIR.glob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass
        self._write_json(CV_HISTORY_INDEX_PATH, [])
        logger.info("Remy memory cleared")

    # --- CV chronicler (snapshots + deltas + profile) ---

    async def snapshot_cv(self, cv: dict) -> dict | None:
        """Snapshot a CV save. Returns None if unchanged from the latest snapshot."""
        cv_id = cv.get("id") or ""
        name = " ".join(
            [
                (cv.get("personal_info") or {}).get("first_name", ""),
                (cv.get("personal_info") or {}).get("last_name", ""),
            ]
        ).strip() or "CV"
        signature = {
            "cv_id": cv_id,
            "name": name,
            "updated_at": cv.get("updated_at", ""),
            "skills_count": len(cv.get("skills") or []),
            "career_count": len(cv.get("career") or []),
            "role": name,
        }
        timestamp = _now()

        index = self._read_json(CV_HISTORY_INDEX_PATH, [])
        if index and index[0].get("signature") == signature:
            return None

        stamp = timestamp.replace(":", "-").replace(".", "-")
        snapshot = {
            "timestamp": timestamp,
            "signature": signature,
            "cv": cv,
        }
        self._write_json(CV_HISTORY_DIR / f"{stamp}.json", snapshot)

        index.insert(0, {"timestamp": timestamp, "signature": signature, "file": f"{stamp}.json"})
        self._write_json(CV_HISTORY_INDEX_PATH, index[:MAX_CV_HISTORY])
        for stale in index[MAX_CV_HISTORY:]:
            path = CV_HISTORY_DIR / stale.get("file", "")
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass

        await self._update_profile_from_cv(cv)
        logger.info("CV snapshot %s saved (%d total)", stamp, len(index[:MAX_CV_HISTORY]))
        return {"timestamp": timestamp, "signature": signature}

    async def list_cv_history(self, limit: int = 100) -> list[dict]:
        index = self._read_json(CV_HISTORY_INDEX_PATH, [])
        return index[: max(1, min(limit, MAX_CV_HISTORY))]

    async def get_cv_snapshot(self, filename: str) -> dict | None:
        if "/" in filename or ".." in filename:
            return None
        path = CV_HISTORY_DIR / filename
        if not path.exists():
            return None
        return self._read_json(path, None)

    async def _update_profile_from_cv(self, cv: dict) -> None:
        profile = await self.get_profile()
        personal = cv.get("personal_info") or {}
        first = personal.get("first_name", "")
        last = personal.get("last_name", "")
        name = " ".join([first, last]).strip()
        if name and name != profile.get("role"):
            profile["role"] = name
        career = cv.get("career") or []
        latest_role = ""
        if career and career[0].get("role"):
            latest_role = career[0]["role"]
        entry = {"timestamp": _now(), "latest_role": latest_role, "skills_count": len(cv.get("skills") or []), "career_count": len(career)}
        profile.setdefault("skills_timeline", []).insert(0, entry)
        profile["skills_timeline"] = profile["skills_timeline"][:50]
        await self._save_profile(profile)

    # --- chat threads ---

    def list_threads(self) -> list[dict]:
        entries = []
        for path in sorted(MEMORY_DIR.glob("chat_*.json")):
            try:
                data = self._read_json(path, None)
                if not data:
                    continue
                entries.append({
                    "thread_id": data.get("thread_id", ""),
                    "title": data.get("title", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages") or []),
                })
            except Exception:
                continue
        return entries

    def get_thread(self, thread_id: str) -> dict | None:
        if not thread_id or "/" in thread_id or ".." in thread_id:
            return None
        path = MEMORY_DIR / f"chat_{thread_id}.json"
        return self._read_json(path, None)

    def save_thread(self, thread_id: str, messages: list[dict], title: str = "") -> None:
        existing = self.get_thread(thread_id) or {}
        self._write_json(
            MEMORY_DIR / f"chat_{thread_id}.json",
            {
                "thread_id": thread_id,
                "title": title or existing.get("title", ""),
                "messages": messages,
                "updated_at": _now(),
            },
        )

    def delete_thread(self, thread_id: str) -> bool:
        if not thread_id or "/" in thread_id or ".." in thread_id:
            return False
        path = MEMORY_DIR / f"chat_{thread_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True
