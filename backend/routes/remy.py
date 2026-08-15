from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.config import load_config
from backend.database import get_storage, StorageBackend
from backend.models import RemyQuery, RemyQueryInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/remy", tags=["remy"])


async def _get_storage() -> StorageBackend:
    return get_storage()


def _require_remy_enabled() -> None:
    config = load_config()
    if not config.remy_enabled:
        raise HTTPException(status_code=404, detail="Remy agent is disabled")


@router.get("/sources")
async def list_sources():
    _require_remy_enabled()
    from backend.services.remy import available_skills, enabled_sources, skill_info

    config = load_config()
    enabled = enabled_sources(config)
    implemented = available_skills()

    infos: dict[str, dict] = {}
    for info in skill_info():
        infos[info["name"]] = info
        for alias in info.get("aliases", []):
            infos[alias] = info

    sources = []
    for name in sorted(set(enabled) | set(implemented)):
        info = infos.get(name, {})
        sources.append({
            "name": name,
            "enabled": name in enabled,
            "implemented": name in implemented,
            "display_name": info.get("display_name", ""),
            "description": info.get("description", ""),
            "tos_notice": info.get("tos_notice", ""),
        })
    return {"sources": sources, "enabled_sources": enabled, "implemented_skills": implemented}


@router.get("/queries")
async def list_queries(storage: StorageBackend = Depends(_get_storage)):
    _require_remy_enabled()
    queries = await storage.list_remy_queries()
    return {"queries": [q.model_dump() for q in queries]}


@router.post("/queries")
async def create_query(body: RemyQueryInput, storage: StorageBackend = Depends(_get_storage)):
    _require_remy_enabled()
    query = RemyQuery(**body.model_dump())
    await storage.save_remy_query(query)
    return {"query": query.model_dump()}


@router.get("/queries/{query_id}")
async def get_query(query_id: str, storage: StorageBackend = Depends(_get_storage)):
    _require_remy_enabled()
    query = await storage.get_remy_query(query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")
    return {"query": query.model_dump()}


@router.put("/queries/{query_id}")
async def update_query(query_id: str, body: RemyQueryInput, storage: StorageBackend = Depends(_get_storage)):
    _require_remy_enabled()
    existing = await storage.get_remy_query(query_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Query not found")
    data = body.model_dump()
    data["id"] = query_id
    data["created_at"] = existing.created_at
    query = RemyQuery(**data)
    await storage.save_remy_query(query)
    return {"query": query.model_dump()}


@router.delete("/queries/{query_id}")
async def delete_query(query_id: str, storage: StorageBackend = Depends(_get_storage)):
    _require_remy_enabled()
    deleted = await storage.delete_remy_query(query_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Query not found")
    return {"ok": True}


@router.post("/queries/{query_id}/scrape")
async def scrape_query(query_id: str, storage: StorageBackend = Depends(_get_storage)):
    _require_remy_enabled()
    query = await storage.get_remy_query(query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")
    if not query.enabled:
        raise HTTPException(status_code=400, detail="Query is disabled")

    from backend.models import RemyRun, _now
    from backend.services.remy.scraper import run_query

    run = RemyRun(task_id="", trigger="manual", status="running")
    await storage.save_remy_run(run)

    try:
        result = await run_query(query, storage)
    except Exception as e:
        logger.exception("Manual scrape for query %s failed", query_id)
        run.status = "failed"
        run.error = str(e)
        run.finished_at = _now()
        await storage.save_remy_run(run)
        raise HTTPException(status_code=502, detail=str(e)) from e

    run.listings_found = result.listings_found
    run.new_listings = result.new_listings
    run.status = "partial" if result.errors else "success"
    run.error = "; ".join(result.errors)
    run.log = "\n".join(
        f"{s.source}: found={s.found} new={s.new} updated={s.updated}"
        + (f" error={s.error}" if s.error else "")
        for s in result.by_source
    )
    run.finished_at = _now()
    await storage.save_remy_run(run)
    return {"run": run.model_dump(), "stats": result.by_source}


@router.get("/listings")
async def list_listings(
    source: Optional[str] = None,
    query_id: Optional[str] = None,
    active: Optional[bool] = None,
    new: bool = False,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    storage: StorageBackend = Depends(_get_storage),
):
    _require_remy_enabled()
    limit = max(1, min(limit, 500))
    listings = await storage.list_remy_listings(
        source=source,
        query_id=query_id,
        is_active=active,
        search=search,
        new_only=new,
        limit=limit,
        offset=offset,
    )
    return {"listings": [l.model_dump() for l in listings], "total": len(listings)}


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: str,
    refresh: bool = False,
    storage: StorageBackend = Depends(_get_storage),
):
    _require_remy_enabled()
    listing = await storage.get_remy_listing(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    refreshed = False
    if refresh and listing.url:
        from backend.services.remy import get_skill

        skill = get_skill(listing.source)
        if skill is not None:
            try:
                detail_md = await skill.fetch_detail(listing.url)
                if detail_md:
                    listing.description_md = detail_md
                    await storage.save_remy_listing(listing)
                    refreshed = True
            except Exception as e:
                logger.warning("Detail refresh failed for listing %s: %s", listing_id, e)

    return {"listing": listing.model_dump(), "refreshed": refreshed}
