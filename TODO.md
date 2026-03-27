# Roadmap

---

## v2.0.0 — Current Release (March 2026)

### Shipped
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

### Remaining
- [x] Commit, build, smoke test (`make it_build`)
- [x] `make release_finish` → tag v2.0.0, merge to master, push
- [x] `make it_build_multi_arch_push_GHCR` → push amd64+arm64 to GHCR
- [x] Verify: `docker pull ghcr.io/sage-is/ai-ui:2.0.0`
- [x] Push `Sage-is/homebrew-apps` repo to GitHub
- [x] Update sha256 in `Formula/ai-ui.rb`
- [ ] Test: `brew tap sage-is/apps && brew install ai-ui` (after Docker image slimming)
- [ ] Fix homebrew-apps Makefile `release_finish` — git flow state got stuck on v0.1.2 release; manual merge required to complete

---

## v2.x — Near Term

### Auth & Onboarding
- [x] Single sign-on
- [x] OAuth setup in the setup wizard (Google/Microsoft/GitHub/OIDC)

- [x] No email verification for admin-created accounts
- [ ] Outgoing email notifications (reuse bridge SMTP config)
- [ ] Consolidate LDAP config into Auth/Integrations tab

### Spaces
- [ ] Agent context mode: `conversation` (last ~5 messages) and `full` (all recent) — `single` ships in v2.0.0
- [ ] Optional per-agent TTL for auto-reply expiration

### Frontend Toolchain Upgrade
- [ ] Svelte 4 → 5 (runes replace `$:` reactive declarations, faster compilation, smaller bundles)
- [ ] Vite 5 → 6 (faster HMR, improved build performance)
- [ ] SvelteKit 2.5 → latest (incremental improvements)

### Docker Image Slimming — Phase 1
- [x] Multi-stage Dockerfile: frontend → python-build → python:slim runtime
- [x] Split `requirements.txt` → core + `requirements-ml.txt` (ML installed via wizard)
- [x] Drop node_modules, build tools, Node.js from runtime image
- [x] Deduplicate static file copies (single copy + incremental sync)
- [x] Strip cloud storage providers (S3/GCS/Azure) — local filesystem only, backup via rclone
- [x] Strip unused packages: pandoc, git, opencv, playwright, nltk, pytube, youtube-transcript-api
- [x] Non-blocking startup: embedding models loaded from cache or deferred to wizard
- [x] AI Engine wizard step for on-demand ML package + model download
- [x] `posthog<7` pin fixes chromadb telemetry error
- [x] Production log level defaults to WARNING (dev stays INFO)
- [ ] Target: ~2.5GB (down from 9.7GB) — further trimming possible

### Podman Compatibility
- [ ] Test and fix Podman build issues (VM memory, rootless networking)
- [ ] Document Podman-specific setup (VM memory bump, `host.containers.internal`)
- [ ] Makefile `CONTAINER_RUNTIME` auto-detection: standardize on Docker for v2.0.0, Podman as tested alternative

### CI/CD
- [ ] `make install_dev` — auto-install dev tools via Homebrew
- [ ] `make scan_container` — trivy image scanning (post-build)
- [ ] `make lint` — eslint + prettier + black rollup
- [ ] Gate `release_finish` on passing DB tests (`test_db_upgrade`, `test_db_fresh`) and scans
- [ ] Allow gated release to run locally or hand off to a CI/CD server (same Makefile targets)
- [ ] Staging CapRover instance for pre-prod testing
- [ ] Selenium-driven browser regression tests
- [ ] OWASP ZAP DAST via `make scan_dast`

### Build System
- [ ] Evaluate migrating Makefile to a cleaner build tool (Ruby Rake, Python Invoke, or Just) — Make works everywhere but sed/shell escaping hurts readability as complexity grows

### Knowledge Base
- [ ] AI-Parsed ingestion mode + admin Documents page cleanup
- [ ] Admin page: fold engine-specific config with `<details>/<summary>`

### Cleanup
- [ ] Channel → Space DB migration (Alembic: rename tables, columns, enum values)
- [ ] Rename `components/channel/` directory → `components/space/`
- [ ] Replace wrapper `<div>` elements with semantic custom elements
- [ ] Swagger UI: custom styling, branding, auth handling
- [ ] CapRover one-click template
- [ ] Scrub remaining upstream open-webui references in comments and defaults:
  - `config.py:1972` — stale k8s comment
  - `test/util/abstract_integration_test.py:76` — `POSTGRES_DB: "openwebui"` → `sage_is_ai`
  - `pdf_generator.py:111` — comment references `open-webui serve`
  - `storage/provider.py:202` — comment references open-webui
  - `FunctionEditor.svelte:45-47` — default template author/urls → sage-is
  - `SettingsModal.svelte:423-428` — add sage search keywords alongside open-webui ones
- [ ] Migration idempotency guards on all `create_table` / `add_column` calls (10 migration files)
- [x] Fix ChromaDB telemetry error — pinned `posthog<7` (chromadb uses 3-arg capture removed in v7)
- [ ] Replace login slideshow images (`app/static/assets/images/`) with original or CC/public domain photos — sea life, Azores landscapes, night sky/star shots. Source from Wikimedia Commons or original photography. Update `SlideShow.svelte` defaults if filenames change.

---

## v3.0 — Future

### Docker Image Slimming — Phase 2
- [x] Volume-based ML packages: `pip install --target` to data volume, persists across restarts
- [x] AI Engine wizard step triggers pip install + model download in background
- [ ] Target: ~1.5GB base image (chromadb transitive deps still heavy)

### Developer Mode
- [ ] `ai-ui dev` CLI command: clones repo, mounts source, enables DEV_MODE
- [ ] DeveloperStep wizard: informational in prod, celebration with wizard illustration in dev mode
- [ ] Node.js + npm installed to data volume on first dev start
- [ ] Same image, same container — DEV_MODE=true switches to vite HMR + uvicorn reload

### Upload & Download UX
- [ ] Download progress streaming to frontend (WebSocket/SSE from backend)
- [ ] Admin panel tab for AI Engine download status and progress
- [ ] HF_TOKEN support for faster authenticated HuggingFace downloads
- [ ] Download time estimates based on measured connection speed
- [ ] Upload progress bars with percentage and speed meters
- [ ] Configurable upload timeouts based on file size (replace hardcoded 240s)
- [ ] Console/log viewer tab in admin (WebSocket log streaming)

### Platform
- [ ] Sage.is hosted email notification service (for deployments without SMTP)
- [ ] Workspace switcher (project-scoped model configs, shared vs private)
- [ ] Built-in task tracking (convert chat responses to tasks, due dates, progress)
- [ ] Personal analytics dashboard (usage patterns, model preferences)
- [ ] Semantic search across all chats and documents
- [ ] Mobile-first optimizations (swipe gestures, PWA enhancements)
- [ ] Accessibility: screen reader, high contrast, keyboard navigation

---

> **Archived items**: See [`docs/completed-todos.md`](docs/completed-todos.md) for verified-completed and stale/resolved tasks.
