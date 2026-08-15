from __future__ import annotations

from typing import Optional

from backend.config import AppConfig
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


class MongoStore(StorageBackend):

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._client = None
        self._db = None

    async def _ensure_connected(self) -> None:
        if self._client is not None:
            return
        from pymongo import AsyncMongoClient
        self._client = AsyncMongoClient(self._config.mongo_uri)
        self._db = self._client["open_resume"]

    async def _collection(self, name: str):
        await self._ensure_connected()
        return self._db[name]

    # --- Base CV ---

    async def get_cv(self) -> Optional[BaseCV]:
        col = await self._collection("base_cv")
        doc = await col.find_one({"_type": "base_cv"})
        if doc is None:
            return None
        doc.pop("_id", None)
        doc.pop("_type", None)
        return BaseCV(**doc)

    async def save_cv(self, cv: BaseCV) -> None:
        col = await self._collection("base_cv")
        cv.updated_at = _now()
        data = cv.model_dump()
        data["_type"] = "base_cv"
        await col.replace_one({"_type": "base_cv"}, data, upsert=True)

    # --- Settings ---

    async def get_config(self) -> AppConfig:
        col = await self._collection("config")
        doc = await col.find_one({"_type": "config"})
        if doc is None:
            return load_config()
        doc.pop("_id", None)
        doc.pop("_type", None)
        return AppConfig(**doc)

    async def save_config(self, config: AppConfig) -> None:
        col = await self._collection("config")
        data = config.model_dump()
        data["_type"] = "config"
        await col.replace_one({"_type": "config"}, data, upsert=True)

    # --- Positions ---

    async def list_positions(self, company: Optional[str] = None, status: Optional[str] = None) -> list[Position]:
        col = await self._collection("positions")
        query: dict = {}
        if company:
            query["company_name"] = {"$regex": company, "$options": "i"}
        if status:
            query["status"] = status
        cursor = col.find(query)
        results: list[Position] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(Position(**doc))
        return results

    async def get_position(self, position_id: str) -> Optional[Position]:
        col = await self._collection("positions")
        doc = await col.find_one({"id": position_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return Position(**doc)

    async def save_position(self, position: Position) -> None:
        col = await self._collection("positions")
        position.updated_at = _now()
        data = position.model_dump()
        await col.replace_one({"id": position.id}, data, upsert=True)

    async def delete_position(self, position_id: str) -> bool:
        col = await self._collection("positions")
        result = await col.delete_one({"id": position_id})
        return result.deleted_count > 0

    # --- Onboarding ---

    async def get_onboarding_session(self, session_id: str) -> Optional[OnboardingSession]:
        col = await self._collection("onboarding_sessions")
        doc = await col.find_one({"id": session_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return OnboardingSession(**doc)

    async def save_onboarding_session(self, session: OnboardingSession) -> None:
        col = await self._collection("onboarding_sessions")
        data = session.model_dump()
        await col.replace_one({"id": session.id}, data, upsert=True)

    async def delete_onboarding_session(self, session_id: str) -> None:
        col = await self._collection("onboarding_sessions")
        await col.delete_one({"id": session_id})

    # --- STAR ---

    async def get_star_session(self, session_id: str) -> Optional[StarSession]:
        col = await self._collection("star_sessions")
        doc = await col.find_one({"id": session_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return StarSession(**doc)

    async def save_star_session(self, session: StarSession) -> None:
        col = await self._collection("star_sessions")
        data = session.model_dump()
        await col.replace_one({"id": session.id}, data, upsert=True)

    async def delete_star_session(self, session_id: str) -> None:
        col = await self._collection("star_sessions")
        await col.delete_one({"id": session_id})

    async def list_star_stories(self) -> list[StarStory]:
        col = await self._collection("star_stories")
        cursor = col.find({})
        results: list[StarStory] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(StarStory(**doc))
        return results

    async def get_star_story(self, story_id: str) -> Optional[StarStory]:
        col = await self._collection("star_stories")
        doc = await col.find_one({"id": story_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return StarStory(**doc)

    async def save_star_story(self, story: StarStory) -> None:
        col = await self._collection("star_stories")
        story.updated_at = _now()
        data = story.model_dump()
        await col.replace_one({"id": story.id}, data, upsert=True)

    async def delete_star_story(self, story_id: str) -> bool:
        col = await self._collection("star_stories")
        result = await col.delete_one({"id": story_id})
        return result.deleted_count > 0

    # --- Remy Queries ---

    async def list_remy_queries(self) -> list[RemyQuery]:
        col = await self._collection("remy_queries")
        cursor = col.find({})
        results: list[RemyQuery] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(RemyQuery(**doc))
        return results

    async def get_remy_query(self, query_id: str) -> Optional[RemyQuery]:
        col = await self._collection("remy_queries")
        doc = await col.find_one({"id": query_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RemyQuery(**doc)

    async def save_remy_query(self, query: RemyQuery) -> None:
        col = await self._collection("remy_queries")
        query.updated_at = _now()
        await col.replace_one({"id": query.id}, query.model_dump(), upsert=True)

    async def delete_remy_query(self, query_id: str) -> bool:
        col = await self._collection("remy_queries")
        result = await col.delete_one({"id": query_id})
        return result.deleted_count > 0

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
        from datetime import datetime, timedelta

        col = await self._collection("remy_listings")
        query: dict = {}
        if source:
            query["source"] = source
        if query_id:
            query["query_id"] = query_id
        if is_active is not None:
            query["is_active"] = is_active
        if search:
            pattern = {"$regex": search, "$options": "i"}
            query["$or"] = [{"title": pattern}, {"company": pattern}]
        if new_only:
            query["is_active"] = True
            query["first_seen_at"] = {
                "$gte": (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
            }
        cursor = col.find(query).sort("last_seen_at", -1).skip(offset).limit(limit)
        results: list[RemyListing] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(RemyListing(**doc))
        return results

    async def get_remy_listing(self, listing_id: str) -> Optional[RemyListing]:
        col = await self._collection("remy_listings")
        doc = await col.find_one({"id": listing_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RemyListing(**doc)

    async def get_remy_listing_by_url(self, url: str) -> Optional[RemyListing]:
        col = await self._collection("remy_listings")
        doc = await col.find_one({"url": url})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RemyListing(**doc)

    async def save_remy_listing(self, listing: RemyListing) -> None:
        col = await self._collection("remy_listings")
        listing.last_seen_at = _now()
        await col.replace_one({"id": listing.id}, listing.model_dump(), upsert=True)

    # --- Remy Tasks ---

    async def list_remy_tasks(self) -> list[RemyTask]:
        col = await self._collection("remy_tasks")
        cursor = col.find({})
        results: list[RemyTask] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(RemyTask(**doc))
        return results

    async def get_remy_task(self, task_id: str) -> Optional[RemyTask]:
        col = await self._collection("remy_tasks")
        doc = await col.find_one({"id": task_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RemyTask(**doc)

    async def save_remy_task(self, task: RemyTask) -> None:
        col = await self._collection("remy_tasks")
        task.updated_at = _now()
        await col.replace_one({"id": task.id}, task.model_dump(), upsert=True)

    async def delete_remy_task(self, task_id: str) -> bool:
        col = await self._collection("remy_tasks")
        result = await col.delete_one({"id": task_id})
        return result.deleted_count > 0

    # --- Remy Runs ---

    async def list_remy_runs(
        self,
        task_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RemyRun]:
        col = await self._collection("remy_runs")
        query: dict = {}
        if task_id:
            query["task_id"] = task_id
        cursor = col.find(query).sort("started_at", -1).skip(offset).limit(limit)
        results: list[RemyRun] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(RemyRun(**doc))
        return results

    async def get_remy_run(self, run_id: str) -> Optional[RemyRun]:
        col = await self._collection("remy_runs")
        doc = await col.find_one({"id": run_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RemyRun(**doc)

    async def save_remy_run(self, run: RemyRun) -> None:
        col = await self._collection("remy_runs")
        await col.replace_one({"id": run.id}, run.model_dump(), upsert=True)

    # --- Remy Reports ---

    async def list_remy_reports(self, query_id: Optional[str] = None) -> list[RemyReport]:
        col = await self._collection("remy_reports")
        query: dict = {}
        if query_id:
            query["query_id"] = query_id
        cursor = col.find(query).sort("created_at", -1)
        results: list[RemyReport] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(RemyReport(**doc))
        return results

    async def get_remy_report(self, report_id: str) -> Optional[RemyReport]:
        col = await self._collection("remy_reports")
        doc = await col.find_one({"id": report_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RemyReport(**doc)

    async def save_remy_report(self, report: RemyReport) -> None:
        col = await self._collection("remy_reports")
        await col.replace_one({"id": report.id}, report.model_dump(), upsert=True)


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


def load_config() -> AppConfig:
    from backend.config import load_config as _lc
    return _lc()