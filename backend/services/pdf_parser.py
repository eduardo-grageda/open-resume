from __future__ import annotations

import json
import logging
from typing import Any

import pdfplumber

from backend.config import load_config
from backend.models import BaseCV
from backend.services.llm import LLMClient

logger = logging.getLogger(__name__)

PDF_PARSE_PROMPT = """You are a CV parser. Given the raw text extracted from a PDF resume/CV, extract all
information into structured JSON matching the schema below. Be thorough — include everything you find.

Rules:
- DO NOT invent or fabricate ANY information not present in the text.
- If a field is not found in the text, leave it as an empty string or empty array.
- For dates, preserve the original format from the CV (e.g., "Jan 2020", "2020-01", "2020").
- For accomplishments under career entries, extract bullet points or sentence fragments.
- For skills, group them into logical categories if the CV organizes them that way.
- If the CV has a summary section, extract it verbatim.

Return ONLY valid JSON (no markdown wrapping, no code fences):

{
  "personal_info": {
    "first_name": "",
    "last_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "address": "",
    "website": "",
    "linkedin": "",
    "github": "",
    "twitter": "",
    "other_social": []
  },
  "professional_summary": "",
  "career": [
    {
      "company": "",
      "title": "",
      "start_date": "",
      "end_date": "",
      "location": "",
      "description": "",
      "accomplishments": [],
      "technologies": []
    }
  ],
  "formation": [
    {
      "degree": "",
      "institution": "",
      "field": "",
      "start_year": "",
      "end_year": "",
      "notes": ""
    }
  ],
  "skills": [
    {
      "category": "",
      "technologies": []
    }
  ],
  "tools": [
    {
      "category": "",
      "items": []
    }
  ],
  "accomplishments": [
    {
      "title": "",
      "description": "",
      "year": ""
    }
  ],
  "hobbies": [],
  "languages": {
    "programming": [],
    "spoken": [
      {
        "language": "",
        "level": ""
      }
    ]
  },
  "projects": [
    {
      "name": "",
      "url": "",
      "year": "",
      "description": "",
      "technologies": []
    }
  ],
  "certifications": [
    {
      "name": "",
      "issuer": "",
      "year": "",
      "url": ""
    }
  ]
}"""


class PdfParser:
    def __init__(self) -> None:
        self._config = load_config()

    @property
    def _llm(self) -> LLMClient:
        return LLMClient(self._config)

    @staticmethod
    def extract_text(file_path: str) -> str:
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                if not pages:
                    raise RuntimeError("No extractable text found in PDF")
                return "\n\n".join(pages)
        except Exception as e:
            logger.error("PDF text extraction failed: %s", e)
            raise RuntimeError(f"Failed to extract text from PDF: {e}") from e

    @staticmethod
    def _truncate_text(text: str, max_chars: int = 15000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...[truncated]"

    async def parse_to_cv(self, pdf_text: str) -> dict[str, Any]:
        truncated = self._truncate_text(pdf_text)

        try:
            response = await self._llm.chat_json(
                messages=[{"role": "user", "content": f"Extract structured CV data from this PDF text:\n\n{truncated}"}],
                system=PDF_PARSE_PROMPT,
                temperature=0.2,
                max_tokens=16384,
            )
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response: %s", e)
            raise RuntimeError("AI failed to produce valid structured data") from e
        except Exception as e:
            logger.error("LLM PDF parsing failed: %s", e)
            raise RuntimeError(f"PDF parsing failed: {e}") from e

        if not isinstance(response, dict):
            raise RuntimeError("AI returned unexpected response format")

        return response

    @staticmethod
    def parsed_to_base_cv(parsed: dict[str, Any]) -> BaseCV:
        from backend.models import (
            Accomplishment, CareerEntry, Certification, EducationEntry,
            Languages, PersonalInfo, Project, SkillCategory, SpokenLanguage,
            ToolCategory,
        )

        pi = parsed.get("personal_info", {})
        personal_info = PersonalInfo(
            first_name=pi.get("first_name", ""),
            last_name=pi.get("last_name", ""),
            email=pi.get("email", ""),
            phone=pi.get("phone", ""),
            location=pi.get("location", ""),
            address=pi.get("address", ""),
            website=pi.get("website", ""),
            linkedin=pi.get("linkedin", ""),
            github=pi.get("github", ""),
            twitter=pi.get("twitter", ""),
            other_social=pi.get("other_social", []),
        )

        lang = parsed.get("languages", {})
        languages = Languages(
            programming=lang.get("programming", []),
            spoken=[
                SpokenLanguage(**s)
                for s in lang.get("spoken", [])
                if isinstance(s, dict) and s.get("language")
            ],
        )

        return BaseCV(
            personal_info=personal_info,
            professional_summary=parsed.get("professional_summary", ""),
            career=[
                CareerEntry(**c)
                for c in parsed.get("career", [])
                if isinstance(c, dict) and (c.get("company") or c.get("title"))
            ],
            formation=[
                EducationEntry(**e)
                for e in parsed.get("formation", [])
                if isinstance(e, dict) and (e.get("degree") or e.get("institution"))
            ],
            skills=[
                SkillCategory(**s)
                for s in parsed.get("skills", [])
                if isinstance(s, dict) and s.get("category")
            ],
            tools=[
                ToolCategory(**t)
                for t in parsed.get("tools", [])
                if isinstance(t, dict) and t.get("category")
            ],
            accomplishments=[
                Accomplishment(**a)
                for a in parsed.get("accomplishments", [])
                if isinstance(a, dict) and a.get("title")
            ],
            hobbies=[
                h for h in parsed.get("hobbies", [])
                if isinstance(h, str) and h.strip()
            ],
            languages=languages,
            projects=[
                Project(**p)
                for p in parsed.get("projects", [])
                if isinstance(p, dict) and p.get("name")
            ],
            certifications=[
                Certification(**c)
                for c in parsed.get("certifications", [])
                if isinstance(c, dict) and c.get("name")
            ],
        )