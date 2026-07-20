from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.database import get_storage
from backend.database import StorageBackend
from backend.models import BaseCV

router = APIRouter(prefix="/api/cv", tags=["cv"])


async def _get_storage() -> StorageBackend:
    return get_storage()


@router.get("")
async def get_cv(storage: StorageBackend = Depends(_get_storage)):
    cv = await storage.get_cv()
    if cv is None:
        return {"cv": None, "exists": False}
    return {"cv": cv.model_dump(), "exists": True}


@router.put("")
async def update_cv(body: BaseCV, storage: StorageBackend = Depends(_get_storage)):
    await storage.save_cv(body)
    return {"ok": True, "cv": body.model_dump()}


@router.post("/ingest-pdf")
async def ingest_pdf(file: UploadFile = File(...)):
    raise HTTPException(status_code=501, detail="PDF ingest not yet implemented")


@router.post("/ingest-pdf/confirm")
async def ingest_pdf_confirm(body: BaseCV, storage: StorageBackend = Depends(_get_storage)):
    raise HTTPException(status_code=501, detail="PDF ingest confirm not yet implemented")