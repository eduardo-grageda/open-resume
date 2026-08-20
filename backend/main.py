from __future__ import annotations

import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("open-resume")


if __name__ == "__main__":
    import argparse
    import socket

    def _find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _get_app_data_dir() -> Path:
        if sys.platform == "linux":
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.cwd()
        return base / "open-resume"

    _parser = argparse.ArgumentParser(description="Open Resume backend")
    _parser.add_argument("--port", type=int, default=0, help="0 = find free port")
    _parser.add_argument("--data-dir", type=str, default=None, help="Data directory path")
    _cli_args = _parser.parse_args()

    if _cli_args.data_dir:
        os.environ["DATA_DIR"] = str(Path(_cli_args.data_dir).resolve())
    else:
        os.environ["DATA_DIR"] = str(_get_app_data_dir())

    _port = _cli_args.port if _cli_args.port > 0 else _find_free_port()
    print(f"PORT={_port}", flush=True)

    def _shutdown(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)


from backend.config import load_config
from backend.database import get_storage
from backend.routes.cv import router as cv_router
from backend.routes.positions import router as positions_router
from backend.routes.remy import router as remy_router
from backend.routes.search import router as search_router
from backend.routes.settings import router as settings_router
from backend.routes.star import router as star_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Open Resume backend")
    try:
        config = load_config()
        logger.info("Storage backend: %s", config.storage_backend)
    except Exception as e:
        logger.warning("Could not load config: %s", e)

    if load_config().remy_enabled:
        try:
            from backend.services.remy.scheduler import get_scheduler
            await get_scheduler().start()
        except Exception as e:
            logger.warning("Could not start Remy scheduler: %s", e)

    yield

    try:
        from backend.services.remy.scheduler import get_scheduler
        get_scheduler().stop()
    except Exception:
        pass
    logger.info("Shutting down Open Resume backend")


app = FastAPI(
    title="Open Resume",
    description="AI-powered CV manager and job hunter",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "tauri://localhost",
        "https://tauri.localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings_router)
app.include_router(cv_router)
app.include_router(positions_router)
app.include_router(search_router)
app.include_router(star_router)
app.include_router(remy_router)


@app.get("/api/health")
async def health():
    storage = get_storage()
    cv = await storage.get_cv()
    return {
        "status": "ok",
        "has_cv": cv is not None,
        "storage": (await storage.get_config()).storage_backend,
    }


@app.post("/api/shutdown")
async def api_shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "shutting_down"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=_port)