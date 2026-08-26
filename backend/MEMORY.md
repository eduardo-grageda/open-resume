# MEMORY.md — Backend

## Structure

```
backend/
├── main.py              # FastAPI app, CORS, lifespan, route registration
├── config.py            # AppConfig model, env/file loader, save
├── models.py            # All Pydantic v2 schemas
├── migrate.py           # JSON ↔ MongoDB data migration script
├── open-resume-backend.spec  # PyInstaller build config
├── database/
│   ├── __init__.py      # StorageBackend ABC + factory (get_storage)
│   ├── json_store.py    # Full JSON file-based storage implementation
│   └── mongo_store.py   # Full MongoDB storage implementation (pymongo AsyncMongoClient)
├── routes/
│   ├── settings.py      # GET/PUT /api/settings, POST /api/settings/test-llm
│   ├── cv.py            # GET/PUT /api/cv, POST onboarding (start/answer/confirm/progress), ingest-pdf stubs
│   ├── positions.py     # CRUD /api/positions, adapt, export md/pdf
│   ├── search.py        # POST /api/search/jobs, GET /api/search/sources, POST /api/search/extract-jd
│   ├── star.py          # POST /api/star/start, /answer, /confirm, GET/PUT/DELETE /api/star/stories
│   └── remy.py          # Remy routes: sources, queries, tasks, runs, listings, reports, analyze/recommend, chat (SSE), memory, import listing→position
├── services/
│   ├── llm.py            # LLMClient wrapping openai SDK (AsyncOpenAI)
│   ├── onboarding.py     # OnboardingService: session state machine, prompt templates, answer processing, extracted→BaseCV conversion
│   ├── adapter.py        # AdapterService: CV tailoring via LLM, prompt construction, response parsing
│   ├── job_search.py     # JobSearchService: SerpAPI + Brave Search, JD extraction via LLM
│   ├── star.py           # StarService: STAR interview prep, achievement identification, S/T/A/R Q&A, pitch generation
│   ├── remy/             # Remy agent: base.py (ScraperSkill ABC), __init__.py (skill registry),
│   │                     #   utils.py, occ.py, linkedin.py, aggregator.py, scraper.py, scheduler.py,
│   │                     #   vectordb.py, prompts.py, analyzer.py, recommender.py, subagents.py,
│   │                     #   memory.py, chat.py
│   └── __init__.py
└── requirements.txt
```

## Implemented

### Config (`config.py`)
- `AppConfig` model: openrouter_api_key, openrouter_base_url, openrouter_model, storage_backend, mongo_uri, search_provider, search_api_key
- Remy agent fields: remy_enabled (bool, default true), remy_sources ("places,linkedin,occ,serpapi"), remy_request_delay (2.0), remy_tz ("" = server local), remy_embedding_model (""), google_places_api_key ("")
- Env var overrides for all fields (REMY_ENABLED parsed as bool, REMY_REQUEST_DELAY as float)
- `load_config()` reads `data/config.json`, falls back to defaults
- `save_config()` writes to `data/config.json`
- All text file I/O (config, JSON store, Remy memory/vectordb, migrate) uses explicit `encoding="utf-8"` so non-ASCII content (emoji, accents) is safe on Windows (default cp1252 otherwise throws `UnicodeEncodeError`)

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
- `RemyCity` — city search target: name, country, lat, lng, radius_km (default Guadalajara, MX, 25 km)
- `RemyQuery` (+ `RemyQueryInput`) — saved search profile: name, keywords, cities, sources, remote_only, experience_level, exclude_keywords, enabled
- `RemyListing` — one scraped job posting: source, query_id, title, company, location, url (dedup key), salary, description_md, posted_date, first_seen_at, last_seen_at, is_active, embedding_id, imported_position_id
- `RemyTask` (+ `RemyTaskInput`) — cronjob: query_id, type (scrape|analyze|recommend), frequency (daily|weekly — validated at model level), day_of_week (0-6, weekly only), time (HH:MM — validated at model level), enabled
- `RemyRun` — execution record: task_id, trigger (cron|manual), status (running|success|failed|partial), started_at, finished_at, listings_found, new_listings, error, log
- `RemyReport` — persisted AI output: run_id, query_id, type (analysis|recommendation), content_md, top_matches (`RemyTopMatch`: listing_id, listing_title, listing_company, score 0-100, reason)

### Storage (`database/`)
- `StorageBackend` ABC: get_cv, save_cv, get_config, save_config, list_positions, get_position, save_position, delete_position, get/save/delete onboarding sessions, get/save/delete star sessions, list/get/save/delete star stories
- Remy section: list/get/save/delete remy queries & tasks; list/get/get_by_url/save remy listings (filter by source, query_id, is_active, limit/offset); list/get/save remy runs (filter by task_id); list/get/save remy reports (filter by query_id)
- `JsonStore` — full implementation; Remy data as JSON files under `data/remy/` (queries.json, listings.json, tasks.json, runs.json, reports.json)
- `MongoStore` — full implementation using pymongo AsyncMongoClient with lazy connection; Remy collections `remy_queries`, `remy_listings`, `remy_tasks`, `remy_runs`, `remy_reports`
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
- `PUT /api/cv` — full replace of base CV, triggers Remy CV snapshot if enabled
- `POST /api/cv/onboard/start` — begins AI-guided onboarding, returns first question
- `POST /api/cv/onboard/answer` — processes answer, returns next question or completion
- `POST /api/cv/onboard/confirm` — finalizes extracted data to BaseCV, saves, triggers snapshot, deletes session
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

**Remy (`routes/remy.py`)**
- `GET /api/remy/sources` — list enabled (config) + implemented (registry) scraper skills
- `GET /api/remy/queries` — list search profiles
- `POST /api/remy/queries` — create from `RemyQueryInput`
- `GET /api/remy/queries/{id}` — single query
- `PUT /api/remy/queries/{id}` — update (preserves id/created_at)
- `DELETE /api/remy/queries/{id}` — delete
- `POST /api/remy/queries/{id}/scrape` — manual trigger: run all enabled skills, dedup, persist Run + stats
- `GET /api/remy/listings` — browse (`?source=`, `?query_id=`, `?active=`, `?new=`, `?search=`, `?limit=`, `?offset=`)
- `GET /api/remy/listings/{id}` — detail, optional `?refresh=true` re-fetches from source
- `POST /api/remy/listings/{id}/import` — create Position from listing, set `imported_position_id`
- `GET /api/remy/tasks` — list cron tasks
- `POST /api/remy/tasks` — create (validates query_id exists, 422 on bad frequency/time/day_of_week); schedules job
- `GET /api/remy/tasks/{id}` — single task
- `PUT /api/remy/tasks/{id}` — update (preserves id/created_at); reschedules job
- `DELETE /api/remy/tasks/{id}` — delete; removes job
- `POST /api/remy/tasks/{id}/run` — manual trigger, returns persisted `RemyRun`
- `GET /api/remy/runs` — run history (`?task_id=`, `?limit=`, `?offset=`, newest first)
- `GET /api/remy/runs/{id}` — single run
- `POST /api/remy/analyze/{query_id}` — run market analysis, returns `{run, report}` (502 on failure)
- `POST /api/remy/recommend/{query_id}` — run recommendations, returns `{run, report}` (502 on failure)
- `GET /api/remy/reports` — report history (`?query_id=`, `?limit=`, `?offset=`, newest first)
- `GET /api/remy/reports/{id}` — single report
- `POST /api/remy/chat` — SSE streaming conversational agent (`{message, thread_id?}` → SSE `data:` events)
- `GET /api/remy/chat/threads` — list saved chat threads
- `GET /api/remy/chat/{thread_id}` — resume thread (returns messages array)
- `DELETE /api/remy/chat/{thread_id}` — delete thread
- `GET /api/remy/memory` — profile + CV change history + recent tracked runs
- `DELETE /api/remy/memory` — clear all memory (profile, CV history, run index)
- All routes return 404 when `REMY_ENABLED=false`

### Services

**LLM (`services/llm.py`)**
- `LLMClient`: wraps `AsyncOpenAI` with configurable base_url
- `test_connection()` — quick chat call to verify API key
- `chat()` — full chat completion with system prompt, temperature, max_tokens
- `chat_json()` — chat with JSON response_format, auto-retries on empty/malformed responses (up to 2 retries, doubles max_tokens on `length` errors), returns `(result, retries)` tuple
- `chat_stream()` — streaming chat completion, async generator yielding text deltas via `AsyncOpenAI` streaming API
- `embed(texts, model)` — embeddings via OpenAI-compatible endpoint (used by Remy vectordb when `REMY_EMBEDDING_MODEL` is set)

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

**Remy skills (`services/remy/`)**
- `base.py` — `ScraperSkill` ABC: class attrs `name`/`display_name`/`description`/`aliases`/`tos_notice`, abstract `search(query, limit)` → normalized listing dicts, `fetch_detail(url)` → cleaned markdown
- `__init__.py` — skill registry: `register` decorator, `get_skill(name)`, `available_skills()`, `skill_info()`, `enabled_sources(config)` (parses REMY_SOURCES). Built-in skills lazy-loaded via `_ensure_loaded()`.
- `utils.py` — shared helpers: `fetch_text()` (httpx with headers), `html_to_markdown()` (bs4 deterministic converter), `polite_sleep()` (respects `REMY_REQUEST_DELAY`), `normalize_url()` (strip tracking params for dedup), `url_is_blocked()` (robots.txt cache), `slugify()`.
- `aggregator.py` — `AggregatorSkill`: wraps `JobSearchService` (SerpAPI/Brave). Registered under name `aggregator` with aliases `serpapi`/`brave`. `fetch_detail()` delegates to LLM-based JD extractor (if configured) falling back to HTML→MD.
- `linkedin.py` — `LinkedInSkill`: guest jobs API (`jobs-guest/jobs/api/seeMoreJobPostings/search` for cards, `jobs-guest/jobs/api/jobPosting/{id}` for detail). Includes `tos_notice` disclaimer. Parses `div.base-card` cards.
- `occ.py` — `OccSkill`: OCC Mundial HTML parser (occ.com.mx). Search URL: `/empleos/de-{keyword}/`. Parses `div.card-job-offer[data-id]` cards. Fetches via `curl_cffi` with browser TLS impersonation (`IMPERSONATE = "chrome"`) — OCC's Cloudflare 403s httpx clients ("scraping abuse") regardless of cookies/headers; challenge detection falls back to link-only stub. Manual fallback if Turnstile escalates: solve in a real browser and export cookies (not wired in).
- `scraper.py` — `ScraperService.run_query()`: resolve enabled skills for a query, run each skill, dedup by URL (normalize_url → `get_remy_listing_by_url`), upsert listings, mark stale listings inactive per (query, source). `ScrapeResult`/`ScrapeStats` dataclasses.
- `POST /api/remy/queries/{id}/scrape` — manual trigger: executes scraper, persists `RemyRun` with stats.
- `scheduler.py` — `RemyScheduler`: APScheduler `AsyncIOScheduler` (daily/weekly cron only). `start()` loads persisted enabled tasks from storage and registers jobs; `stop()` on shutdown; `sync_task(task)` add/update/remove one job (used by task routes); `run_now(task_id)` manual execution; `reload()` syncs all jobs with storage. Jobs: `max_instances=1`, `coalesce=True`, 1h misfire grace. Timezone from `REMY_TZ` (ZoneInfo) or server-local. `_execute_task()` persists `RemyRun` (running → success/partial/failed) with listings counts + per-source log; dispatches all three task types: `scrape` → `run_query()`, `analyze` → `analyzer.run_analysis()`, `recommend` → `recommender.run_recommendation()`. Wired to FastAPI lifespan in `main.py` when `REMY_ENABLED`.
- `vectordb.py` — vector search backend (Phase 2/4): `Embedder` (provider embeddings via `LLMClient.embed()` when `REMY_EMBEDDING_MODEL` + API key set, otherwise deterministic dependency-free local feature-hashing embedder, dim 512), `VectorStore` (JSON-persisted under `data/remy/vectors/vectors.json`; `upsert`/`get`/`delete`/`search` with pure-Python cosine similarity), helpers `listing_text()`, `cv_text()` (reuses `AdapterService._format_cv`), `ensure_listing_embedded()`, `get_cv_vector()` (cached per `cv.updated_at`). Swap-in point for ChromaDB later.
- `prompts.py` — analyst + recommender system prompts (JSON schemas, "never invent experience" rule) and message builders (`build_analyst_messages`, `build_recommender_messages`).
- `analyzer.py` — `RemyAnalyzer`: market-trend + skills-gap report. Embeds active query listings, gets CV vector, selects 15 nearest in vector space (falls back to query keywords vector if no CV), LLM JSON → `content_md` + `top_skills`; vector-only fallback report when LLM unavailable. `run_analysis(storage, query, run)` helper updates the `RemyRun` and records memory. Returns `AnalysisResult(report, listings_considered, top_skills)`.
- `recommender.py` — `RemyRecommender`: two-pass scoring — pass 1 vector similarity narrows to top 20 candidates, pass 2 LLM scores 0-100 with one-sentence reasons (fallback: relative vector scores). Returns `RecommendationResult(report, listings_considered)`; `run_recommendation(storage, query, run)` helper updates the `RemyRun` + memory.
- `subagents.py` — sub-agent registry (`SUBAGENTS`: `analyst`, `recommender` specs with handler functions), `get_subagent(name)`, `run_subagent(name, query, storage)` dispatch — the entry point future deepagents `task` tools will call.
- `memory.py` — `RemyMemory` (singleton via `get_remy_memory()`): JSON under `data/remy/memory/` — `profile.json` (role, skills_timeline, preferences, `market_signals.top_skills` merged after analysis runs) and `runs_index.json` (last 200 runs). CV chronicler: `snapshot_cv(cv)` saves timestamped JSON in `cv_history/` + `cv_history.index.json` (max 100), `_update_profile_from_cv()` auto-updates profile on each CV save, `list_cv_history()`, `get_cv_snapshot()`, `clear()`. Chat threads: `list_threads()`, `get_thread()`, `save_thread()`, `delete_thread()` stored as `chat_{id}.json`.
- `chat.py` — Conversational agent: `stream_chat()` async generator builds context from CV + queries + listings + reports + memory profile, streams LLM response via SSE `{type:"meta"|"delta"|"done"|"error"}` events, saves thread history on completion. `list_threads()`, `get_thread()`, `delete_thread()` wrappers.
- `prompts.py` — `AGENT_SYSTEM_PROMPT` (main conversational Remy persona), `ANALYST_SYSTEM_PROMPT`, `RECOMMENDER_SYSTEM_PROMPT`, message builders.

### Main (`main.py`)
- FastAPI app with CORS (localhost:5173)
- Registers settings, cv, positions, search, star, remy routers
- `GET /api/health` — status, has_cv, storage backend info
- `POST /api/shutdown` — graceful shutdown via SIGTERM
- Standalone mode (`__name__ == "__main__"`): argparse `--port` (0=auto), `--data-dir`; platform data dir (`~/.local/share/open-resume/` Linux, `%APPDATA%\open-resume\` Windows); `PORT=<n>` stdout; SIGTERM/SIGINT handlers; `uvicorn.run()` on `127.0.0.1`
- Import mode (`uvicorn backend.main:app`): no CLI parsing, defaults to `DATA_DIR=./data`, no stdout PORT= line

### Not Yet Implemented
- Remy Phase 6–7: Mongo unique indexes/politeness polish, import-as-position end-to-end integration, topic suggestions, deepagents harness (Phase 1 items 10-16) — see `REMY_PHASES.md`
- Desktop Phases 4–6: Integration & lifecycle, build pipeline, polish — see `DESKTOP_PLAN.md`
- Tests, linting

### Desktop Bundling (Phase 3 — Complete)
- `backend/open-resume-backend.spec` — PyInstaller spec: onefile mode, `pathex=['..']` for package resolution, comprehensive hiddenimports (uvicorn, fastapi, pydantic, weasyprint, apscheduler, pymongo, python_multipart, etc.), curl_cffi dynamic libs collected, excludes for tkinter/pip/setuptools. Built binary: 74MB.
- `scripts/build-backend.sh` (Linux) — builds via `pyinstaller --clean --noconfirm backend/open-resume-backend.spec`, copies binary to `src-tauri/binaries/open-resume-backend-x86_64-unknown-linux-gnu`.
- `scripts/build-backend.ps1` (Windows) — equivalent PowerShell script, copies to `src-tauri/binaries/open-resume-backend-x86_64-pc-windows-msvc.exe`.
- Verified: binary starts, prints `PORT=<n>`, responds to `/api/health` (`{"status":"ok","has_cv":false,"storage":"json"}`), creates data directories, shuts down cleanly via `/api/shutdown`.