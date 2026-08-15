## Remy Implementation Phases

### Remy Phase 1: Agent Foundation (backend core)
- [x] Pydantic models: `RemyQuery`, `RemyListing`, `RemyTask`, `RemyRun`, `RemyReport`.
- [x] `StorageBackend` extension + `JsonStore` implementation (JSON files under `data/remy/`).
- [x] Config additions (`REMY_ENABLED`, `REMY_SOURCES`, `REMY_REQUEST_DELAY`, `REMY_TZ`).
- [x] `backend/services/remy/` package: `ScraperSkill` ABC + skill registry.
- [x] `/api/remy/sources` + `/api/remy/queries` CRUD routes.

### Remy Phase 2: Scraper Skills & Search Database
- [ ] `occ.py` skill — parse OCC search results + listing pages (HTML → normalized listings).
- [ ] `linkedin.py` skill — public Jobs RSS feed / guest endpoint (with ToS disclaimer in UI).
- [ ] `aggregator.py` skill — wrap existing `JobSearchService` (SerpAPI/Brave) into a skill.
- [ ] Scraper service: run query against enabled skills, dedup by URL, upsert listings (`first_seen`/`last_seen`/`is_active`).
- [ ] `/api/remy/listings` browser routes + single listing detail.

### Remy Phase 3: Cronjobs (daily/weekly only)
- [ ] Add `apscheduler`; `RemyScheduler` service with `AsyncIOScheduler` wired to FastAPI lifespan.
- [ ] `RemyTask` CRUD routes with strict frequency validation (daily | weekly).
- [ ] Cron trigger mapping: daily → time; weekly → weekday + time; reschedule on task change; load-on-boot.
- [ ] `RemyRun` persistence: cron + manual triggers, statuses, counts, errors.
- [ ] `/api/remy/tasks/{id}/run` manual trigger + `/api/remy/runs` history.

### Remy Phase 4: AI Analysis & Recommendations
- [ ] `RemyAnalyzer` service: market-trend + skills-gap report from listings vs base CV (prompt design in `services/remy/prompts.py`).
- [ ] `RemyRecommender` service: 0–100 match scoring + top-N with reasons.
- [ ] `RemyReport` persistence + `/api/remy/analyze/{query_id}`, `/api/remy/recommend/{query_id}`, `/api/remy/reports/{query_id}`.
- [ ] Wire analyze/recommend as schedulable task types.

### Remy Phase 5: Frontend
- [ ] `RemyPage` dashboard with schedule status + recent activity.
- [ ] `RemyQueriesPage` — search profile CRUD.
- [ ] `RemyTasksPage` + `RemyTaskForm` — frequency toggle (daily/weekly only), weekday + time pickers, enable/disable, run now.
- [ ] `RemyListingsPage` — search database browser with filters + "Import to Position".
- [ ] `RemyReportsPage` — rendered reports + top-match list.
- [ ] Layout nav entry + api.js helpers.

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
