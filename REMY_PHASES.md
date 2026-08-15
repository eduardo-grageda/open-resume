## Remy Implementation Phases

### Remy Phase 1: Agent Foundation (backend core)
- [x] Pydantic models: `RemyQuery`, `RemyListing`, `RemyTask`, `RemyRun`, `RemyReport`.
- [x] `StorageBackend` extension + `JsonStore` implementation (JSON files under `data/remy/`).
- [x] Config additions (`REMY_ENABLED`, `REMY_SOURCES`, `REMY_REQUEST_DELAY`, `REMY_TZ`).
- [x] `backend/services/remy/` package: `ScraperSkill` ABC + skill registry.
- [x] `/api/remy/sources` + `/api/remy/queries` CRUD routes.
- [ ] Install `deepagents` + `langchain-openai`; build `create_remy_agent()` harness — main orchestrator agent with system prompt, LangGraph checkpointer (SQLite, `data/remy/checkpoints.sqlite`), and context management defaults.
- [ ] `subagents.py`: define `scraper`, `analyst`, `recommender`, `cv-chronicler` sub-agents — each with isolated tools, skills, and system prompts; registered as deepagents `task` sub-agents.
- [ ] `tools.py`: agent tool implementations — listings DB CRUD, query read, run write, CV read, report store, import-as-position.
- [ ] `memory.py`: CV memory service — snapshot base CV on every change (`cv_history/` + `cv_history.index.json`), diff generation (`cv_deltas.jsonl`), `profile.json` (role, skills timeline, preferences). LangGraph JSON store (`data/remy/memory/memories/`) for semantic memory (preferences, past feedback, decisions). Read latest CV + recent deltas into agent context.
- [ ] `prompts.py`: main agent system prompt + sub-agent prompts (scraper, analyst, recommender, cv-chronicler) — all include "never invent experience" rule.
- [ ] `/api/remy/chat` conversational agent endpoint (SSE streaming); `/api/remy/chat/{thread_id}` resume thread; `/api/remy/memory` read/clear.
- [ ] Wire `cv-chronicler` sub-agent to CV save path: on every `PUT /api/cv`, trigger snapshot + delta + profile update.
- [ ] `backend/memory/` module for AGENTS.md and MEMORY.md updates accordingly.

### Remy Phase 2: Scraper Skills & Search Database
- [x] `occ.py` skill — parse OCC search results + listing pages (HTML → normalized listings).
- [x] `linkedin.py` skill — public Jobs RSS feed / guest endpoint (with ToS disclaimer in UI).
- [x] `aggregator.py` skill — wrap existing `JobSearchService` (SerpAPI/Brave) into a skill.
- [x] Scraper service: run query against enabled skills, dedup by URL, upsert listings (`first_seen`/`last_seen`/`is_active`).
- [x] `/api/remy/listings` browser routes + single listing detail.

### Remy Phase 3: Cronjobs (daily/weekly only)
- [ ] Add `apscheduler`; `RemyScheduler` service with `AsyncIOScheduler` wired to FastAPI lifespan.
- [ ] `RemyTask` CRUD routes with strict frequency validation (daily | weekly).
- [ ] Cron trigger mapping: daily → time; weekly → weekday + time; reschedule on task change; load-on-boot.
- [ ] `RemyRun` persistence: cron + manual triggers, statuses, counts, errors.
- [ ] `/api/remy/tasks/{id}/run` manual trigger + `/api/remy/runs` history.

### Remy Phase 4: AI Analysis & Recommendations
- [ ] Wire `analyst` sub-agent → `RemyAnalyzer` service: market-trend + skills-gap report from listings vs base CV (prompt from `prompts.py`).
- [ ] Wire `recommender` sub-agent → `RemyRecommender` service: 0–100 match scoring + top-N with reasons.
- [ ] `RemyReport` persistence + `/api/remy/analyze/{query_id}`, `/api/remy/recommend/{query_id}`, `/api/remy/reports/{query_id}`.
- [ ] Wire analyze/recommend as schedulable task types.
- [ ] Memory update after each run: store report ID, top matches, user feedback. Update profile with new market signals.

### Remy Phase 5: Frontend
- [ ] `RemyPage` dashboard with schedule status + recent activity + Remy chat panel (conversational agent interface, SSE streaming).
- [ ] `RemyQueriesPage` — search profile CRUD.
- [ ] `RemyTasksPage` + `RemyTaskForm` — frequency toggle (daily/weekly only), weekday + time pickers, enable/disable, run now.
- [ ] `RemyListingsPage` — search database browser with filters + "Import to Position".
- [ ] `RemyReportsPage` — rendered reports + top-match list.
- [ ] `RemyMemoryPage` — CV change history timeline, profile view, cleared/reset option.
- [ ] Layout nav entry + api.js helpers (including SSE stream for /chat).

### Remy Phase 6: Integration, Polish & Mongo
- [ ] "Import listing as Position" end-to-end (listing → Position → adapt → export).
- [ ] `MongoStore` Remy collections + indexes (unique `url` on listings).
- [ ] Politeness: per-source rate limiting, robots.txt checks, request delay from config.
- [ ] Empty states, loading/error handling, LinkedIn ToS disclaimer UI.
- [ ] Docs: README Remy section, PLAN/MEMORY updates.

### Remy Open Questions
1. **LinkedIn depth**: start with public RSS (low risk) and optionally add a "user-provided cookies" mode later for logged-in scraping — never ship credentials in the app.
2. **OCC parsing**: OCC's HTML structure changes occasionally — pin parser versions and log parse failures as `partial` runs instead of crashing.
3. **Timezone**: server-local by default; `REMY_TZ` later via `zoneinfo` if users request it.
4. **Recommendation → action**: recommendations link to import flow; auto-adaptation of CVs from cron remains a manual step (user approval), keeping the "no invented experience" principle.
5. **Deep Agents model**: use the same OpenRouter/OpenAI-compatible `base_url` + `api_key` from Settings via `langchain-openai` ChatOpenAI. If the configured model isn't good at tool-calling, the agent degrades gracefully (fallbacks in place). Dedicated `REMY_MODEL` config allows a stronger model for planning while cheaper models handle scraping and analysis.
6. **Sub-agent parallelism**: deepagents tasks run sequentially by default; `REMY_MAX_SUBAGENTS` can be raised to run independent tasks in parallel (e.g., scrape LinkedIn + OCC simultaneously). Start conservative, benchmark before raising.
7. **Memory store backend**: start with the in-process JSON store (LangGraph `BaseStore` backed by `data/remy/memory/`). Upgrade path to Postgres/SQLite `AsyncPostgresStore` / `AsyncSqliteStore` from `langgraph` if performance demands it. The CV snapshot + delta mechanism is custom code alongside the LangGraph store; they can be unified later.
