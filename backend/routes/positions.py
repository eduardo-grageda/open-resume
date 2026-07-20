from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_storage, StorageBackend
from backend.models import Position

router = APIRouter(prefix="/api/positions", tags=["positions"])


async def _get_storage() -> StorageBackend:
    return get_storage()


@router.get("")
async def list_positions(
    company: str | None = None,
    status: str | None = None,
    storage: StorageBackend = Depends(_get_storage),
):
    positions = await storage.list_positions(company=company, status=status)
    return {"positions": [p.model_dump() for p in positions]}


@router.post("")
async def create_position(body: Position, storage: StorageBackend = Depends(_get_storage)):
    await storage.save_position(body)
    return {"position": body.model_dump()}


@router.get("/{position_id}")
async def get_position(position_id: str, storage: StorageBackend = Depends(_get_storage)):
    pos = await storage.get_position(position_id)
    if pos is None:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"position": pos.model_dump()}


@router.put("/{position_id}")
async def update_position(position_id: str, body: Position, storage: StorageBackend = Depends(_get_storage)):
    existing = await storage.get_position(position_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Position not found")
    body.id = position_id
    await storage.save_position(body)
    return {"position": body.model_dump()}


@router.delete("/{position_id}")
async def delete_position(position_id: str, storage: StorageBackend = Depends(_get_storage)):
    deleted = await storage.delete_position(position_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"ok": True}
