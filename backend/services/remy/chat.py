from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncIterator, Optional

from backend.config import load_config
from backend.database import get_storage
from backend.services.llm import LLMClient
from backend.services.remy.memory import get_remy_memory
from backend.services.remy.prompts import AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_CONTEXT_LISTINGS = 15
MAX_CONTEXT_REPORTS = 5
MAX_HISTORY_MESSAGES = 20


def _now() -> str:
    from backend.models import _now as model_now

    return model_now()


async def _build_context() -> str:
    """Collect current state (CV, queries, listings, reports) for the agent."""
    storage = get_storage()
    memory = get_remy_memory()
    parts: list[str] = []

    cv = await storage.get_cv()
    if cv is not None:
        from backend.services.remy.vectordb import cv_text

        parts.append("CANDIDATE CV (excerpt):\n" + cv_text(cv)[:5000])
    else:
        parts.append("CANDIDATE CV: none yet.")

    queries = await storage.list_remy_queries()
    if queries:
        q_lines = []
        for q in queries:
            cities = ", ".join(c.name for c in q.cities)
            q_lines.append(
                f"- [{q.id}] {q.name or 'unnamed'} | keywords: {', '.join(q.keywords) or '-'} "
                f"| cities: {cities} | enabled: {q.enabled}"
            )
        parts.append("SEARCH PROFILES:\n" + "\n".join(q_lines))
    else:
        parts.append("SEARCH PROFILES: none yet.")

    listings = await storage.list_remy_listings(is_active=True, limit=MAX_CONTEXT_LISTINGS)
    if listings:
        l_lines = []
        for l in listings:
            desc = (l.description_md or "").strip().replace("\n", " ")
            if len(desc) > 220:
                desc = desc[:220] + "…"
            l_lines.append(
                f"- [{l.id}] {l.title} — {l.company} ({l.location or 'n/a'}, {l.source})"
                + (f" | {desc}" if desc else "")
            )
        parts.append(f"RECENT LISTINGS ({len(listings)} shown):\n" + "\n".join(l_lines))
    else:
        parts.append("RECENT LISTINGS: none yet.")

    reports = await storage.list_remy_reports()
    if reports:
        r_lines = []
        for r in reports[:MAX_CONTEXT_REPORTS]:
            r_lines.append(f"- [{r.type}] report {r.id} (query {r.query_id})")
        parts.append("RECENT REPORTS:\n" + "\n".join(r_lines))

    profile = await memory.get_profile()
    signals = profile.get("market_signals", {})
    if signals.get("top_skills"):
        parts.append("MARKET SIGNALS (top skills seen in listings): " + ", ".join(signals["top_skills"][:15]))

    return "\n\n".join(parts)


async def stream_chat(
    message: str,
    thread_id: Optional[str] = None,
) -> AsyncIterator[dict]:
    """Stream a chat reply over SSE events. First event is {"type": "meta"}."""
    config = load_config()
    memory = get_remy_memory()

    thread = memory.get_thread(thread_id) if thread_id else None
    history: list[dict] = thread.get("messages", []) if thread else []
    thread_id = thread_id or uuid.uuid4().hex[:12]

    context = await _build_context()
    system = AGENT_SYSTEM_PROMPT + "\n\nCURRENT CONTEXT:\n" + context

    llm_messages = [{"role": m["role"], "content": m["content"]} for m in history[-MAX_HISTORY_MESSAGES:]]
    llm_messages.append({"role": "user", "content": message})

    yield {"type": "meta", "thread_id": thread_id}

    full_reply = ""
    try:
        client = LLMClient(config)
        async for delta in client.chat_stream(llm_messages, system=system):
            full_reply += delta
            yield {"type": "delta", "content": delta}
    except Exception as e:
        logger.exception("Remy chat stream failed")
        yield {"type": "error", "detail": str(e)}
        return

    history = [*history, {"role": "user", "content": message}, {"role": "assistant", "content": full_reply}]
    title = thread.get("title", "") if thread else ""
    if not title and len(message) > 4:
        title = message[:60]
    memory.save_thread(thread_id, history, title=title)
    yield {"type": "done"}


def get_thread(thread_id: str) -> Optional[dict]:
    return get_remy_memory().get_thread(thread_id)


def list_threads() -> list[dict]:
    return get_remy_memory().list_threads()


def delete_thread(thread_id: str) -> bool:
    return get_remy_memory().delete_thread(thread_id)
