# MEMORY.md — Backend

## Structure

```
backend/
├── main.py              # FastAPI app, CORS, lifespan, route registration
├── config.py            # AppConfig model, env/file loader, save
├── models.py            # All Pydantic v2 schemas
├── database/
│   ├── __init__.py      # StorageBackend ABC + factory (get_storage)
│   ├── json_store.py    # Full JSON file-based storage implementation
│   └── mongo_store.py   # MongoDB stub (not implemented)
├── routes/
│   ├── settings.py      # GET/PUT /api/settings, POST /api/settings/test-llm
│   ├── cv.py            # GET/PUT /api/cv, POST /api/cv/ingest-pdf (stub)
│   └── positions.py     # CRUD /api/positions (list, create, get, update, delete)
├── services/
│   ├── llm.py            # LLMClient wrapping openai SDK (AsyncOpenAI)
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

### Storage (`database/`)
- `StorageBackend` ABC: get_cv, save_cv, get_config, save_config, list_positions, get_position, save_position, delete_position, get/save/delete onboarding sessions
- `JsonStore` — full implementation using `data/` directory
- `MongoStore` — importable stub, will raise NotImplementedError
- `get_storage()` factory — returns JsonStore or MongoStore based on config

### Routes

**Settings (`routes/settings.py`)**
- `GET /api/settings` — returns config with redacted API keys
- `PUT /api/settings` — merge-update settings from SettingsUpdate body
- `POST /api/settings/test-llm` — tests AI provider connection

**CV (`routes/cv.py`)**
- `GET /api/cv` — returns CV or `{exists: false}`
- `PUT /api/cv` — full replace of base CV
- `POST /api/cv/ingest-pdf` — stub (501)
- `POST /api/cv/ingest-pdf/confirm` — stub (501)

**Positions (`routes/positions.py`)**
- `GET /api/positions` — list all, optional `?company=` and `?status=` filters
- `POST /api/positions` — create from Position body
- `GET /api/positions/{position_id}` — single position
- `PUT /api/positions/{position_id}` — full update
- `DELETE /api/positions/{position_id}` — delete (removes directory)

### Services

**LLM (`services/llm.py`)**
- `LLMClient`: wraps `AsyncOpenAI` with configurable base_url
- `test_connection()` — quick chat call to verify API key
- `chat()` — full chat completion with system prompt, temperature, max_tokens
- `chat_json()` — chat with JSON response_format, parses result

### Main (`main.py`)
- FastAPI app with CORS (localhost:5173)
- Registers settings, cv, positions routers
- `GET /api/health` — status, has_cv, storage backend info

## Not Yet Implemented
- `services/onboarding.py` — onboarding state machine (Phase 3)
- `services/adapter.py` — CV tailoring logic (Phase 4)
- `services/job_search.py` — web search aggregator (Phase 5)
- `services/pdf_parser.py` — PDF text extraction (Phase 7)
- PDF export (weasyprint integration)
- URL JD scraping
- MongoStore full implementation (Phase 6)
- Migration script JSON ↔ MongoDB (Phase 6)
