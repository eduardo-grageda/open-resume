from __future__ import annotations

from typing import Optional

from backend.models import BaseCV, RemyListing

ANALYST_SYSTEM_PROMPT = """You are the "analyst" sub-agent of Remy, a local-first job-search assistant.
Your job is to turn a set of job listings into a market analysis report for a candidate.

Rules:
- Base every conclusion ONLY on the listings and CV provided to you. NEVER invent or
  fabricate facts, experience, skills, or accomplishments — the candidate's skills come
  exclusively from the CV text given.
- Do not claim the candidate has a skill that is not present in the provided CV.
- Be specific: cite companies, titles, salaries, and skill frequencies when possible.
- Respond ONLY with a valid JSON object and nothing else.

JSON schema:
{
  "market_summary": "string, 2-4 sentences summarizing the market for this search",
  "market_trends": ["string, one observed trend each (technologies, seniority, salary, remote)"],
  "skills_gaps": [
    {
      "skill": "string",
      "frequency": "number of listings mentioning it",
      "effort": "days | weeks | months",
      "rationale": "one sentence"
    }
  ],
  "recommended_focus": ["string, prioritized actions to improve match odds"],
  "content_md": "full markdown report with sections: Overview, Market Trends, In-Demand Skills (with counts), Skills Gaps vs CV, Recommended Focus"
}"""

RECOMMENDER_SYSTEM_PROMPT = """You are the "recommender" sub-agent of Remy, a local-first job-search assistant.
You score job listings for a candidate on a 0-100 match scale.

Rules:
- The candidate's real skills and experience come ONLY from the CV text provided.
  NEVER invent or assume experience, skills, or accomplishments for the candidate.
- Score 0-100: 90+ = strong match across most requirements; 70-89 = good match with
  some gaps; 50-69 = partial match; below 50 = weak match.
- Consider seniority fit, tech-stack overlap, domain overlap, and location/remote fit.
- Give a one-sentence, honest reason for each score that mentions concrete evidence.
- Respond ONLY with a valid JSON object and nothing else.

JSON schema:
{
  "scores": [
    {"listing_id": "string", "score": 0-100 integer, "reason": "one sentence"}
  ]
}"""

_ANALYST_FALLBACK_PROMPT = "Write the market analysis report as JSON per the schema."

_RECOMMENDER_FALLBACK_PROMPT = "Score each candidate listing as JSON per the schema."


def _cv_block(cv: BaseCV, max_chars: int = 6000) -> str:
    from backend.services.remy.vectordb import cv_text

    return cv_text(cv)[:max_chars]


def _listing_block(listing: RemyListing, max_desc: int = 600) -> str:
    desc = (listing.description_md or "").strip().replace("\n", " ")
    if len(desc) > max_desc:
        desc = desc[:max_desc] + "…"
    parts = [
        f"[{listing.id}] {listing.title} — {listing.company}",
        f"Location: {listing.location or 'n/a'}",
    ]
    if listing.salary:
        parts.append(f"Salary: {listing.salary}")
    if listing.url:
        parts.append(f"URL: {listing.url}")
    parts.append(f"Description: {desc}")
    return "\n".join(parts)


def build_analyst_messages(
    query_name: str,
    keywords: list[str],
    cities: list[str],
    listings: list[RemyListing],
    cv: Optional[BaseCV],
) -> list[dict[str, str]]:
    listing_blocks = "\n\n---\n\n".join(_listing_block(l) for l in listings)

    user_parts = [
        f"Search profile: {query_name or 'unnamed'}",
        f"Keywords: {', '.join(keywords) if keywords else 'n/a'}",
        f"Cities: {', '.join(cities) if cities else 'n/a'}",
        "",
        "Candidate CV:",
        _cv_block(cv) if cv is not None else "(no base CV provided — market-only analysis)",
        "",
        f"Job listings ({len(listings)}):",
        listing_blocks or "(none)",
        "",
        _ANALYST_FALLBACK_PROMPT,
    ]
    return [{"role": "user", "content": "\n\n".join(user_parts)}]


def build_recommender_messages(
    query_name: str,
    keywords: list[str],
    cities: list[str],
    cv: Optional[BaseCV],
    candidates: list[RemyListing],
) -> list[dict[str, str]]:
    listing_blocks = "\n\n---\n\n".join(_listing_block(l) for l in candidates)

    user_parts = [
        f"Search profile: {query_name or 'unnamed'}",
        f"Keywords: {', '.join(keywords) if keywords else 'n/a'}",
        f"Cities: {', '.join(cities) if cities else 'n/a'}",
        "",
        "Candidate CV:",
        _cv_block(cv) if cv is not None else "(no base CV provided)",
        "",
        f"Candidate listings to score ({len(candidates)}):",
        listing_blocks or "(none)",
        "",
        _RECOMMENDER_FALLBACK_PROMPT,
    ]
    return [{"role": "user", "content": "\n\n".join(user_parts)}]
