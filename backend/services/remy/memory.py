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

MAX_RUNS_INDEX = 200
MAX_TOP_SKILLS = 25

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
        logger.info("Remy memory cleared")
