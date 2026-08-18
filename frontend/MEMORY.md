# MEMORY.md — Frontend

## Stack
- React 18.2+, React Router DOM 6.21+, React Markdown 9.0+
- Vite 5.0+ with @vitejs/plugin-react
- Vite dev server proxies `/api` → `http://localhost:8000`
- Port: 5173

## Structure

```
frontend/
├── package.json
├── vite.config.js       # Vite config (supports VITE_BACKEND_URL env var for Docker)
├── Dockerfile            # Node 18-alpine dev container
├── index.html
└── src/
    ├── main.jsx           # React root, BrowserRouter wrapper
    ├── App.jsx            # Routes, config check (first-run redirect)
    ├── App.css            # Complete design system (variables, layout, components)
    ├── api.js             # Fetch wrapper for all backend endpoints
    ├── components/
    │   ├── Layout.jsx     # Sidebar nav + main content area
    │   ├── MdEditor.jsx   # Split-pane markdown editor with toolbar + live preview
    │   ├── OnboardingChat.jsx  # Chat-bubble Q&A interface with typing indicator
    │   ├── JobSearchFilters.jsx  # Filter form: keywords, location, remote, experience, date
    │   ├── PdfUploader.jsx     # Drag-and-drop PDF upload with AI parsing
    │   ├── AdaptedPreview.jsx  # Print-friendly CV preview with print button
    │   ├── PositionCard.jsx    # Reusable position list item card
    │   └── LoadingSpinner.jsx  # Reusable loading indicator
    └── pages/
        ├── HomePage.jsx       # Dashboard: CV summary card + recent positions
        ├── SettingsPage.jsx   # AI provider, API keys, storage, search config
        ├── OnboardingPage.jsx # AI-guided interview wizard with start form, chat, progress bar, review grid
        ├── CvEditorPage.jsx   # Markdown CV editor with template, save to backend
        ├── PositionsPage.jsx  # List positions grouped by company, create/delete
        ├── PositionPage.jsx   # Single position: 3 tabs (JD, Tailored CV, Export)
        ├── SearchJobsPage.jsx # Web job search with filters, results, import flow
        ├── StarPage.jsx       # STAR interview prep: achievement Q&A chat, story review/editor, saved stories list
        ├── RemyPage.jsx       # Remy dashboard: schedule status + recent activity + SSE streaming chat panel
        ├── RemyQueriesPage.jsx   # Search profile CRUD with city management (add/remove cities, radius slider)
        ├── RemyTasksPage.jsx     # Scheduled tasks list + RemyTaskForm (frequency, day/time, run now)
        ├── RemyListingsPage.jsx  # Listings browser with filters + split-pane detail + Import to Position
        ├── RemyReportsPage.jsx   # Reports viewer with top-match scores + run analysis/recommend buttons
        └── RemyMemoryPage.jsx    # Profile view, CV change timeline, market signals, memory clear
```

## Design System (`App.css`)
- CSS custom properties for theming
- Sidebar layout (220px fixed, scrollable main area)
- Component classes: `.card`, `.btn` (primary/secondary/danger), `.badge` (new/tailoring/tailored/exported), `.tabs`, `.alert` (success/error/info)
- Utility classes: `.grid-2`, `.inline-row`, `.flex-between`, spacing and text helpers

## API Client (`api.js`)
- Base URL: `/api`
- Methods: `health`, `getSettings`, `updateSettings`, `testLlm`, `getCv`, `updateCv`, `ingestPdf`, `onboardStart`, `onboardAnswer`, `onboardConfirm`, `onboardProgress`, `listPositions`, `getPosition`, `createPosition`, `updatePosition`, `deletePosition`, `adaptPosition`, `exportMarkdownUrl`, `exportPdfUrl`, `searchJobs`, `getSearchSources`, `extractJd`, `starStart`, `starAnswer`, `starConfirm`, `listStarStories`, `getStarStory`, `updateStarStory`, `deleteStarStory`, `generateStarPitch`
- Remy methods: `getRemySources`, `listRemyQueries`, `createRemyQuery`, `getRemyQuery`, `updateRemyQuery`, `deleteRemyQuery`, `scrapeRemyQuery`, `listRemyTasks`, `createRemyTask`, `getRemyTask`, `updateRemyTask`, `deleteRemyTask`, `runRemyTask`, `listRemyRuns`, `listRemyListings`, `getRemyListing`, `importRemyListing`, `analyzeRemy`, `recommendRemy`, `listRemyReports`, `getRemyReport`, `getRemyMemory`, `clearRemyMemory`, `listRemyThreads`, `getRemyThread`, `deleteRemyThread`, `streamRemyChat(message, threadId, onEvent)` — SSE streaming via fetch with ReadableStream parser
- Handles JSON serialization, error extraction from response body

## Pages

### HomePage (`/`)
- Fetches CV and positions list on mount
- Left card: CV summary (name, email, skill count, experience count) or "Create Base CV" CTA
- Right card: position count with status breakdown
- Recent positions list (top 5) linking to detail pages

### SettingsPage (`/settings`)
- First-run mandatory: App.jsx redirects all routes here when no config exists
- Sections: AI Provider (base URL, API key, model), Storage (backend selector, conditional Mongo URI), Search (provider, API key)
- "Test Connection" button calls `/api/settings/test-llm`
- Save merges partial updates via PUT

### CvEditorPage (`/cv`)
- Loads existing CV from backend, converts to markdown, or shows default template
- Two tabs: Editor (markdown/structured) and Import PDF
- Editor tab: MdEditor for markdown editing with live preview
- Import PDF tab: PdfUploader for drag-and-drop upload, AI parsing, review before save
- Toggle between markdown and structured edit mode (structured mode placeholder)
- Save writes back full CV via PUT or PDF confirm endpoint

### OnboardingPage (`/onboard`)
- Multi-step AI-guided CV builder
  - **Step 1 — Start**: Form for first name (required), last name, target role; calls `POST /api/cv/onboard/start`
  - **Step 2 — Chat**: OnboardingChat component with alternating AI/user bubbles; progress bar showing completed sections out of 12; calls `POST /api/cv/onboard/answer` for each response
  - **Step 3 — Review**: Collapsible review grid organized by section (accordion cards with green/blue dots); editable fields for each data type (strings, arrays, nested objects); "Save CV" calls `POST /api/cv/onboard/confirm` then redirects to `/cv`

### PositionsPage (`/positions`)
- Lists positions grouped by company name (accordion-style cards)
- Create form: company name, job title, source URL, job description (markdown)
- "Add from URL" form: paste job listing URL, AI scrapes and extracts JD
- Filter input for company/title search
- Delete with confirmation

### PositionPage (`/positions/:id`)
- Header: job title, company, status badge, edit/save/delete buttons
- Three tabs:
  - **Job Description**: Read-only markdown render, "Edit" button for inline editing of title, company, JD
  - **Tailored CV**: MdEditor for CV editing (if generated), change summary callout, "Generate Tailored CV" / "Regenerate" button calling `POST /api/positions/{id}/adapt`
  - **Export**: AdaptedPreview component with print-friendly rendering, Markdown download via backend endpoint, PDF download via weasyprint backend endpoint, print preview button
- All updates go through PUT `/api/positions/{id}`

### SearchJobsPage (`/search`)
- Filter form (JobSearchFilters component): keywords, location, remote toggle, experience level, job type, date posted
- Calls `POST /api/search/jobs` with filter payload
- Results list with job cards: title (linked), company, location, snippet, source badge, posted date
- "Import" button on each result: fetches JD via `POST /api/search/extract-jd`, creates Position, redirects to `/positions/:id`
- Loading, empty, and error states handled

### StarPage (`/star`)
- Multi-step STAR interview prep builder
  - **Step 1 — Start**: Description of STAR methodology, optional target role; calls `POST /api/star/start`
  - **Step 2 — Chat**: OnboardingChat component with AI/user bubbles; StarProgress showing phase and S→T→A→R step dots; calls `POST /api/star/answer` for each response; stories accumulate incrementally
  - **Step 3 — Review**: StoryEditor inline editing for each story (Situation/Task/Action/Result fields + interview pitch); Generate Pitch button calls `POST /api/star/generate-pitch/{id}`; Delete and Edit controls
  - **Saved View**: Lists all saved stories with full editing, pitch generation, and deletion
- Requires base CV to exist; shows "No CV Found" state otherwise
- `StarProgress` component: phase label + S/T/A/R step indicator dots
- `StoryEditor` component: collapsible edit/view for individual STAR stories
- `SavedStories` component: loads and displays all saved stories with full management

## Components

### Layout
- Fixed sidebar (220px) with brand "Open Resume"
- NavLink items: Dashboard, Base CV, Onboarding, Interview Prep, Positions, Search Jobs
- Remy Agent section (with separator): Remy Dashboard, Queries, Tasks, Listings, Reports, Memory
- Settings link at bottom
- Main content area with left margin offset

### JobSearchFilters
- Props: `filters`, `onChange`, `onSearch`, `loading`
- Two-column grid layout for filter inputs
- Keywords, location, experience level dropdown, job type dropdown, date posted dropdown, remote checkbox
- Submit button triggers parent search

### MdEditor
- Toolbar: B, I, H1, H2, H3, Link, List, Num, Code, inline code
- Insertion helpers wrap selected text
- Toggle preview button
- Split-pane: textarea (left) + ReactMarkdown rendered preview (right)
- Props: `value`, `onChange`, `readOnly`

### OnboardingChat
- Chat-bubble interface with AI/user role indicators
- System messages for retry/error notifications (centered, muted, italic)
- Auto-scroll to bottom on new messages
- Typing indicator ("AI is thinking...") with animated dots while waiting
- Text input with Enter-to-send (Shift+Enter for newline)

### PdfUploader
- Drag-and-drop zone with file type validation (.pdf only, max 10MB)
- Uploads to `POST /api/cv/ingest-pdf`, returns parsed CV data
- Visual feedback: drag-over highlight, uploading spinner, error messages
- Props: `onParsed(cvData, rawText)` callback

### AdaptedPreview
- Rendered markdown with print-optimized CSS
- Print Preview button opens new window with A4-page-styled content
- Simple markdown-to-HTML converter for print output
- Props: `markdown`, `jobTitle`, `companyName`

### PositionCard
- Reusable card component for position list items
- Displays job title, company name, and status badge
- Links to `/positions/:id`
- Props: `position`

### LoadingSpinner
- Reusable loading indicator with animated spinner and optional text
- Used by all pages instead of blank `return null` during data fetches
- Props: `text` (default: "Loading...")

## Remy Pages (Phase 5)

### RemyPage (`/remy`)
- Dashboard: status card (profile count, task count, listing count, recent runs with status badges)
- Full chat panel: thread list for switching/creating conversations, message history with react-markdown rendering, streaming text with typing indicator, input with Enter-to-send
- `streamRemyChat()` SSE helper: reads `ReadableStream`, parses `data:` JSON events, yields `{type, content/thread_id/detail}` via callback

### RemyQueriesPage (`/remy/queries`)
- List search profiles with keywords, cities, source info
- CRUD form: name, keywords (comma-sep), exclude keywords, sources, experience level dropdown, remote checkbox
- `CityForm` sub-component: city name, country (2-letter), lat/lng inputs, radius slider (1-200 km)
- Multi-city support: add/remove cities, must have at least one
- "Scrape now" button per query triggers ad-hoc scraper

### RemyTasksPage (`/remy/tasks`)
- `RemyTaskForm` component: profile dropdown (loaded from queries), task type select (scrape/analyze/recommend), frequency (daily/weekly), conditional weekday select (Sun-Sat), time picker, enabled checkbox
- List tasks with type badge, frequency, schedule display, disabled indicator
- "Run now" button triggers manual execution, "Edit" opens inline form

### RemyListingsPage (`/remy/listings`)
- Filter bar: text search, source select, query/profile select, active/expired filter, "unseen only" checkbox
- Split-pane: left listing list (scrollable, click to select), right detail panel
- Detail: title, company, location, salary, source badge, link to original URL, rendered markdown description
- "Import to Position" button: creates Position from listing, sets `imported_position_id`, links to `/positions/:id`
- "Refresh" button re-fetches listing detail from source

### RemyReportsPage (`/remy/reports`)
- "Run Analysis" / "Run Recommendations" buttons
- Split-pane: left report list by type/date, right detail panel
- Detail: report type, timestamp, top matches list (score/100 + reason, each links to listings), rendered markdown content

### RemyMemoryPage (`/remy/memory`)
- Profile card: role, snapshot count, tracked runs, preferences
- Market signals card: top skill badges from analysis runs, last updated
- CV Change History: timeline with dots/lines, each entry shows name + snapshot date + skill/position counts
- Clear Memory button with confirmation
