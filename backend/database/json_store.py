from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import AppConfig, DATA_DIR, load_config, save_config as file_save_config
from backend.database import StorageBackend
from backend.models import BaseCV, OnboardingSession, Position

POSITIONS_DIR = DATA_DIR / "positions"
EXPORTS_DIR = DATA_DIR / "exports"
SESSIONS_DIR = DATA_DIR / "onboarding_sessions"
CV_PATH = DATA_DIR / "base_cv.json"


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


class JsonStore(StorageBackend):

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        POSITIONS_DIR.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

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