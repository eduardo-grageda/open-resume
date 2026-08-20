# MEMORY.md — Open Resume (Root)

## Current Status

**Phase 1 (Backend Core):** Complete  
**Phase 2 (Frontend Foundation):** Complete  
**Phase 3 (Onboarding):** Complete  
**Phase 4 (CV Adaptation & Export):** Complete  
**Phase 5 (Job Search):** Complete  
**Phase 6 (MongoDB & Docker):** Complete  
**Phase 7 (Polish):** Complete

**Desktop Phase 1 (Tauri v2 Setup):** Complete — `src-tauri/` scaffolded, Rust 1.97, `@tauri-apps/cli` v2.11.4, `cargo check` passes. Frontend adapted for Tauri compat (dynamic backend URL, `strictPort`, `clearScreen`).
**Desktop Phase 2 (Backend Adaptations):** Complete — `backend/main.py` supports `--port` (dynamic port binding with `PORT=<n>` stdout), `--data-dir` (platform data dir: `~/.local/share/open-resume/` on Linux, `%APPDATA%\open-resume\` on Windows), SIGTERM/SIGINT graceful shutdown, `/api/shutdown` endpoint, `uvicorn.run()` in standalone mode.
**Desktop Phase 3 (PyInstaller Bundling):** Complete — `backend/open-resume-backend.spec` builds a 74MB standalone `open-resume-backend` binary with all Python deps (FastAPI, uvicorn, weasyprint, curl_cffi, pymongo, etc.). `scripts/build-backend.sh` (Linux) and `scripts/build-backend.ps1` (Windows) automate the build. Binary outputs `PORT=<n>` to stdout, binds to dynamic/fixed port, writes data to `--data-dir`, responds to `/api/health` and `/api/shutdown`. Verified end-to-end: startup (~8s extraction), health check, settings endpoint, clean shutdown.
**Desktop Phase 4 (Integration & Lifecycle):** Complete — `src-tauri/src/lib.rs` implements full sidecar lifecycle: spawns `open-resume-backend`, reads `PORT=<n>` from stdout, polls `/api/health` via raw TCP, injects `window.__BACKEND_PORT__` into webview, kills sidecar on `CloseRequested`. Dev mode fallback when sidecar binary not found.
**Desktop Phase 5 (Build Pipeline):** Complete — `scripts/build-desktop.sh` (Linux) and `scripts/build-desktop.ps1` (Windows) orchestrate full build (backend PyInstaller → frontend Vite → Tauri cargo build). `.github/workflows/desktop-release.yml` CI/CD for tagged releases and manual triggers, targeting `x86_64-unknown-linux-gnu` (Ubuntu) and `x86_64-pc-windows-msvc` (Windows). Linux system deps (libwebkit2gtk, GTK3, etc.) documented. `tauri-action@v0` used for automated Tauri bundling.
**Desktop Phase 6 (Polish):** Complete — App icon generated (1024×1024 `app-icon.png`, `cargo tauri icon` produced `.ico`, `.icns`, multi-size PNGs including Windows `StoreLogo` and `Square*` variants). `tauri.conf.json` extended with `bundle` config (Linux `.deb` with webkit2gtk+gtk3 deps, Windows `.msi` via WiX), `maximized: true`, `visible: false` (hidden on start). Single-instance enforcement via `tauri-plugin-single-instance` (focus existing window on second launch). Full native menu bar: File (Close Window, Quit), Edit (Undo, Redo, Cut, Copy, Paste, Select All), View (Reload, Toggle DevTools), Help (About Open Resume). Splash screen (`frontend/public/splash.html`) — 420×320 centered frameless window with loading spinner and status text, shown while backend sidecar starts. On backend success: splash closes, main window shows. On failure: splash displays error message with Close button. `Cargo.toml` updated with `tray-icon` feature and `tauri-plugin-single-instance` dep. Capabilities updated for splash window.

**Remy Phase 1 (Agent Foundation):** Mostly complete (models/storage/config/skills/registry; agent harness pending)  
**Remy Phase 2 (Scraper Skills & Search Database):** Mostly complete (skills + listings DB; places skill + ChromaDB pending)  
**Remy Phase 3 (Cronjobs):** Complete  
**Remy Phase 4 (AI Analysis & Recommendations):** Complete  
**Remy Phases 5–7:** Not started

### What exists

- `src-tauri/` — Tauri v2 Rust project: `Cargo.toml`, `build.rs`, `src/main.rs`, `src/lib.rs`, `tauri.conf.json`, `capabilities/default.json`, placeholder `icons/icon.png`. Shell + process plugins configured. Sidecar scope for `open-resume-backend`.
- `src-tauri/binaries/` — PyInstaller-built backend sidecar (74MB onefile binary, gitignored).
- `scripts/` — Build automation: `build-backend.sh` (Linux) and `build-backend.ps1` (Windows) for PyInstaller bundling.
- `backend/` — FastAPI app with CORS, health endpoint, config loader, settings routes, CV CRUD routes, positions CRUD routes, LLM client, JSON storage backend, MongoDB storage adapter, Pydantic v2 models, migration script.
- `frontend/` — React 18 + Vite 5 app with react-router-dom v6, react-markdown v9. Six pages (Home, Settings, CV Editor, Positions list, Position detail), Layout with sidebar nav, MdEditor split-pane component, api.js fetch wrapper. Builds clean. Dockerfile for containerized dev. **Tauri compat**: `api.js` detects `window.__BACKEND_PORT__` for dynamic backend URL, `vite.config.js` has `strictPort` + `clearScreen`, `@tauri-apps/cli` in devDeps.
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

- `README.md` — comprehensive documentation: quick start (Linux-only; Windows `install.ps1` pending fix), Remy agent usage guide (queries/tasks/listings/reports/memory), Remy env vars, configuration reference.

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
