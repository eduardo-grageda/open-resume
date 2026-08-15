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
    remy_enabled: Optional[bool] = None
    remy_sources: Optional[str] = None
    remy_request_delay: Optional[float] = None
    remy_tz: Optional[str] = None
    remy_embedding_model: Optional[str] = None
    google_places_api_key: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    location: str = ""
    remote: bool = False
    job_type: str = ""
    experience_level: str = ""
    date_posted: str = ""


class SearchImportRequest(BaseModel):
    search_result: dict


class RemyCity(BaseModel):
    name: str = "Guadalajara"
    country: str = "MX"
    lat: float = 20.6597
    lng: float = -103.3496
    radius_km: float = 25.0


def _default_cities() -> list[RemyCity]:
    return [RemyCity()]


class RemyQuery(BaseModel):
    id: str = Field(default_factory=_uid)
    name: str = ""
    keywords: list[str] = Field(default_factory=list)
    cities: list[RemyCity] = Field(default_factory=_default_cities)
    sources: list[str] = Field(default_factory=list)
    remote_only: bool = False
    experience_level: str = "any"
    exclude_keywords: list[str] = Field(default_factory=list)
    enabled: bool = True
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class RemyQueryInput(BaseModel):
    name: str = ""
    keywords: list[str] = Field(default_factory=list)
    cities: list[RemyCity] = Field(default_factory=_default_cities)
    sources: list[str] = Field(default_factory=list)
    remote_only: bool = False
    experience_level: str = "any"
    exclude_keywords: list[str] = Field(default_factory=list)
    enabled: bool = True


class RemyListing(BaseModel):
    id: str = Field(default_factory=_uid)
    source: str = ""
    query_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    salary: str = ""
    description_md: str = ""
    posted_date: str = ""
    first_seen_at: str = Field(default_factory=_now)
    last_seen_at: str = Field(default_factory=_now)
    is_active: bool = True
    embedding_id: str = ""
    imported_position_id: str = ""


class RemyTask(BaseModel):
    id: str = Field(default_factory=_uid)
    query_id: str = ""
    type: str = "scrape"
    frequency: str = "daily"
    day_of_week: int = 0
    time: str = "09:00"
    enabled: bool = True
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

    @model_validator(mode="after")
    def _validate_frequency(self) -> "RemyTask":
        if self.frequency not in ("daily", "weekly"):
            raise ValueError("frequency must be 'daily' or 'weekly'")
        if self.type not in ("scrape", "analyze", "recommend"):
            raise ValueError("type must be 'scrape', 'analyze', or 'recommend'")
        if self.frequency == "weekly" and (self.day_of_week < 0 or self.day_of_week > 6):
            raise ValueError("day_of_week must be 0-6 for weekly tasks")
        return self


class RemyTaskInput(BaseModel):
    query_id: str = ""
    type: str = "scrape"
    frequency: str = "daily"
    day_of_week: int = 0
    time: str = "09:00"
    enabled: bool = True


class RemyRun(BaseModel):
    id: str = Field(default_factory=_uid)
    task_id: str = ""
    trigger: str = "manual"
    status: str = "running"
    started_at: str = Field(default_factory=_now)
    finished_at: str = ""
    listings_found: int = 0
    new_listings: int = 0
    error: str = ""
    log: str = ""


class RemyTopMatch(BaseModel):
    listing_id: str = ""
    score: int = 0
    reason: str = ""


class RemyReport(BaseModel):
    id: str = Field(default_factory=_uid)
    run_id: str = ""
    query_id: str = ""
    type: str = "analysis"
    content_md: str = ""
    top_matches: list[RemyTopMatch] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now)


class StarStory(BaseModel):
    id: str = Field(default_factory=_uid)
    title: str = ""
    source_company: str = ""
    source_title: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    interview_pitch: str = ""
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class StarSession(BaseModel):
    id: str = Field(default_factory=_uid)
    state: str = "in_progress"
    first_name: str = ""
    last_name: str = ""
    target_role: str = ""
    cv_summary: str = ""
    current_phase: str = "intro"
    current_story_index: int = 0
    current_star_step: str = ""
    achievements: list[dict] = Field(default_factory=list)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    extracted_stories: list[dict] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now)