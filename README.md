# Open Resume

An open-source, local-first web tool for managing a comprehensive base CV, searching for open positions, and generating tailored resumes using AI.

## Features

- **Single Base CV** — maintain one comprehensive CV as the source of truth
- **AI-Powered Onboarding** — chat-based wizard to build your CV from scratch
- **PDF Import** — upload an existing CV PDF and let AI extract structured data
- **Job Search** — search open positions across the web (SerpAPI, Brave Search)
- **Tailored Resumes** — generate compact, job-specific CVs using AI adaptation
- **Export** — download tailored CVs as Markdown or PDF
- **Remy Agent** — AI job-hunting assistant that searches OCC, LinkedIn, and SerpAPI on a schedule, analyzes market trends, and scores listings against your CV
- **STAR Interview Prep** — build structured STAR stories from your CV and generate 2-minute interview pitches
- **Local-First** — all data stored locally in JSON files (or optional MongoDB)
- **Multi-Provider** — works with OpenRouter, OpenAI, or any OpenAI-compatible API

## Quick Start

> **Platform note:** Currently supported on Linux only. The Windows install script (`install.ps1`) is pending a fix — contributions welcome.

### Prerequisites

- Linux (Ubuntu/Debian recommended)
- Python 3.10+
- Node.js 18+
- npm
- `build-essential` and system libraries for PDF export (`libpango-1.0-0`, `libpangoft2-1.0-0`, `libffi-dev`, `libgdk-pixbuf2.0-0`, `libxml2`, `libxslt1.1`)

Install system dependencies (Ubuntu/Debian):

```bash
sudo apt install -y python3 python3-venv python3-pip nodejs npm \
  libpango-1.0-0 libpangoft2-1.0-0 libffi-dev libgdk-pixbuf2.0-0 libxml2 libxslt1.1
```

### Setup

**Automated (recommended):**

```bash
chmod +x install.sh && ./install.sh      # Linux
# powershell -ExecutionPolicy Bypass -File install.ps1   # Windows (pending fix)
```

The script checks prerequisites, creates a virtual environment, installs all dependencies, and creates `.env` from the template.

**Manual:**

```bash
# Clone the repository
git clone https://github.com/your-org/open-resume.git
cd open-resume

# Set up backend
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Set up frontend
cd frontend
npm install
cd ..
```

### Configure

Create `.env` from the template or configure via the web UI on first launch:

```bash
cp .env.example .env
```

Edit `.env` with your AI provider API key:

```env
OPENROUTER_API_KEY=your-api-key-here
```

### Run

**Terminal 1 — Backend:**

```bash
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**

```bash
cd frontend && npm run dev
```

Open **http://localhost:5173** in your browser.

On first launch, you'll be redirected to the Settings page to configure your AI provider.

### Run with Docker

```bash
cp .env.example .env
# Edit .env with your API key
docker compose up -d
```

Open **http://localhost:5173**.

## Desktop App (Tauri)

Open Resume can be built as a standalone desktop application for Linux and Windows using Tauri v2. The app bundles the React frontend in a native webview window and spawns the Python backend as a sidecar process.

### Prerequisites (Desktop Build)

All standard prerequisites plus:

- **Rust** 1.77+ — [rustup.rs](https://rustup.rs)
- **Linux system libraries** for WebKitGTK:

```bash
sudo apt install -y \
  libwebkit2gtk-4.1-dev libgtk-3-dev libcairo2-dev \
  libpango1.0-dev libgdk-pixbuf-2.0-dev libsoup-3.0-dev \
  libjavascriptcoregtk-4.1-dev librsvg2-dev \
  libayatana-appindicator3-dev pkg-config
```

- **PyInstaller** — installed automatically by the build script

### Build

**Linux:**

```bash
# Build backend binary
bash scripts/build-backend.sh

# Build full desktop app (backend + frontend + Tauri)
bash scripts/build-desktop.sh
```

**Windows (PowerShell):**

```powershell
powershell -File scripts/build-desktop.ps1
```

This produces:
- Backend: `src-tauri/binaries/open-resume-backend-<target-triple>[.exe]` (74 MB standalone Python binary)
- Frontend: `frontend/dist/` (static Vite build)
- Desktop bundle: `src-tauri/target/release/bundle/` — `.deb` and `.AppImage` (Linux) or `.msi` (Windows)

### Dev Mode

Run the backend separately, then launch the Tauri dev window:

```bash
# Terminal 1 — backend
source venv/bin/activate && uvicorn backend.main:app --port 8000

# Terminal 2 — Tauri dev
cd frontend && npm run tauri:dev
```

In dev mode the frontend loads from the Vite dev server (`localhost:5173`) and proxies API calls to the backend. The splash screen also loads from Vite's dev server.

### Architecture

```
Tauri (Rust) window
├── React/Vite frontend (static or Vite dev server)
│   └── api.js → dynamic backend URL (window.__BACKEND_PORT__)
└── Sidecar: open-resume-backend (PyInstaller binary)
    └── FastAPI on 127.0.0.1:<dynamic port>
```

On launch, Tauri spawns the backend sidecar, reads the port from stdout, polls `/api/health`, then shows the main window. Closing the app terminates the backend. A single-instance plugin prevents duplicate launches.

## Usage Guide

### 1. Configure AI Provider (`/settings`)

Set up your API key, base URL, and model. Click **Test Connection** to verify.

Supported providers:
- **OpenRouter** (default) — `https://openrouter.ai/api/v1`
- **OpenAI** — `https://api.openai.com/v1`
- **Custom** — any OpenAI-compatible endpoint

### 2. Create Your Base CV

**Option A: AI Onboarding Wizard (`/onboard`)**

Answer questions in a chat interface. The AI guides you through all CV sections (personal info, experience, education, skills, etc.) and builds a structured CV.

**Option B: Import PDF (`/cv` → Import PDF tab)**

Upload an existing CV PDF. The AI extracts text, parses it into structured data, and presents it for review before saving.

**Option C: Manual Entry (`/cv`)**

Use the markdown editor to write or edit your CV directly. Supports live preview.

### 3. Search for Jobs (`/search`)

Enter keywords and optionally set filters (location, remote, experience level, date posted). Results are fetched from your configured search provider (SerpAPI or Brave Search).

Click **Import** on any result to scrape the job description and create a position entry.

### 4. Remy Agent — Automated Job Hunting (`/remy`)

Remy is a scheduled AI agent that continuously searches for jobs, analyzes market trends, and recommends the best-matching positions — all without manual intervention.

**Search Queries** (`/remy/queries`): Define what Remy should search for — keywords, cities, sources. Each query can target multiple job boards simultaneously:
- **OCC Mundial** — direct HTML parser for occ.com.mx (Mexican job board)
- **LinkedIn** — public job listings via RSS/guest API
- **SerpAPI / Brave** — aggregator wrapping the general web search provider

**Scheduled Tasks** (`/remy/tasks`): Set up daily or weekly cron jobs to:
- **Scrape** — run search queries across enabled sources and collect new listings
- **Analyze** — generate market-trend and skills-gap reports by comparing listings against your base CV
- **Recommend** — two-pass match scoring: vector similarity narrows candidates, then AI reasoning scores each listing 0–100 with personalized reasons

**Listings Browser** (`/remy/listings`): Browse all collected job listings with filters. Each listing shows the full job description extracted and cleaned by Remy. Import listings as positions for one-click CV adaptation.

**Reports** (`/remy/reports`): Review market analysis reports with top in-demand skills and gap assessments. Recommendation reports show the best matches with detailed reasons.

**Memory** (`/remy/memory`): Your CV change history timeline with automatic snapshots, tracked runs, and the evolving profile Remy builds from your preferences.

The `/remy` dashboard shows the full picture — active queries, scheduled tasks, recent runs (with timestamps, counts, and per-source error details), and the latest collected listings.

Enable Remy with `REMY_ENABLED=true` in `.env` (enabled by default). The scheduler starts automatically when the backend boots.

### 5. Manage Positions (`/positions`)

Positions follow a **Company → Job Description → Tailored CV** hierarchy.

- **Add Position** — paste a job description manually
- **Add from URL** — scrape a job listing URL (AI extracts the JD)
- **Import from Search** — from the search results page

### 6. Generate Tailored CVs

Open a position, go to the **Tailored CV** tab, and click **Generate Tailored CV**.

The AI reads your base CV and the job description, then produces a compact, role-specific resume. It **never invents information** — it only reorders, emphasizes, or de-emphasizes existing content from your base CV.

A change summary explains what was emphasized, de-emphasized, and why.

### 7. Export

From the **Export** tab on any position page:
- **Download Markdown** — `.md` file
- **Download PDF** — `.pdf` file (generated with WeasyPrint)
- **Print Preview** — print-optimized view

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | — | AI provider API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | AI provider base URL |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v4-pro` | Default model |
| `STORAGE_BACKEND` | `json` | `json` or `mongodb` |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `SEARCH_PROVIDER` | `serpapi` | Search provider (`serpapi` or `brave`) |
| `SEARCH_API_KEY` | — | Search API key |
| `REMY_ENABLED` | `true` | Enable the Remy agent and its scheduler |
| `REMY_SOURCES` | `places,linkedin,occ,serpapi` | Comma-separated enabled sources |
| `REMY_REQUEST_DELAY` | `2.0` | Delay between requests (politeness, seconds) |
| `REMY_TZ` | server local | Timezone for scheduled tasks (e.g. `America/Mexico_City`) |
| `REMY_EMBEDDING_MODEL` | — | Embedding model for vector similarity (falls back to local feature-hashing) |
| `GOOGLE_PLACES_API_KEY` | — | Google Places API key for company discovery (optional) |
| `DATA_DIR` | `data` | Directory for JSON storage |
| `HOST` | `0.0.0.0` | Listen address |
| `PORT` | `8000` | Backend port |

## Storage Backends

### JSON (Default)

Data stored in the `data/` directory as JSON files. No database required. Perfect for single-user local use.

### MongoDB (Optional)

Enable with `STORAGE_BACKEND=mongodb` in `.env`. Requires MongoDB 7. Docker Compose includes a MongoDB service (activated via the `mongodb` profile).

A migration script (`backend/migrate.py`) handles JSON ↔ MongoDB transfers.

## Project Structure

```
open-resume/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration loader
│   ├── models.py            # Pydantic data models
│   ├── database/            # Storage backends (JSON, MongoDB)
│   ├── routes/              # API routes (CV, positions, search, settings, remy, star)
│   └── services/            # Business logic (LLM, onboarding, adapter, search)
│       └── remy/            # Remy agent (skills, scraper, scheduler, analyzer, recommender, vector DB)
├── frontend/
│   └── src/
│       ├── pages/           # React pages
│       └── components/      # Reusable components
├── data/                    # Runtime data (gitignored)
├── install.sh               # Linux install script
├── install.ps1              # Windows install script (pending fix)
├── docker-compose.yml       # Docker services
└── PLAN.md                  # Development plan
```

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic v2, `openai` SDK
- **Frontend**: React 18+, Vite, react-router-dom v6, react-markdown v9
- **Storage**: JSON files (default) or MongoDB 7
- **PDF**: weasyprint (export), pdfplumber (ingest)
- **AI**: OpenRouter, OpenAI, or any OpenAI-compatible endpoint

## Principles

- **Open Source** — MIT licensed
- **Local-First** — no auth, no cloud dependency
- **JSON by Default** — zero-dependency storage
- **Factual Accuracy** — AI reorders and emphasizes; never invents
- **You Own Your Data** — everything stored locally

## License

MIT