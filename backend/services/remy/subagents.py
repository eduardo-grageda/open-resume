from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from backend.models import RemyQuery, RemyReport

logger = logging.getLogger(__name__)


@dataclass
class SubAgentSpec:
    name: str
    description: str
    prompt: str
    handler: Callable


def _analyst_handler(query: RemyQuery, storage, *, run_id: str = "") -> Any:
    from backend.services.remy.analyzer import RemyAnalyzer

    return RemyAnalyzer().run(query, storage, run_id=run_id)


def _recommender_handler(query: RemyQuery, storage, *, run_id: str = "") -> Any:
    from backend.services.remy.recommender import RemyRecommender

    return RemyRecommender().run(query, storage, run_id=run_id)


SUBAGENTS: dict[str, SubAgentSpec] = {
    "analyst": SubAgentSpec(
        name="analyst",
        description=(
            "Market analysis sub-agent. Given a search profile (RemyQuery) "
            "and the vector store, generates a market-trend + skills-gap report "
            "by comparing the nearest listings to the candidate's base CV."
        ),
        prompt=(
            "You are the analyst sub-agent. Your job is to turn a set of job "
            "listings into a market analysis report for the candidate. "
            "See RemyAnalyzer for full logic; this is a task wrapper."
        ),
        handler=_analyst_handler,
    ),
    "recommender": SubAgentSpec(
        name="recommender",
        description=(
            "Recommendation sub-agent. Two-pass scoring: vector similarity "
            "narrows candidates, then LLM reasoning scores each on a 0-100 "
            "match scale with reasons."
        ),
        prompt=(
            "You are the recommender sub-agent. Score job listings for the "
            "candidate on a 0-100 match scale. See RemyRecommender for full "
            "logic; this is a task wrapper."
        ),
        handler=_recommender_handler,
    ),
}


def get_subagent(name: str) -> Optional[SubAgentSpec]:
    return SUBAGENTS.get(name)


async def run_subagent(name: str, query: RemyQuery, storage, *, run_id: str = "") -> Any:
    """Dispatch to the named sub-agent. Future deepagents `task` tool entry point."""
    spec = get_subagent(name)
    if spec is None:
        raise ValueError(f"Unknown sub-agent: {name}")
    logger.info("Running sub-agent %s for query %s", name, query.id)
    return await spec.handler(query, storage, run_id=run_id)