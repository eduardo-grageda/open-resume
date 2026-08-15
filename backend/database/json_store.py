from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.config import AppConfig, DATA_DIR, load_config, save_config as file_save_config
from backend.database import StorageBackend
from backend.models import (
    BaseCV,
    OnboardingSession,
    Position,
    RemyListing,
    RemyQuery,
    RemyReport,
    RemyRun,
    RemyTask,
    StarSession,
    StarStory,
)

POSITIONS_DIR = DATA_DIR / "positions"
EXPORTS_DIR = DATA_DIR / "exports"
SESSIONS_DIR = DATA_DIR / "onboarding_sessions"
STAR_SESSIONS_DIR = DATA_DIR / "star_sessions"
STAR_STORIES_DIR = DATA_DIR / "star_stories"
REMY_DIR = DATA_DIR / "remy"
REMY_QUERIES_PATH = REMY_DIR / "queries.json"
REMY_LISTINGS_PATH = REMY_DIR / "listings.json"
REMY_TASKS_PATH = REMY_DIR / "tasks.json"
REMY_RUNS_PATH = REMY_DIR / "runs.json"
REMY_REPORTS_PATH = REMY_DIR / "reports.json"
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
        REMY_DIR.mkdir(parents=True, exist_ok=True)

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

    # --- Remy helpers ---

    @staticmethod
    def _read_json_list(path: Path, model_cls):
        if not path.exists():
            return []
        with open(path) as f:
            raw = json.load(f)
        return [model_cls(**item) for item in raw]

    @staticmethod
    def _write_json_list(path: Path, items: list) -> None:
        with open(path, "w") as f:
            json.dump([item.model_dump() for item in items], f, indent=2, ensure_ascii=False)

    # --- Remy Queries ---

    async def list_remy_queries(self) -> list[RemyQuery]:
        return self._read_json_list(REMY_QUERIES_PATH, RemyQuery)

    async def get_remy_query(self, query_id: str) -> Optional[RemyQuery]:
        for q in await self.list_remy_queries():
            if q.id == query_id:
                return q
        return None

    async def save_remy_query(self, query: RemyQuery) -> None:
        query.updated_at = _now()
        queries = await self.list_remy_queries()
        for i, q in enumerate(queries):
            if q.id == query.id:
                queries[i] = query
                break
        else:
            queries.append(query)
        self._write_json_list(REMY_QUERIES_PATH, queries)

    async def delete_remy_query(self, query_id: str) -> bool:
        queries = await self.list_remy_queries()
        new_queries = [q for q in queries if q.id != query_id]
        if len(new_queries) == len(queries):
            return False
        self._write_json_list(REMY_QUERIES_PATH, new_queries)
        return True

    # --- Remy Listings ---

    async def list_remy_listings(
        self,
        source: Optional[str] = None,
        query_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        new_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RemyListing]:
        listings = self._read_json_list(REMY_LISTINGS_PATH, RemyListing)
        if source:
            listings = [l for l in listings if l.source == source]
        if query_id:
            listings = [l for l in listings if l.query_id == query_id]
        if is_active is not None:
            listings = [l for l in listings if l.is_active == is_active]
        if search:
            q = search.lower()
            listings = [l for l in listings if q in l.title.lower() or q in l.company.lower()]
        if new_only:
            cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
            listings = [l for l in listings if l.is_active and l.first_seen_at >= cutoff]
        listings.sort(key=lambda l: l.last_seen_at, reverse=True)
        return listings[offset:offset + limit]

    async def get_remy_listing(self, listing_id: str) -> Optional[RemyListing]:
        for l in self._read_json_list(REMY_LISTINGS_PATH, RemyListing):
            if l.id == listing_id:
                return l
        return None

    async def get_remy_listing_by_url(self, url: str) -> Optional[RemyListing]:
        for l in self._read_json_list(REMY_LISTINGS_PATH, RemyListing):
            if l.url == url:
                return l
        return None

    async def save_remy_listing(self, listing: RemyListing) -> None:
        listing.last_seen_at = _now()
        listings = self._read_json_list(REMY_LISTINGS_PATH, RemyListing)
        for i, l in enumerate(listings):
            if l.id == listing.id:
                listings[i] = listing
                break
        else:
            listings.append(listing)
        self._write_json_list(REMY_LISTINGS_PATH, listings)

    # --- Remy Tasks ---

    async def list_remy_tasks(self) -> list[RemyTask]:
        return self._read_json_list(REMY_TASKS_PATH, RemyTask)

    async def get_remy_task(self, task_id: str) -> Optional[RemyTask]:
        for t in await self.list_remy_tasks():
            if t.id == task_id:
                return t
        return None

    async def save_remy_task(self, task: RemyTask) -> None:
        task.updated_at = _now()
        tasks = await self.list_remy_tasks()
        for i, t in enumerate(tasks):
            if t.id == task.id:
                tasks[i] = task
                break
        else:
            tasks.append(task)
        self._write_json_list(REMY_TASKS_PATH, tasks)

    async def delete_remy_task(self, task_id: str) -> bool:
        tasks = await self.list_remy_tasks()
        new_tasks = [t for t in tasks if t.id != task_id]
        if len(new_tasks) == len(tasks):
            return False
        self._write_json_list(REMY_TASKS_PATH, new_tasks)
        return True

    # --- Remy Runs ---

    async def list_remy_runs(
        self,
        task_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RemyRun]:
        runs = self._read_json_list(REMY_RUNS_PATH, RemyRun)
        if task_id:
            runs = [r for r in runs if r.task_id == task_id]
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[offset:offset + limit]

    async def get_remy_run(self, run_id: str) -> Optional[RemyRun]:
        for r in self._read_json_list(REMY_RUNS_PATH, RemyRun):
            if r.id == run_id:
                return r
        return None

    async def save_remy_run(self, run: RemyRun) -> None:
        runs = self._read_json_list(REMY_RUNS_PATH, RemyRun)
        for i, r in enumerate(runs):
            if r.id == run.id:
                runs[i] = run
                break
        else:
            runs.append(run)
        self._write_json_list(REMY_RUNS_PATH, runs)

    # --- Remy Reports ---

    async def list_remy_reports(self, query_id: Optional[str] = None) -> list[RemyReport]:
        reports = self._read_json_list(REMY_REPORTS_PATH, RemyReport)
        if query_id:
            reports = [r for r in reports if r.query_id == query_id]
        reports.sort(key=lambda r: r.created_at, reverse=True)
        return reports

    async def get_remy_report(self, report_id: str) -> Optional[RemyReport]:
        for r in self._read_json_list(REMY_REPORTS_PATH, RemyReport):
            if r.id == report_id:
                return r
        return None

    async def save_remy_report(self, report: RemyReport) -> None:
        reports = self._read_json_list(REMY_REPORTS_PATH, RemyReport)
        for i, r in enumerate(reports):
            if r.id == report.id:
                reports[i] = report
                break
        else:
            reports.append(report)
        self._write_json_list(REMY_REPORTS_PATH, reports)