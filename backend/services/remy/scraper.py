from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.config import load_config
from backend.database import StorageBackend
from backend.models import RemyListing, RemyQuery
from backend.services.remy import enabled_sources, get_skill

logger = logging.getLogger(__name__)


@dataclass
class ScrapeStats:
    source: str
    found: int = 0
    new: int = 0
    updated: int = 0
    error: str = ""


@dataclass
class ScrapeResult:
    query_id: str
    listings_found: int = 0
    new_listings: int = 0
    by_source: list[ScrapeStats] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


async def _resolve_sources(query: RemyQuery) -> list[str]:
    config = load_config()
    configured = enabled_sources(config)
    requested = [s for s in query.sources if s] if query.sources else configured
    from backend.services.remy import available_skills

    available = set(available_skills())
    resolved = [s for s in requested if s in available]
    if not resolved:
        resolved = [s for s in configured if s in available]
    return resolved


async def _populate_listing(raw: dict, query_id: str, source: str) -> RemyListing:
    return RemyListing(
        source=source,
        query_id=query_id,
        title=str(raw.get("title", "")).strip(),
        company=str(raw.get("company", "")).strip(),
        location=str(raw.get("location", "")).strip(),
        url=str(raw.get("url", "")).strip(),
        salary=str(raw.get("salary", "")).strip(),
        description_md=str(raw.get("description_md", "")).strip(),
        posted_date=str(raw.get("posted_date", "")).strip(),
    )


async def run_query(
    query: RemyQuery,
    storage: StorageBackend,
    *,
    limit: int = 20,
) -> ScrapeResult:
    """Execute all enabled+suitable scraper skills for a query, dedup+upsert listings."""
    from backend.services.remy.utils import normalize_url

    result = ScrapeResult(query_id=query.id)
    sources = await _resolve_sources(query)

    for source_name in sources:
        skill = get_skill(source_name)
        if skill is None:
            result.errors.append(f"{source_name}: skill not implemented")
            continue
        source_stats = ScrapeStats(source=source_name)
        seen_urls: set[str] = set()
        try:
            raw_list = await skill.search(query, limit=limit)
        except Exception as e:
            source_stats.error = str(e)
            result.by_source.append(source_stats)
            result.errors.append(f"{source_name}: {e}")
            logger.warning("Skill %s search failed: %s", source_name, e)
            continue

        for raw in raw_list:
            raw_url = (raw.get("url") or "").strip()
            if not raw_url:
                continue
            url = normalize_url(raw_url)
            if not url:
                continue
            seen_urls.add(url)
            source_stats.found += 1

            existing = await storage.get_remy_listing_by_url(url)
            if existing:
                changed = False
                if str(raw.get("title", "")).strip() and existing.title != str(raw.get("title", "")).strip():
                    existing.title = str(raw.get("title", "")).strip()
                    changed = True
                if str(raw.get("company", "")).strip() and existing.company != str(raw.get("company", "")).strip():
                    existing.company = str(raw.get("company", "")).strip()
                    changed = True
                if str(raw.get("location", "")).strip() and existing.location != str(raw.get("location", "")).strip():
                    existing.location = str(raw.get("location", "")).strip()
                    changed = True
                if str(raw.get("salary", "")).strip() and existing.salary != str(raw.get("salary", "")).strip():
                    existing.salary = str(raw.get("salary", "")).strip()
                    changed = True
                snippet = str(raw.get("description_md", "")).strip()
                if snippet and (not existing.description_md or snippet != existing.description_md):
                    existing.description_md = snippet
                    changed = True
                pd = str(raw.get("posted_date", "")).strip()
                if pd and existing.posted_date != pd:
                    existing.posted_date = pd
                    changed = True
                if not existing.is_active:
                    existing.is_active = True
                    changed = True
                if existing.query_id != query.id and not existing.query_id:
                    existing.query_id = query.id
                    changed = True
                if changed:
                    await storage.save_remy_listing(existing)
                    source_stats.updated += 1
            else:
                listing = await _populate_listing(raw, query.id, source_name)
                await storage.save_remy_listing(listing)
                source_stats.new += 1

        if not source_stats.error:
            try:
                await _mark_stale_inactive(storage, query.id, source_name, seen_urls)
            except Exception as e:
                logger.warning("Stale-marking failed for %s/%s: %s", query.id, source_name, e)

        result.by_source.append(source_stats)
        result.listings_found += source_stats.found
        result.new_listings += source_stats.new

    return result


async def _mark_stale_inactive(
    storage: StorageBackend,
    query_id: str,
    source: str,
    seen_urls: set[str],
) -> None:
    """Mark listings for this query+source as inactive if not seen in this run."""
    all_active = await storage.list_remy_listings(
        query_id=query_id,
        source=source,
        is_active=True,
        limit=10000,
        offset=0,
    )
    for listing in all_active:
        if listing.url not in seen_urls:
            listing.is_active = False
            await storage.save_remy_listing(listing)