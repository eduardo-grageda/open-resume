# MEMORY.md — Open Resume (Root)

## Current Status

**Phase 1 (Backend Core):** Complete  
**Phase 2 (Frontend Foundation):** Complete  
**Phase 3 (Onboarding):** Complete  
**Phase 4 (CV Adaptation & Export):** Complete

### What exists

- `backend/` — FastAPI app with CORS, health endpoint, config loader, settings routes, CV CRUD routes, positions CRUD routes, LLM client, JSON storage backend, Mongo storage stub, Pydantic v2 models.
- `frontend/` — React 18 + Vite 5 app with react-router-dom v6, react-markdown v9. Six pages (Home, Settings, CV Editor, Positions list, Position detail), Layout with sidebar nav, MdEditor split-pane component, api.js fetch wrapper. Builds clean.
- `data/` — runtime directory (gitignored) for config, CV, positions, exports, onboarding sessions.
- `PLAN.md` — full architecture, data models, API routes, implementation phases.
- `AGENTS.md` — tech stack, commands, conventions, commit format.
- `backend/routes/positions.py` — full CRUD for positions (created as part of Phase 2 to support frontend pages).

### What does NOT exist yet

- Onboarding wizard (Phase 3) — COMPLETE
- CV adaptation / export to PDF (Phase 4) — COMPLETE
- Job search integration (Phase 5)
- MongoDB adapter implementation (Phase 6)
- Docker setup (Phase 6)
- PDF ingest, URL scraping, polish (Phase 7)
- Tests, linting

### Key decisions

- Default AI model: `openai/gpt-4o` via OpenRouter
- PDF: weasyprint (no LaTeX)
- Web search: SerpAPI first, Brave Search secondary
- Ports: backend :8000, frontend :5173
- No auth — local-only tool
- License: MIT
