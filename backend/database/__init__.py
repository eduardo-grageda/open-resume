from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.config import AppConfig, load_config
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


class StorageBackend(ABC):

    # --- Base CV ---
    @abstractmethod
    async def get_cv(self) -> Optional[BaseCV]:
        ...

    @abstractmethod
    async def save_cv(self, cv: BaseCV) -> None:
        ...

    # --- Settings ---
    @abstractmethod
    async def get_config(self) -> AppConfig:
        ...

    @abstractmethod
    async def save_config(self, config: AppConfig) -> None:
        ...

    # --- Positions ---
    @abstractmethod
    async def list_positions(self, company: Optional[str] = None, status: Optional[str] = None) -> list[Position]:
        ...

    @abstractmethod
    async def get_position(self, position_id: str) -> Optional[Position]:
        ...

    @abstractmethod
    async def save_position(self, position: Position) -> None:
        ...

    @abstractmethod
    async def delete_position(self, position_id: str) -> bool:
        ...

    # --- Onboarding ---
    @abstractmethod
    async def get_onboarding_session(self, session_id: str) -> Optional[OnboardingSession]:
        ...

    @abstractmethod
    async def save_onboarding_session(self, session: OnboardingSession) -> None:
        ...

    @abstractmethod
    async def delete_onboarding_session(self, session_id: str) -> None:
        ...

    # --- STAR ---
    @abstractmethod
    async def get_star_session(self, session_id: str) -> Optional[StarSession]:
        ...

    @abstractmethod
    async def save_star_session(self, session: StarSession) -> None:
        ...

    @abstractmethod
    async def delete_star_session(self, session_id: str) -> None:
        ...

    @abstractmethod
    async def list_star_stories(self) -> list[StarStory]:
        ...

    @abstractmethod
    async def get_star_story(self, story_id: str) -> Optional[StarStory]:
        ...

    @abstractmethod
    async def save_star_story(self, story: StarStory) -> None:
        ...

    @abstractmethod
    async def delete_star_story(self, story_id: str) -> bool:
        ...

    # --- Remy Queries ---

    @abstractmethod
    async def list_remy_queries(self) -> list[RemyQuery]:
        ...

    @abstractmethod
    async def get_remy_query(self, query_id: str) -> Optional[RemyQuery]:
        ...

    @abstractmethod
    async def save_remy_query(self, query: RemyQuery) -> None:
        ...

    @abstractmethod
    async def delete_remy_query(self, query_id: str) -> bool:
        ...

    # --- Remy Listings ---

    @abstractmethod
    async def list_remy_listings(
        self,
        source: Optional[str] = None,
        query_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RemyListing]:
        ...

    @abstractmethod
    async def get_remy_listing(self, listing_id: str) -> Optional[RemyListing]:
        ...

    @abstractmethod
    async def get_remy_listing_by_url(self, url: str) -> Optional[RemyListing]:
        ...

    @abstractmethod
    async def save_remy_listing(self, listing: RemyListing) -> None:
        ...

    # --- Remy Tasks ---

    @abstractmethod
    async def list_remy_tasks(self) -> list[RemyTask]:
        ...

    @abstractmethod
    async def get_remy_task(self, task_id: str) -> Optional[RemyTask]:
        ...

    @abstractmethod
    async def save_remy_task(self, task: RemyTask) -> None:
        ...

    @abstractmethod
    async def delete_remy_task(self, task_id: str) -> bool:
        ...

    # --- Remy Runs ---

    @abstractmethod
    async def list_remy_runs(
        self,
        task_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RemyRun]:
        ...

    @abstractmethod
    async def get_remy_run(self, run_id: str) -> Optional[RemyRun]:
        ...

    @abstractmethod
    async def save_remy_run(self, run: RemyRun) -> None:
        ...

    # --- Remy Reports ---

    @abstractmethod
    async def list_remy_reports(self, query_id: Optional[str] = None) -> list[RemyReport]:
        ...

    @abstractmethod
    async def get_remy_report(self, report_id: str) -> Optional[RemyReport]:
        ...

    @abstractmethod
    async def save_remy_report(self, report: RemyReport) -> None:
        ...


_config: Optional[AppConfig] = None


def _get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_storage() -> StorageBackend:
    config = _get_config()
    if config.storage_backend == "mongodb":
        from backend.database.mongo_store import MongoStore
        return MongoStore(config)
    from backend.database.json_store import JsonStore
    return JsonStore()