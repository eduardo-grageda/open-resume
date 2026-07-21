from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_storage, StorageBackend
from backend.models import SearchRequest, SearchImportRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


async def _get_storage() -> StorageBackend:
    return get_storage()


@router.post("/jobs")
async def search_jobs(body: SearchRequest, storage: StorageBackend = Depends(_get_storage)):
    config = await storage.get_config()
    if not config.search_api_key:
        raise HTTPException(status_code=400, detail="Search API key not configured. Add it in Settings.")

    from backend.services.job_search import JobSearchService
    service = JobSearchService()

    try:
        results = await service.search(
            query=body.query,
            location=body.location,
            remote=body.remote,
            job_type=body.job_type,
            experience_level=body.experience_level,
            date_posted=body.date_posted,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {"results": results}


@router.get("/sources")
async def list_sources():
    from backend.services.job_search import JobSearchService
    return {"sources": JobSearchService.get_available_sources()}


@router.post("/extract-jd")
async def extract_jd(body: dict, storage: StorageBackend = Depends(_get_storage)):
    url = body.get("url", "")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    config = await storage.get_config()
    if not config.openrouter_api_key:
        raise HTTPException(status_code=400, detail="AI provider not configured")

    from backend.services.job_search import JobSearchService
    service = JobSearchService()

    try:
        markdown = await service.extract_jd(url)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {"job_description_md": markdown}
