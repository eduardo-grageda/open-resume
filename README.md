# Open Resume

An open-source, local-first web tool for managing a comprehensive base CV, searching for open positions, and generating tailored resumes using AI.

## Features

- **Single Base CV** — maintain one comprehensive CV as the source of truth
- **AI-Powered Onboarding** — chat-based wizard to build your CV from scratch
- **PDF Import** — upload an existing CV PDF and let AI extract structured data
- **Job Search** — search open positions across the web (SerpAPI, Brave Search)
- **Tailored Resumes** — generate compact, job-specific CVs using AI adaptation
- **Export** — download tailored CVs as Markdown or PDF
- **Local-First** — all data stored locally in JSON files (or optional MongoDB)
- **Multi-Provider** — works with OpenRouter, OpenAI, or any OpenAI-compatible API

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### Setup

**Automated (recommended):**

```bash
chmod +x install.sh && ./install.sh      # Linux / macOS
# or
powershell -ExecutionPolicy Bypass -File install.ps1   # Windows
```

The script checks prerequisites, creates a virtual environment, installs all dependencies, and creates `.env` from the template.

**Manual:**

```bash
# Clone the repository
git clone https://github.com/your-org/open-resume.git
cd open-resume

# Set up backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
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

### 4. Manage Positions (`/positions`)

Positions follow a **Company → Job Description → Tailored CV** hierarchy.

- **Add Position** — paste a job description manually
- **Add from URL** — scrape a job listing URL (AI extracts the JD)
- **Import from Search** — from the search results page

### 5. Generate Tailored CVs

Open a position, go to the **Tailored CV** tab, and click **Generate Tailored CV**.

The AI reads your base CV and the job description, then produces a compact, role-specific resume. It **never invents information** — it only reorders, emphasizes, or de-emphasizes existing content from your base CV.

A change summary explains what was emphasized, de-emphasized, and why.

### 6. Export

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
│   ├── routes/              # API routes (CV, positions, search, settings)
│   └── services/            # Business logic (LLM, onboarding, adapter, search)
├── frontend/
│   └── src/
│       ├── pages/           # React pages
│       └── components/      # Reusable components
├── data/                    # Runtime data (gitignored)
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