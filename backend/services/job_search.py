from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.config import load_config
from backend.services.llm import LLMClient

logger = logging.getLogger(__name__)

JD_EXTRACTION_PROMPT = """You are a job description parser. Given raw HTML or text from a job listing page,
extract only the job description content: role overview, responsibilities,
requirements, qualifications, company info, and benefits. Ignore navigation, ads,
headers, footers, and unrelated text. Return clean, well-formatted markdown.

If you cannot identify a job description in the content, respond with:
{"error": "No job description found on this page."}"""


class JobSearchService:
    def __init__(self) -> None:
        self._config = load_config()

    @property
    def _llm(self) -> LLMClient:
        return LLMClient(self._config)

    async def search(
        self,
        query: str,
        location: str = "",
        remote: bool = False,
        job_type: str = "",
        experience_level: str = "",
        date_posted: str = "",
    ) -> list[dict[str, Any]]:
        provider = self._config.search_provider
        api_key = self._config.search_api_key

        if not api_key:
            raise RuntimeError("Search API key not configured")

        if provider == "serpapi":
            raw = await self._search_serpapi(query, location, remote, api_key)
        elif provider == "brave":
            raw = await self._search_brave(query, location, remote, job_type, experience_level, date_posted, api_key)
        else:
            raise RuntimeError(f"Unknown search provider: {provider}")

        return self._normalize_results(raw, provider)

    async def _search_serpapi(
        self,
        query: str,
        location: str,
        remote: bool,
        api_key: str,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "api_key": api_key,
            "engine": "google_jobs",
            "q": query,
        }
        if location:
            params["location"] = location
        if remote:
            params["q"] = f"{query} remote"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            logger.error("SerpAPI error: %s", data["error"])
            raise RuntimeError(data.get("error", "SerpAPI request failed"))

        jobs = data.get("jobs_results", [])
        return self._parse_serpapi_jobs(jobs)

    @staticmethod
    def _parse_serpapi_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for job in jobs:
            results.append({
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "location": job.get("location", ""),
                "url": job.get("apply_link", "") or job.get("link", ""),
                "description_snippet": job.get("description", ""),
                "source": "serpapi",
                "posted_date": job.get("detected_extensions", {}).get("posted_at", "") if isinstance(job.get("detected_extensions"), dict) else "",
            })
        return results

    async def _search_brave(
        self,
        query: str,
        location: str,
        remote: bool,
        job_type: str,
        experience_level: str,
        date_posted: str,
        api_key: str,
    ) -> list[dict[str, Any]]:
        q = f"{query} job"
        if location:
            q += f" in {location}"
        if remote:
            q += " remote"
        if job_type:
            q += f" {job_type}"
        if experience_level:
            q += f" {experience_level}"

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        }
        params: dict[str, Any] = {"q": q, "count": 20}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        web_results = data.get("web", {}).get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "company": "",
                "location": location,
                "url": r.get("url", ""),
                "description_snippet": r.get("description", ""),
                "source": "brave",
                "posted_date": "",
            }
            for r in web_results
        ]

    @staticmethod
    def _normalize_results(
        raw: list[dict[str, Any]],
        provider: str,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in raw:
            results.append({
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "url": item.get("url", ""),
                "description_snippet": item.get("description_snippet", ""),
                "source": item.get("source", provider),
                "posted_date": item.get("posted_date", ""),
            })
        return results

    async def extract_jd(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; OpenResume/1.0)"},
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("Failed to fetch JD URL %s: %s", url, e)
                raise RuntimeError(f"Failed to fetch job listing: {e}") from e

        html = resp.text

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"

        try:
            response = await self._llm.chat(
                messages=[{"role": "user", "content": text}],
                system=JD_EXTRACTION_PROMPT,
                temperature=0.3,
                max_tokens=4096,
            )
        except Exception as e:
            logger.error("LLM JD extraction failed: %s", e)
            raise RuntimeError(f"JD extraction failed: {e}") from e

        if response.strip().startswith('{"error"'):
            import json
            try:
                error_data = json.loads(response.strip())
                raise RuntimeError(error_data.get("error", "No job description found"))
            except (json.JSONDecodeError, RuntimeError):
                raise RuntimeError("No job description found on this page")

        return response

    @staticmethod
    def get_available_sources() -> list[str]:
        return ["serpapi", "brave"]
