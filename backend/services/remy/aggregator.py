from __future__ import annotations

import logging
from typing import Any

from backend.models import RemyQuery
from backend.services.remy.base import ScraperSkill
from backend.services.remy import register
from backend.services.remy.utils import get_config, html_to_markdown, normalize_url

logger = logging.getLogger(__name__)


@register
class AggregatorSkill(ScraperSkill):
    """Wraps the existing JobSearchService (SerpAPI/Brave) as a Remy skill."""

    name = "aggregator"
    display_name = "Aggregator (SerpAPI / Brave)"
    description = "Web search aggregation via the configured search provider (SerpAPI Google Jobs or Brave Search)."
    aliases = ("serpapi", "brave")

    def __init__(self) -> None:
        self._config = get_config()

    async def search(self, query: RemyQuery, limit: int = 20) -> list[dict[str, Any]]:
        from backend.services.job_search import JobSearchService

        if not self._config.search_api_key:
            raise RuntimeError("Search API key not configured")
        if not query.keywords:
            raise RuntimeError("Query has no keywords")

        service = JobSearchService()
        results = await service.search(
            query=" ".join(query.keywords),
            location=(query.locations[0] if query.locations else ""),
            remote=query.remote_only,
            experience_level=query.experience_level if query.experience_level != "any" else "",
        )
        provider = self._config.search_provider
        normalized: list[dict[str, Any]] = []
        for item in results:
            url = normalize_url(item.get("url", ""))
            if not url:
                continue
            normalized.append({
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "url": url,
                "salary": "",
                "description_md": item.get("description_snippet", ""),
                "posted_date": item.get("posted_date", ""),
                "source": provider,
            })
        return normalized[:limit]

    async def fetch_detail(self, url: str) -> str:
        from backend.services.job_search import JobSearchService

        service = JobSearchService()
        if self._config.openrouter_api_key:
            try:
                return await service.extract_jd(url)
            except Exception as e:
                logger.warning("LLM JD extraction failed for %s, falling back to HTML: %s", url, e)
        from backend.services.remy.utils import fetch_text

        html = await fetch_text(url)
        return html_to_markdown(html)
