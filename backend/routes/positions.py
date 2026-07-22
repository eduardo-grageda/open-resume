from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from backend.config import DATA_DIR, load_config
from backend.database import get_storage, StorageBackend
from backend.models import Position, _now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/positions", tags=["positions"])
EXPORTS_DIR = DATA_DIR / "exports"


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


@router.post("/ingest-url")
async def ingest_url(body: dict, storage: StorageBackend = Depends(_get_storage)):
    url = (body.get("url") or "").strip()

    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    from backend.services.job_search import JobSearchService

    service = JobSearchService()

    try:
        jd_md = await service.extract_jd(url)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    position = Position(
        company_name="",
        job_title="",
        job_description_md=jd_md,
        job_source_url=url,
        job_source_type="url",
        status="new",
    )

    return {"position": position.model_dump()}


@router.post("/{position_id}/adapt")
async def adapt_position(position_id: str, storage: StorageBackend = Depends(_get_storage)):
    pos = await storage.get_position(position_id)
    if pos is None:
        raise HTTPException(status_code=404, detail="Position not found")

    config = load_config()
    if not config.openrouter_api_key:
        raise HTTPException(status_code=400, detail="AI provider not configured")

    cv = await storage.get_cv()
    if cv is None:
        raise HTTPException(status_code=400, detail="No base CV found. Create one first via onboarding or /api/cv.")

    from backend.services.adapter import AdapterService
    service = AdapterService()

    try:
        result = await service.adapt(cv, pos.job_description_md)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    pos.tailored_cv_md = result["tailored_cv_md"]
    pos.change_summary = result["change_summary"]
    pos.status = "tailored"
    pos.updated_at = _now()
    await storage.save_position(pos)

    return {
        "position": pos.model_dump(),
        "tailored_cv_md": result["tailored_cv_md"],
        "change_summary": result["change_summary"],
    }


@router.get("/{position_id}/export/md")
async def export_position_md(position_id: str, storage: StorageBackend = Depends(_get_storage)):
    pos = await storage.get_position(position_id)
    if pos is None:
        raise HTTPException(status_code=404, detail="Position not found")
    if not pos.tailored_cv_md:
        raise HTTPException(status_code=400, detail="No tailored CV to export")

    filename = f"{pos.company_slug or 'cv'}-tailored.md"
    return PlainTextResponse(
        content=pos.tailored_cv_md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{position_id}/export/pdf")
async def export_position_pdf(position_id: str, storage: StorageBackend = Depends(_get_storage)):
    pos = await storage.get_position(position_id)
    if pos is None:
        raise HTTPException(status_code=404, detail="Position not found")
    if not pos.tailored_cv_md:
        raise HTTPException(status_code=400, detail="No tailored CV to export")

    import markdown2
    from weasyprint import HTML

    md = pos.tailored_cv_md

    css = """
    @page {
        size: A4;
        margin: 2cm;
    }
    body {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.5;
        color: #1a1a1a;
    }
    h1 {
        font-size: 18pt;
        margin-bottom: 4pt;
    }
    h2 {
        font-size: 14pt;
        border-bottom: 1px solid #ddd;
        padding-bottom: 4pt;
        margin-top: 16pt;
    }
    h3 {
        font-size: 12pt;
    }
    ul, ol {
        padding-left: 1.2em;
    }
    hr {
        border: none;
        border-top: 1px solid #ddd;
        margin: 16pt 0;
    }
    """

    html_content = markdown2.markdown(md, extras=["fenced-code-blocks", "tables", "break-on-newline"])
    full_html = f"<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><style>{css}</style></head><body>{html_content}</body></html>"

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{pos.company_slug or 'cv'}-{position_id[:8]}.pdf"
    pdf_path = EXPORTS_DIR / filename

    HTML(string=full_html).write_pdf(str(pdf_path))

    pos.pdf_export_path = str(pdf_path.relative_to(DATA_DIR))
    pos.status = "exported"
    pos.updated_at = _now()
    await storage.save_position(pos)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
    )
