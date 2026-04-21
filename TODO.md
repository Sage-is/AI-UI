# Roadmap

This file tracks active work only.

> Historical snapshots and completed bulk moved to `docs/completed-todos.md` and `docs/archive/` on 2026-04-09.
>
> **Convention** — Sections below map to kanban columns. Inline source-code
> tags use the same vocabulary so items stay cross-referenced between this
> file and the codebase. `KANBAN.canvas` auto-generates from this file and
> inline tags — do not hand-edit it.
>
> | Column      | Markdown section  | Inline tag  |
> |-------------|-------------------|-------------|
> | Backlog     | `## Backlog`      |             |
> | TODO        | `## TODO`         | `# TODO:`   |
> | In Progress | `## In Progress`  | `# FIXME:`  |
> | Bugs        | `## Bugs`         | `# BUG:`    |
> | Done        | `- [x]` items / `## Done` | —   |
>
> `# DEPRECATED:` tags should be tracked as TODO items for removal at the
> stated version.

---

-[x] **Happy Summary**
  -[x]v2.0.0 shipped the Sage rename, Spaces UX, setup wizard, chat sharing, knowledge-base improvements, and messaging bridges for WhatsApp, Telegram, Signal, and Email.
  -[x] Release engineering is in much better shape: security scanning, pre-commit hooks, DB upgrade smoke tests, dependency cleanup, and a much leaner Docker path are all in place.
  -[x] The docs now keep active references separate from historical audits, plans, and retrospectives so this roadmap can stay focused on unfinished work.

---

## In Progress

_Items currently in progress. Move items here and or use tag source with `# FIXME:` when work begins._

- [ ] **Docker Image Slimming**: (Alexander Somma)
  - [x] Hit the ~2.5GB target (down from 9.7GB)
  - [ ] Hit the ~1.5GB base-image target after trimming heavy transitive deps

---

## TODO

### Release Wrap-Up

- [x] **Homebrew Tap Release**: Finish and verify the brew install path #critical
  - [x] Test: `brew tap sage-is/apps && brew install ai-ui`
  - [x] Fix homebrew-apps Makefile `release_finish`
  - [x] git flow state got stuck on v0.1.2 release; manual merge required to complete
  - [x] celebrate!!! :D

### v2.x — Near Term

- [ ] **Auth & Onboarding**: Email notifications and LDAP consolidation
  - [ ] Outgoing email notifications (reuse bridge SMTP config)
  - [ ] Consolidate LDAP config into Auth/Integrations tab

- [ ] **Spaces Enhancements**: Agent context modes and auto-reply TTL
  - [ ] Agent context mode: `conversation` (last ~5 messages) and `full` (all recent) — `single` already ships
  - [ ] Optional per-agent TTL for auto-reply expiration
    <!-- inline: spaces.py:384 -->

- [ ] **Frontend Toolchain Upgrade**: Svelte 5, Vite 6, SvelteKit latest
  - [ ] Svelte 4 → 5
  - [ ] Vite 5 → 6
  - [ ] SvelteKit 2.5 → latest

- [ ] **Podman Compatibility**: Verify builds and document setup
  - [ ] Test and fix Podman build issues (VM memory, rootless networking)
  - [ ] Document Podman-specific setup (VM memory bump, `host.containers.internal`)
  - [ ] Revisit Makefile `CONTAINER_RUNTIME` auto-detection once Podman is a verified alternative

- [ ] **Knowledge Base Improvements**: AI ingestion and admin cleanup
  - [ ] AI-parsed ingestion mode + admin Documents page cleanup
  - [ ] Fold engine-specific config under `<details>/<summary>` in the admin page

- [ ] **Codebase Cleanup**: Channel→Space rename, semantic HTML, branding
  - [ ] Channel → Space DB migration (Alembic rename of tables, columns, enum values)
  - [ ] Rename `components/channel/` directory → `components/space/`
  - [ ] Replace wrapper `<div>` elements with semantic custom elements
  - [ ] Swagger UI: custom styling, branding, auth handling
  - [ ] CapRover one-click template
  - [ ] Scrub remaining upstream open-webui references in comments and defaults
  - [ ] Add migration idempotency guards on all `create_table` / `add_column` calls
  - [ ] Replace login slideshow images with original or CC/public-domain photos

### v3.0 — Future

- [ ] **Backend Rewrite Research**: Evaluate framework options and build contract tests
  - [ ] Review `docs/backend-rewrite-research.md` with team
  - [ ] Phase -1: Generate contract test suite from OpenAPI spec (private submodule)
  - [ ] Phase 0 spike: chosen framework + streaming Ollama proxy
  - [ ] Team decision: Go + PocketBase, Rust + Loco, or Python + Django?

- [ ] **Developer Mode**: Single image, dev CLI, HMR
  - [ ] `ai-ui dev` CLI command: clones repo, mounts source, enables DEV_MODE
  - [ ] DeveloperStep wizard: informational in prod, celebration with wizard illustration in dev mode
  - [ ] Node.js + npm installed to data volume on first dev start
  - [ ] Same image, same container — `DEV_MODE=true` switches to vite HMR + uvicorn reload

- [ ] **Upload & Download UX**: Progress streaming, time estimates, admin viewer
  - [ ] Download progress streaming to frontend (WebSocket/SSE from backend)
  - [ ] Admin panel tab for AI Engine download status and progress
  - [ ] `HF_TOKEN` support for faster authenticated HuggingFace downloads
  - [ ] Download time estimates based on measured connection speed
  - [ ] Upload progress bars with percentage and speed meters
    <!-- inline: ollama.py:1748 -->
  - [ ] Configurable upload timeouts based on file size (replace hardcoded 240s)
    <!-- inline: audio.py:598,652,759 ollama.py:1699,1799,1823 -->
  - [ ] Console/log viewer tab in admin (WebSocket log streaming)

- [ ] **Platform Features**: Workspaces, analytics, search, mobile, a11y
  - [ ] Sage.is hosted email notification service (for deployments without SMTP)
  - [ ] Workspace switcher (project-scoped model configs, shared vs private)
  - [ ] Built-in task tracking (convert chat responses to tasks, due dates, progress)
  - [ ] Personal analytics dashboard (usage patterns, model preferences)
  - [ ] Semantic search across all chats and documents
  - [ ] Mobile-first optimizations (swipe gestures, PWA enhancements)
  - [ ] Accessibility: screen reader, high contrast, keyboard navigation

### From Codebase (untracked)

- [ ] **Backend Inline TODOs**: Load balancing, type updates, deprecation removal
  - [ ] Intelligent load balancing for multiple Ollama backends (`ollama.py:1`)
  - [ ] Update Ollama type support when upstream adds new types (`ollama.py:1378`)
  - [ ] Handle tool name collisions by prepending toolkit name (`utils/tools.py:109`)
  - [ ] Replace legacy system message insertion with `add_or_update_system_message` (`middleware.py:997`)
  - [ ] Add retries to audio processing requests (`audio.py:1120`)
  - [ ] Remove deprecated `WEBUI_JWT_SECRET_KEY` fallback at next major version (`env.py:393`)

- [ ] **Frontend Inline TODOs**: UX polish, component upgrades, bug investigation
  - [ ] Filter order handling in model config (`FiltersSelector.svelte:34`)
  - [ ] Voice input auto-stop logic in Knowledge Base (`AddTextContentModal.svelte:21`)
  - [ ] Shortcut support for generate-title button (`ChatItem.svelte:415`)
  - [ ] User-facing error for Space participant issues (`Space.svelte:81`)
  - [ ] Emoji picker search filtering (`EmojiPickerClean.svelte:47`)
  - [ ] Update RichTextInput Bubble/Floating to v3 (`RichTextInput.svelte:79`)
  - [ ] Note pages feature — multiple pages per note (`NoteEditor.svelte:80`)
  - [ ] Decide native vs custom file handling in notes (`NoteEditor/Chat.svelte:191`)
  - [ ] Investigate Kokoro worker issues (`kokoro.worker.ts:4`)

---

## Backlog

_Items deferred to a later planning cycle. Move here from TODO when deprioritized._

- [ ] **CI/CD Pipeline**: Gated releases, scanning, and regression tests
  - [ ] `make install_dev` — auto-install dev tools via Homebrew
  - [ ] `make scan_container` — trivy image scanning (post-build)
  - [ ] `make lint` — eslint + prettier + black rollup
  - [ ] Gate release finish on passing DB tests and scans
  - [ ] Support the same gated release flow locally or on CI
  - [ ] Staging CapRover instance for pre-prod testing
    <!-- inline: Makefile:572 -->
  - [ ] Selenium-driven browser regression tests
  - [ ] OWASP ZAP DAST via `make scan_dast`

- [ ] **Build System Evaluation**: Consider alternatives to Make
  - [ ] Evaluate migrating Makefile to a cleaner build tool (Rake, Invoke, or Just)

---

## Bugs

_No known bugs. Use `# BUG:` inline tags to flag defects in source._

---

## Done

> Completed items are moved to `docs/completed-todos.md` periodically.
> Check off items with `- [x]` and leave them in place until the next cleanup.

- [x] TodoScope Alignment
  - [x] Restructure TODO.md to TodoScope conventions
  - [x] Fix duplicate rows in `.todoscope-exclude.csv`
  - [x] Run TodoScope scanner and verify kanban board matches expectations
