# MEMORY.md — Open Resume (Root)

## Current Status

**Phase 1 (Backend Core):** Complete  
**Phase 2 (Frontend Foundation):** Complete  
**Phase 3 (Onboarding):** Complete  
**Phase 4 (CV Adaptation & Export):** Complete  
**Phase 5 (Job Search):** Complete  
**Phase 6 (MongoDB & Docker):** Complete  
**Phase 7 (Polish):** Complete

**Remy Phase 1 (Agent Foundation):** Mostly complete (models/storage/config/skills/registry; agent harness pending)  
**Remy Phase 2 (Scraper Skills & Search Database):** Mostly complete (skills + listings DB; places skill + ChromaDB pending)  
**Remy Phase 3 (Cronjobs):** Complete  
**Remy Phase 4 (AI Analysis & Recommendations):** Complete  
**Remy Phases 5–7:** Not started

### What exists

- `backend/` — FastAPI app with CORS, health endpoint, config loader, settings routes, CV CRUD routes, positions CRUD routes, LLM client, JSON storage backend, MongoDB storage adapter, Pydantic v2 models, migration script.
- `frontend/` — React 18 + Vite 5 app with react-router-dom v6, react-markdown v9. Six pages (Home, Settings, CV Editor, Positions list, Position detail), Layout with sidebar nav, MdEditor split-pane component, api.js fetch wrapper. Builds clean. Dockerfile for containerized dev.
- `data/` — runtime directory (gitignored) for config, CV, positions, exports, onboarding sessions, star sessions, star stories, and Remy agent state (`data/remy/`).
- `PLAN.md` — full architecture, data models, API routes, implementation phases.
- `AGENTS.md` — tech stack, commands, conventions, commit format.
- `Dockerfile` — backend container image (Python 3.10-slim).
- `docker-compose.yml` — services: backend, frontend, mongo (profiled).
- `run.sh` — native launch script (venv + npm dev).
- `start-docker.sh` — Docker Compose launch with conditional mongo profile.
- `backend/routes/positions.py` — full CRUD for positions.
- `backend/migrate.py` — JSON ↔ MongoDB data migration tool.
- `backend/services/remy/` — Remy agent: `ScraperSkill` ABC (`base.py`), skill registry with alias support (`__init__.py`), shared utils (`utils.py` — fetch helper, HTML→MD, polite delay, robots.txt), three concrete skills (`aggregator.py`, `linkedin.py` with ToS disclaimer, `occ.py` — fetches via `curl_cffi` browser-TLS impersonation to bypass OCC's Cloudflare bot block), scraper service (`scraper.py` — dedup, upsert, stale-marking), cron scheduler (`scheduler.py` — APScheduler daily/weekly jobs, run persistence, load-on-boot, dispatches scrape/analyze/recommend task types), vector DB (`vectordb.py` — JSON-backed vector store + provider/local embedder), prompts (`prompts.py`), `analyzer.py` (market-trend + skills-gap reports), `recommender.py` (two-pass match scoring), `subagents.py` (analyst/recommender registry), `memory.py` (run index + profile market signals under `data/remy/memory/`).
- `backend/routes/remy.py` — `/api/remy/sources` (skills + enabled state), `/api/remy/queries` CRUD, `/api/remy/tasks` CRUD with scheduler sync, `/api/remy/tasks/{id}/run` manual trigger, `/api/remy/runs` history, `/api/remy/analyze/{query_id}`, `/api/remy/recommend/{query_id}`, `/api/remy/reports` (+ `/{report_id}`). Gated by `REMY_ENABLED` config flag.

- `README.md` — comprehensive documentation with quick start, usage guide, and configuration reference.

### What does NOT exist yet

- **Remy AI Agent phases 5–7** — frontend pages, chat endpoint (deepagents harness), Mongo indexes/politeness polish, import-as-position, topic suggestions. Phases 1–4 are done (Phase 1 agent harness + Phase 2 places/ChromaDB pending). See `REMY_PHASES.md`.
- Tests, linting

### Key decisions

- Default AI model: `deepseek/deepseek-v4-pro` via OpenRouter
- PDF: weasyprint (no LaTeX)
- Web search: SerpAPI first, Brave Search secondary
- Ports: backend :8000, frontend :5173
- No auth — local-only tool
- License: MIT
