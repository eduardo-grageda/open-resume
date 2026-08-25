from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.config import AppConfig, config_file_exists, load_config, save_config
from backend.database import get_storage
from backend.database import StorageBackend
from backend.models import SettingsUpdate
from backend.services.llm import LLMClient

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_storage() -> StorageBackend:
    return get_storage()


@router.get("")
async def get_settings(storage: StorageBackend = Depends(_get_storage)):
    config = await storage.get_config()
    redacted = config.model_dump()
    if redacted.get("openrouter_api_key"):
        key = redacted["openrouter_api_key"]
        redacted["openrouter_api_key"] = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
    if redacted.get("search_api_key"):
        key = redacted["search_api_key"]
        redacted["search_api_key"] = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
    if redacted.get("google_places_api_key"):
        key = redacted["google_places_api_key"]
        redacted["google_places_api_key"] = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
    return {"config": redacted, "has_config": config_file_exists()}


@router.put("")
async def update_settings(body: SettingsUpdate, storage: StorageBackend = Depends(_get_storage)):
    current = await storage.get_config()
    updates = body.model_dump(exclude_none=True)
    merged = current.model_dump()
    merged.update(updates)
    new_config = AppConfig(**merged)
    await storage.save_config(new_config)
    return {"ok": True}


@router.post("/wipe-data")
async def wipe_data(storage: StorageBackend = Depends(_get_storage)):
    deleted = {
        "positions": 0,
        "remy_listings": 0,
        "remy_queries": 0,
        "remy_tasks": 0,
        "remy_runs": 0,
        "remy_reports": 0,
        "star_stories": 0,
    }

    positions = await storage.list_positions()
    for p in positions:
        await storage.delete_position(p.id)
    deleted["positions"] = len(positions)

    deleted["remy_listings"] = await storage.delete_all_remy_listings()

    queries = await storage.list_remy_queries()
    for q in queries:
        await storage.delete_remy_query(q.id)
    deleted["remy_queries"] = len(queries)

    tasks = await storage.list_remy_tasks()
    for t in tasks:
        await storage.delete_remy_task(t.id)
    deleted["remy_tasks"] = len(tasks)

    runs = await storage.list_remy_runs(limit=10000)
    deleted["remy_runs"] = len(runs)

    reports = await storage.list_remy_reports()
    deleted["remy_reports"] = len(reports)

    stories = await storage.list_star_stories()
    for s in stories:
        await storage.delete_star_story(s.id)
    deleted["star_stories"] = len(stories)

    cv = await storage.get_cv()
    if cv:
        cv_path = None
        try:
            from backend.config import DATA_DIR
            cv_path = DATA_DIR / "base_cv.json"
            if cv_path.exists():
                cv_path.unlink()
        except Exception:
            pass

    return {"ok": True, "deleted": deleted}


@router.post("/test-llm")
async def test_llm(storage: StorageBackend = Depends(_get_storage)):
    config = await storage.get_config()
    if not config.openrouter_api_key:
        raise HTTPException(status_code=400, detail="No API key configured")
    client = LLMClient(config)
    ok, detail = await client.test_connection()
    return {"ok": ok, "model": detail}