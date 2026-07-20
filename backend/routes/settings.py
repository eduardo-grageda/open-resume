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


@router.post("/test-llm")
async def test_llm(storage: StorageBackend = Depends(_get_storage)):
    config = await storage.get_config()
    if not config.openrouter_api_key:
        raise HTTPException(status_code=400, detail="No API key configured")
    client = LLMClient(config)
    ok, detail = await client.test_connection()
    return {"ok": ok, "model": detail}