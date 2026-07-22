# MEMORY.md — Open Resume (Root)

## Current Status

**Phase 1 (Backend Core):** Complete  
**Phase 2 (Frontend Foundation):** Complete  
**Phase 3 (Onboarding):** Complete  
**Phase 4 (CV Adaptation & Export):** Complete  
**Phase 5 (Job Search):** Complete  
**Phase 6 (MongoDB & Docker):** Complete

### What exists

- `backend/` — FastAPI app with CORS, health endpoint, config loader, settings routes, CV CRUD routes, positions CRUD routes, LLM client, JSON storage backend, MongoDB storage adapter, Pydantic v2 models, migration script.
- `frontend/` — React 18 + Vite 5 app with react-router-dom v6, react-markdown v9. Six pages (Home, Settings, CV Editor, Positions list, Position detail), Layout with sidebar nav, MdEditor split-pane component, api.js fetch wrapper. Builds clean. Dockerfile for containerized dev.
- `data/` — runtime directory (gitignored) for config, CV, positions, exports, onboarding sessions.
- `PLAN.md` — full architecture, data models, API routes, implementation phases.
- `AGENTS.md` — tech stack, commands, conventions, commit format.
- `Dockerfile` — backend container image (Python 3.10-slim).
- `docker-compose.yml` — services: backend, frontend, mongo (profiled).
- `run.sh` — native launch script (venv + npm dev).
- `start-docker.sh` — Docker Compose launch with conditional mongo profile.
- `backend/routes/positions.py` — full CRUD for positions.
- `backend/migrate.py` — JSON ↔ MongoDB data migration tool.

### What does NOT exist yet

- PDF ingest, URL scraping, polish (Phase 7)
- Tests, linting

### Key decisions

- Default AI model: `openai/gpt-4o` via OpenRouter
- PDF: weasyprint (no LaTeX)
- Web search: SerpAPI first, Brave Search secondary
- Ports: backend :8000, frontend :5173
- No auth — local-only tool
- License: MIT
