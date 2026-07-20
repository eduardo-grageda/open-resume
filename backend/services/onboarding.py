from __future__ import annotations

import json
import logging
from typing import Any, Optional

from backend.config import AppConfig, load_config
from backend.models import BaseCV, ConversationMessage, OnboardingSession
from backend.services.llm import LLMClient

logger = logging.getLogger(__name__)

SECTIONS = [
    "personal_info",
    "professional_summary",
    "career",
    "formation",
    "skills",
    "tools",
    "accomplishments",
    "projects",
    "certifications",
    "programming_languages",
    "spoken_languages",
    "hobbies",
]

SECTION_LABELS: dict[str, str] = {
    "personal_info": "Personal & Contact Info",
    "professional_summary": "Professional Summary",
    "career": "Work Experience",
    "formation": "Education",
    "skills": "Skills",
    "tools": "Tools & Technologies",
    "accomplishments": "Accomplishments",
    "projects": "Projects",
    "certifications": "Certifications",
    "programming_languages": "Programming Languages",
    "spoken_languages": "Spoken Languages",
    "hobbies": "Hobbies & Interests",
}

SYSTEM_PROMPT = """You are an expert CV builder conducting an onboarding interview with {first_name} {last_name}, a {target_role}. Your goal is to gather structured information to build a comprehensive base CV.

Ask one question at a time, progressing through these sections:

1. Personal & contact info (email, phone, location, address, LinkedIn, GitHub, other social)
2. Professional summary (2-3 sentences about experience and focus)
3. Career / Work experience (company, title, dates, description, accomplishments)
4. Formation / Education (degree, institution, field, years)
5. Skills by category (AI, DevOps, Cloud, Containers, Paradigms, Security, etc.)
6. Tools & technologies (by category: Backend, Frontend, DevOps, etc.)
7. Accomplishments (notable achievements, awards, publications)
8. Projects (name, description, URL, technologies)
9. Certifications (name, issuer, year)
10. Programming languages
11. Spoken languages
12. Hobbies & interests

Current section: {current_section}
Completed sections: {completed_sections}
Previously extracted data: {extracted_summary}

Rules:
- Ask ONE question at a time.
- Keep questions conversational but concise.
- If the user provides vague answers, ask follow-ups for specifics.
- DO NOT invent or fabricate any information.
- After each answer, organize the information into the JSON response format below.

Response format (valid JSON only, no markdown wrapping):
{{
  "done": false,
  "section": "{current_section}",
  "question": "Your next question here",
  "extracted": {{
    "personal_info": {{"first_name": "...", "last_name": "...", "email": "...", "phone": "...", "location": "...", "address": "...", "website": "...", "linkedin": "...", "github": "...", "twitter": "...", "other_social": []}},
    "professional_summary": "...",
    "career": [{{"company": "...", "title": "...", "start_date": "...", "end_date": "...", "location": "...", "description": "...", "accomplishments": [], "technologies": []}}],
    "formation": [{{"degree": "...", "institution": "...", "field": "...", "start_year": "...", "end_year": "...", "notes": ""}}],
    "skills": [{{"category": "...", "technologies": []}}],
    "tools": [{{"category": "...", "items": []}}],
    "accomplishments": [{{"title": "...", "description": "...", "year": ""}}],
    "projects": [{{"name": "...", "url": "", "year": "", "description": "...", "technologies": []}}],
    "certifications": [{{"name": "...", "issuer": "...", "year": "", "url": ""}}],
    "languages": {{"programming": [], "spoken": []}},
    "hobbies": []
  }}
}}

When ALL 12 sections are fully covered, respond with:
{{
  "done": true,
  "message": "All sections complete! Your CV is ready for review.",
  "section": "complete",
  "extracted": {{
    // complete extracted data with all sections filled
  }}
}}

IMPORTANT:
- Always include the "extracted" field with any new data from this answer (not just the current section).
- Build up the data incrementally — include everything you've learned so far.
- Use empty arrays for lists when no data is available yet.
- Do NOT set "done": true until every section has been addressed."""


class OnboardingService:
    def __init__(self) -> None:
        self._config = load_config()

    @property
    def _llm(self) -> LLMClient:
        return LLMClient(self._config)

    def _build_system_prompt(self, session: OnboardingSession, first_name: str, last_name: str, target_role: str) -> str:
        completed = [s for s in SECTIONS if s != session.current_section and self._section_has_data(s, session.extracted_data)]
        completed_labels = ", ".join(SECTION_LABELS.get(s, s) for s in completed) or "None"
        extracted_summary = self._summarize_extracted(session.extracted_data)
        return SYSTEM_PROMPT.format(
            first_name=first_name,
            last_name=last_name,
            target_role=target_role,
            current_section=SECTION_LABELS.get(session.current_section, session.current_section),
            completed_sections=completed_labels,
            extracted_summary=extracted_summary,
        )

    @staticmethod
    def _section_has_data(section: str, extracted: dict) -> bool:
        if section not in extracted:
            return False
        val = extracted[section]
        if val is None:
            return False
        if isinstance(val, str):
            return len(val.strip()) > 0
        if isinstance(val, list):
            if len(val) == 0:
                return False
            if section in ("hobbies",):
                return any(v for v in val if isinstance(v, str) and v.strip())
            for item in val:
                if isinstance(item, dict):
                    if any(v for v in item.values() if v):
                        return True
            return False
        if isinstance(val, dict):
            for sub_val in val.values():
                if isinstance(sub_val, list) and len(sub_val) > 0:
                    return True
                if isinstance(sub_val, str) and sub_val.strip():
                    return True
        return False

    @staticmethod
    def _summarize_extracted(extracted: dict) -> str:
        if not extracted:
            return "{}"
        lines = []
        for section in SECTIONS:
            if section not in extracted:
                continue
            val = extracted[section]
            if val is None:
                continue
            label = SECTION_LABELS.get(section, section)
            if isinstance(val, str) and val.strip():
                lines.append(f"  {label}: {val[:100]}")
            elif isinstance(val, list) and len(val) > 0:
                lines.append(f"  {label}: {len(val)} entries")
            elif isinstance(val, dict):
                non_empty = {k: v for k, v in val.items() if v}
                if non_empty:
                    lines.append(f"  {label}: {json.dumps(non_empty)}")
        if not lines:
            return "{}"
        return "{\n" + "\n".join(lines) + "\n}"

    def _merge_extracted(self, existing: dict, new_data: dict) -> dict:
        result = dict(existing)
        for key, val in new_data.items():
            if val is None or val == "" or val == [] or val == {}:
                continue
            if isinstance(val, dict) and isinstance(result.get(key), dict):
                result[key] = {**result[key], **val}
            elif isinstance(val, list) and isinstance(result.get(key), list):
                if len(val) > 0:
                    if all(isinstance(v, dict) for v in val):
                        seen = set()
                        merged = list(result[key])
                        for item in val:
                            item_key = json.dumps(item, sort_keys=True)
                            if item_key not in seen:
                                seen.add(item_key)
                                merged.append(item)
                        result[key] = merged
                    else:
                        existing_set = set(result[key])
                        new_set = set(val)
                        result[key] = list(existing_set | new_set)
            else:
                result[key] = val
        return result

    async def start_session(
        self, session: OnboardingSession, first_name: str, last_name: str, target_role: str = "professional"
    ) -> dict:
        session.current_section = "personal_info"
        session.extracted_data = {"personal_info": {"first_name": first_name, "last_name": last_name}}
        session.conversation_history = []

        system = self._build_system_prompt(session, first_name, last_name, target_role)

        try:
            response = await self._llm.chat_json(
                messages=[{"role": "user", "content": f"Hello! I'm {first_name} {last_name}. Please start the interview."}],
                system=system,
                temperature=0.7,
                max_tokens=2048,
            )
        except Exception as e:
            logger.error("Failed to start onboarding: %s", e)
            return {"question": f"Error: {e}. Please try again.", "section": session.current_section, "done": False, "error": str(e)}

        return self._process_llm_response(session, response)

    async def process_answer(self, session: OnboardingSession, answer: str, first_name: str = "", last_name: str = "", target_role: str = "professional") -> dict:
        session.conversation_history.append(ConversationMessage(role="user", content=answer))

        system = self._build_system_prompt(session, first_name, last_name, target_role)

        messages = [
            {"role": m.role, "content": m.content}
            for m in session.conversation_history[-20:]
        ]

        try:
            response = await self._llm.chat_json(
                messages=messages,
                system=system,
                temperature=0.7,
                max_tokens=2048,
            )
        except Exception as e:
            logger.error("Failed to process onboarding answer: %s", e)
            return {"question": f"Error: {e}. Please try again.", "section": session.current_section, "done": False, "error": str(e)}

        return self._process_llm_response(session, response)

    def _process_llm_response(self, session: OnboardingSession, response: Any) -> dict:
        if not isinstance(response, dict):
            logger.warning("LLM returned non-dict response: %s", response)
            return {"question": str(response), "section": session.current_section, "done": False}

        is_done = response.get("done", False)

        if not is_done:
            question = response.get("question", "")
            new_section = response.get("section", session.current_section)

            if new_section and new_section in SECTIONS:
                session.current_section = new_section
            elif new_section == "complete":
                pass

            if question:
                session.conversation_history.append(ConversationMessage(role="assistant", content=question))

            extracted = response.get("extracted", {})
            if extracted and isinstance(extracted, dict):
                session.extracted_data = self._merge_extracted(session.extracted_data, extracted)

            completed = [s for s in SECTIONS[:-1] if self._section_has_data(s, session.extracted_data)]
            completed.append(session.current_section if self._section_has_data(session.current_section, session.extracted_data) else None)
            completed = [s for s in completed if s]

            return {
                "question": question,
                "section": session.current_section,
                "done": False,
                "completed_sections": completed,
                "total_sections": len(SECTIONS),
                "extracted_data": session.extracted_data,
            }

        final_message = response.get("message", "All sections complete!")
        session.conversation_history.append(ConversationMessage(role="assistant", content=final_message))
        session.state = "complete"
        session.current_section = "complete"

        extracted = response.get("extracted", {})
        if extracted and isinstance(extracted, dict):
            session.extracted_data = self._merge_extracted(session.extracted_data, extracted)

        return {
            "question": None,
            "section": "complete",
            "done": True,
            "message": final_message,
            "completed_sections": SECTIONS,
            "total_sections": len(SECTIONS),
            "extracted_data": session.extracted_data,
        }

    def extracted_to_base_cv(self, extracted: dict) -> BaseCV:
        from backend.models import (
            Accomplishment, CareerEntry, Certification, EducationEntry,
            Languages, PersonalInfo, Project, SkillCategory, SpokenLanguage,
            ToolCategory,
        )

        def build_personal_info(pi: dict) -> PersonalInfo:
            return PersonalInfo(
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

        def build_languages(lang: dict) -> Languages:
            return Languages(
                programming=lang.get("programming", []),
                spoken=[SpokenLanguage(**s) for s in lang.get("spoken", []) if isinstance(s, dict) and s.get("language")],
            )

        return BaseCV(
            personal_info=build_personal_info(extracted.get("personal_info", {})),
            professional_summary=extracted.get("professional_summary", ""),
            career=[CareerEntry(**c) for c in extracted.get("career", []) if isinstance(c, dict) and c.get("company")],
            formation=[EducationEntry(**e) for e in extracted.get("formation", []) if isinstance(e, dict) and e.get("institution")],
            skills=[SkillCategory(**s) for s in extracted.get("skills", []) if isinstance(s, dict) and s.get("category")],
            tools=[ToolCategory(**t) for t in extracted.get("tools", []) if isinstance(t, dict) and t.get("category")],
            accomplishments=[Accomplishment(**a) for a in extracted.get("accomplishments", []) if isinstance(a, dict) and a.get("title")],
            projects=[Project(**p) for p in extracted.get("projects", []) if isinstance(p, dict) and p.get("name")],
            certifications=[Certification(**c) for c in extracted.get("certifications", []) if isinstance(c, dict) and c.get("name")],
            hobbies=[h for h in extracted.get("hobbies", []) if isinstance(h, str) and h.strip()],
            languages=build_languages(extracted.get("languages", {})),
        )