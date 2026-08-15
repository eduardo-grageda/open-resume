from __future__ import annotations

import logging
from typing import Optional

from backend.config import AppConfig
from backend.services.remy.base import ScraperSkill

logger = logging.getLogger(__name__)

_skills: dict[str, type[ScraperSkill]] = {}


def register(cls: type[ScraperSkill]) -> type[ScraperSkill]:
    """Class decorator: register a ScraperSkill implementation."""
    if not cls.name:
        raise ValueError(f"ScraperSkill {cls.__name__} must define a non-empty `name`")
    _skills[cls.name] = cls
    return cls


def get_skill(name: str) -> Optional[ScraperSkill]:
    """Return an instance of the named skill, or None if not implemented."""
    cls = _skills.get(name)
    return cls() if cls else None


def available_skills() -> list[str]:
    """Names of all implemented (registered) skills."""
    return sorted(_skills.keys())


def enabled_sources(config: AppConfig) -> list[str]:
    """Parse config.remy_sources into a clean list of source names."""
    return [s.strip() for s in config.remy_sources.split(",") if s.strip()]
