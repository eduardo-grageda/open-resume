from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from backend.models import RemyQuery

logger = logging.getLogger(__name__)


class ScraperSkill(ABC):
    """Base class for Remy scraper skills.

    One skill per platform (OCC, LinkedIn, aggregator, ...). `search` returns
    normalized listing dicts; `fetch_detail` returns cleaned markdown for a
    listing page. Dedup and upsert happen at the service layer.
    """

    name: str = ""
    display_name: str = ""
    description: str = ""

    @abstractmethod
    async def search(self, query: RemyQuery, limit: int = 20) -> list[dict[str, Any]]:
        """Run a search against this skill's platform.

        Returns a list of normalized listing dicts with at least the keys:
        title, company, location, url, salary, description_md, posted_date.
        """
        ...

    @abstractmethod
    async def fetch_detail(self, url: str) -> str:
        """Fetch a listing page and return cleaned markdown."""
        ...
