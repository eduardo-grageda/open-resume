from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.database import get_storage
from backend.database import StorageBackend
from backend.models import BaseCV, ConversationMessage, OnboardingSession
from backend.services.onboarding import SECTIONS, SECTION_LABELS, OnboardingService

router = APIRouter(prefix="/api/cv", tags=["cv"])


async def _get_storage() -> StorageBackend:
    return get_storage()

# ═══════════════════════════════════════════════════════════════
# Base CV CRUD
# ═══════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════
# Onboarding
# ═══════════════════════════════════════════════════════════════


@router.post("/onboard/start")
async def onboard_start(
    body: dict,
    storage: StorageBackend = Depends(_get_storage),
):
    first_name = (body.get("first_name") or "").strip()
    last_name = (body.get("last_name") or "").strip()
    target_role = (body.get("target_role") or "professional").strip()

    if not first_name:
        raise HTTPException(status_code=400, detail="first_name is required")

    service = OnboardingService()
    session = OnboardingSession()
    session.extracted_data = {"personal_info": {"first_name": first_name, "last_name": last_name}}
    session.conversation_history = []
    session.current_section = "personal_info"

    result = await service.start_session(session, first_name, last_name, target_role)

    session.current_section = result.get("section", session.current_section)
    session.extracted_data = result.get("extracted_data", session.extracted_data)

    await storage.save_onboarding_session(session)

    return {
        "session_id": session.id,
        "question": result.get("question", ""),
        "section": session.current_section,
        "done": result.get("done", False),
        "completed_sections": result.get("completed_sections", []),
        "total_sections": result.get("total_sections", len(SECTIONS)),
        "extracted_data": session.extracted_data,
    }


@router.post("/onboard/answer")
async def onboard_answer(
    body: dict,
    storage: StorageBackend = Depends(_get_storage),
):
    session_id = (body.get("session_id") or "").strip()
    answer = (body.get("answer") or "").strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not answer:
        raise HTTPException(status_code=400, detail="answer is required")

    session = await storage.get_onboarding_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state == "complete":
        raise HTTPException(status_code=400, detail="Session is already complete")

    pi = session.extracted_data.get("personal_info", {})
    first_name = pi.get("first_name", "")
    last_name = pi.get("last_name", "")
    target_role = "professional"

    service = OnboardingService()
    result = await service.process_answer(session, answer, first_name, last_name, target_role)

    session.current_section = result.get("section", session.current_section)
    session.extracted_data = result.get("extracted_data", session.extracted_data)
    if result.get("done"):
        session.state = "complete"

    await storage.save_onboarding_session(session)

    return {
        "session_id": session.id,
        "question": result.get("question"),
        "section": session.current_section,
        "done": result.get("done", False),
        "message": result.get("message"),
        "completed_sections": result.get("completed_sections", []),
        "total_sections": result.get("total_sections", len(SECTIONS)),
        "extracted_data": session.extracted_data,
        "conversation_history": [m.model_dump() for m in session.conversation_history],
    }


@router.post("/onboard/confirm")
async def onboard_confirm(
    body: dict,
    storage: StorageBackend = Depends(_get_storage),
):
    session_id = (body.get("session_id") or "").strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = await storage.get_onboarding_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    service = OnboardingService()

    if "confirmed_data" in body and body["confirmed_data"]:
        session.extracted_data = body["confirmed_data"]

    base_cv = service.extracted_to_base_cv(session.extracted_data)
    await storage.save_cv(base_cv)
    await storage.delete_onboarding_session(session_id)

    return {
        "ok": True,
        "cv": base_cv.model_dump(),
    }


@router.get("/onboard/progress/{session_id}")
async def onboard_progress(
    session_id: str,
    storage: StorageBackend = Depends(_get_storage),
):
    session = await storage.get_onboarding_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    completed = [
        s for s in SECTIONS
        if OnboardingService._section_has_data(s, session.extracted_data)
    ]

    return {
        "session_id": session.id,
        "current_section": session.current_section,
        "completed_sections": completed,
        "total_sections": len(SECTIONS),
        "extracted_data": session.extracted_data,
        "conversation_history": [m.model_dump() for m in session.conversation_history],
    }
