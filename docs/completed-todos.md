# Completed & Archived TODOs

*Moved from TODO.md on 2026-03-18 to keep the active task list focused.*

*Updated on 2026-04-09 to preserve the v2.0.0 release snapshot and completed release follow-up tasks after the roadmap cleanup.*

*Updated on 2026-07-03 to archive the `## Done` bug-fix and feature-ship entries accumulated since — try.sage.is env-gating bugs, the homebrew tap release, try.sage Phase A/B, four try.sage regression bugs, and the TodoScope alignment pass.*

---

## ✅ `## Done` section archived from TODO.md on 2026-07-03

- [x] **try.sage Runtime `/llm-status` Endpoint Not Env-Gated**: With `ENABLE_TRY_SAGE=false`, `GET /api/v1/sage/runtime/llm-status` returns `403 {"detail":"Not authenticated"}` instead of 404. The route handler is registered unconditionally; auth is the only barrier. Sibling endpoints (`status`, `personas`, `limits`) correctly 404 when the env flag is off. #critical #bug
  - [x] Locate the `llm-status` route handler in the trial runtime router
  - [x] Confirm whether it sits outside the trial router or whether the router-level `enable_try_sage` check is missing for this handler specifically — root cause was **dependency order**: `_require_try_sage_enabled()` was called inline AFTER `Depends(get_admin_user)` had already evaluated, so auth's 401/403 fired before the env-gate's 404. Same defect class affected `/extend` and `/reset`.
  - [x] Add the same gating that protects `status` / `personas` / `limits` so the route returns 404 when the env flag is false — fix at `app/backend/sage_is_ai/routers/sage_runtime.py:267-272`: lifted gate into `_gate: None = Depends(_require_try_sage_enabled)` parameter listed BEFORE `Depends(get_admin_user)`. Applied to `/llm-status`, `/extend`, `/reset`. Docstring of `_require_try_sage_enabled` now documents the ordering contract.
  - [x] Re-run the trial smoke for-loop; confirm `404 /llm-status` — verified against fresh `sage-is/ai-ui:bug-verify` image; all seven trial endpoints (`status`, `personas`, `limits`, `llm-status`, `extend`, `clear`, `reset`) return 404.

*(Surfaced 2026-05-10 during the regression sweep — caught by the `for ep in status personas limits llm-status extend clear` curl loop.)*

- [x] **Unregistered `/api/*` Paths Return SPA HTML Instead of 404**: With `ENABLE_TRY_SAGE=false`, `GET /api/v1/sage/runtime/extend` and `GET /api/v1/sage/runtime/clear` return `200 text/html` (5463 bytes, identical etag) — the SvelteKit static catch-all serves `index.html` for unregistered backend paths. Breaks any curl-based smoke test that expects 404 for absent routes and masks future router-registration bugs. #bug
  - [x] Locate where the SPA static catch-all is mounted in the FastAPI app — `SPAStaticFiles.get_response` in `app/backend/sage_is_ai/main.py`.
  - [x] Add a guard so `/api/*` paths that don't match a registered router return JSON 404, not the SPA index — fix at `app/backend/sage_is_ai/main.py:498-510`: in `SPAStaticFiles.get_response`, paths equal to `api` or starting with `api/` now return `JSONResponse(status_code=404, content={"detail": "Not Found"})` instead of falling through to `index.html`.
  - [x] Verify with a curl against any made-up `/api/v1/nonexistent` path — should return 404 with `application/json` — verified: `GET /api/v1/literally_made_up_path` returns `404 Not Found` with 22-byte JSON body. Non-api SPA paths still return `200 text/html` (frontend routing intact).
  - [x] Re-run the trial smoke for-loop; `extend` and `clear` should report `404 /<endpoint>` — verified, plus `/reset` also 404 (which would have been a third leak without this fix).

*(Surfaced 2026-05-10 during the same sweep.)*

- [x] **Homebrew Tap Release**: Finish and verify the brew install path #critical
  - [x] Test: `brew tap sage-is/apps && brew install ai-ui`
  - [x] Fix homebrew-apps Makefile `release_finish`
  - [x] git flow state got stuck on v0.1.2 release; manual merge required to complete
  - [x] celebrate!!! :D

- [x] **try.sage Runtime and Admin Controls**: (Alexander Somma + Izzy Plante) — Shipped Phase A 2026-04-27.
  - [x] Gate try.sage.is ai behind env vars
  - [x] Seed default try.sage agents: Sage Strawberry, Sage Startr.Style, AstroPi AI tutor (with KBs)
  - [x] Register `https://tool-server.example.com` in `TOOL_SERVER_CONNECTIONS`
  - [x] Add a dummy-tools server with placeholder endpoints (revisit later — see Production Decisions)
  - [x] Trial helper endpoints: status, personas, limits, llm-status, extend, reset
  - [x] Auto-reset every 24h via env-configurable settings; selective wipe preserves persona accounts and KBs
  - [x] Admin-only extend (capped at one extension per window) and force-reset
  - [x] RBAC via existing `get_admin_user` dependency on protected endpoints
  - [x] Hidden OpenAI-compatible LLM connection (memory-only, never persisted, never echoed in any response)
  - [x] Model allowlist via `TRY_SAGE_LLM_MODELS`
  - [x] Document env vars, reset semantics, admin controls in `docs/try-sage-deployment.md`
  - [x] Makefile targets `try_sage_start` / `try_sage_stop`

- [x] **try.sage.is Experience and Insights**: (Alexander Somma + Izzy Plante) — Shipped Phase B 2026-04-27.
  - [x] Persistent top-of-screen try.sage banner with live HH:MM:SS countdown
  - [x] Admin extend/reset CTAs in the banner row (live next to the countdown they affect)
  - [x] Non-admin info line directing to docs and admin
  - [x] User-bar persona switcher: admin + facilitator + 3 trial users (configurable up to 5 trial users)
  - [x] Tutorial overlay with config-driven steps (`TRY_SAGE_TUTORIAL_STEPS_JSON`); 6-step default with placeholder cards when unset
  - [x] Setup wizard suppression in trial mode + admin escape hatch in Admin → Settings → Trial Mode
  - [x] Per-step `dismissible` flag honored; localStorage seen-flag persists across sessions
  - [x] Provider-agnostic analytics shim (Matomo + GA + Plausible) wired via `$config.analytics`
  - [x] Pure-Svelte zero-dep QR encoder for persona magic-link sharing in workshops
  - [x] Document the UX + analytics event map in `docs/try-sage-deployment.md`

- [x] **try.sage Tutorial Step Cards Render Empty**: When the tutorial does open (via Admin → Trial Mode → Replay tutorial), the step cards are missing content — title, "Video coming soon" placeholder, and `description` paragraph all missing or partially missing. #bug
  - [x] Reproduce: with `TRY_SAGE_TUTORIAL_STEPS_JSON` unset, open the tutorial via the admin replay button — confirm cards render without expected content
  - [x] Inspect the default-step rendering branch in `app/src/lib/components/setup/TrySageTutorial.svelte` — specifically the placeholder card layout that fires when `step.video_url` is empty/missing
  - [x] Confirm whether the `DEFAULT_STEPS` constant is reachable, the iteration is correct, and i18n wrapping isn't producing empty strings
  - [x] Fix the missing-cards rendering so at minimum each step shows: title, "Video coming soon" placeholder, and the step's `description` paragraph

*(Surfaced 2026-04-29 in the same regression session.)*

- [x] **Trial Banner Overlapped by Left Sidebar**: Once a persona signed in, the left sidebar (admin / chat list) overlapped the trial banner. Banner was a full-width strip pushed into the layout flow; sidebar's z-index let it cut into the banner's edges. #bug
  - [x] Float the banner above the app shell rather than reflowing it inline. Outer wrapper `position:fixed; top:0.5rem; left:0; right:0; z:40; pointer-events:none`. Inner pill `max-w:60ch; margin:0 auto; pointer-events:auto; rounded; subtle shadow`. Doesn't push navbar/content down on first paint and z-index keeps it above the sidebar.
  - [x] Edited `app/src/lib/components/TrySageBanner.svelte` outer wrapper only — inner content (countdown row, persona-jump row, `<details>` block) untouched.
  - [x] Banner now slides 280px right when the desktop sidebar opens so it stays centered over the chat content, not the full viewport. Driven off the existing `showSidebar` store with a 200ms ease transition. Mobile is unaffected (sidebar overlays there).

*(Surfaced + fixed 2026-04-29 during regression testing.)*

- [x] **Replace David / Sistine Chapel Art in Login Slideshow**: The login/onboarding/welcome slideshow ships a Michelangelo's David and a Sistine Chapel ceiling image — both are recognisable Renaissance pieces that don't fit the Sage.is brand and may carry licensing risk depending on the source photo. Swap for original or CC/public-domain imagery. #bug
  - [x] Find the offending images under `app/static/` (likely `static/assets/images/` or wherever `SlideShow.svelte` reads from) and confirm the exact filenames + license source
  - [x] Pick replacements: original Sage.is photography, or CC0 / public-domain alternatives that match the warm-workshop tone (libraries, classrooms, observatories, etc.)
  - [x] Replace files in-tree, keep filenames stable so `SlideShow.svelte` keeps working without code change. Run the build and visually confirm new images render in the welcome slideshow + try.sage welcome page.
  - [x] Cross-link with the existing **Codebase Cleanup → "Replace login slideshow images with original or CC/public-domain photos"** task — collapse if both are doing the same work.

*(Surfaced 2026-04-29 reviewing the trial welcome page imagery.)*

- [x] **try.sage Tutorial Does Not Auto-Open on First Persona Sign-In**: The TrySageTutorial modal is supposed to auto-open the first time a persona signs in (gated on `$config?.features?.enable_try_sage` + signed-in `$user` + missing `localStorage.try_sage_tutorial_seen_v1`). Manually triggering "Replay tutorial" from Admin → Trial Mode opens it correctly, so the modal itself works — only the auto-trigger fails. #bug
  - [x] Reproduce: clear `localStorage.try_sage_tutorial_seen_v1`, sign in via a persona magic link, confirm modal does NOT appear
  - [x] Inspect the `onMount`/reactive trigger condition in `app/src/lib/components/setup/TrySageTutorial.svelte` — likely the `$user` check fires before the user store hydrates after magic-link verify, OR the SvelteKit hard-navigation from `/auth#magic_token=...` lands before the layout has subscribed to `tutorialReopen`
  - [x] Fix so the auto-show fires on first persona sign-in, not just from the admin "Replay tutorial" button
  - [x] Add a Vitest spec that mounts the component with mocked `$config`, `$user`, and a clean `localStorage`, and asserts the modal opens

*(Surfaced 2026-04-29 during manual regression of the persona sign-in flow.)*

- [x] TodoScope Alignment
  - [x] Restructure TODO.md to TodoScope conventions
  - [x] Fix duplicate rows in `.todoscope-exclude.csv`
  - [x] Run TodoScope scanner and verify kanban board matches expectations

---

## ✅ Roadmap History Snapshot (moved from TODO.md on 2026-04-09)

### ✅ v2.0.0 Shipped
- [x] Package rename: `open_webui` → `sage_is_ai` (imports, env vars, deployment artifacts)
- [x] "Channel" → "Space" terminology (UI, API routes, socket events; DB schema rename deferred)
- [x] Messaging Bridges — WhatsApp (WAHA), Telegram, Signal, Email (IMAP/SMTP)
- [x] Spaces: @mentions, threads, reactions, member management, agent auto-reply on `?`
- [x] Spaces: animated thinking indicators with rotating status phrases
- [x] Setup wizard with live connection verification (Ollama, OpenAI endpoints)
- [x] Home dashboard with recent/pinned conversations
- [x] Sidebar search, collapsible folders and date groups
- [x] Chat sharing between users ("Shared with me" / "Shared by me")
- [x] Magic links for passwordless auth
- [x] Knowledge base with multi-collection support
- [x] AI document parsing with configurable ingestion modes (plain / structured / AI-parsed)
- [x] Note editor with title management
- [x] Security scanning framework: `make scan` (gitleaks, semgrep, bandit, trivy)
- [x] Pre-commit git hooks (`.pre-commit-config.yaml`)
- [x] Offline semgrep rules (`.semgrep/` — Python, JS/TS, Svelte)
- [x] DB upgrade smoke test: `make test_db_upgrade`
- [x] Dependency security upgrades (authlib, pillow, aiohttp, jspdf, etc.)
- [x] Dead code cleanup (litellm endpoint, open-webui version check, Scarf analytics)
- [x] Changelog parser fix (handles em-dash dates + prose format)
- [x] Dockerfile: copies root CHANGELOG.md, removed stale app/CHANGELOG.md
- [x] Simplified root `docker-compose.yaml` (single-service, Docker)

### ✅ v2.0.0 Release Follow-Up Completed
- [x] Commit, build, smoke test (`make it_build`)
- [x] `make release_finish` → tag v2.0.0, merge to master, push
- [x] `make it_build_multi_arch_push_GHCR` → push amd64+arm64 to GHCR
- [x] Verify: `docker pull ghcr.io/sage-is/ai-ui:2.0.0`
- [x] Push `Sage-is/homebrew-apps` repo to GitHub
- [x] Update sha256 in `Formula/ai-ui.rb`

---

## ✅ Verified Completed (March 2026 audit)

### ✅ API Layer Cleanup - COMPLETED
- [x] **Systematic API Refactoring**: 24/24 API files migrated to centralized `createApiHelper()`
  - [x] 0 files still using local `api()` helper — fully migrated
  - [x] `streaming/index.ts` reference implementation in place
  - [x] 5,426+ lines of repetitive code eliminated (75% average reduction)

### ✅ Workspace → Workshop Rename - COMPLETED
- [x] **Complete Workspace → Workshop Rename**: 563 replacements across 103 files
  - [x] `workshop/` component and route directories exist, `workspace/` dirs removed
  - [x] All phases (analysis, migration, content updates, testing) verified complete

### ✅ Channel → Space Rename - COMPLETED
- [x] **Complete Channel → Space Rename**: 1,097 replacements across 87 files
  - [x] `space/` route exists, `channel/` and `channels/` routes removed

### ✅ DRY Code Analysis - 3/4 COMPLETED
- [x] **Priority 1**: ShortcutsModal.svelte — 13KB → 6.1KB (53% reduction) ✅
- [x] **Priority 2**: AdvancedParams.svelte — data-driven config system ✅
- [x] **Priority 4**: Interface.svelte — data-driven config system ✅
- [~] **Priority 3**: WebSearch.svelte — file no longer exists at expected path, status unclear

### ✅ KISS/DRY License Table - COMPLETED
- [x] Simplified to inline data structure, removed async markdown loading

### ✅ Emoji Data DRY Refactoring - COMPLETED
- [x] Pure string-based emoji data, category skin tone logic, Intl.Segmenter

### ✅ Model Editor "Save & Chat" - COMPLETED
### ✅ Model Creation Flow Fix - COMPLETED
### ✅ Interface Settings Default - COMPLETED
### ✅ FloatingButtons UX Improvement - COMPLETED
### ✅ Voice Input UI Enhancement - COMPLETED

---

## ❌ Stale / Resolved (March 2026 audit)

### ❌ Config Management (Sept 2025) - MOOT
- [~] **Move config variables to .env**: Backend uses `PersistentConfig(env_name, config_key, default)` pattern natively — already reads from env vars. `.env.example` exists. The proposed dotenv migration doesn't align with the existing architecture.

### ❌ Documents Component DRY - REVERTED/LOST
- [~] **FormField.svelte**: Marked as created and deployed but `FormField.svelte` does not exist in the codebase. Work was either reverted or never committed. `FormFieldRow.svelte` exists and serves a similar purpose.

### ❌ WebSearch Component DRY - FILE MISSING
- [~] **WebSearch.svelte**: File not found at `admin/Settings/WebSearch.svelte`. Either renamed, merged into another component, or deleted. Task is stale.

### ❌ Storage Provider Tests DRY - COMPLETED
- [~] **Refactor Storage Provider Tests**: Full DRY test suite already exists. Task completed differently than originally scoped.

### ✅ Dev Mode Console Cleanup - RESOLVED
- [x] **Fix Dev Mode 404 and CORS Issues**: COEP/CORS properly configured. Vite proxy handles static files correctly.

### ✅ PostCSS Browser Compatibility - RESOLVED
- [x] **PostCSS Warnings**: Config is now minimal Tailwind v4 plugin only (`@tailwindcss/postcss`). Original warnings from older PostCSS setup no longer apply.

---

## ✅ Completed Work Summary

### Major Achievements (August 1, 2025)

#### 🏆 Development Environment Fixes - COMPLETED
- **COEP Policy Fix**: Disabled Cross-Origin-Embedder-Policy for localhost development
  - Modified vite.config.ts to conditionally set COEP headers only for production
  - Kept COOP (Cross-Origin-Opener-Policy) for security but removed COEP in dev
  - Eliminated COEP-related errors in development environment
  - Production builds still maintain proper security headers
- **Audio File Error Handling**: Fixed Audio NotSupportedError in +layout.svelte
  - Added error handling for audio.play() calls to prevent uncaught exceptions
  - Ensured audio files are accessible in development mode
  - Added fallback behavior when audio files are missing
- **Authentication Error Cleanup**: Fixed Token Warning in +layout.svelte
  - Changed console.warn to console.log for better UX during initial auth
  - Ensured proper token handling without alarming users
  - Verified socket connection handling is appropriate
- **Static File 404 Fix**: Resolved favicon.png, logo.png returning 404 in container
  - Fixed manifest.json 404 errors with proper proxy config
  - Resolved favicon CORS blocking with CORS_ALLOW_ORIGIN
  - Configured proper dev server static file handling with vite proxies

#### 🏆 Docker Build Optimization (July 29-30, 2025) - COMPLETED
- **MAJOR SUCCESS**: Achieved 50% build time improvement (5m52s vs 10m+)
- **Runtime Model Loading**: Successfully moved expensive model downloads from build to runtime
  - PyTorch installation: ~120s moved to runtime
  - SentenceTransformer downloads: ~148s moved to runtime
  - Whisper model downloads: ~10s moved to runtime
  - Tiktoken encoding: ~5s moved to runtime
- **Smart Caching System**: Created `init_models.sh` with intelligent model persistence
- **Volume Mounts**: Model cache directories properly mounted for persistence
- **Development Workflow**: Fast rebuild process documented and working

#### 🏆 Massive API Layer Cleanup (July 27-29, 2025) - COMPLETED
- **Campaign Results**: 24/24 API files processed (100% complete)
- **Lines Eliminated**: 5,426+ lines of repetitive code removed
- **Average Reduction**: 75% code reduction across all files
- **Highest Achievement**: 88% reduction in functions/index.ts (545→67 lines)
- **Pattern**: Identified and eliminated systematic commit padding across entire codebase
- **Enhanced Error Reporting**: Implemented comprehensive error context system

#### 🏆 API Documentation (July 29, 2025) - COMPLETED
- **Swagger UI Enabled**: Configured FastAPI to serve interactive API docs at `/docs`
- **ReDoc Added**: Additional documentation option available
- **Testing Complete**: Verified Swagger UI accessibility and functionality

#### 🏆 Audio Settings Bug Fix (July 28, 2025) - COMPLETED
- **Kokoro.js TTS Fix**: Personal settings now properly respected over global config
- **Testing Complete**: Verified all dtype configurations (fp32, fp16, q8, q4)
- **Documentation**: Created comprehensive fix documentation

### Development Workflow Improvements
- **Enhanced Error Reporting**: Detailed logging for API endpoint failures
- **Code Quality**: Systematic elimination of code bloat and repetitive patterns
- **Documentation**: Comprehensive troubleshooting guides and fix documentation
- **Testing**: Thorough validation of all fixes and improvements
