# PLAN — Open Resume: AI-Powered CV Manager & Job Hunter

An open-source, local-first web tool that manages a comprehensive base CV, searches for open positions, and generates tailored resumes for specific job descriptions — all powered by AI.

---

## Overview

### Purpose
- Maintain a **single base CV** as the source of truth (stored in JSON by default, optional MongoDB).
- AI-guided onboarding wizard to build the base CV from scratch.
- Search the web for open positions with configurable filters.
- Generate **compact, tailored CVs** for specific positions using AI adaptation.
- Export adapted CVs as Markdown and PDF.
- Manage positions with a hierarchical structure: Company → Job Description → Tailored Resume.

### Core Principles
- **Open source** — MIT licensed, community-friendly.
- **Python-first** — backend written entirely in Python (FastAPI).
- **Local-first** — runs on localhost, no auth required, no cloud dependency.
- **JSON by default** — zero-dependency storage with JSON files; MongoDB is optional for scaling.
- **Container-ready** — includes Docker Compose for easy deployment; also runs natively without Docker.
- **Factual accuracy** — the LLM reorders and emphasizes existing content; it never invents experience.
- **User owns their data** — all data stored locally, no telemetry, no external services beyond the AI provider.

---

## Project Structure

```
open-resume/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, lifespan, config loading
│   ├── config.py                  # Configuration loader (env vars + config.json)
│   ├── models.py                  # Pydantic data models (schema definitions)
│   ├── database/
│   │   ├── __init__.py            # Storage backend factory (JSON or MongoDB)
│   │   ├── json_store.py          # JSON file-based storage
│   │   └── mongo_store.py         # MongoDB storage adapter
│   ├── routes/
│   │   ├── cv.py                  # Base CV CRUD + PDF ingest + onboarding
│   │   ├── jobs.py                # Job descriptions CRUD + URL ingest
│   │   ├── positions.py           # Positions manager (company → JD → CV)
│   │   ├── search.py              # Web search for open positions
│   │   ├── adapt.py               # CV adaptation + export (.md / .pdf)
│   │   └── settings.py            # API keys and configuration management
│   ├── services/
│   │   ├── pdf_parser.py          # PyPDF2 / pdfplumber: extract text from PDF
│   │   ├── llm.py                 # AI provider client (OpenRouter, OpenAI-compatible)
│   │   ├── onboarding.py          # AI-guided Q&A engine (state machine)
│   │   ├── adapter.py             # CV tailoring logic (base CV + JD → adapted CV)
│   │   └── job_search.py          # Web search aggregator for open positions
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api.js                 # Fetch wrapper for all backend endpoints
│   │   ├── pages/
│   │   │   ├── HomePage.jsx           # Dashboard: CV summary + recent positions
│   │   │   ├── SettingsPage.jsx       # API keys & configuration (first-run)
│   │   │   ├── OnboardingPage.jsx     # Chat-like AI-guided Q&A wizard
│   │   │   ├── CvEditorPage.jsx       # Markdown editor for CV editing + preview
│   │   │   ├── SearchJobsPage.jsx     # Web search for open positions
│   │   │   ├── PositionsPage.jsx      # Positions manager: companies & JDs
│   │   │   └── PositionPage.jsx       # Single position: JD + tailored CV + export
│   │   └── components/
│   │       ├── MdEditor.jsx           # Simple markdown editor (textarea + preview)
│   │       ├── OnboardingChat.jsx     # Chat-bubble Q&A interface
│   │       ├── AdaptedPreview.jsx     # Rendered markdown preview panel
│   │       ├── PdfUploader.jsx        # Drag-and-drop PDF ingest widget
│   │       ├── PositionCard.jsx       # Position list item (company → JD → CV)
│   │       └── JobSearchFilters.jsx   # Filters for web job search
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── data/                              # Runtime state (gitignored)
│   ├── config.json                    # User configuration (API keys, model, storage)
│   ├── base_cv.json                   # The base CV (default JSON storage)
│   ├── positions/
│   │   └── <company-name>/
│   │       ├── metadata.json          # Company + JD metadata
│   │       ├── job_description.md     # Original job description
│   │       └── tailored_cv.md         # Tailored CV for this position
│   └── exports/                       # Generated PDF files
├── docker-compose.yml                 # MongoDB + app services
├── Dockerfile                         # Container image for the app
├── .env.example                       # Environment variables template
├── run.sh                             # Launch script: backend + frontend (native)
├── start-docker.sh                    # Launch with Docker Compose
├── PLAN.md                            # This file
├── README.md                          # Project documentation
└── .gitignore
```

---

## Data Model

### BaseCV
Stored in `data/base_cv.json` (JSON mode) or in MongoDB collection `base_cv`.

```json
{
  "personal_info": {
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "address": "string",
    "website": "string",
    "linkedin": "string",
    "github": "string",
    "twitter": "string",
    "other_social": [{ "platform": "string", "url": "string" }]
  },
  "professional_summary": "string (2-3 sentences)",
  "career": [
    {
      "company": "string",
      "title": "string",
      "start_date": "string",
      "end_date": "string (or 'Present')",
      "location": "string",
      "description": "string",
      "accomplishments": ["string"],
      "technologies": ["string"]
    }
  ],
  "formation": [
    {
      "degree": "string",
      "institution": "string",
      "field": "string",
      "start_year": "string",
      "end_year": "string",
      "notes": "string"
    }
  ],
  "skills": [
    {
      "category": "string",
      "technologies": ["string"]
    }
  ],
  "tools": [
    {
      "category": "string",
      "items": ["string"]
    }
  ],
  "accomplishments": [
    {
      "title": "string",
      "description": "string",
      "year": "string"
    }
  ],
  "hobbies": ["string"],
  "languages": {
    "programming": ["string"],
    "spoken": [
      { "language": "string", "level": "string (native/fluent/intermediate/basic)" }
    ]
  },
  "projects": [
    {
      "name": "string",
      "url": "string (optional)",
      "year": "string",
      "description": "string",
      "technologies": ["string"]
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string",
      "year": "string",
      "url": "string (optional)"
    }
  ],
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

### Position (Company → Job Description → Tailored CV)
Stored under `data/positions/<company-slug>/`.

**metadata.json:**
```json
{
  "id": "uuid",
  "company_name": "string",
  "company_slug": "string",
  "job_title": "string",
  "job_description_md": "string (original JD in markdown)",
  "job_source_url": "string (optional)",
  "job_source_type": "paste | file | url | web_search",
  "tailored_cv_md": "string (AI-tailored CV in markdown)",
  "change_summary": "string (what was changed and why)",
  "pdf_export_path": "string (optional path to exported PDF)",
  "status": "new | tailoring | tailored | exported",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

### OnboardingSession (transient state)
```json
{
  "id": "uuid",
  "state": "in_progress | complete",
  "current_section": "string",
  "conversation_history": [
    { "role": "assistant | user", "content": "string" }
  ],
  "extracted_data": { /* partial BaseCV fields */ },
  "created_at": "ISO8601 datetime"
}
```

---

## Storage Backends

### JSON (Default)
- Zero dependencies.
- Data stored in `data/` directory as `.json` files.
- Single-file for `BaseCV`, directory-per-position for positions.
- Onboarding sessions stored in `data/onboarding_sessions/<session_id>.json`.
- Config stored in `data/config.json`.

### MongoDB (Optional)
- Enabled via `STORAGE_BACKEND=mongodb` in `.env`.
- Requires `MONGO_URI` environment variable.
- Docker Compose includes a MongoDB 7 service.
- Collections: `base_cv`, `positions`, `onboarding_sessions`, `config`.

### Switching Backends
- A migration script (`backend/migrate.py`) exports JSON → MongoDB and vice versa.
- Storage backend is abstracted behind a common interface; routes don't care which backend is active.

---

## API Routes

### Settings & Configuration

| Method | Path | Body / Params | Response | Description |
|--------|------|---------------|----------|-------------|
| `GET` | `/api/settings` | — | `{ config }` | Get current configuration (API keys redacted) |
| `PUT` | `/api/settings` | `{ openrouter_api_key?, openrouter_model?, storage_backend?, mongo_uri?, search_provider?, ... }` | Updated config | Save configuration |
| `POST` | `/api/settings/test-llm` | — | `{ ok, model }` | Test API key connectivity |

### Base CV

| Method | Path | Body / Params | Response | Description |
|--------|------|---------------|----------|-------------|
| `GET` | `/api/cv` | — | `BaseCV` JSON | Get the full base CV |
| `PUT` | `/api/cv` | Partial `BaseCV` fields | Updated `BaseCV` | Update CV sections |
| `POST` | `/api/cv/ingest-pdf` | Multipart: `file` (.pdf) | Parsed `BaseCV` | Extract text, parse with LLM, return structured CV for review |
| `POST` | `/api/cv/ingest-pdf/confirm` | Confirmed `BaseCV` fields | Saved `BaseCV` | Save parsed CV after user review |

### Onboarding Wizard

| Method | Path | Body / Params | Response | Description |
|--------|------|---------------|----------|-------------|
| `POST` | `/api/cv/onboard/start` | `{ first_name, last_name, target_role? }` | `{ session_id, question, section }` | Begin AI-guided onboarding |
| `POST` | `/api/cv/onboard/answer` | `{ session_id, answer }` | `{ question?, section?, done: bool, extracted_data }` | Send answer, get next question or completion signal |
| `POST` | `/api/cv/onboard/confirm` | `{ session_id }` | `BaseCV` | Finalize: write accumulated data to base CV, delete session |
| `GET` | `/api/cv/onboard/progress/{session_id}` | — | `{ current_section, completed_sections, total_sections }` | Get onboarding progress |

### Web Job Search

| Method | Path | Body / Params | Response | Description |
|--------|------|---------------|----------|-------------|
| `POST` | `/api/search/jobs` | `{ query, location?, remote?, job_type?, experience_level?, date_posted?, sources? }` | `[{ title, company, location, url, description_snippet, source, posted_date }]` | Search open positions across configured sources |
| `GET` | `/api/search/sources` | — | `[source_name]` | List available search sources |

### Job Descriptions (via Positions Manager)

| Method | Path | Body / Params | Response | Description |
|--------|------|---------------|----------|-------------|
| `GET` | `/api/positions` | `?company=&status=` | `[Position]` | List all positions, optionally filtered |
| `POST` | `/api/positions` | `{ company_name, job_title, job_description_md, source_url?, source_type }` | `Position` | Create a new position entry |
| `GET` | `/api/positions/{id}` | — | `Position` | Single position with full details |
| `PUT` | `/api/positions/{id}` | Partial fields | Updated `Position` | Edit position (JD, metadata, tailored CV) |
| `DELETE` | `/api/positions/{id}` | — | `204` | Delete position and its files |
| `POST` | `/api/positions/ingest-url` | `{ url }` | `Position (draft)` | Scrape JD from URL, return for review |
| `POST` | `/api/positions/search-import` | `{ search_result }` | `Position` | Import a search result as a new position |

### Adaptation & Export

| Method | Path | Body / Params | Response | Description |
|--------|------|---------------|----------|-------------|
| `POST` | `/api/positions/{id}/adapt` | — | `{ tailored_cv_md, change_summary }` | Generate/regenerate tailored CV for this position |
| `PUT` | `/api/positions/{id}/cv` | `{ tailored_cv_md }` | Updated `Position` | Manually edit the tailored CV markdown |
| `GET` | `/api/positions/{id}/export/md` | — | `text/markdown` file download | Download tailored CV as `.md` |
| `GET` | `/api/positions/{id}/export/pdf` | — | `application/pdf` file download | Download tailored CV as `.pdf` |

---

## AI Integration

### Setup (First-Run Experience)
- The app boots and checks if `data/config.json` exists.
- If not, the user is redirected to `/settings` to configure:
  - **AI Provider**: OpenRouter (default), OpenAI, or any OpenAI-compatible endpoint.
  - **API Key**: Provider API key (stored locally, never sent anywhere else).
  - **Model**: Configurable model name (default: `openai/gpt-4o`).
  - **Web Search Provider**: Configurable search API (SerpAPI, Brave Search, etc.).
- A "Test Connection" button validates the API key before proceeding.
- Configuration is saved to `data/config.json` (or MongoDB `config` collection).

### Supported AI Providers
- **OpenRouter** — `https://openrouter.ai/api/v1` (default, no account needed for free tier).
- **OpenAI** — `https://api.openai.com/v1`.
- **Any OpenAI-compatible endpoint** — custom `base_url` + `api_key`.
- Implementation uses the `openai` Python SDK with configurable `base_url`.

### Onboarding Flow

**System Prompt:**
```
You are an expert CV builder conducting an onboarding interview with {first_name} {last_name},
a {target_role or "professional"}. Your goal is to gather structured information to build a
comprehensive base CV. Ask one question at a time, progressing through these sections:

1. Personal & contact info (email, phone, location, address, LinkedIn, GitHub, other social)
2. Professional summary (2-3 sentences about experience and focus)
3. Career / Work experience (company, title, dates, description, accomplishments)
4. Formation / Education (degree, institution, field, years)
5. Skills by category (AI, DevOps, Cloud, Containers, Paradigms, Security, etc.)
6. Tools & technologies (by category: Backend, Frontend, DevOps, etc.)
7. Accomplishments (notable achievements, awards, publications)
8. Projects (name, description, URL, technologies)
9. Certifications (name, issuer, year)
10. Programming languages
11. Spoken languages
12. Hobbies & interests

Rules:
- Ask ONE question at a time.
- After each answer, extract structured data into your accumulated knowledge.
- When a section feels complete, move to the next section.
- When all sections are covered, respond with: {"done": true, "message": "All sections complete!"}
- Keep questions conversational but concise.
- If the user provides vague answers, ask follow-ups for specifics.
- DO NOT invent or fabricate any information.
```

**Flow:**
1. User navigates to `/onboard` → frontend calls `POST /onboard/start`.
2. Frontend renders chat interface (`OnboardingChat`): alternating AI/user bubbles.
3. Each `POST /onboard/answer` appends to conversation; AI returns next question or completion.
4. When `done: true`, frontend transitions to a review grid showing extracted data by section.
5. User can edit any field before confirming.
6. `POST /onboard/confirm` writes the full BaseCV to storage.

### CV Adaptation Flow

**System Prompt:**
```
You are a CV optimization expert. You have a comprehensive base CV and a specific
job description. Your task is to produce a compact, tailored CV that emphasizes
skills and experience most relevant to the job description.

Rules:
- NEVER invent or fabricate experience, skills, or accomplishments.
- Only reorder, emphasize (expand), de-emphasize (condense), or omit content from the base CV.
- The output must be valid markdown with these sections:
  # {first_name} {last_name}
  Contact info line (email, phone, location, LinkedIn, GitHub)
  ## Professional Summary (2-3 sentences, tailored to the role)
  ## Skills (only relevant categories and technologies)
  ## Tools & Technologies (only relevant ones)
  ## Experience (most relevant first, de-emphasize less relevant roles)
  ## Education (condensed)
  ## Projects (only if highly relevant)
  ## Languages
  ## Certifications (if relevant)

After the CV, under a "---" separator, add a "## Change Summary" section explaining:
- Which skills/experiences were emphasized and why
- Which were de-emphasized or omitted and why
- Overall strategy for this adaptation
```

**Flow:**
1. `POST /api/positions/{id}/adapt` → backend retrieves base CV + JD.
2. Constructs a single prompt with both inputs + the system prompt above.
3. Calls the configured AI provider, returns tailored markdown + change summary.
4. Parses response, saves to the position, generates PDF.
5. Returns `{ tailored_cv_md, change_summary }` to frontend.

### Web Job Search

**System Prompt (JD extraction):**
```
You are a job description parser. Given raw HTML or text from a job listing page,
extract only the job description content: role overview, responsibilities,
requirements, qualifications, company info, and benefits. Ignore navigation, ads,
headers, footers, and unrelated text. Return clean, well-formatted markdown.

If you cannot identify a job description in the content, respond with:
{"error": "No job description found on this page."}
```

**Search Aggregation:**
- Backend service queries configured search APIs (SerpAPI, Brave Search, custom).
- Results are deduplicated and normalized.
- Filters: remote/onsite/hybrid, location, experience level, date posted, job type.
- Results displayed in `SearchJobsPage` with "Import as Position" button.
- Importing fetches the full JD page, extracts description via LLM, creates a Position.

---

## Frontend Pages & Components

### Routing

| Path | Page | Description |
|------|------|-------------|
| `/` | `HomePage` | Dashboard: CV summary + recent positions |
| `/settings` | `SettingsPage` | API keys, model, storage backend config |
| `/onboard` | `OnboardingPage` | AI-guided onboarding wizard |
| `/cv` | `CvEditorPage` | Markdown editor for base CV |
| `/search` | `SearchJobsPage` | Web search for open positions |
| `/positions` | `PositionsPage` | Positions manager: list by company |
| `/positions/:id` | `PositionPage` | Single position: JD + tailored CV + export |

### Page Details

**SettingsPage** (`/settings`)
- First-run mandatory: redirects here if no config exists.
- Sections: AI Provider, API Key, Model, Search Provider, Storage Backend.
- "Test Connection" button per provider.
- MongoDB URI field (shown when storage backend is `mongodb`).

**HomePage** (`/`)
- Left: Base CV summary card (name, title, skill count, experience years).
- Right: Recent positions list.
- If no base CV exists: prominent "Start Onboarding" button → `/onboard`.
- Quick actions: "Search Jobs", "Manage Positions".

**OnboardingPage** (`/onboard`)
- Chat interface (`OnboardingChat` component).
- AI asks questions; user types answers.
- Progress bar showing completed sections.
- When done: review grid with all extracted data, editable before confirm.

**CvEditorPage** (`/cv`)
- **Left pane**: Simple markdown editor (`MdEditor` component — textarea with syntax highlighting).
- **Right pane**: Live preview rendered with `react-markdown`.
- Toolbar: Save, Download MD, Download PDF, "Regenerate from AI".
- Template button: inserts the BaseCV markdown template.

**SearchJobsPage** (`/search`)
- Search bar + filters panel (`JobSearchFilters` component).
- Filters: keywords, location, remote/onsite/hybrid, experience level, date posted, source.
- Results list with job cards: title, company, location, snippet, posted date.
- "Import" button on each result → creates a Position → redirects to `/positions/:id`.

**PositionsPage** (`/positions`)
- Grouped by company (accordion or tree view).
- Each entry: Job Title → Status badge (new/tailored/exported).
- "Add Position" button: manual entry or paste JD text.

**PositionPage** (`/positions/:id`)
- **Tab 1 — Job Description**: Read-only markdown render of the JD. "Edit" button opens MdEditor.
- **Tab 2 — Tailored CV**: 
  - If not generated: "Generate Tailored CV" button with loading state.
  - If generated: `MdEditor` with the tailored markdown (editable) + live preview.
  - Change Summary block below.
- **Tab 3 — Export**: Download Markdown, Download PDF, print preview.
- "Regenerate" button to re-run adaptation.

### Components

**MdEditor**
```
┌─────────────────────────────────────────┐
│  [B] [I] [H1] [H2] [Link] [List] [Code] │  ← toolbar
├────────────────────┬────────────────────┤
│ # My CV            │  Rendered Preview  │
│                    │  ================  │
│ **Name**           │  **Name**          │
│                    │                    │
│ - Skill 1          │  - Skill 1         │
│ - Skill 2          │  - Skill 2         │
│                    │                    │
│ (textarea editor)  │  (live preview)    │
└────────────────────┴────────────────────┘
```
- Split-pane: textarea (left) + `react-markdown` preview (right).
- Toolbar with common markdown formatting buttons.
- Auto-save on blur or Ctrl+S.

**OnboardingChat**
- Chat bubbles with role indicators (AI / User).
- Auto-scroll to bottom on new messages.
- Text input with send button.
- Typing indicator ("AI is thinking...") while waiting for response.

**AdaptedPreview**
- Rendered markdown with `react-markdown`.
- Print-friendly CSS class.
- Change Summary section highlighted in a callout box.

**PdfUploader**
- Drag-and-drop zone.
- File type validation (`.pdf` only).
- Upload progress bar.
- On success: shows structured preview for review.

**JobSearchFilters**
- Keyword input.
- Location input.
- Remote/Hybrid/Onsite toggle.
- Experience level dropdown (Entry, Mid, Senior, Lead, Executive).
- Date posted (24h, Week, Month, Any).
- Source checkboxes.

**PositionCard**
- Displays: Company name > Job title > Status badge.
- Click navigates to `/positions/:id`.

---

## Markdown → PDF Export

- Backend uses `weasyprint` (no LaTeX dependency).
- A print-friendly CSS stylesheet is applied during conversion.
- Markdown is converted to HTML via `markdown2`, then styled + printed via weasyprint.
- PDFs saved to `data/exports/` and served as downloadable files.

---

## Docker & Deployment

### Running Locally Without Docker

**Prerequisites:** Python 3.10+, Node.js 18+, npm.

```bash
# 1. Clone the repo
git clone https://github.com/your-org/open-resume.git
cd open-resume

# 2. Set up backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt

# 3. Set up frontend
cd frontend
npm install
cd ..

# 4. Configure environment
cp .env.example .env
# Edit .env: add your AI provider API key

# 5. Launch (two terminals, or use run.sh)
# Terminal 1 — Backend:
source venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend:
cd frontend && npm run dev

# 6. Open http://localhost:5173
```

### Running with Docker

**Prerequisites:** Docker + Docker Compose.

```bash
# 1. Clone and configure
git clone https://github.com/your-org/open-resume.git
cd open-resume
cp .env.example .env
# Edit .env: add API key, optionally set STORAGE_BACKEND=mongodb

# 2. Launch
./start-docker.sh
# Or: docker compose up -d

# 3. Open http://localhost:5173
```

### Docker Compose Services

```yaml
services:
  backend:
    build: .
    ports: ["8000:8000"]
    depends_on: [mongo]
    environment: ${ENV_VARS}
    volumes:
      - ./data:/app/data

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    depends_on: [backend]

  mongo:
    image: mongo:7
    ports: ["27017:27017"]
    volumes:
      - mongo_data:/data/db
    profiles: ["mongodb"]  # Only starts when STORAGE_BACKEND=mongodb

volumes:
  mongo_data:
```

---

## Configuration

### `.env` / `data/config.json`

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | AI provider API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | AI provider base URL |
| `OPENROUTER_MODEL` | `openai/gpt-4o` | Default model |
| `STORAGE_BACKEND` | `json` | `json` or `mongodb` |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `SEARCH_PROVIDER` | `serpapi` | Web search provider |
| `SEARCH_API_KEY` | — | Search API key |
| `HOST` | `0.0.0.0` | Listen address |
| `PORT` | `8000` | Backend port |
| `FRONTEND_PORT` | `5173` | Frontend dev server port |

---

## Dependencies

### Backend (`requirements.txt`)
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
openai>=1.6.0
pdfplumber>=0.10.0
httpx>=0.26.0
beautifulsoup4>=4.12.0
markdown2>=2.4.0
weasyprint>=60.0
python-multipart>=0.0.6
pymongo>=4.6.0
python-dotenv>=1.0.0
```

### Frontend (`package.json`)
```
react>=18.2.0
react-dom>=18.2.0
react-router-dom>=6.21.0
react-markdown>=9.0.0
vite>=5.0.0
@vitejs/plugin-react>=4.2.0
```

---

## Implementation Phases

### Phase 1: Backend Core
- [ ] FastAPI app scaffold (`main.py`, CORS, lifespan, config).
- [ ] Storage backend abstraction + JSON store.
- [ ] Data models (Pydantic schemas).
- [ ] Settings/configuration routes (`/api/settings`).
- [ ] AI provider client (`services/llm.py`) with connection test.
- [ ] Base CV CRUD routes.

### Phase 2: Frontend Foundation
- [x] Vite + React scaffold.
- [x] Router setup, layout shell, navigation.
- [x] `api.js` fetch wrapper.
- [x] SettingsPage (first-run configuration).
- [x] HomePage + CvEditorPage (MdEditor component).
- [x] PositionsPage + PositionPage (basic CRUD, no adaptation).

### Phase 3: Onboarding
- [ ] OnboardingService: session state, prompt templates, response parsing.
- [ ] `/api/cv/onboard/start`, `answer`, `confirm` routes.
- [ ] OnboardingPage + OnboardingChat frontend.

### Phase 4: CV Adaptation & Export
- [ ] AdapterService: prompt construction, response parsing, change summary.
- [ ] `/api/positions/{id}/adapt` route.
- [ ] MdEditor for tailored CV editing on PositionPage.
- [ ] Export routes: markdown download + PDF generation (weasyprint).

### Phase 5: Job Search
- [ ] JobSearchService: search API integration (SerpAPI, Brave Search).
- [ ] `/api/search/jobs` route with filters.
- [ ] SearchJobsPage + JobSearchFilters component.
- [ ] "Import as Position" flow with LLM JD extraction.

### Phase 6: MongoDB & Docker
- [ ] MongoDB storage adapter.
- [ ] Migration script (JSON ↔ MongoDB).
- [ ] Dockerfile for backend + frontend.
- [ ] docker-compose.yml with MongoDB service.
- [ ] `run.sh` and `start-docker.sh` scripts.

### Phase 7: Polish
- [ ] PDF ingest (upload + LLM parse + review).
- [ ] URL JD scraping + LLM cleaning.
- [ ] Error handling, loading states, empty states.
- [ ] Print-friendly CSS for PDF export.
- [ ] README.md with full documentation.

---

## Open Questions & Decisions

1. **Default AI model**: `openai/gpt-4o` via OpenRouter. User can change to any model/provider in Settings.
2. **Markdown → PDF**: `weasyprint` (no LaTeX, pure Python).
3. **Web search**: Start with SerpAPI (Google Jobs), add Brave Search as secondary. Abstract behind an interface for easy extension.
4. **Ports**: Backend `:8000`, frontend `:5173`. Vite proxies `/api` to backend.
5. **MongoDB profile**: MongoDB container starts conditionally (Docker Compose profile `mongodb`). Default JSON storage needs no containers.
6. **No auth**: Local-only tool. If deployed remotely, put it behind a reverse proxy with basic auth.
7. **License**: MIT.