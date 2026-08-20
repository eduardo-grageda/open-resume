from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from backend.config import load_config
from backend.models import BaseCV, RemyListing, RemyQuery, RemyReport, RemyRun, RemyTopMatch, _now
from backend.services.llm import LLMClient
from backend.services.remy.prompts import ANALYST_SYSTEM_PROMPT, build_analyst_messages

if TYPE_CHECKING:
    from backend.database import StorageBackend

logger = logging.getLogger(__name__)

NEAREST_LISTINGS = 15
TOP_MATCHES_IN_REPORT = 5


@dataclass
class AnalysisResult:
    report: RemyReport
    listings_considered: int = 0
    top_skills: list[str] = field(default_factory=list)


def _relative_score(sim: float, max_sim: float) -> int:
    if max_sim <= 0:
        return 0
    return max(0, min(100, round(100.0 * sim / max_sim)))


class RemyAnalyzer:
    """Market analysis service: nearest listings in vector space vs base CV.

    Wired to the `analyst` sub-agent via `backend.services.remy.subagents`.
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
    ) -> AnalysisResult:
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
                "## Market Analysis\n\n"
                "No active listings found for this search profile yet. "
                "Run a scrape first so the analyst has market data to work with."
            )
            report = RemyReport(
                run_id=run_id, query_id=query.id, type="analysis", content_md=content
            )
            await storage.save_remy_report(report)
            return AnalysisResult(report=report, listings_considered=0)

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
                logger.warning("Could not embed CV: %s", e)
        if reference_vector is None:
            reference_text = " ".join(query.keywords) + " " + " ".join(
                c.name for c in query.cities
            )
            reference_vector = local_embed(reference_text)

        nearest: list[tuple[RemyListing, float]] = []
        if embedded:
            scored = await store.search(
                reference_vector, top_k=NEAREST_LISTINGS, kind="listing"
            )
            by_id = {listing.id: listing for listing, _ in embedded}
            for vector_id, sim in scored:
                ref_id = (
                    vector_id.split(":", 1)[1]
                    if vector_id.startswith("listing:")
                    else ""
                )
                listing = by_id.get(ref_id)
                if listing is not None:
                    nearest.append((listing, sim))
        if not nearest:
            nearest = [(listing, 0.0) for listing, _ in embedded[:NEAREST_LISTINGS]]

        selected = [listing for listing, _ in nearest]
        max_sim = max((sim for _, sim in nearest), default=0.0)

        messages = build_analyst_messages(
            query_name=query.name,
            keywords=query.keywords,
            cities=[c.name for c in query.cities],
            listings=selected,
            cv=cv,
        )

        top_skills: list[str] = []
        try:
            data, _retries = await self._llm.chat_json(
                messages=messages,
                system=ANALYST_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=4096,
            )
            if not isinstance(data, dict):
                raise ValueError(f"Unexpected LLM response type: {type(data).__name__}")
            content_md = str(data.get("content_md", "")).strip()
            if not content_md:
                raise ValueError("LLM response missing content_md")
            for gap in data.get("skills_gaps", []):
                if isinstance(gap, dict) and gap.get("skill"):
                    top_skills.append(str(gap["skill"]))
        except Exception as e:
            logger.warning("Analyst LLM call failed, using fallback report: %s", e)
            content_md = self._fallback_content(nearest, str(e))

        top_matches = [
            RemyTopMatch(
                listing_id=listing.id,
                listing_title=listing.title or "",
                listing_company=listing.company or "",
                score=_relative_score(sim, max_sim),
                reason=f"Vector similarity {sim:.2f}",
            )
            for listing, sim in nearest[:TOP_MATCHES_IN_REPORT]
        ]

        report = RemyReport(
            run_id=run_id,
            query_id=query.id,
            type="analysis",
            content_md=content_md,
            top_matches=top_matches,
        )
        await storage.save_remy_report(report)
        logger.info(
            "Analysis report %s for query %s (%d listings considered)",
            report.id, query.id, len(selected),
        )
        return AnalysisResult(
            report=report,
            listings_considered=len(selected),
            top_skills=top_skills,
        )

    @staticmethod
    def _fallback_content(nearest: list[tuple[RemyListing, float]], error: str) -> str:
        lines = [
            "## Market Analysis (vector-only fallback)",
            "",
            f"> The AI analyst was unavailable ({error}). This report is based on vector "
            "similarity between your CV and the nearest listings only.",
            "",
            "### Nearest Listings",
            "",
        ]
        for listing, sim in nearest:
            url = f" ([link]({listing.url}))" if listing.url else ""
            lines.append(
                f"- **{listing.title}** — {listing.company} — similarity {sim:.2f}{url}"
            )
        lines += [
            "",
            "### Skills Gap",
            "",
            "Not available without the AI analyst. Nearest listings above can be reviewed manually.",
        ]
        return "\n".join(lines)


async def run_analysis(
    storage: StorageBackend,
    query: RemyQuery,
    run: RemyRun,
) -> tuple[RemyRun, Optional[RemyReport]]:
    """Execute analysis for a query, updating the given run + memory."""
    from backend.services.remy.memory import get_remy_memory

    report: Optional[RemyReport] = None
    top_skills: list[str] = []
    try:
        result = await RemyAnalyzer().run(query, storage, run_id=run.id)
        report = result.report
        top_skills = result.top_skills
        run.status = "success"
        run.listings_found = result.listings_considered
        run.new_listings = 0
        run.log = (
            f"report_id={report.id} candidates={result.listings_considered} "
            f"top_matches={len(report.top_matches)}"
        )
    except Exception as e:
        logger.exception("Analysis for query %s failed", query.id)
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
                top_skills=top_skills,
            )
        except Exception as e:
            logger.warning("Memory update after analysis run failed: %s", e)
    return run, report
