from __future__ import annotations

from typing import Optional

from backend.config import AppConfig
from backend.database import StorageBackend
from backend.models import BaseCV, OnboardingSession, Position


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


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


def load_config() -> AppConfig:
    from backend.config import load_config as _lc
    return _lc()