from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote

from bs4 import BeautifulSoup

from backend.models import RemyQuery
from backend.services.remy import register
from backend.services.remy.base import ScraperSkill
from backend.services.remy.utils import fetch_text, get_config, html_to_markdown, normalize_url, polite_sleep

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
POSTING_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
PAGE_SIZE = 10

TOS_NOTICE = (
    "LinkedIn results use the public guest job endpoints and are best-effort: they may be rate-limited "
    "or change without notice. Automated access to LinkedIn is restricted by its Terms of Service — "
    "use at your own risk and review https://www.linkedin.com/legal/user-agreement."
)


@register
class LinkedInSkill(ScraperSkill):
    """Public LinkedIn guest jobs search endpoint (HTML cards, no login)."""

    name = "linkedin"
    display_name = "LinkedIn (guest)"
    description = "Public guest job search on linkedin.com (jobs-guest API). No account required."
    tos_notice = TOS_NOTICE

    def __init__(self) -> None:
        self._config = get_config()

    @staticmethod
    def _parse_cards(html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        cards: list[dict[str, Any]] = []
        for card in soup.select("li div.base-card"):
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            location_el = card.select_one("span.job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            time_el = card.select_one("time")
            if not title_el or not link_el:
                continue
            href = link_el.get("href", "")
            url = normalize_url(href) if href else ""
            if not url:
                continue
            cards.append({
                "title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "url": url,
                "salary": "",
                "description_md": "",
                "posted_date": time_el.get("datetime", "") if time_el else "",
                "source": "linkedin",
            })
        return cards

    async def search(self, query: RemyQuery, limit: int = 20) -> list[dict[str, Any]]:
        if not query.keywords:
            raise RuntimeError("Query has no keywords")

        location = ""
        if query.remote_only:
            location = "Remote"
        elif query.locations:
            location = query.locations[0]

        params = {
            "keywords": " ".join(query.keywords),
            "start": "0",
        }
        if location:
            params["location"] = location

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        start = 0
        while len(results) < limit and start < 100:
            params["start"] = str(start)
            await polite_sleep(self._config)
            try:
                async with __import__("httpx").AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(SEARCH_URL, params=params, headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
                        "Accept": "text/html,application/xhtml+xml",
                    })
                    resp.raise_for_status()
                    html = resp.text
            except Exception as e:
                logger.warning("LinkedIn search failed at start=%s: %s", start, e)
                break

            page = self._parse_cards(html)
            if not page:
                break
            new = 0
            for item in page:
                if item["url"] in seen:
                    continue
                seen.add(item["url"])
                results.append(item)
                new += 1
            if new < PAGE_SIZE:
                break
            start += PAGE_SIZE

        return results[:limit]

    async def fetch_detail(self, url: str) -> str:
        match = re.search(r"/jobs/view/[^/]*?(\d+)", url)
        if not match:
            match = re.search(r"(\d{6,})", url)
        if not match:
            raise RuntimeError(f"Could not extract LinkedIn job ID from {url}")
        job_id = match.group(1)

        await polite_sleep(self._config)
        html = await fetch_text(POSTING_URL.format(job_id=job_id), headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        })

        soup = BeautifulSoup(html, "html.parser")
        description = soup.select_one("div.show-more-less-html__markup")
        if not description:
            return html_to_markdown(html)

        parts: list[str] = []
        title = soup.select_one("h2.top-card-layout__title")
        if title:
            parts.append(f"# {title.get_text(strip=True)}")
        company = soup.select_one("a.topcard__org-name-link")
        if company:
            parts.append(f"**{company.get_text(strip=True)}**")
        location = soup.select_one("span.topcard__flavor--bullet")
        if location:
            parts.append(f"*{location.get_text(strip=True)}*")
        parts.append("")
        parts.append(html_to_markdown(str(description)))
        return "\n".join(parts).strip()
