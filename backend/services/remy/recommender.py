from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from backend.config import load_config
from backend.models import BaseCV, RemyListing, RemyQuery, RemyReport, RemyRun, RemyTopMatch, _now
from backend.services.llm import LLMClient
from backend.services.remy.prompts import RECOMMENDER_SYSTEM_PROMPT, build_recommender_messages

if TYPE_CHECKING:
    from backend.database import StorageBackend

logger = logging.getLogger(__name__)

PASS1_TOP = 20
PASS2_TOP = 10


@dataclass
class RecommendationResult:
    report: RemyReport
    listings_considered: int = 0


def _relative_score(sim: float, max_sim: float) -> int:
    if max_sim <= 0:
        return 0
    return max(0, min(100, round(100.0 * sim / max_sim)))


def _fallback_reason(sim: float, listing: RemyListing) -> str:
    parts = [f"{listing.title} at {listing.company}"]
    if listing.location:
        parts.append(f"in {listing.location}")
    return f"Vector similarity {sim:.2f} — {'. '.join(parts)}"


class RemyRecommender:
    """Two-pass recommendation: vector similarity then LLM scoring.

    Wired to the `recommender` sub-agent via `backend.services.remy.subagents`.
    """

    def __init__(self) -> None:
        self._config = load_config()

    @property
    def _llm(self) -> LLMClient:
        return LLMClient(self._config)

    async def run(
        self,
        query: RemyQuery,
        storage: StorageBackend,
        *,
        run_id: str = "",
    ) -> RecommendationResult:
        from backend.services.remy.vectordb import (
            Embedder,
            VectorStore,
            ensure_listing_embedded,
            get_cv_vector,
            local_embed,
        )

        listings = await storage.list_remy_listings(
            query_id=query.id, is_active=True, limit=500
        )
        if not listings:
            content = (
                "## Recommendations\n\n"
                "No active listings found for this search profile. "
                "Run a scrape first to get listings to recommend."
            )
            report = RemyReport(run_id=run_id, query_id=query.id, type="recommendation", content_md=content)
            await storage.save_remy_report(report)
            return RecommendationResult(report=report, listings_considered=0)

        embedder = Embedder()
        store = VectorStore()
        embedded: list[tuple[RemyListing, str]] = []
        for listing in listings:
            try:
                vector_id = await ensure_listing_embedded(listing, embedder)
                if vector_id != listing.embedding_id:
                    listing.embedding_id = vector_id
                    await storage.save_remy_listing(listing)
                embedded.append((listing, vector_id))
            except Exception as e:
                logger.warning("Could not embed listing %s: %s", listing.id, e)

        if not embedded:
            embedded = [(l, "") for l in listings]

        cv: Optional[BaseCV] = await storage.get_cv()
        reference_vector: Optional[list[float]] = None
        if cv is not None:
            try:
                reference_vector = await get_cv_vector(cv, embedder)
            except Exception as e:
                logger.warning("Could not embed CV for recommender: %s", e)
        if reference_vector is None:
            reference_text = " ".join(query.keywords) + " " + " ".join(
                c.name for c in query.cities
            )
            reference_vector = local_embed(reference_text)

        pass1: list[tuple[RemyListing, float]] = []
        if embedded:
            scored = await store.search(reference_vector, top_k=PASS1_TOP, kind="listing")
            by_id = {listing.id: listing for listing, _ in embedded}
            for vector_id, sim in scored:
                ref_id = (
                    vector_id.split(":", 1)[1]
                    if vector_id.startswith("listing:")
                    else ""
                )
                listing = by_id.get(ref_id)
                if listing is not None:
                    pass1.append((listing, sim))
        if not pass1:
            pass1 = [(listing, 0.0) for listing, _ in embedded[:PASS1_TOP]]

        max_sim = max((s for _, s in pass1), default=0.0)
        candidates = [listing for listing, _ in pass1]

        top_matches: list[RemyTopMatch] = []
        try:
            messages = build_recommender_messages(
                query_name=query.name,
                keywords=query.keywords,
                cities=[c.name for c in query.cities],
                cv=cv,
                candidates=candidates,
            )
            data, _retries = await self._llm.chat_json(
                messages=messages,
                system=RECOMMENDER_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=4096,
            )
            top_matches = self._parse_scores(data, candidates)
        except Exception as e:
            logger.warning("Recommender LLM call failed, using vector-only scores: %s", e)
            for listing, sim in pass1[:PASS2_TOP]:
                top_matches.append(
                    RemyTopMatch(
                        listing_id=listing.id,
                        score=_relative_score(sim, max_sim),
                        reason=_fallback_reason(sim, listing),
                    )
                )

        if not top_matches:
            for listing, sim in pass1[:PASS2_TOP]:
                top_matches.append(
                    RemyTopMatch(
                        listing_id=listing.id,
                        score=_relative_score(sim, max_sim),
                        reason=_fallback_reason(sim, listing),
                    )
                )

        content_md = self._build_content(query, top_matches, _by_id(candidates))
        report = RemyReport(
            run_id=run_id,
            query_id=query.id,
            type="recommendation",
            content_md=content_md,
            top_matches=top_matches,
        )
        await storage.save_remy_report(report)
        logger.info(
            "Recommendation report %s for query %s (%d scored)",
            report.id, query.id, len(top_matches),
        )
        return RecommendationResult(
            report=report,
            listings_considered=len(candidates),
        )

    @staticmethod
    def _parse_scores(
        data: dict,
        candidates: list[RemyListing],
    ) -> list[RemyTopMatch]:
        by_id: dict[str, RemyListing] = {l.id: l for l in candidates}
        raw = data.get("scores", []) if isinstance(data, dict) else []
        if not isinstance(raw, list):
            return []
        matches: list[RemyTopMatch] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            lid = str(item.get("listing_id", ""))
            if lid not in by_id or lid in seen:
                continue
            score = max(0, min(100, int(item.get("score", 0) or 0)))
            if score <= 0:
                continue
            reason = str(item.get("reason", "")).strip()
            if not reason:
                reason = f"Score {score} — {by_id[lid].title} at {by_id[lid].company}"
            matches.append(RemyTopMatch(listing_id=lid, score=score, reason=reason))
            seen.add(lid)
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:PASS2_TOP]

    @staticmethod
    def _build_content(
        query: RemyQuery,
        top_matches: list[RemyTopMatch],
        by_id: dict[str, RemyListing],
    ) -> str:
        lines = [
            "## Recommendations",
            "",
            f"Search profile: **{query.name or 'unnamed'}**",
            f"Keywords: {', '.join(query.keywords) if query.keywords else 'n/a'}",
            "",
        ]
        if not top_matches:
            lines.append("No strong matches found in the current listings.")
            return "\n".join(lines)

        lines.append("### Top Matches")
        lines.append("")
        for i, match in enumerate(top_matches, 1):
            listing = by_id.get(match.listing_id)
            title = (listing.title or "Unknown") if listing else "Unknown"
            company = (listing.company or "") if listing else ""
            url = ""
            if listing and listing.url:
                url = f" ([link]({listing.url}))"
            lines.append(f"**{i}. {title}** — {company} — Score: {match.score}/100{url}")
            lines.append(f"> {match.reason}")
            lines.append("")
        return "\n".join(lines)


def _by_id(listings: list[RemyListing]) -> dict[str, RemyListing]:
    return {l.id: l for l in listings}


async def run_recommendation(
    storage: StorageBackend,
    query: RemyQuery,
    run: RemyRun,
) -> tuple[RemyRun, Optional[RemyReport]]:
    """Execute recommendation for a query, updating the given run + memory."""
    from backend.services.remy.memory import get_remy_memory

    report: Optional[RemyReport] = None
    try:
        result = await RemyRecommender().run(query, storage, run_id=run.id)
        report = result.report
        run.status = "success"
        run.listings_found = result.listings_considered
        run.new_listings = 0
        run.log = (
            f"report_id={report.id} candidates={result.listings_considered} "
            f"top_matches={len(report.top_matches)}"
        )
    except Exception as e:
        logger.exception("Recommendation for query %s failed", query.id)
        run.status = "failed"
        run.error = str(e)
    finally:
        run.finished_at = _now()
        await storage.save_remy_run(run)

    if report is not None and run.status == "success":
        try:
            await get_remy_memory().record_run(
                run_id=run.id,
                report_id=report.id,
                report_type=report.type,
                query_id=query.id,
                top_listing_ids=[m.listing_id for m in report.top_matches],
                top_skills=None,
            )
        except Exception as e:
            logger.warning("Memory update after recommendation run failed: %s", e)
    return run, report