from __future__ import annotations

import logging

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
    from backend.services.remy import available_skills, enabled_sources

    config = load_config()
    enabled = enabled_sources(config)
    implemented = available_skills()

    sources = [
        {
            "name": name,
            "enabled": name in enabled,
            "implemented": name in implemented,
        }
        for name in sorted(set(enabled) | set(implemented))
    ]
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
