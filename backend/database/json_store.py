from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import AppConfig, DATA_DIR, load_config, save_config as file_save_config
from backend.database import StorageBackend
from backend.models import BaseCV, OnboardingSession, Position, StarSession, StarStory

POSITIONS_DIR = DATA_DIR / "positions"
EXPORTS_DIR = DATA_DIR / "exports"
SESSIONS_DIR = DATA_DIR / "onboarding_sessions"
STAR_SESSIONS_DIR = DATA_DIR / "star_sessions"
STAR_STORIES_DIR = DATA_DIR / "star_stories"
CV_PATH = DATA_DIR / "base_cv.json"


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class JsonStore(StorageBackend):

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        POSITIONS_DIR.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        STAR_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        STAR_STORIES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Base CV ---

    async def get_cv(self) -> Optional[BaseCV]:
        if not CV_PATH.exists():
            return None
        with open(CV_PATH) as f:
            return BaseCV(**json.load(f))

    async def save_cv(self, cv: BaseCV) -> None:
        cv.updated_at = _now()
        with open(CV_PATH, "w") as f:
            json.dump(cv.model_dump(), f, indent=2, ensure_ascii=False)

    # --- Settings ---

    async def get_config(self) -> AppConfig:
        return load_config()

    async def save_config(self, config: AppConfig) -> None:
        file_save_config(config)

    # --- Positions ---

    async def list_positions(self, company: Optional[str] = None, status: Optional[str] = None) -> list[Position]:
        results: list[Position] = []
        if not POSITIONS_DIR.exists():
            return results
        for slug_dir in sorted(POSITIONS_DIR.iterdir()):
            if not slug_dir.is_dir():
                continue
            meta_path = slug_dir / "metadata.json"
            if not meta_path.exists():
                continue
            with open(meta_path) as f:
                pos = Position(**json.load(f))
            if company and company.lower() not in pos.company_name.lower():
                continue
            if status and pos.status != status:
                continue
            results.append(pos)
        return results

    async def get_position(self, position_id: str) -> Optional[Position]:
        for slug_dir in POSITIONS_DIR.iterdir():
            if not slug_dir.is_dir():
                continue
            meta_path = slug_dir / "metadata.json"
            if not meta_path.exists():
                continue
            with open(meta_path) as f:
                pos = Position(**json.load(f))
            if pos.id == position_id:
                return pos
        return None

    async def save_position(self, position: Position) -> None:
        position.updated_at = _now()
        slug_dir = POSITIONS_DIR / (position.company_slug or "unknown")
        slug_dir.mkdir(parents=True, exist_ok=True)
        meta_path = slug_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(position.model_dump(), f, indent=2, ensure_ascii=False)
        jd_path = slug_dir / "job_description.md"
        if position.job_description_md:
            with open(jd_path, "w") as f:
                f.write(position.job_description_md)
        cv_path = slug_dir / "tailored_cv.md"
        if position.tailored_cv_md:
            with open(cv_path, "w") as f:
                f.write(position.tailored_cv_md)

    async def delete_position(self, position_id: str) -> bool:
        for slug_dir in POSITIONS_DIR.iterdir():
            if not slug_dir.is_dir():
                continue
            meta_path = slug_dir / "metadata.json"
            if not meta_path.exists():
                continue
            with open(meta_path) as f:
                pos = Position(**json.load(f))
            if pos.id == position_id:
                shutil.rmtree(slug_dir)
                return True
        return False

    # --- Onboarding ---

    async def get_onboarding_session(self, session_id: str) -> Optional[OnboardingSession]:
        session_path = SESSIONS_DIR / f"{session_id}.json"
        if not session_path.exists():
            return None
        with open(session_path) as f:
            return OnboardingSession(**json.load(f))

    async def save_onboarding_session(self, session: OnboardingSession) -> None:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session_path = SESSIONS_DIR / f"{session.id}.json"
        with open(session_path, "w") as f:
            json.dump(session.model_dump(), f, indent=2, ensure_ascii=False)

    async def delete_onboarding_session(self, session_id: str) -> None:
        session_path = SESSIONS_DIR / f"{session_id}.json"
        if session_path.exists():
            session_path.unlink()

    # --- STAR ---

    async def get_star_session(self, session_id: str) -> Optional[StarSession]:
        session_path = STAR_SESSIONS_DIR / f"{session_id}.json"
        if not session_path.exists():
            return None
        with open(session_path) as f:
            return StarSession(**json.load(f))

    async def save_star_session(self, session: StarSession) -> None:
        STAR_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session_path = STAR_SESSIONS_DIR / f"{session.id}.json"
        with open(session_path, "w") as f:
            json.dump(session.model_dump(), f, indent=2, ensure_ascii=False)

    async def delete_star_session(self, session_id: str) -> None:
        session_path = STAR_SESSIONS_DIR / f"{session_id}.json"
        if session_path.exists():
            session_path.unlink()

    async def list_star_stories(self) -> list[StarStory]:
        results: list[StarStory] = []
        if not STAR_STORIES_DIR.exists():
            return results
        for story_file in sorted(STAR_STORIES_DIR.iterdir()):
            if not story_file.suffix == ".json":
                continue
            with open(story_file) as f:
                results.append(StarStory(**json.load(f)))
        return results

    async def get_star_story(self, story_id: str) -> Optional[StarStory]:
        story_path = STAR_STORIES_DIR / f"{story_id}.json"
        if not story_path.exists():
            return None
        with open(story_path) as f:
            return StarStory(**json.load(f))

    async def save_star_story(self, story: StarStory) -> None:
        story.updated_at = _now()
        STAR_STORIES_DIR.mkdir(parents=True, exist_ok=True)
        story_path = STAR_STORIES_DIR / f"{story.id}.json"
        with open(story_path, "w") as f:
            json.dump(story.model_dump(), f, indent=2, ensure_ascii=False)

    async def delete_star_story(self, story_id: str) -> bool:
        story_path = STAR_STORIES_DIR / f"{story_id}.json"
        if story_path.exists():
            story_path.unlink()
            return True
        return False