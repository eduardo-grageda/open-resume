## Remy Implementation Phases

### Remy Phase 1: Agent Foundation (backend core)
- [x] Pydantic models: `RemyCity` (name, country, lat, lng, radius_km — default Guadalajara, MX), `RemyQuery`/`RemyQueryInput` (with `cities` array), `RemyListing` (with `embedding_id`), `RemyTask`, `RemyRun`, `RemyReport`.
- [x] `StorageBackend` extension + `JsonStore` implementation (JSON files under `data/remy/`).
- [x] Config additions (`REMY_ENABLED`, `REMY_SOURCES` (default `places,linkedin,occ,serpapi`), `REMY_REQUEST_DELAY`, `REMY_TZ`, `GOOGLE_PLACES_API_KEY`, `REMY_EMBEDDING_MODEL`) + `SettingsUpdate` fields + API-key redaction in `/api/settings`.
- [x] `backend/services/remy/` package: `ScraperSkill` ABC + skill registry.
- [x] `/api/remy/sources` + `/api/remy/queries` CRUD routes.
- [x] Scraper skills (`occ`, `linkedin`, `aggregator`) read `query.cities` (first city name) for location filtering.
- [ ] Install `deepagents` + `langchain-openai`; build `create_remy_agent()` harness — main orchestrator agent with system prompt, LangGraph checkpointer (SQLite, `data/remy/checkpoints.sqlite`), and context management defaults.
- [ ] `subagents.py`: define `scraper`, `analyst`, `recommender`, `cv-chronicler` sub-agents — each with isolated tools, skills, and system prompts; registered as deepagents `task` sub-agents.
- [ ] `tools.py`: agent tool implementations — listings DB CRUD, query read, run write, CV read, report store, import-as-position.
- [ ] `memory.py`: CV memory service — snapshot base CV on every change (`cv_history/` + `cv_history.index.json`), diff generation (`cv_deltas.jsonl`), `profile.json` (role, skills timeline, preferences). LangGraph JSON store (`data/remy/memory/memories/`) for semantic memory (preferences, past feedback, decisions). Read latest CV + recent deltas into agent context.
- [ ] `prompts.py`: main agent system prompt + sub-agent prompts (scraper, analyst, recommender, cv-chronicler) — all include "never invent experience" rule.
- [ ] `/api/remy/chat` conversational agent endpoint (SSE streaming); `/api/remy/chat/{thread_id}` resume thread; `/api/remy/memory` read/clear.
- [ ] Wire `cv-chronicler` sub-agent to CV save path: on every `PUT /api/cv`, trigger snapshot + delta + profile update.
- [ ] `backend/memory/` module for AGENTS.md and MEMORY.md updates accordingly.

### Remy Phase 2: Scraper Skills, Search Database & Vector DB
- [x] `occ.py` skill — parse OCC search results + listing pages (HTML → normalized listings).
- [x] `linkedin.py` skill — public Jobs RSS feed / guest endpoint (with ToS disclaimer in UI).
- [x] `aggregator.py` skill — wrap existing `JobSearchService` (SerpAPI/Brave) into a skill.
- [x] Scraper service: run query against enabled skills, dedup by URL, upsert listings (`first_seen`/`last_seen`/`is_active`).
- [x] `/api/remy/listings` browser routes + single listing detail.
- [ ] Install `chromadb` + `googlemaps`; add both to `backend/requirements.txt`.
- [ ] `places.py` skill — Google Places API: "Text Search" for businesses/companies near each city in `RemyQuery.cities` within configured `radius_km`. Fetches Place Details for additional info (website, phone, type). Normalizes into `RemyListing` dicts. Caches results per city+radius+keyword to minimize API costs.
- [ ] `vectordb.py` service — wraps ChromaDB (default) or LanceDB: embed listings and CVs using the configured embedding model (`REMY_EMBEDDING_MODEL` or provider default). Provides `upsert_listing()`, `upsert_cv()`, `search_similar(embedding, top_k)`, `delete_listing()`. Data persisted under `data/remy/vectors/`.
- [ ] Wire scraper service to vector DB: after upsert, embed the listing text (title + company + description_md) and store in vector DB. Link `RemyListing.embedding_id` to the vector entry.
- [ ] Wire CV save to vector DB: on every CV change (via `cv-chronicler`), embed the full CV text and upsert into vector DB.
- [ ] City management: models + Guadalajara default already done (Phase 1); add add/remove-city CRUD support + validation (radius > 0, lat/lng ranges). City management UI in Phase 5.

### Remy Phase 3: Cronjobs (daily/weekly only)
- [x] Add `apscheduler`; `RemyScheduler` service with `AsyncIOScheduler` wired to FastAPI lifespan.
- [x] `RemyTask` CRUD routes with strict frequency validation (daily | weekly).
- [x] Cron trigger mapping: daily → time; weekly → weekday + time; reschedule on task change; load-on-boot.
- [x] `RemyRun` persistence: cron + manual triggers, statuses, counts, errors.
- [x] `/api/remy/tasks/{id}/run` manual trigger + `/api/remy/runs` history.

### Remy Phase 4: AI Analysis & Recommendations
- [x] Wire `analyst` sub-agent → `RemyAnalyzer` service: market-trend + skills-gap report from nearest listings in vector space vs base CV (prompt from `prompts.py`).
- [x] Wire `recommender` sub-agent → `RemyRecommender` service: two-pass scoring — (1) vector similarity as first pass to narrow candidates, (2) LLM reasoning for nuanced 0–100 match scoring. Returns top-N with reasons.
- [x] `RemyReport` persistence + `/api/remy/analyze/{query_id}`, `/api/remy/recommend/{query_id}`, `/api/remy/reports/{query_id}`.
- [x] Wire analyze/recommend as schedulable task types.
- [x] Memory update after each run: store report ID, top matches, user feedback. Update profile with new market signals.

### Remy Phase 5: Frontend
- [ ] `RemyPage` dashboard with schedule status + recent activity + Remy chat panel (conversational agent interface, SSE streaming).
- [ ] `RemyQueriesPage` — search profile CRUD with city management (add/remove cities, set radius per city via `CityRadiusPicker` component).
- [ ] `RemyTasksPage` + `RemyTaskForm` — frequency toggle (daily/weekly only), weekday + time pickers, enable/disable, run now.
- [ ] `RemyListingsPage` — search database browser with filters + "Import to Position".
- [ ] `RemyReportsPage` — rendered reports + top-match list.
- [ ] `RemyMemoryPage` — CV change history timeline, profile view, cleared/reset option.
- [ ] Layout nav entry + api.js helpers (including SSE stream for /chat).

### Remy Phase 6: Integration, Polish & Mongo
- [ ] "Import listing as Position" end-to-end (listing → Position → adapt → export).
- [ ] `MongoStore` Remy collections + indexes (unique `url` on listings).
- [ ] Politeness: per-source rate limiting, Google Places API quota tracking, robots.txt checks, request delay from config.
- [ ] Empty states, loading/error handling, LinkedIn ToS disclaimer UI.
- [ ] Docs: README Remy section, PLAN/MEMORY updates.

### Remy Phase 7: Topic Suggestions (nice-to-have)
- [ ] `topic_suggestions.py` service: given the user's CV embedding, query the vector DB for the N nearest **unmatched** listings (high vector similarity but no Position imported or no adaptation done).
- [ ] LLM-powered gap analysis: identify recurring skills, technologies, or certifications across those listings that the user's CV lacks.
- [ ] Generate a ranked study roadmap:
  ```json
  {
    "suggestions": [
      {
        "topic": "string (e.g. 'Kubernetes (CKA-level)')",
        "category": "skill | certification | tool | language",
        "relevance_score": 0.0-1.0,
        "matching_listings_count": 5,
        "estimated_effort": "days | weeks | months",
        "example_listings": ["listing_id", ...],
        "rationale": "string"
      }
    ],
    "generated_at": "ISO8601"
  }
  ```
- [ ] `/api/remy/suggestions/{query_id}` endpoint — returns the ranked list.
- [ ] Frontend: `RemySuggestionsPage` — study roadmap view. User can mark topics as "not started" / "studying" / "learned". Progress persists in `profile.json` under a `study_progress` key.
- [ ] "Add to CV" quick-action: once a topic is marked "learned", offer to open the CV editor pre-filled with the new skill (user confirms — never auto-added).
- [ ] Re-generate suggestions on demand or on schedule (new schedulable task type: `suggest`).

### Remy Open Questions
1. **LinkedIn depth**: start with public RSS (low risk) and optionally add a "user-provided cookies" mode later for logged-in scraping — never ship credentials in the app.
2. **OCC parsing**: OCC's HTML structure changes occasionally — pin parser versions and log parse failures as `partial` runs instead of crashing.
3. **Timezone**: server-local by default; `REMY_TZ` later via `zoneinfo` if users request it.
4. **Recommendation → action**: recommendations link to import flow; auto-adaptation of CVs from cron remains a manual step (user approval), keeping the "no invented experience" principle.
5. **Deep Agents model**: use the same OpenRouter/OpenAI-compatible `base_url` + `api_key` from Settings via `langchain-openai` ChatOpenAI. If the configured model isn't good at tool-calling, the agent degrades gracefully (fallbacks in place). Dedicated `REMY_MODEL` config allows a stronger model for planning while cheaper models handle scraping and analysis.
6. **Sub-agent parallelism**: deepagents tasks run sequentially by default; `REMY_MAX_SUBAGENTS` can be raised to run independent tasks in parallel (e.g., scrape LinkedIn + OCC simultaneously). Start conservative, benchmark before raising.
7. **Memory store backend**: start with the in-process JSON store (LangGraph `BaseStore` backed by `data/remy/memory/`). Upgrade path to Postgres/SQLite `AsyncPostgresStore` / `AsyncSqliteStore` from `langgraph` if performance demands it. The CV snapshot + delta mechanism is custom code alongside the LangGraph store; they can be unified later.
8. **Google Places API**: requires a Google Cloud API key with Places API enabled. Billing is per-request; the `places` skill caches results per city+radius+keyword combination to minimize costs. Free tier includes $200/month credit. The "Nearby Search" endpoint is used for radius-based discovery; "Text Search" for keyword refinement.
9. **Vector database**: Phase 4 ships a dependency-free JSON-backed `VectorStore` (`vectordb.py`, data under `data/remy/vectors/`) with pure-Python cosine search — no ChromaDB install required (ChromaDB on Python 3.13 is risky). Provider embeddings are used when `REMY_EMBEDDING_MODEL` is configured (via `LLMClient.embed()`), otherwise a deterministic local feature-hashing embedder (dim 512). ChromaDB remains the swap-in upgrade path (same upsert/search interface).
10. **Embedding model**: use the configured LLM provider's embedding endpoint if available (e.g., OpenAI `text-embedding-3-small` via OpenRouter or direct). Fall back to a local `sentence-transformers` model if the provider doesn't support embeddings or the user wants fully offline operation. Configurable via `REMY_EMBEDDING_MODEL`.
11. **City search limits**: initially hardcoded to Guadalajara, Mexico. City management (add/remove/rename, set per-city radius) is implemented in Phase 2 backend + Phase 5 frontend. The `RemyQuery.cities` array is forward-compatible from day one — multiple cities can be defined even if the UI isn't ready yet.
12. **Topic suggestions model**: the gap-analysis prompt asks the LLM to identify skills that appear in ≥N nearest unmatched listings but are absent from the CV. The LLM ranks them by frequency × relevance and estimates study effort. Suggestions are always user-reviewed — nothing is added to the CV automatically.