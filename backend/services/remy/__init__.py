from __future__ import annotations

import logging
from typing import Optional

from backend.config import AppConfig
from backend.services.remy.base import ScraperSkill

logger = logging.getLogger(__name__)

_skills: dict[str, type[ScraperSkill]] = {}
_loaded = False


def _ensure_loaded() -> None:
    """Import built-in skill modules so they register in the dict."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        from backend.services.remy import aggregator, linkedin, occ  # noqa: F401
        _ = (aggregator, linkedin, occ)
    except ImportError as e:
        logger.warning("Could not load one or more Remy skills: %s", e)
    except Exception as e:
        logger.warning("Unexpected error loading Remy skills: %s", e)


def register(cls: type[ScraperSkill]) -> type[ScraperSkill]:
    """Class decorator: register a ScraperSkill implementation (and any aliases)."""
    if not cls.name:
        raise ValueError(f"ScraperSkill {cls.__name__} must define a non-empty `name`")
    _skills[cls.name] = cls
    for alias in getattr(cls, "aliases", ()):
        if alias and alias != cls.name:
            _skills[alias] = cls
    return cls


def get_skill(name: str) -> Optional[ScraperSkill]:
    """Return an instance of the named skill, or None if not implemented."""
    _ensure_loaded()
    cls = _skills.get(name)
    return cls() if cls else None


def available_skills() -> list[str]:
    """Names of all implemented (registered) skills, including aliases."""
    _ensure_loaded()
    return sorted(_skills.keys())


def skill_info() -> list[dict]:
    """Return metadata for each registered canonical skill (aliases merged)."""
    _ensure_loaded()
    infos: list[dict] = []
    seen: set[str] = set()
    for name, cls in sorted(_skills.items()):
        if name != cls.name or cls.name in seen:
            continue
        seen.add(cls.name)
        infos.append({
            "name": cls.name,
            "display_name": getattr(cls, "display_name", "") or cls.name,
            "description": getattr(cls, "description", ""),
            "tos_notice": getattr(cls, "tos_notice", ""),
            "aliases": list(getattr(cls, "aliases", ())),
        })
    return infos


def enabled_sources(config: AppConfig) -> list[str]:
    """Parse config.remy_sources into a clean list of source names."""
    return [s.strip() for s in config.remy_sources.split(",") if s.strip()]