from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import load_config
from backend.models import BaseCV, StarSession, ConversationMessage
from backend.services.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert interview coach specializing in the STAR (Situation, Task, Action, Result) methodology used in behavioral interviews at top tech companies.

Your goal: help {first_name} {last_name}, a {target_role}, build 3-5 compelling STAR stories from their career history so they walk into any interview fully prepared.

THE CV:
{cv_summary}

PROCESS:
1. Review the CV and identify the most interview-worthy achievements — moments of leadership, crisis handling, technical breakthroughs, cross-team collaboration, process improvements, or measurable business impact.
2. Present the user with these candidates and ask which they'd like to develop first.
3. For EACH selected achievement, guide the user through STAR with ONE question at a time:
   - SITUATION: "Set the scene. Which company, team, and project was this? What was the challenge or context?"
   - TASK: "What was your specific responsibility or objective in this situation?"
   - ACTION: "Walk me through exactly what you did. Be specific — tools, techniques, decisions, collaboration."
   - RESULT: "What happened? Quantify the impact — metrics, timelines, team size, revenue, user growth, awards, promotions."
4. After completing all 4 steps for an achievement, ask if they want to work on another achievement.

RULES:
- Ask ONE question at a time. Keep them conversational.
- Push for specificity: numbers, team sizes, timelines, dollar amounts, percentages, technologies used.
- NEVER invent or fabricate details. If the CV doesn't mention something, ask — don't assume.
- Be encouraging. Use phrases like "That's a great example" or "Perfect, now let's drill deeper."
- After collecting each answer, extract the structured data into the "extracted" field.

RESPONSE FORMAT (valid JSON only, no markdown wrapping):
{{
  "done": false,
  "phase": "{current_phase}",
  "question": "Your next question here",
  "achievement_label": "Short label for the achievement being discussed",
  "star_step": "{current_star_step}",
  "extracted": {{
    "stories": [
      {{
        "title": "Achievement label",
        "source_company": "Company name",
        "source_title": "Job title",
        "situation": "Context and challenge (accumulated)",
        "task": "Specific responsibility (accumulated)",
        "action": "What was done step by step (accumulated)",
        "result": "Measurable outcome (accumulated)"
      }}
    ]
  }}
}}

When ALL selected achievements have been fully processed, respond with:
{{
  "done": true,
  "phase": "review",
  "star_step": "complete",
  "message": "All stories complete! Here are your STAR stories ready for interview practice.",
  "extracted": {{
    "stories": [
      {{
        "title": "...",
        "source_company": "...",
        "source_title": "...",
        "situation": "...",
        "task": "...",
        "action": "...",
        "result": "..."
      }}
    ]
  }}
}}

IMPORTANT:
- The "extracted.stories" array must always include ALL stories with their current accumulated data, not just the one being discussed.
- Build up each story incrementally across SITUATION → TASK → ACTION → RESULT steps.
- "star_step" must be one of: "situation", "task", "action", "result", or "" (for intro/select phases).
- "phase" must be one of: "intro", "select_achievements", "star_questions", "review".
- Set phase to "star_questions" while working through STAR steps.
- Set "done": true only after ALL stories have complete S, T, A, R sections."""

INTRO_PROMPT_EXTRA = """
You are in the INTRO phase. Start by:
1. Briefly acknowledge the user's career background from the CV.
2. Point out 3-5 standout achievements you've identified that would make excellent STAR stories.
3. Ask which one they'd like to develop first. Be enthusiastic and specific — mention the company and the nature of the achievement.

Current phase: intro
Current star step: (none yet)"""


class StarService:
    def __init__(self) -> None:
        self._config = load_config()

    @property
    def _llm(self) -> LLMClient:
        return LLMClient(self._config)

    def _build_system_prompt(self, session: StarSession) -> str:
        return SYSTEM_PROMPT.format(
            first_name=session.first_name,
            last_name=session.last_name,
            target_role=session.target_role or "professional",
            cv_summary=session.cv_summary,
            current_phase=session.current_phase,
            current_star_step=session.current_star_step,
        )

    @staticmethod
    def _format_cv_for_star(cv: BaseCV) -> str:
        pi = cv.personal_info
        parts: list[str] = []

        parts.append(f"Name: {pi.first_name} {pi.last_name}")
        if pi.email:
            parts.append(f"Email: {pi.email}")
        if pi.linkedin:
            parts.append(f"LinkedIn: {pi.linkedin}")

        if cv.professional_summary:
            parts.append(f"\nProfessional Summary: {cv.professional_summary}")

        if cv.career:
            parts.append("\n## Career History")
            for entry in cv.career:
                parts.append(f"\n### {entry.title} at {entry.company} ({entry.start_date} – {entry.end_date or 'Present'})")
                if entry.location:
                    parts.append(f"Location: {entry.location}")
                if entry.description:
                    parts.append(f"Description: {entry.description}")
                if entry.accomplishments:
                    parts.append("Accomplishments:")
                    for a in entry.accomplishments:
                        parts.append(f"  - {a}")
                if entry.technologies:
                    parts.append(f"Technologies: {', '.join(entry.technologies)}")

        if cv.accomplishments:
            parts.append("\n## Notable Accomplishments")
            for acc in cv.accomplishments:
                parts.append(f"- {acc.title} ({acc.year}): {acc.description}")

        if cv.projects:
            parts.append("\n## Projects")
            for proj in cv.projects:
                url = f" ({proj.url})" if proj.url else ""
                parts.append(f"- {proj.name}{url} ({proj.year}): {proj.description}")

        return "\n".join(parts)

    @staticmethod
    def _extract_achievements_from_cv(cv: BaseCV) -> list[dict]:
        achievements: list[dict] = []
        for entry in cv.career:
            if entry.accomplishments:
                for acc in entry.accomplishments:
                    achievements.append({
                        "company": entry.company,
                        "title": entry.title,
                        "achievement": acc,
                        "technologies": entry.technologies,
                    })
        for acc in cv.accomplishments:
            achievements.append({
                "company": "",
                "title": "",
                "achievement": f"{acc.title}: {acc.description}",
                "technologies": [],
            })
        for proj in cv.projects:
            if proj.description:
                achievements.append({
                    "company": "",
                    "title": "",
                    "achievement": f"Project: {proj.name} — {proj.description}",
                    "technologies": proj.technologies,
                })
        return achievements

    async def start_session(self, session: StarSession, cv: BaseCV, target_role: str = "") -> dict:
        session.cv_summary = self._format_cv_for_star(cv)
        session.achievements = self._extract_achievements_from_cv(cv)
        session.current_phase = "intro"
        session.current_star_step = ""
        session.current_story_index = 0
        session.conversation_history = []
        session.extracted_stories = []
        session.target_role = target_role

        system = self._build_system_prompt(session)
        intro_msg = (
            f"Hello! I'd like to prepare STAR stories for behavioral interviews. "
            f"Here is my CV. Please review it and help me identify my most impactful achievements."
        )

        try:
            response, retries = await self._llm.chat_json(
                messages=[{"role": "user", "content": intro_msg}],
                system=system,
                temperature=0.7,
                max_tokens=2048,
                max_retries=2,
            )
        except Exception as e:
            logger.error("Failed to start STAR session: %s", e)
            return {"question": f"Error: {e}. Please try again.", "phase": session.current_phase, "done": False, "error": str(e)}

        result = self._process_llm_response(session, response)
        result["retries"] = retries
        return result

    async def process_answer(self, session: StarSession, answer: str) -> dict:
        session.conversation_history.append(ConversationMessage(role="user", content=answer))

        system = self._build_system_prompt(session)
        messages = [
            {"role": m.role, "content": m.content}
            for m in session.conversation_history[-20:]
        ]

        try:
            response, retries = await self._llm.chat_json(
                messages=messages,
                system=system,
                temperature=0.7,
                max_tokens=2048,
                max_retries=2,
            )
        except Exception as e:
            logger.error("Failed to process STAR answer: %s", e)
            return {"question": f"Error: {e}. Please try again.", "phase": session.current_phase, "done": False, "error": str(e)}

        result = self._process_llm_response(session, response)
        result["retries"] = retries
        return result

    def _process_llm_response(self, session: StarSession, response: Any) -> dict:
        if not isinstance(response, dict):
            logger.warning("LLM returned non-dict response: %s", response)
            return {"question": str(response), "phase": session.current_phase, "done": False}

        is_done = response.get("done", False)

        if not is_done:
            question = response.get("question", "")
            new_phase = response.get("phase", session.current_phase)
            new_star_step = response.get("star_step", session.current_star_step)

            if new_phase:
                session.current_phase = new_phase
            if new_star_step:
                session.current_star_step = new_star_step

            if question:
                session.conversation_history.append(ConversationMessage(role="assistant", content=question))

            extracted = response.get("extracted", {})
            if extracted and isinstance(extracted, dict):
                stories = extracted.get("stories", [])
                if stories and isinstance(stories, list):
                    session.extracted_stories = self._merge_stories(session.extracted_stories, stories)

            return {
                "question": question,
                "phase": session.current_phase,
                "star_step": session.current_star_step,
                "done": False,
                "stories": session.extracted_stories,
            }

        final_message = response.get("message", "All STAR stories complete!")
        session.conversation_history.append(ConversationMessage(role="assistant", content=final_message))
        session.state = "complete"
        session.current_phase = "review"

        extracted = response.get("extracted", {})
        if extracted and isinstance(extracted, dict):
            stories = extracted.get("stories", [])
            if stories and isinstance(stories, list):
                session.extracted_stories = self._merge_stories(session.extracted_stories, stories)

        return {
            "question": None,
            "phase": "review",
            "star_step": "complete",
            "done": True,
            "message": final_message,
            "stories": session.extracted_stories,
        }

    @staticmethod
    def _merge_stories(existing: list[dict], new_stories: list[dict]) -> list[dict]:
        if not existing:
            return new_stories

        merged: list[dict] = []
        existing_by_title = {}
        for s in existing:
            title = s.get("title", "").strip().lower()
            if title:
                existing_by_title[title] = s

        for new_s in new_stories:
            title = new_s.get("title", "").strip().lower()
            if title and title in existing_by_title:
                existing_story = existing_by_title[title]
                merged_story = dict(existing_story)
                for field in ("situation", "task", "action", "result", "source_company", "source_title"):
                    new_val = new_s.get(field, "")
                    if new_val and len(new_val) > len(merged_story.get(field, "")):
                        merged_story[field] = new_val
                merged.append(merged_story)
            else:
                merged.append(new_s)

        for s in existing:
            title = s.get("title", "").strip().lower()
            if title and title not in {ns.get("title", "").strip().lower() for ns in new_stories}:
                merged.append(s)

        return merged

    async def generate_pitches(self, session: StarSession) -> list[dict]:
        if not session.extracted_stories:
            return []

        stories_text = ""
        for i, story in enumerate(session.extracted_stories, 1):
            stories_text += f"""
STORY {i}: {story.get('title', 'Untitled')}
Company: {story.get('source_company', 'N/A')}
Role: {story.get('source_title', 'N/A')}
SITUATION: {story.get('situation', '')}
TASK: {story.get('task', '')}
ACTION: {story.get('action', '')}
RESULT: {story.get('result', '')}
---
"""

        pitch_system = """You are an interview coach. Given STAR stories, generate a polished 2-minute interview pitch for each one. The pitch should be a natural, conversational narrative that flows through Situation → Task → Action → Result without sounding robotic. Use confident, professional language. Keep each pitch to 150-200 words.

Return valid JSON:
{
  "pitches": [
    {
      "title": "Original story title",
      "interview_pitch": "Polished 2-minute narrative pitch..."
    }
  ]
}"""

        try:
            response, _ = await self._llm.chat_json(
                messages=[{"role": "user", "content": f"Generate interview pitches for these STAR stories:\n\n{stories_text}"}],
                system=pitch_system,
                temperature=0.5,
                max_tokens=4096,
                max_retries=2,
            )
        except Exception as e:
            logger.error("Failed to generate pitches: %s", e)
            return session.extracted_stories

        pitches = response.get("pitches", []) if isinstance(response, dict) else []
        pitch_map = {p.get("title", "").strip().lower(): p.get("interview_pitch", "") for p in pitches}

        result = []
        for story in session.extracted_stories:
            story_copy = dict(story)
            title = story.get("title", "").strip().lower()
            story_copy["interview_pitch"] = pitch_map.get(title, "")
            result.append(story_copy)

        return result