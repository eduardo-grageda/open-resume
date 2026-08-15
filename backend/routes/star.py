from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.config import load_config
from backend.database import get_storage
from backend.models import StarSession, StarStory
from backend.services.star import StarService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/star", tags=["star"])


@router.post("/start")
async def star_start(body: dict):
    storage = get_storage()
    config = load_config()

    if not config.openrouter_api_key:
        raise HTTPException(status_code=400, detail="AI provider not configured. Go to Settings.")

    cv = await storage.get_cv()
    if cv is None:
        raise HTTPException(status_code=400, detail="No base CV found. Create one first.")

    first_name = cv.personal_info.first_name or body.get("first_name", "")
    last_name = cv.personal_info.last_name or body.get("last_name", "")
    target_role = body.get("target_role", "")

    session = StarSession(
        state="in_progress",
        first_name=first_name,
        last_name=last_name,
        target_role=target_role,
    )

    service = StarService()
    result = await service.start_session(session, cv, target_role)

    await storage.save_star_session(session)

    return {
        "session_id": session.id,
        "question": result.get("question", ""),
        "phase": result.get("phase", ""),
        "star_step": result.get("star_step", ""),
        "done": result.get("done", False),
        "stories": result.get("stories", []),
        "retries": result.get("retries", 0),
    }


@router.post("/answer")
async def star_answer(body: dict):
    storage = get_storage()

    session_id = body.get("session_id")
    answer = body.get("answer", "")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = await storage.get_star_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.state != "in_progress":
        raise HTTPException(status_code=400, detail="Session is already complete")

    service = StarService()
    result = await service.process_answer(session, answer)

    await storage.save_star_session(session)

    return {
        "question": result.get("question"),
        "phase": result.get("phase", ""),
        "star_step": result.get("star_step", ""),
        "done": result.get("done", False),
        "message": result.get("message"),
        "stories": result.get("stories", []),
        "retries": result.get("retries", 0),
    }


@router.post("/confirm")
async def star_confirm(body: dict):
    storage = get_storage()

    session_id = body.get("session_id")
    confirmed_stories = body.get("confirmed_stories")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = await storage.get_star_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stories_to_save = confirmed_stories if confirmed_stories else session.extracted_stories

    if stories_to_save:
        service = StarService()
        session.extracted_stories = stories_to_save
        stories_with_pitches = await service.generate_pitches(session)
    else:
        stories_with_pitches = stories_to_save

    saved: list[dict] = []
    for story_data in stories_with_pitches:
        story = StarStory(
            id=story_data.get("id") or StarStory.model_fields["id"].default_factory(),
            title=story_data.get("title", ""),
            source_company=story_data.get("source_company", ""),
            source_title=story_data.get("source_title", ""),
            situation=story_data.get("situation", ""),
            task=story_data.get("task", ""),
            action=story_data.get("action", ""),
            result=story_data.get("result", ""),
            interview_pitch=story_data.get("interview_pitch", ""),
        )
        await storage.save_star_story(story)
        saved.append(story.model_dump())

    await storage.delete_star_session(session_id)

    return {"ok": True, "stories": saved}


@router.get("/stories")
async def list_stories():
    storage = get_storage()
    stories = await storage.list_star_stories()
    return {"stories": [s.model_dump() for s in stories]}


@router.get("/stories/{story_id}")
async def get_story(story_id: str):
    storage = get_storage()
    story = await storage.get_star_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"story": story.model_dump()}


@router.put("/stories/{story_id}")
async def update_story(story_id: str, body: dict):
    storage = get_storage()
    story = await storage.get_star_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    for field in ("title", "source_company", "source_title", "situation", "task", "action", "result", "interview_pitch"):
        if field in body:
            setattr(story, field, body[field])

    await storage.save_star_story(story)
    return {"story": story.model_dump()}


@router.delete("/stories/{story_id}")
async def delete_story(story_id: str):
    storage = get_storage()
    deleted = await storage.delete_star_story(story_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"ok": True}


@router.post("/generate-pitch/{story_id}")
async def generate_pitch(story_id: str):
    storage = get_storage()
    story = await storage.get_star_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    from backend.models import StarSession
    session = StarSession(
        state="complete",
        first_name="",
        last_name="",
        extracted_stories=[story.model_dump()],
    )

    service = StarService()
    stories_with_pitches = await service.generate_pitches(session)

    if stories_with_pitches:
        pitch = stories_with_pitches[0].get("interview_pitch", "")
        story.interview_pitch = pitch
        await storage.save_star_story(story)

    return {"story": story.model_dump()}