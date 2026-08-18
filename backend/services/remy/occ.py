from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from backend.models import RemyQuery
from backend.services.remy import register
from backend.services.remy.base import ScraperSkill
from backend.services.remy.utils import (
    get_config,
    html_to_markdown,
    polite_sleep,
    slugify,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.occ.com.mx"

SEARCH_TEMPLATE = BASE_URL + "/empleos/{query_path}/"
LISTING_TEMPLATE = BASE_URL + "/empleo/oferta/{id}-{slug}"

OCC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

# Browser TLS/HTTP2 fingerprint to impersonate. OCC's Cloudflare config
# serves 403 "scraping abuse" to httpx-style clients regardless of headers
# or cookies; curl_cffi spoofs a real Chrome fingerprint and passes.
IMPERSONATE = "chrome"

_CHALLENGE_MARKERS = ("just a moment", "challenge-platform", "__cf_chl", "cf_chl_opt", "turnstile")


def _is_challenge(text: str, status_code: int) -> bool:
    if status_code in (403, 429):
        return True
    lowered = text[:4000].lower()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


async def _get_impersonated(session: Any, url: str) -> str:
    """GET a URL through a curl_cffi session with a browser fingerprint.

    If Cloudflare escalates to an interactive Turnstile challenge this
    raises RuntimeError; manual intervention then means solving the
    challenge in a real browser and exporting its cookies (not wired in).
    """
    def _run() -> str:
        resp = session.get(url, headers=OCC_HEADERS)
        if _is_challenge(resp.text, resp.status_code):
            raise RuntimeError(f"OCC bot challenge on {url} (HTTP {resp.status_code})")
        return resp.text

    return await asyncio.to_thread(_run)


@register
class OccSkill(ScraperSkill):
    """OCC Mundial (occ.com.mx) search results HTML parser.

    OCC's HTML structure changes occasionally; parse failures are logged as
    partial runs instead of crashing. See REMY_PHASES.md open question 2.
    """

    name = "occ"
    display_name = "OCC Mundial"
    description = "Direct HTML parser for occ.com.mx search results (public pages)."

    def __init__(self) -> None:
        self._config = get_config()

    @staticmethod
    def _build_search_path(query: RemyQuery) -> str:
        keyword = " ".join(query.keywords) if query.keywords else "empleos"
        slug = slugify(keyword)
        parts = ["de-" + slug]
        if query.cities:
            loc_slug = slugify(query.cities[0].name)
            parts.append("en-" + loc_slug)
        return "-".join(parts)

    @staticmethod
    def _parse_cards(html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        cards: list[dict[str, Any]] = []
        for card in soup.select("div.card-job-offer"):
            data_id = card.get("data-id", "")
            if not data_id:
                continue
            title_el = card.find("h2")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            data_id = str(data_id).strip()

            salary_el = None
            for sibling in card.children:
                if getattr(sibling, "name", None) == "span":
                    txt = sibling.get_text(strip=True)
                    if "sueldo" in txt.lower():
                        salary_el = sibling
                        break

            salary = ""
            if salary_el:
                salary = salary_el.get_text(strip=True)
                if "sueldo no mostrado" in salary.lower():
                    salary = ""

            company_link = card.select_one("span.line-clamp-title a") or card.select_one("a.line-clamp-title")
            company = ""
            if company_link:
                company = company_link.get_text(strip=True)
            else:
                conf = card.find(string=re.compile("Empresa confidencial"))
                if conf:
                    company = "Empresa confidencial"

            location_el = card.select_one("div.no-alter-loc-text p")
            location = location_el.get_text(strip=True) if location_el else ""

            posted_el = card.select_one("span.text-sm.font-light")
            posted_date = posted_el.get_text(strip=True) if posted_el else ""

            slug = slugify(title)
            url = LISTING_TEMPLATE.format(id=data_id, slug=slug)

            cards.append({
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "salary": salary,
                "description_md": "",
                "posted_date": posted_date,
                "source": "occ",
            })
        return cards

    async def search(self, query: RemyQuery, limit: int = 20) -> list[dict[str, Any]]:
        path = self._build_search_path(query)
        url = SEARCH_TEMPLATE.format(query_path=path)

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        page = 1
        session = cffi_requests.Session(impersonate=IMPERSONATE, timeout=30.0)
        try:
            while len(results) < limit and page <= 5:
                paged_url = f"{url}?page={page}" if page > 1 else url
                await polite_sleep(self._config)
                try:
                    html = await _get_impersonated(session, paged_url)
                except RuntimeError as e:
                    logger.warning("OCC search page %s failed: %s", page, e)
                    break
                page_cards = self._parse_cards(html)
                if not page_cards:
                    break
                new = 0
                for item in page_cards:
                    if item["url"] in seen:
                        continue
                    seen.add(item["url"])
                    results.append(item)
                    new += 1
                if new < len(page_cards) and len(page_cards) > 0:
                    break
                page += 1
        finally:
            session.close()

        return results[:limit]

    async def fetch_detail(self, url: str) -> str:
        match = re.search(r"/empleo/oferta/(\d+)", url)
        if not match:
            raise RuntimeError(f"Not a recognized OCC listing URL: {url}")
        offer_id = match.group(1)
        slug = slugify(url.split("/")[-1] if "/" in url else "")
        detail_url = LISTING_TEMPLATE.format(id=offer_id, slug=slug)

        await polite_sleep(self._config)
        session = cffi_requests.Session(impersonate=IMPERSONATE, timeout=30.0)
        try:
            try:
                html = await _get_impersonated(session, detail_url)
                return html_to_markdown(html)
            except RuntimeError:
                logger.info("OCC detail page %s behind Cloudflare — returning link-only stub", detail_url)
                return f"Full listing behind OCC's bot protection.\n\nView directly: [{detail_url}]({detail_url})"
        finally:
            session.close()