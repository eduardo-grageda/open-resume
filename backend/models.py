from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _uid() -> str:
    return uuid4().hex


class PersonalInfo(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    address: str = ""
    website: str = ""
    linkedin: str = ""
    github: str = ""
    twitter: str = ""
    other_social: list[dict[str, str]] = Field(default_factory=list)


class CareerEntry(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""
    accomplishments: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str = ""
    institution: str = ""
    field: str = ""
    start_year: str = ""
    end_year: str = ""
    notes: str = ""


class SkillCategory(BaseModel):
    category: str = ""
    technologies: list[str] = Field(default_factory=list)


class ToolCategory(BaseModel):
    category: str = ""
    items: list[str] = Field(default_factory=list)


class Accomplishment(BaseModel):
    title: str = ""
    description: str = ""
    year: str = ""


class SpokenLanguage(BaseModel):
    language: str = ""
    level: str = ""


class Languages(BaseModel):
    programming: list[str] = Field(default_factory=list)
    spoken: list[SpokenLanguage] = Field(default_factory=list)


class Project(BaseModel):
    name: str = ""
    url: str = ""
    year: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str = ""
    issuer: str = ""
    year: str = ""
    url: str = ""


class BaseCV(BaseModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    professional_summary: str = ""
    career: list[CareerEntry] = Field(default_factory=list)
    formation: list[EducationEntry] = Field(default_factory=list)
    skills: list[SkillCategory] = Field(default_factory=list)
    tools: list[ToolCategory] = Field(default_factory=list)
    accomplishments: list[Accomplishment] = Field(default_factory=list)
    hobbies: list[str] = Field(default_factory=list)
    languages: Languages = Field(default_factory=Languages)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class Position(BaseModel):
    id: str = Field(default_factory=_uid)
    company_name: str = ""
    company_slug: str = ""
    job_title: str = ""
    job_description_md: str = ""
    job_source_url: str = ""
    job_source_type: str = "paste"
    tailored_cv_md: str = ""
    change_summary: str = ""
    pdf_export_path: str = ""
    status: str = "new"
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

    @model_validator(mode="after")
    def _derive_slug(self) -> "Position":
        import re
        if self.company_name and not self.company_slug:
            self.company_slug = re.sub(r"[^a-z0-9]+", "-", self.company_name.lower().strip()).strip("-")
        return self


class ConversationMessage(BaseModel):
    role: str
    content: str


class OnboardingSession(BaseModel):
    id: str = Field(default_factory=_uid)
    state: str = "in_progress"
    current_section: str = "personal_info"
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now)


class SettingsUpdate(BaseModel):
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: Optional[str] = None
    openrouter_model: Optional[str] = None
    storage_backend: Optional[str] = None
    mongo_uri: Optional[str] = None
    search_provider: Optional[str] = None
    search_api_key: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    location: str = ""
    remote: bool = False
    job_type: str = ""
    experience_level: str = ""
    date_posted: str = ""


class SearchImportRequest(BaseModel):
    search_result: dict