from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import load_config
from backend.models import BaseCV
from backend.services.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a CV optimization expert. You have a comprehensive base CV and a specific
job description. Your task is to produce a compact, tailored CV that emphasizes
skills and experience most relevant to the job description.

Rules:
- NEVER invent or fabricate experience, skills, or accomplishments.
- Only reorder, emphasize (expand), de-emphasize (condense), or omit content from the base CV.
- The output must be valid markdown with these sections:
  # {first_name} {last_name}
  Contact info line (email, phone, location, LinkedIn, GitHub)
  ## Professional Summary (2-3 sentences, tailored to the role)
  ## Skills (only relevant categories and technologies)
  ## Tools & Technologies (only relevant ones)
  ## Experience (most relevant first, de-emphasize less relevant roles)
  ## Education (condensed)
  ## Projects (only if highly relevant)
  ## Languages
  ## Certifications (if relevant)

After the CV, under a "---" separator on its own line, add a "## Change Summary" section explaining:
- Which skills/experiences were emphasized and why
- Which were de-emphasized or omitted and why
- Overall strategy for this adaptation"""


class AdapterService:
    def __init__(self) -> None:
        self._config = load_config()

    @property
    def _llm(self) -> LLMClient:
        return LLMClient(self._config)

    @staticmethod
    def _format_cv(cv: BaseCV) -> str:
        pi = cv.personal_info

        parts: list[str] = []
        parts.append("## Personal Info")
        parts.append(f"Name: {pi.first_name} {pi.last_name}")
        parts.append(f"Email: {pi.email}")
        parts.append(f"Phone: {pi.phone}")
        parts.append(f"Location: {pi.location}")
        if pi.address:
            parts.append(f"Address: {pi.address}")
        if pi.website:
            parts.append(f"Website: {pi.website}")
        if pi.linkedin:
            parts.append(f"LinkedIn: {pi.linkedin}")
        if pi.github:
            parts.append(f"GitHub: {pi.github}")
        if pi.twitter:
            parts.append(f"Twitter: {pi.twitter}")
        for s in pi.other_social:
            parts.append(f"{s.get('platform', '')}: {s.get('url', '')}")

        if cv.professional_summary:
            parts.append("\n## Professional Summary")
            parts.append(cv.professional_summary)

        if cv.career:
            parts.append("\n## Career / Experience")
            for entry in cv.career:
                parts.append(f"- **{entry.title}** at {entry.company} ({entry.start_date} – {entry.end_date or 'Present'})")
                if entry.location:
                    parts.append(f"  Location: {entry.location}")
                if entry.description:
                    parts.append(f"  {entry.description}")
                if entry.accomplishments:
                    for a in entry.accomplishments:
                        parts.append(f"  - {a}")
                if entry.technologies:
                    parts.append(f"  Technologies: {', '.join(entry.technologies)}")

        if cv.formation:
            parts.append("\n## Education")
            for entry in cv.formation:
                parts.append(f"- {entry.degree} in {entry.field} from {entry.institution} ({entry.start_year} – {entry.end_year})")
                if entry.notes:
                    parts.append(f"  {entry.notes}")

        if cv.skills:
            parts.append("\n## Skills")
            for cat in cv.skills:
                if cat.technologies:
                    parts.append(f"- {cat.category}: {', '.join(cat.technologies)}")

        if cv.tools:
            parts.append("\n## Tools & Technologies")
            for cat in cv.tools:
                if cat.items:
                    parts.append(f"- {cat.category}: {', '.join(cat.items)}")

        if cv.accomplishments:
            parts.append("\n## Accomplishments")
            for acc in cv.accomplishments:
                parts.append(f"- **{acc.title}** ({acc.year}): {acc.description}")

        if cv.projects:
            parts.append("\n## Projects")
            for proj in cv.projects:
                url = f" ({proj.url})" if proj.url else ""
                parts.append(f"- **{proj.name}**{url} ({proj.year})")
                parts.append(f"  {proj.description}")
                if proj.technologies:
                    parts.append(f"  Technologies: {', '.join(proj.technologies)}")

        if cv.certifications:
            parts.append("\n## Certifications")
            for cert in cv.certifications:
                url = f" ({cert.url})" if cert.url else ""
                parts.append(f"- {cert.name} — {cert.issuer}{url} ({cert.year})")

        if cv.languages.programming:
            parts.append(f"\n## Programming Languages\n{', '.join(cv.languages.programming)}")

        if cv.languages.spoken:
            parts.append(f"\n## Spoken Languages")
            for lang in cv.languages.spoken:
                parts.append(f"- {lang.language}: {lang.level}")

        if cv.hobbies:
            parts.append(f"\n## Hobbies & Interests\n{', '.join(cv.hobbies)}")

        return "\n".join(parts)

    async def adapt(self, cv: BaseCV, job_description: str) -> dict[str, Any]:
        cv_markdown = self._format_cv(cv)
        first_name = cv.personal_info.first_name or "Candidate"
        last_name = cv.personal_info.last_name or ""

        system = SYSTEM_PROMPT.format(
            first_name=first_name,
            last_name=last_name,
        )

        user_message = (
            "Here is my comprehensive base CV:\n\n"
            f"{cv_markdown}\n\n"
            "---\n\n"
            "Here is the job description I am applying for:\n\n"
            f"{job_description}\n\n"
            "Please produce a tailored CV and a change summary, "
            "following the rules in the system prompt."
        )

        try:
            response = await self._llm.chat(
                messages=[{"role": "user", "content": user_message}],
                system=system,
                temperature=0.5,
                max_tokens=8192,
            )
        except Exception as e:
            logger.error("Adapter LLM call failed: %s", e)
            raise RuntimeError(f"LLM adaptation failed: {e}") from e

        tailored_cv_md, change_summary = self._parse_response(response)
        return {
            "tailored_cv_md": tailored_cv_md,
            "change_summary": change_summary,
        }

    @staticmethod
    def _parse_response(response: str) -> tuple[str, str]:
        separator = "\n---\n"
        idx = response.rfind(separator)
        if idx == -1:
            idx = response.find("## Change Summary")
            if idx == -1:
                logger.warning("Could not find change summary separator in LLM response")
                return response, ""
            cv_part = response[:idx].strip()
            summary_part = response[idx:].strip()
        else:
            cv_part = response[:idx].strip()
            summary_part = response[idx + len(separator):].strip()

        return cv_part, summary_part