# Completed & Archived TODOs

*Moved from TODO.md on 2026-03-18 to keep the active task list focused.*

*Updated on 2026-04-09 to preserve the v2.0.0 release snapshot and completed release follow-up tasks after the roadmap cleanup.*

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
