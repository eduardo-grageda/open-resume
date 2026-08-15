# MEMORY.md — Backend

## Structure

```
backend/
├── main.py              # FastAPI app, CORS, lifespan, route registration
├── config.py            # AppConfig model, env/file loader, save
├── models.py            # All Pydantic v2 schemas
├── migrate.py           # JSON ↔ MongoDB data migration script
├── database/
│   ├── __init__.py      # StorageBackend ABC + factory (get_storage)
│   ├── json_store.py    # Full JSON file-based storage implementation
│   └── mongo_store.py   # Full MongoDB storage implementation (pymongo AsyncMongoClient)
├── routes/
│   ├── settings.py      # GET/PUT /api/settings, POST /api/settings/test-llm
│   ├── cv.py            # GET/PUT /api/cv, POST onboarding (start/answer/confirm/progress), ingest-pdf stubs
│   ├── positions.py     # CRUD /api/positions, adapt, export md/pdf
│   ├── search.py        # POST /api/search/jobs, GET /api/search/sources, POST /api/search/extract-jd
│   └── star.py          # POST /api/star/start, /answer, /confirm, GET/PUT/DELETE /api/star/stories
├── services/
│   ├── llm.py            # LLMClient wrapping openai SDK (AsyncOpenAI)
│   ├── onboarding.py     # OnboardingService: session state machine, prompt templates, answer processing, extracted→BaseCV conversion
│   ├── adapter.py        # AdapterService: CV tailoring via LLM, prompt construction, response parsing
│   ├── job_search.py     # JobSearchService: SerpAPI + Brave Search, JD extraction via LLM
│   ├── star.py           # StarService: STAR interview prep, achievement identification, S/T/A/R Q&A, pitch generation
│   └── __init__.py
└── requirements.txt
```

## Implemented

### Config (`config.py`)
- `AppConfig` model: openrouter_api_key, openrouter_base_url, openrouter_model, storage_backend, mongo_uri, search_provider, search_api_key
- Env var overrides for all fields
- `load_config()` reads `data/config.json`, falls back to defaults
- `save_config()` writes to `data/config.json`

### Models (`models.py`)
- `PersonalInfo`, `CareerEntry`, `EducationEntry`, `SkillCategory`, `ToolCategory`, `Accomplishment`, `SpokenLanguage`, `Languages`, `Project`, `Certification`
- `BaseCV` — the full CV with all sections
- `Position` — company + JD + tailored CV with auto-derived `company_slug`
- `OnboardingSession` — conversation state for onboarding wizard
- `ConversationMessage` — role + content message
- `SettingsUpdate` — partial settings update model
- `SearchRequest` — job search query with filters (query, location, remote, job_type, experience_level, date_posted)
- `SearchImportRequest` — import a search result as a position
- `StarStory` — single STAR story: title, source_company, source_title, situation, task, action, result, interview_pitch, timestamps
- `StarSession` — STAR prep session state: first_name, last_name, cv_summary, current_phase, current_star_step, achievements, conversation_history, extracted_stories

### Storage (`database/`)
- `StorageBackend` ABC: get_cv, save_cv, get_config, save_config, list_positions, get_position, save_position, delete_position, get/save/delete onboarding sessions, get/save/delete star sessions, list/get/save/delete star stories
- `JsonStore` — full implementation using `data/` directory
- `MongoStore` — full implementation using pymongo AsyncMongoClient with lazy connection
- `get_storage()` factory — returns JsonStore or MongoStore based on config

### Migration (`migrate.py`)
- CLI tool: `python backend/migrate.py {json-to-mongo,mongo-to-json}`
- Migrates config, base CV, positions, and onboarding sessions between backends
- Updates storage_backend setting after migration

### Routes

**Settings (`routes/settings.py`)**
- `GET /api/settings` — returns config with redacted API keys
- `PUT /api/settings` — merge-update settings from SettingsUpdate body
- `POST /api/settings/test-llm` — tests AI provider connection

**CV (`routes/cv.py`)**
- `GET /api/cv` — returns CV or `{exists: false}`
- `PUT /api/cv` — full replace of base CV
- `POST /api/cv/onboard/start` — begins AI-guided onboarding, returns first question
- `POST /api/cv/onboard/answer` — processes answer, returns next question or completion
- `POST /api/cv/onboard/confirm` — finalizes extracted data to BaseCV, saves, deletes session
- `GET /api/cv/onboard/progress/{session_id}` — returns section progress and extracted data
- `POST /api/cv/ingest-pdf` — upload PDF, extract text via pdfplumber, parse with LLM, return structured BaseCV
- `POST /api/cv/ingest-pdf/confirm` — save parsed CV after user review

**Positions (`routes/positions.py`)**
- `GET /api/positions` — list all, optional `?company=` and `?status=` filters
- `POST /api/positions` — create from Position body
- `GET /api/positions/{position_id}` — single position
- `PUT /api/positions/{position_id}` — full update
- `DELETE /api/positions/{position_id}` — delete (removes directory)
- `POST /api/positions/ingest-url` — scrape JD from URL via LLM, return draft Position
- `POST /api/positions/{position_id}/adapt` — generate tailored CV via LLM
- `GET /api/positions/{position_id}/export/md` — download tailored CV as .md
- `GET /api/positions/{position_id}/export/pdf` — generate + download PDF via weasyprint

**Search (`routes/search.py`)**
- `POST /api/search/jobs` — search open positions via configured provider (SerpAPI / Brave Search)
- `GET /api/search/sources` — list available search providers
- `POST /api/search/extract-jd` — fetch URL, extract job description via LLM

**STAR (`routes/star.py`)**
- `POST /api/star/start` — begin STAR prep session; analyzes CV career history, returns first question
- `POST /api/star/answer` — processes user answer, returns next question or completion with extracted stories
- `POST /api/star/confirm` — finalizes stories, generates interview pitches, saves to storage, deletes session
- `GET /api/star/stories` — list all saved STAR stories
- `GET /api/star/stories/{id}` — get a single story
- `PUT /api/star/stories/{id}` — update a story's fields
- `DELETE /api/star/stories/{id}` — delete a story
- `POST /api/star/generate-pitch/{id}` — generate polished interview pitch for a single story

### Services

**LLM (`services/llm.py`)**
- `LLMClient`: wraps `AsyncOpenAI` with configurable base_url
- `test_connection()` — quick chat call to verify API key
- `chat()` — full chat completion with system prompt, temperature, max_tokens
- `chat_json()` — chat with JSON response_format, auto-retries on empty/malformed responses (up to 2 retries, doubles max_tokens on `length` errors), returns `(result, retries)` tuple

**Onboarding (`services/onboarding.py`)**
- `OnboardingService`: manages onboarding session state machine
- 12-section progression: personal_info → professional_summary → career → formation → skills → tools → accomplishments → projects → certifications → programming_languages → spoken_languages → hobbies
- `start_session()` — sends initial prompt, returns first question and extracted data
- `process_answer()` — appends answer to conversation, calls LLM with full context, returns next question/done signal and merged extracted data
- `extracted_to_base_cv()` — converts accumulated extracted_data dict to validated BaseCV model
- System prompt instructs LLM to respond in JSON with `done`, `section`, `question`, `extracted` fields

**Adapter (`services/adapter.py`)**
- `AdapterService`: takes BaseCV + job description, calls LLM to produce tailored CV
- `_format_cv()` — converts BaseCV model to structured markdown for the LLM prompt
- `adapt()` — constructs system prompt per PLAN.md spec, calls LLM, parses response
- `_parse_response()` — splits LLM output into tailored CV markdown and change summary using `---` separator
- System prompt instructs LLM to never invent content, only reorder/emphasize/de-emphasize/omit

**Job Search (`services/job_search.py`)**
- `JobSearchService`: search aggregation via SerpAPI (Google Jobs engine) and Brave Search
- `search()` — dispatches to provider-specific method based on config, normalizes results
- `_search_serpapi()` — queries SerpAPI Google Jobs, parses `jobs_results`
- `_search_brave()` — queries Brave Search web API with job-focused query construction
- `_normalize_results()` — maps provider-specific fields to common schema (title, company, location, url, description_snippet, source, posted_date)
- `extract_jd()` — fetches URL via httpx, strips HTML with BeautifulSoup, sends text to LLM for clean markdown extraction
- `get_available_sources()` — returns `["serpapi", "brave"]`

**PDF Parser (`services/pdf_parser.py`)**
- `PdfParser`: extracts text from PDFs and parses into structured BaseCV via LLM
- `extract_text()` — uses pdfplumber to extract text from PDF pages
- `parse_to_cv()` — sends extracted text to LLM with structured JSON schema prompt
- `parsed_to_base_cv()` — converts LLM JSON response to validated BaseCV model

**STAR (`services/star.py`)**
- `StarService`: manages STAR interview prep session state machine
- `_format_cv_for_star()` — converts BaseCV to structured text for LLM context
- `_extract_achievements_from_cv()` — pulls accomplishments from career entries, achievements, and projects
- `start_session()` — analyzes CV, identifies top achievements, returns intro question
- `process_answer()` — processes user answers through intro → select_achievements → star_questions (S→T→A→R) → review phases
- `generate_pitches()` — generates polished 2-minute interview pitches from completed STAR stories
- `_merge_stories()` — merges extracted story data across LLM responses, keeping longest field values

### Main (`main.py`)
- FastAPI app with CORS (localhost:5173)
- Registers settings, cv, positions, search routers
- `GET /api/health` — status, has_cv, storage backend info

### Not Yet Implemented
- (none — all phases complete)