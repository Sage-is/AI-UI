# Completed & Archived TODOs

*Moved from TODO.md on 2026-03-18 to keep the active task list focused.*

*Updated on 2026-04-09 to preserve the v2.0.0 release snapshot and completed release follow-up tasks after the roadmap cleanup.*

*Updated on 2026-07-03 to archive the `## Done` bug-fix and feature-ship entries accumulated since — try.sage.is env-gating bugs, the homebrew tap release, try.sage Phase A/B, four try.sage regression bugs, and the TodoScope alignment pass.*

*Updated on 2026-08-01 to archive 25 resolved entries — the 2.3.x ship and try.sage regression sign-off, the Sprig™ B1 extraction and B2 clarity work, the Bonsai™ spec-site section, and five wizard bugs closed by the no-build cut-over. The no-build migration's own entries stay in TODO.md: that work is still in flight.*

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

## ✅ Archived from TODO.md on 2026-08-01


### In Progress

- [x] **Deploy 2.3.2 to try.sage.is**: `v2.3.2` deployed at some point after the 2026-06-10 freeze lifted — confirmed live 2026-07-03 (`GET try.sage.is/api/config` → `version: 2.3.2`; `/assets/loader.js` → `200`, was 404 at the time this item was written). Never checked off. #critical

- [x] **Ship 2.3.1 — Jidoka spine + three Poka-Yoke children**: Shipped 2026-05-19. Tag `v2.3.1` pushed, `ghcr.io/sage-is/ai-ui:2.3.1` published, `SERVER_TAG=2.3.1` pinned across the hardlink chain. Detail in `CHANGELOG.md`; plan at `~/.claude/plans/given-our-newest-trends-modular-sloth.md`. #critical

- [x] **try.sage Manual Regression Sign-off** (2026-04-27): Phase A backend + Phase B frontend shipped. All 12 smoke checks passed (container boot, persona magic-links, banner, switcher, tutorial, admin tab, hidden connection, model filter, env-gate disable). Reference left for future regression-pass authors.


### Repo Hygiene & Security

- [x] **Node lockfile CVE sweep — 17 → 0** (2026-07-26): the `audit-deps` pre-commit hook (trivy, `HIGH,CRITICAL`, fires only on `bun.lock`/`requirements.txt`) had not run in a while because nothing touched `bun.lock`. The Phase Q cruft sweep touched it and woke the hook: **17 findings (15 HIGH, 2 CRITICAL)**. Pre-existing, not sweep-caused — the sweep's lockfile diff is 13 lines, all deletions, and scanning `HEAD`'s untouched `bun.lock` returns the identical 17. All were transitive; fixed by raising the existing `overrides` floors plus one direct bump, then regenerating in Docker (`make bun_install`): `tar >=7.5.11 → >=7.5.19` (CRIT gzip bomb), new `protobufjs >=7.6.1` (CRIT RCE via injected type fields, from `onnxruntime-web`), new `linkify-it >=5.0.2` (from `markdown-it`, the one that genuinely ships to the browser), new `brace-expansion >=5.0.8` (from `minimatch`), new `ws >=8.21.0` (from `engine.io-client`/`pyodide`), new `sharp >=0.35.0` (from `@huggingface/transformers`; resolved 0.35.3, the one major bump, and it installed clean), and direct `undici ^7.24.0 → ^7.28.0` (a pin only — 0 `src/` imports, pulled by `cheerio` ← the dev-only `i18next-parser`). Exposure context: `node_modules` is NOT baked into the runtime image (the Dockerfile copies only `/app/build/`), so apart from what Vite bundles this was build-time surface, not shipped-runtime surface. Verified: `trivy` **0 vulnerabilities, exit 0**; `make it_build` frozen-lockfile build green; `make e2e` 11/13 with only the two known pre-existing leak failures below. We could NOT delete our way out of the two biggest — `@huggingface/transformers` is live in `Leaderboard.svelte` and `kokoro.worker.ts`, and pulls `onnxruntime-web` with it. Committed. #security


### Release Wrap-Up

- [x] **Shared build/gate libraries — DRY pass** (2026-07-22; committed): extracted two shared libs to kill copy-pasted boilerplate. `scripts/lib/gate.sh` — PASS/FAIL + `ok`/`no`/`require`/`gate_summary`; adopted by `verify-image-manifest.sh` + `manifest-verify-fixture.sh` + the 4 heavy smoke gates (lifecycle/upgrade/durability/signing), all re-certified green via `gauntlet_full` (66/66, 12/12, 10/10). `scripts/lib/sprig-build.sh` — `sprig_build_defaults` (the 8 OCI/registry constants), `sprig_arch_normalize`, portable `sha256`, `sprig_ensure_registry`, `sprig_push` (optional `SIG_LAYER` superset), `sprig_timing_start|end`. **9 `build-sprig-*` recipes** now source it (tika, docling, backup-rclone, rag-loaders, export-document, media-ffmpeg, dev-svelte, vector-chroma, whisper) — ~270 lines of duplication gone; every recipe gained the ⏱ footer. Certified by REAL rebuild across 3 shapes: **tika** (jlink server, both arches — sha256 **byte-identical** to the CATALOG pins), **backup-rclone** (static-download deliver + SIGN), **rag-loaders** (pip). Hazards caught during rollout: set-e safety (helpers `return 0` past benign falses — arm64 arch, registry poll); `TAG=v2` preserved for dev-svelte/vector-chroma; whisper's out-of-block `ORAS_IMG`/`sha256` de-duplicated.
  - [ ] **4 outlier recipes stay OFF the lib** (by design — none has the standard arch/push blocks; forcing them = over-fit): `build-sprig-theme.sh` (arch-neutral 846-byte token artifacts), `build-sprig-minilm.sh` (arch-neutral ONNX weights, custom push — **also carries the macOS `bsdtar` lacks-`--sort=name` reproducibility bug: switch its pack to GNU-tar-in-docker when next touched**), `build-sprig-reranker.sh` (GGUF, two push paths), `repack-sprig-arch.sh` (re-tags an existing artifact — different tool). Optional light reuse: they COULD call `sprig_build_defaults` + `sprig_ensure_registry` for constants/registry only.
  - [ ] **`wizard-smoke.sh` keeps its own helper style** (`require`/`fail` with container-log dump, `KEEP_ON_FAIL`) — could adopt `gate.sh` for consistency, but its fail-shape differs; low priority.
  - [x] **`parity_gate` EXERCISED for the first time — green** (2026-07-27). Context: the gate SKIPs rather than FAILs when its 8.I.3 artifacts are absent (shipped 2026-07-22, so `gauntlet_full` does not halt on a not-yet-built gate) — but it turned out to be **structurally unrunnable**, not merely unbuilt: `harness.py` READS `/w/harness/reference.json`, and nothing in the repo ever wrote it, so no invocation of `make parity_gate` could ever have exercised parity. Two missing halves now shipped: **`scripts/gates/embedding-parity/gen-reference.py`** (sentence-transformers embeddings + HF tokenizer ids, emitted in the exact order `harness.py` expects — `parity + corpus + queries` — and merged per-model so several cultivars can share the file) and **`scripts/gates/embedding-parity/build-artifacts.sh`** (one container: cpu-torch, HF pull, `convert_hf_to_gguf.py` at the SAME pinned `b9859` as `build-llama-static.sh`, `llama-quantize` to Q8_0, then the reference). Egress IS required at build time; nothing produced here ships in the image, so the runtime zero-egress property is untouched. **FIRST REAL RESULT — both quants pass with room:** `e5-f16` cos_mean=1.00000 **cos_min=0.99999** tok_mismatch=0 recall=5/5 top3agree=15/15 (needs ≥0.999); `e5-q8` cos_mean=0.99966 **cos_min=0.99913** tok_mismatch=0 recall=5/5 top3agree=15/15 (needs ≥0.99 + full recall). `tok_mismatch=0` on both means the Korean/Hangul canary that held minilm and bge back is clean for e5 — which is why e5 is the shipped cultivar. Verified the static musl `llama-quantize` runs under Debian glibc (the any-libc property holds). Two traps burned in for the next runner: bind-mounts must NOT nest inside the `$OUT` mount (Docker Desktop virtiofs refuses it — `$BIN` already lives inside `$OUT`, so mount the gate scripts on their own path), and a bare `snapshot_download` pulls safetensors AND pytorch-bin AND onnx AND openvino (**9.0GB measured**), so the script now ignores the redundant formats (~2.3GB; the kept/dropped split was verified against the live repo file list, not assumed). Artifacts live at `/tmp/sprig-build/8i3/{bin,gguf,harness}` and are NOT in git — rerun `build-artifacts.sh` after a machine wipe or a llama.cpp tag bump. #bonsai

- [x] **TODO.md cleanup pass** (2026-05-25): Post-2.3.1 reconcile — collapsed the shipped 2.3.1 entry to a single [x], promoted the 2.4 ML bundle follow-up to its own item, added v2.3.1 to Happy Summary, trimmed the completed try.sage regression entry. KANBAN.canvas will regenerate automatically from this file.


### Bonsai™ Spec Site & Documentation Architecture

- [x] **First Graft: make one wizard toggle pull a Sprig** (2026-06-30, exceeded by 2026-07-03): Shipped as the walking skeleton (mock-embedding on a loopback port, `RAG_EMBEDDING_ENGINE=openai` dispatch) and grew well past it in the four days since. Catalog now carries **14 entries across 9 capabilities** (`app/backend/sage_is_ai/sprigs/supervisor.py`, AST-counted): six `embedding` cultivars (mock-embedding, all-MiniLM-onnx, minilm-onnx-inhoused, multilingual-e5-large, bge-large-en-v1.5, e5-large-gguf), plus one each for `dev`, `vector`, `rag`, `export`, `code`, `browser-ml`, `media`, `backup`. `GET /catalog`, `POST /graft`, and `POST /prune` are all live (`routers/sprigs.py`); docstring drift that claimed prune/top-graft/multi-catalog were deferred is fixed. `revive` = re-graft (no separate op); `topgraft` runs inside graft(). **12 of the 14 deliver via sha256-verified `oci-artifact`** from a local registry (matching the 12 registry repos, no HuggingFace/pip pull at graft time); the 2 that don't are `mock-embedding` (mock server) and `all-MiniLM-onnx` (live HF pull). The in-housing north star (no end user pulls from HuggingFace or pip once Sprigs work) is real for those 12, not aspirational. `scripts/smoke/sprig-lifecycle.sh` is wired into `gauntlet` and passes 41/41 (verified 2026-07-03: bare-rootstock absences, clean pre-graft 503s, GGUF-on-bare-rootstock, vector-chroma, rag-loaders restart-free, live onnx→gguf top-graft, export-document, code-pyodide/browser-ml, media-ffmpeg/backup-rclone/dev-svelte, final image 604MB). `make sprig_registry` (new 2026-07-03) makes the local OCI registry an idempotent one-command dependency of `sprig_smoke` instead of an undocumented "must already be running" assumption. #bonsai #critical

- [x] **Sprig subsystem audit + Poka-Yoke pass** (2026-07-03/04): 5-dimension adversarial audit (44 verified findings). Answered the operator's three questions — clean? / all chunks sprigged? / clear for non-technical people? Shipped this pass: **(quick wins)** the admin UI now surfaces the backend's actual graft/prune error detail instead of a generic toast (`Sprigs.svelte`); pinned the redundant runtime `chromadb==0.6.3` install (`retrieval.py`, was unpinned → base-breaking 1.5.x); rewrote the drifted "DEFERRED" docstrings across `supervisor.py`/`routers/sprigs.py`/`mock_embedding_server.py`/`embedding_server.py`; fixed the grafted counter to include `delivered`; added the 21 missing Sprig i18n keys to `en-US`; corrected the "12 → 14 entries" miscount. **(durability — the lead ask)** grafts now survive a Rootstock™ restart: the supervisor persists a volume-resident `state.json` and reconciles on boot — re-extracting deliver overlays from a volume-cached sha256-verified tar (`artifact.py`, offline; also fixes the "tag bump won't re-pull" footgun via a `.delivered-tag` marker) and re-spawning embedding cultivars, with a single-owner flock guard for multi-worker and an import-time fail-clean guard in `main.py` (a dead-loopback embedding config no longer reports "ready"). Config-pointing extracted to a shared `sprigs/embedding_dispatch.py` (router + reconcile, no drift). **(test coverage, 2026-07-04)** `sprig_smoke` grew to **44 checks** — new section 6c grafts `minilm-onnx-inhoused`, the only user of artifact.py's `chroma-onnx` seed path (previously zero coverage on that path), asserts a 384-dim vector from the seeded offline cache, and checks `state.json` on the volume. New **`make sprig_durability`** gate (`scripts/smoke/sprig-durability.sh`, wired into `gauntlet_full`): full `docker rm -f` recreation with the registry STOPPED → boot reconcile restores the ffmpeg overlay + re-spawns the embedding child from the volume, offline. Cypress `sprigs-panel.cy.ts` grew to **7 tests**: new failed-graft test asserts the backend's fix-pointer ("Graft vector-chroma first") reaches the toast, and a counter regression test asserts `delivered` sprigs count as grafted. The two big cultivars the default gates skip got their own **opt-in `make e2e_heavy`** gate (`cypress/e2e/heavy/sprig-cultivars.cy.ts`, in NO gauntlet — run on demand): verified 3/3 green 2026-07-04 — vector-chroma delivery, **bge-large-en-v1.5 grafting restart-free straight after the overlay delivery** (enabled by a new `importlib.invalidate_caches()` poka-yoke in the supervisor's dep pre-check — the parent's stale import cache used to force a restart between vector-chroma and any onnx graft), and **all-MiniLM-onnx doing its real ~80MB HF/chroma-S3 pull** then top-grafting over bge with the 1024→384 "must be reindexed" width warning asserted in the UI (a Poka-Yoke path nothing else tested). Fixing the heavy runner also surfaced+fixed that `SPEC=` spec selection was silently broken for ALL subdir suites (Cypress 15 intersects `--spec` with the top-level-only `specPattern` — `cypress/e2e/upstream/` was unreachable too); `run-cypress.sh` now overrides `specPattern` instead. Default gates stay zero-egress. #bonsai


### Sprig B1 — finish extraction (audit backlog, sequenced next)

- [x] **Extraction pass shipped** (2026-07-05/06, all gates green: smoke **57/57**, durability 12/12, e2e 12/12, e2e_heavy 3/3): Catalog is now **15 entries / 11 capabilities, zero-egress at graft time**. **(reranker)** New `bge-reranker-v2-m3-gguf` — the design pivoted from ONNX cross-encoder to GGUF once scouting confirmed the in-house static llama-server (b9859) supports `--rerank` and its `/v1/rerank` speaks the exact Jina/Cohere contract the existing `ExternalReranker` (`engine=external`) already parses: one binary + one Q8_0 model (~360MB), zero client changes, `sprigs/reranker_dispatch.py` points `RAG_EXTERNAL_RERANKER_URL` at the loopback. Packaging `scripts/build-sprig-reranker.sh` sanity-gates semantic ordering before push. **(stt)** New `whisper-base-ggml` — static whisper.cpp **v1.9.1** `whisper-server` (v1.7.4 lacks `/health`; static musl needs `-DGGML_OPENMP=OFF`) + ggml-base-q8_0, serving `/v1/audio/transcriptions` for the untouched `STT_ENGINE=openai` client path (`sprigs/stt_dispatch.py`); grafting makes the wizard's HF whisper download skippable. **(cleanup)** `all-MiniLM-onnx` RETIRED (last live-pull entry; heavy cypress swapped to `minilm-onnx-inhoused`, same 1024→384 width-warning coverage, gate now zero-egress and 5× faster); `sprigs/vector_bootstrap.py` unifies the two divergent chromadb pip sites into ONE sprig-first bootstrap (volume tar → registry → pinned-pip fallback; try.sage flips to sprig-first automatically at prod cutover); top-graft/reconcile/prune/restart-backstops generalized to all three server capabilities (`server_args` catalog field). Ops lessons burned in: host disk hit 100% mid-build (Docker VM corruption — recovered, zero artifact loss), macOS bsdtar lacks `--sort=name` (packs now run GNU tar in docker), `e2e` needs `app/node_modules` (containerized `bun install --frozen-lockfile` restores it after cleanup sweeps). **(upgrade path, 2026-07-06 follow-up)** "Pull the new image and boot" still upgrades everything: pins/tags ship WITH the image, and boot reconcile brings the volume into agreement — deliver overlays re-extract (offline on same tag, re-pull on bump), weight cultivars now honor tag bumps too (`.delivered-tag` marker extended to model-dir/chroma-onnx seeds; the sentinel-only check silently served STALE weights across version bumps), retired catalog entries are skipped WITH a logged re-graft pointer, and a failed upgrade pull leaves the current version serving (wipe only after verified pull). Live-proven by tag-bump simulation; smoke re-verified 57/57. Prod caveat: tag bumps need the registry reachable → don't bump artifact tags in prod images until the registry cutover ships. #bonsai

- [x] **Poka-Yoke pass + sage.startr.cloud upgrade rehearsal SHIPPED** (2026-07-12; all standard gates green on the final image — smoke 66/66, signing 10/10, durability 12/12, e2e green, upgrade_gate 16/16; committed): a 32-agent adversarial audit (refute-first verify, several findings reproduced live) returned **25 confirmed findings**; every code-level one fixed. **Security/correctness (backend):** theme validator now decodes CSS escapes before scanning so `url(\68ttp…)` / `\@import` can't smuggle an external beacon past the self-containment check (unit-proven in-image); `SPRIG_REQUIRE_SIGNED` with no pubkey is a LOUD boot error instead of silently bricking every signature-required graft on reconcile; arch-refused (and registry-unreachable) reconcile entries no longer erode from `state.json` — a new `_deferred` set keeps them in desired-state until an explicit prune or a compatible host (prune clears them); `MODEL_DOWNLOAD_STATUS["chromadb"]` starts honest ("pending", not a literal "ready" lie on a slim boot); `_check_boot_config` names a malformed `SPRIG_REGISTRY`, an unknown host arch, and the require-signed-without-key case at boot. **Operator-facing (UI):** `/catalog` exposes `host_arch` + per-entry `compatible`; the admin Sprigs panel greys out incompatible cards with "Not available on this server (amd64)" + tooltip, so no click 503s (i18n keys added). **Supply chain:** `publish-sprigs.sh` now derives the repo list from the supervisor CATALOG (not whatever's in the local registry — the gap that let the 2 theme artifacts ship unpublished) and verifies ANONYMOUS ghcr pullability via the token endpoint, not just gh-api visibility. **Privacy:** `tools/db_snapshots/` fully gitignored — real user data (176MB webui.db, 3.9GB vectors) was one `git add` from committing. **New gate `make upgrade_gate`** (`scripts/smoke/upgrade-gate.sh` + `scripts/snapshots/inject-test-admin.py` + `cypress/e2e/upgrade/legacy-data.cy.ts`, reusable via `TARGET_URL` against any snapshot/staging clone): boots THIS image on a COPY of the prod snapshot (read-only source, throwaway admin injected into the copy), proving DB migration, user/chat/knowledge survival, legacy openai-embedding config untouched, RAG degrading cleanly (asserts HTTP code, not just body shape), chromadb reading the prod store with collection PARITY, themes on legacy data, and the amd64 capability gap (loud + asserted, section 6). Gate-quality fixes: `jq length`-counts-error-keys, unconditional "restarted healthy", and the fresh-volume amd64 rehearsal were all self-defeating and are fixed. `run-cypress.sh` gained `TARGET_URL` mode so the upgrade Cypress half can actually run against an existing container. Findings the audit surfaced but that are ARCH/DEPLOY decisions, not code bugs → the two items below. #bonsai #critical

- [x] **Prod-registry cutover SHIPPED** (2026-07-12, poka-yoke pass): registry is env-driven — `SPRIG_REGISTRY` (default `ghcr.io/sage-is`, SECURE) + `SPRIG_REGISTRY_INSECURE` (auto-on only for loopback/local hosts) in `sprigs/supervisor.py`; all 16 catalog `repo`/`insecure` fields resolve from those constants; boot reachability probe (`_check_registry_reachable`) turns an unreachable registry into ONE loud boot log instead of a per-graft 503; boot-config validation catches a malformed `SPRIG_REGISTRY` (scheme prefix, uppercase path). 5 smoke/e2e boot sites + Makefile run targets pass the dev registry through; `SPRIG_REGISTRY` env pass-through added to `COMMON_RUN_ARGS`. **NEAR-TERM per Alexander:** self-host the prod registry in-cluster with GHCR as mirror, or proxy GHCR for now — `SPRIG_REGISTRY` makes that a zero-code swap. #bonsai

- [x] **amd64 Sprig artifacts (8.J) — DEPLOY BLOCKER RESOLVED** (2026-07-15, shipped in 3.0.0): all **17 catalog entries graft on both arm64 and amd64** — nothing arm64-only remains (static recheck 17/17 in the real image). amd64 artifacts: python-wheel closures (vector-chroma `v2-amd64`, rag-loaders/export-document `v1-amd64`) built per-arch under QEMU; ONNX embedding weights flipped arch-neutral (minilm/e5-large/bge — empty `amd64` override, same tag+sha, they ride the vector-chroma onnxruntime); static servers (whisper `v1-amd64`, and the two GGUF via `repack-sprig-arch.sh` after `scripts/build-llama-static.sh`); static downloads (media-ffmpeg/backup-rclone `v1-amd64`); dev-svelte `v2-amd64`. **The llama.cpp b9859 yak is solved:** `LLAMA_BUILD_UI=OFF` + `LLAMA_USE_PREBUILT_UI=OFF` builds the server headless (empty embedded-UI lib), dodging the missing-`loading.html` HF-bundle failure — `LLAMA_BUILD_UI=OFF` alone is NOT enough (the prebuilt fetch still runs). Both GGUF amd64 artifacts BOOT-TESTED under QEMU: e5-gguf serves 1024-dim embeddings, reranker orders correctly via `/v1/rerank`. Multi-arch schema (`arches: {arch: {tag, binary_sha256}}`) + graft-time overlay unchanged. `upgrade_gate` section 6 flipped from must-REFUSE to must-GRAFT. Full status in `docs/deploy-sage-startr-cloud.md`. #bonsai #critical #deploy-blocker

- [x] **Sprigs published to GHCR** (2026-07-07): all **14 sprig artifacts** (16 tags — incl. the catalog-pinned `vector-chroma:v2` + `dev-svelte:v2`) copied registry-to-registry from `local-registry:5000` to `ghcr.io/sage-is/sprig-*` via dockerized oras (`oras cp`, gh-token login). Off-machine durability for the whole catalog: the anonymous-Docker-volume single-point-of-failure is now mitigated even before the 11 missing build recipes land. Visibility: **all 14 flipped to PUBLIC** (2026-07-07, per-package web UI — GitHub has NO API for container-package visibility; two flips silently didn't take on the first pass and needed an API-verified retry). Anonymous pulls verified with a credential-less oras client. Any self-hoster can now pull the whole catalog; sha256 pins in the CATALOG remain the integrity guarantee. Registry-host cutover (env-driven, `insecure` gating) remains the separate #critical item below — until it lands, deployed images still pull from `local-registry:5000` only. #bonsai

- [x] **Publish pipeline + public sprig catalog page** (2026-07-07): **(a) `make sprig_publish`** (`scripts/publish-sprigs.sh`) — pushes every local tag to `ghcr.io/sage-is` idempotently, then GATES on visibility: fails with per-package fix URLs when anything is non-public (GitHub has no visibility API; the gate makes silently-internal packages impossible — three of the 14 manual flips silently failed on the first pass, which is exactly the failure mode this closes). Run it after any `build-sprig-*.sh`. One-time org check [MANUALLY]: allow public package creation at github.com/organizations/sage-is/settings/packages. **(b) `sage.is/sprigs/`** — canonical public catalog page in WEB-Sage.is (`src/sprigs.njk` + `src/_data/sprigs.yaml`, books.njk card-grid pattern, startr.style mobile-first): 14 sprigs in 4 plain-language groups with size/license/tag, `oras pull` commands, GHCR links, and a "how grafting works" section. The YAML's title/description fields deliberately prefigure the B2 catalog-schema enrichment — when that lands, generate this file from the supervisor CATALOG instead of hand-maintaining. Build verified (11ty renders `dist/sprigs/`); deploy = commit+push WEB-Sage.is [MANUALLY]. #bonsai

- [x] **Sprig™ artifact signing shipped (minisign, offline)** (2026-07-08/09; gate `make sprig_signing` **10/10 first run**; committed): artifacts now carry a minisign signature as a second OCI layer (`application/vnd.sage-is.sprig.minisig`), verified **offline in the Rootstock before extraction**. Verifier `sprigs/minisign.py` is pure in-base (stdlib blake2b + the `cryptography` Ed25519 already shipped — zero new deps), validated against real minisign 0.11 output including content-tamper, trusted-comment-tamper, and wrong-key refusals; wired into `artifact.py` under the same verify-before-cache discipline as the sha256 pin (which remains the allowlist — the signature adds publisher provenance for mirrors and the future marketplace, via the per-entry `pubkey` hook). Policy: a present signature is ALWAYS verified fail-closed; required per-entry (`signed: True`) or globally (`SPRIG_REQUIRE_SIGNED=1`); a cache that predates the requirement re-pulls instead of failing. Sigstore keyless was rejected for v1: Fulcio/Rekor round-trips break air-gapped verify (boot reconcile re-verifies cached artifacts with NO network); anyone can still audit with the stock CLI (`minisign -Vm <tar> -P <pubkey>` — trusted comment binds `repo:tag sha256=…`). Tooling: `make sprig_sign` (`scripts/sign-sprigs.sh`, dockerized oras+minisign, re-signs every local tag in place — tar bytes unchanged so pins hold), SIGN_KEY hooks in all three `build-sprig-*.sh`, `FORCE=1 make sprig_publish` for the changed manifests, committed DEV fixture key (`scripts/dev-keys/`, worthless by design) powering the gate, and `sprig_signing` wired into `gauntlet_full`. **Remaining:** [MANUALLY] generate the production keypair (recipe in `scripts/dev-keys/README.md`, passphrase to the password manager) → `SIGN_KEY=~/sage-keys/sprig.key make sprig_sign` → `FORCE=1 make sprig_publish`; then [WE] pin the `.pub` line as `_DEFAULT_PUBKEY` in `artifact.py` and flip catalog entries to `signed: True`. IMPLEMENTATION.md divergence #1 updated in both spec repos (the divergence is now WHICH scheme, not whether to sign). #bonsai #critical


### Sprig B2 — non-technical clarity (audit backlog; data model before UI)

- [x] **Author `sage.is/bonsai/` explainer** (2026-06-28; AUTHORED 2026-07-08, deploy = commit+push WEB-Sage.is [MANUALLY]): Curious-visitor doorway at `WEB-Sage.is/src/bonsai.njk` (single file mirroring the shipped sprigs.njk pattern rather than the originally-sketched `src/bonsai/` dir). What-is-Bonsai in plain prose, What-is-a-Sprig with an inline-SVG graft diagram (rootstock + three fingerprint-checked sprigs + Graft Union label), the AGPL-and-proprietary-Sprigs FAQ (4 Q&As in newcomer language: your-Sprig-your-license, selling proprietary Sprigs, operator obligations, where the derivative-work line is), hand-off CTAs to both specs (GitHub repos until the hub is live — flip to `bonsai.sage.is/*/v1/` after, tracked in the hub item above), SEO title/description tuned. Sprigs page closing paragraph cross-links /bonsai/ + both spec repos. Build verified (dist/bonsai/ renders, cross-links present both directions). 2026-07-08 follow-ups: Graft Union™ SVG label moved off the connector lines (junction dot added), marketplace line added to the sell-a-Sprig FAQ answer. #bonsai

- [x] **Theme Sprigs™ SHIPPED — mechanism (1) of the UI-extension ladder** (Alexander's "make it so" 2026-07-11; smoke **66/66 first run**, was 57; committed): a Sprig can now theme the running interface with design tokens only. **Catalog is 17 entries / 12 capabilities** (+`theme-workshop-bio` green, +`theme-workshop-math` blue — the workshop presets the Spaces-theming backlog wanted, 846-byte artifacts, the first Sprigs with FULL in-repo source: `scripts/themes/` + `scripts/build-sprig-theme.sh` with a build-time self-containment gate). Mechanics: capability `theme`, `server: deliver` + `seed: model-dir` composes unchanged (volume-resident, restart/upgrade durable via existing machinery); graft-time validation fail-closed in `sprigs/theme_dispatch.py` (strips comments, then refuses `@import`/external `url()`/script-shaped content — CSS can't execute but CAN beacon, so external refs break zero-egress — plus a 512KB cap); activation = one PersistentConfig pointer (`SPRIG_ACTIVE_THEME`, `ui.sprig_active_theme`); unauthenticated `GET /themes/active.css` in main.py serves the active sheet (styles the login page too; empty sheet when none); `app.html` loads it on every page; last-grafted-wins, prune of the active theme resets (`theme_reset` flag + admin toast + i18n key). The token hook: the interface's Tailwind gray scale reads `var(--color-gray-N)` with the variables never declared, so a `:root` block wins without `!important` (oled-dark's four inline gray overrides still beat stylesheets by design). Spec: the `theme-` reservation graduated to a **defined v1 contract** (Theme Sprigs™ section in sprig-spec v1.md, written FROM the shipped implementation — 4 Sprig MUSTs + 4 rootstock MUSTs), CHANGELOG updated, both IMPLEMENTATION.md files record the match, hub renders `#theme-sprigs`. **Remaining on the ladder:** (2) declarative extensions (manifest of menu items/actions/iframe panels — the marketplace default, Slack/Shopify-shaped) and (3) signed slot-mounted web components (hold until prod signing + publisher identity mature); `ui-` prefix stays reserved. [MANUALLY] after the prod signing pass: FORCE-publish the two theme artifacts to GHCR, flip visibility, add their cards to sage.is `sprigs.yaml`. #bonsai #ui #marketplace

- [x] **Confirm Bonsai™ metaphor horizon before `bonsai.sage.is` ships** (2026-06-28; DECIDED 2026-07-08): Rich Harris's strategic question answered by Alexander — **Bonsai™ is sticking as the 10-year name**, so `bonsai.sage.is` ships as the canonical spec URL and the hub scaffold proceeds against it. The `spec.sage.is` reservation above stays as the escape hatch per Daniel Stenberg's guardrail (parked DNS, no content). #bonsai #strategic-decision
  - [x] Founders' decision: is Bonsai™ the long-horizon name? — YES (Alexander, 2026-07-08)
  - [x] `bonsai.sage.is` ships as canonical (hub scaffold built the same day)
  - [ ] Document the decision and the reasoning in a brief `docs/` note so future-us doesn't relitigate


### Bugs

- [x] **Changelog pager button does not move sides in a real browser** (fixed 2026-07-31): the Continue button on `/pages/admin/setup/changelog` paged and relabelled correctly but never travelled to the other side of the row, confirmed twice by Alexander in a real browser on 2026-07-30. Fixed by deleting the mechanism rather than debugging it. The button used to travel by `transform: translateX(var(--pager-shift))`, with `changelog-pager.js` measuring `row.clientWidth - button.offsetWidth` on every sync and on every resize. It now travels by `margin-left: auto`, flipped to `margin-left: 0` by a `[data-at-end='false']` attribute the script sets — one attribute, no measurement, nothing to compute wrong. `changelog-pager.js` lost the measuring and the resize listener with it. Verified working by Alexander in a real browser 2026-07-31. Neither suspect on the old entry (a startr.style `--t` collision, a first-paint measurement race) was ever confirmed, and both describe code that no longer exists.

- [x] **Setup wizard shows a step the admin explicitly unchecked** (fixed 2026-07-31): deselecting Authentication on Welcome and pressing "Get Started" opened the Authentication panel anyway. `handleWelcomeStart` assigned `dynamicPanels` and called `skipIfNeeded()` in the same synchronous block, against a `panels` value Svelte had not recomputed — so the skip loop ran on a stale one-entry array and skipped nothing. Fixed by deletion: the orchestrator is gone, and `welcome_panel.start_wizard` now stores the choice and returns the first chosen step's route, with no reactive value to be stale. `wizard-welcome.cy.ts` asserts every step lands on its own route.

- [x] **`CompleteStep` leaks a 5s interval when the wizard is closed mid-download** (fixed 2026-07-31): the component started a `setInterval` polling `/api/v1/retrieval/models/status` with no `onDestroy`, so closing the modal mid-download left the poll running for the rest of the session. Fixed by deletion — the panel is now `pages/complete_panel.py`, which reports what the server holds at render time and starts no timer.

- [x] **`UsersStep` offers a role its own CSV importer rejects** (fixed 2026-07-30): both the Svelte importer and `pages/users_panel.CSV_ROLES` now accept `facilitator`. `pending` was kept, because removing it would break CSV files that import correctly today. Asserted in `wizard-users.cy.ts`.

- [x] **`ChangesAndSetupModal` comment states a stale panel order** (fixed 2026-07-31): the file is deleted. The order it described now lives once, in `_SETUP_ORDER` in `pages/router.py`, and `setup-navigation.cy.ts` discovers it by walking `setup-next` rather than restating it.


### Done

- [x] **try.sage Production Decisions**: (Alexander Somma + Izzy Plante) — Surfaced by Docker exploration. Block CapRover one-click rollout.
  - [x] Decide where `TRY_SAGE_LLM_API_KEY` lives in production: plain env, Docker secret mount, or external vault. Recommend Docker secret for try.sage.is itself, plain env for self-hosted workshops.
    - [x] note:As we use cap rover and the system injects env vars we're leaning this way

- [x] **Cypress E2E revival — docker-only headless + interactive-watch infra, three new specs** (2026-07-02 to 2026-07-03): Pinned `cypress/included:15.18.0` (not the 13.x devDep major — Cypress 13 bundles a Chromium whose `ReadableStream` isn't async-iterable and the app's streaming path throws on it). `scripts/e2e/run-cypress.sh` runs the suite headless against a fresh rootstock + Caddy TLS sidecar, no npm/cypress on the host. `scripts/e2e/run-cypress-watch.sh` + `scripts/e2e/watch/` adds an interactive GUI variant: Xvfb + x11vnc + noVNC served at `localhost:6080/vnc.html`, Sage-branded (logo, favicons, Archivo type via a subsetted font — see the font-subsetting TODO above). New specs: `degradation.cy.ts`, `sprigs-panel.cy.ts`, `users.cy.ts`; `registration.cy.ts` moved to `cypress/e2e/upstream/`. Headless run verified green: 10/10 specs passed. Decided 2026-07-02 alongside the noVNC-transport backlog item below (WebRTC swap still pending). #tests

> Archived 2026-07-03: the 8 bug-fix/feature entries that had accumulated here (try.sage env-gating bugs, homebrew tap, try.sage Phase A/B, four regression bugs, TodoScope alignment) moved to `docs/completed-todos.md`.
