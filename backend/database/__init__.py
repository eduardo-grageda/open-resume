from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.config import AppConfig, load_config
from backend.models import BaseCV, OnboardingSession, Position


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