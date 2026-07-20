# AGENTS.md — Open Resume

An open-source, local-first web tool for managing a comprehensive base CV, searching for open positions, and generating tailored resumes using AI.

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic v2, `openai` SDK (OpenRouter/OpenAI-compatible)
- **Frontend**: React 18+, Vite, react-router-dom v6, react-markdown v9
- **Storage**: JSON files (default) or MongoDB 7 (optional)
- **AI**: OpenRouter (default), OpenAI, or any OpenAI-compatible endpoint
- **PDF**: weasyprint for export, pdfplumber for ingest

## Commands

```bash
# Backend (from repo root)
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (from repo root)
cd frontend && npm run dev

# Install backend deps
pip install -r backend/requirements.txt

# Install frontend deps
cd frontend && npm install

# Docker
docker compose up -d
```

No lint or test commands exist yet.

## Project Structure

See `PLAN.md` for the full directory layout.

## Code Conventions

- Backend: Python, Pydantic v2 models, async FastAPI routes, type hints everywhere.
- Storage is abstracted behind a common interface (`database/json_store.py`, `database/mongo_store.py`). Routes never depend on the storage backend directly — they use the factory in `database/__init__.py`.
- AI calls go through `services/llm.py` — a single client that wraps the `openai` SDK with configurable `base_url`.
- Frontend: Functional components, hooks, `api.js` fetch wrapper for all backend calls.
- No auth — local-only tool. No telemetry, no external services beyond the configured AI/search providers.
- License: MIT.

## Memory Files

After every meaningful change, update the relevant MEMORY.md file(s) to reflect the new state:

- `MEMORY.md` (root) — overall project status, what phases are done, key decisions
- `backend/MEMORY.md` — backend modules, routes, services, what's implemented vs pending
- `frontend/MEMORY.md` — frontend pages, components, design system, what's implemented vs pending

Keep these files concise but accurate. They serve as the source of truth for what exists and what remains.

## Commit Convention

```
type(scope): short summary (imperative, <=72 chars)

Optional body explaining what and why. Wrap at 72 chars.
```

**Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`

**Scopes:** `backend`, `frontend`, `storage`, `ai`, `routes`, `models`, `config`, `pdf`, `search`, `docker`, `onboarding`, `adapt`, `export`, `ui`, `api`

**Examples:**
- `feat(backend): add FastAPI app scaffold with CORS and health endpoint`
- `feat(storage): implement JSON file-based storage backend`
- `feat(ai): add LLM client wrapper with connection test`
- `feat(routes): add settings and base CV CRUD endpoints`
- `chore(docker): add Docker Compose with MongoDB profile`

## Implementation Phases

See `PLAN.md` for full details. Current phase is tracked below:

- [x] Phase 1: Backend Core
- [x] Phase 2: Frontend Foundation
- [ ] Phase 3: Onboarding
- [ ] Phase 4: CV Adaptation & Export
- [ ] Phase 5: Job Search
- [ ] Phase 6: MongoDB & Docker
- [ ] Phase 7: Polish