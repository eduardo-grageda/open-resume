from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_config
from backend.database import get_storage
from backend.routes.cv import router as cv_router
from backend.routes.positions import router as positions_router
from backend.routes.settings import router as settings_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("open-resume")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Open Resume backend")
    try:
        config = load_config()
        logger.info("Storage backend: %s", config.storage_backend)
    except Exception as e:
        logger.warning("Could not load config: %s", e)
    yield
    logger.info("Shutting down Open Resume backend")


app = FastAPI(
    title="Open Resume",
    description="AI-powered CV manager and job hunter",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings_router)
app.include_router(cv_router)
app.include_router(positions_router)


@app.get("/api/health")
async def health():
    storage = get_storage()
    cv = await storage.get_cv()
    return {
        "status": "ok",
        "has_cv": cv is not None,
        "storage": (await storage.get_config()).storage_backend,
    }