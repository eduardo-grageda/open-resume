# MEMORY.md — Open Resume (Root)

## Current Status

**Phase 1 (Backend Core):** Complete  
**Phase 2 (Frontend Foundation):** Complete  
**Phase 3 (Onboarding):** Complete  
**Phase 4 (CV Adaptation & Export):** Complete  
**Phase 5 (Job Search):** Complete  
**Phase 6 (MongoDB & Docker):** Complete  
**Phase 7 (Polish):** Complete

**Remy Phase 1 (Agent Foundation):** Complete  
**Remy Phase 2 (Scraper Skills & Search Database):** Complete  
**Remy Phases 3–6:** Not started

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
- `backend/services/remy/` — Remy agent: `ScraperSkill` ABC (`base.py`), skill registry with alias support (`__init__.py`), shared utils (`utils.py` — fetch helper, HTML→MD, polite delay, robots.txt), three concrete skills (`aggregator.py`, `linkedin.py` with ToS disclaimer, `occ.py`), scraper service (`scraper.py` — dedup, upsert, stale-marking).
- `backend/routes/remy.py` — `/api/remy/sources` (skills + enabled state) and `/api/remy/queries` CRUD. Gated by `REMY_ENABLED` config flag.

- `README.md` — comprehensive documentation with quick start, usage guide, and configuration reference.

### What does NOT exist yet

- **Remy AI Agent phases 3–6** — daily/weekly cron scheduler (apscheduler), AI analysis & recommendations (LangGraph deepagents), frontend pages, Mongo indexes/politeness polish. Phases 1–2 are done. See `REMY_PHASES.md`.
- Tests, linting

### Key decisions

- Default AI model: `deepseek/deepseek-v4-pro` via OpenRouter
- PDF: weasyprint (no LaTeX)
- Web search: SerpAPI first, Brave Search secondary
- Ports: backend :8000, frontend :5173
- No auth — local-only tool
- License: MIT
