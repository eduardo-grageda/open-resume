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
├── vite.config.js
├── index.html
└── src/
    ├── main.jsx           # React root, BrowserRouter wrapper
    ├── App.jsx            # Routes, config check (first-run redirect)
    ├── App.css            # Complete design system (variables, layout, components)
    ├── api.js             # Fetch wrapper for all backend endpoints
    ├── components/
    │   ├── Layout.jsx     # Sidebar nav + main content area
    │   ├── MdEditor.jsx   # Split-pane markdown editor with toolbar + live preview
    │   └── OnboardingChat.jsx  # Chat-bubble Q&A interface with typing indicator
    └── pages/
        ├── HomePage.jsx       # Dashboard: CV summary card + recent positions
        ├── SettingsPage.jsx   # AI provider, API keys, storage, search config
        ├── OnboardingPage.jsx # AI-guided interview wizard with start form, chat, progress bar, review grid
        ├── CvEditorPage.jsx   # Markdown CV editor with template, save to backend
        ├── PositionsPage.jsx  # List positions grouped by company, create/delete
        └── PositionPage.jsx   # Single position: 3 tabs (JD, Tailored CV, Export)
```

## Design System (`App.css`)
- CSS custom properties for theming
- Sidebar layout (220px fixed, scrollable main area)
- Component classes: `.card`, `.btn` (primary/secondary/danger), `.badge` (new/tailoring/tailored/exported), `.tabs`, `.alert` (success/error/info)
- Utility classes: `.grid-2`, `.inline-row`, `.flex-between`, spacing and text helpers

## API Client (`api.js`)
- Base URL: `/api`
- Methods: `health`, `getSettings`, `updateSettings`, `testLlm`, `getCv`, `updateCv`, `ingestPdf`, `onboardStart`, `onboardAnswer`, `onboardConfirm`, `onboardProgress`, `listPositions`, `getPosition`, `createPosition`, `updatePosition`, `deletePosition`
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
- MdEditor for markdown editing with live preview
- Toggle between markdown and structured edit mode (structured mode placeholder)
- Save writes back full CV via PUT

### OnboardingPage (`/onboard`)
- Multi-step AI-guided CV builder
  - **Step 1 — Start**: Form for first name (required), last name, target role; calls `POST /api/cv/onboard/start`
  - **Step 2 — Chat**: OnboardingChat component with alternating AI/user bubbles; progress bar showing completed sections out of 12; calls `POST /api/cv/onboard/answer` for each response
  - **Step 3 — Review**: Collapsible review grid organized by section (accordion cards with green/blue dots); editable fields for each data type (strings, arrays, nested objects); "Save CV" calls `POST /api/cv/onboard/confirm` then redirects to `/cv`

### PositionsPage (`/positions`)
- Lists positions grouped by company name (accordion-style cards)
- Create form: company name, job title, source URL, job description (markdown)
- Filter input for company/title search
- Delete with confirmation

### PositionPage (`/positions/:id`)
- Header: job title, company, status badge, edit/save/delete buttons
- Three tabs:
  - **Job Description**: Read-only markdown render, "Edit" button for inline editing of title, company, JD
  - **Tailored CV**: MdEditor for CV editing (if exists), change summary callout, "Generate" placeholder for future adaptation
  - **Export**: Markdown download as `.md` file, print preview (opens new window)
- All updates go through PUT `/api/positions/{id}`

## Components

### Layout
- Fixed sidebar (220px) with brand "Open Resume"
- NavLink items: Dashboard, Base CV, Onboarding, Positions (highlighted when active)
- Settings link at bottom
- Main content area with left margin offset

### MdEditor
- Toolbar: B, I, H1, H2, H3, Link, List, Num, Code, inline code
- Insertion helpers wrap selected text
- Toggle preview button
- Split-pane: textarea (left) + ReactMarkdown rendered preview (right)
- Props: `value`, `onChange`, `readOnly`

### OnboardingChat
- Chat-bubble interface with AI/user role indicators
- Auto-scroll to bottom on new messages
- Typing indicator ("AI is thinking...") with animated dots while waiting
- Text input with Enter-to-send (Shift+Enter for newline)

## Not Yet Implemented
- SearchJobsPage + JobSearchFilters (Phase 5)
- AdaptedPreview component
- PdfUploader component
- PositionCard component (inlined in PositionsPage currently)
- Structured CV editing mode (placeholder in CvEditorPage)
- Generation/regeneration of tailored CVs (adaptation API)
