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

- [ ] **try.sage Runtime and Admin Controls**: (Alexander Somma + Izzy Plante)
  - [ ] Gate try.sage.is ai behind env vars
  - [ ] Seed default try.sage agents, including Sage Strawberry, Sage Startr.Style and AstroPi AI tutor
  - [ ] Register `https://markdown-search.production.openco.ca` in `TOOL_SERVER_CONNECTIONS` for try.sage mode (reuse existing OpenAPI markdown server)
  - [ ] Add a small OpenAPI dummy-tools server with clearly labeled placeholder endpoints that advertise advanced capabilities without exposing them in try mode
  - [ ] Add a small set of trial helper endpoints (status, limits, reset policy) that return clear "you are in try mode" responses
  - [ ] Default trial instances to auto-reset after 24 hours via env-configurable try.sage settings
  - [ ] Add admin-only control to extend the reset deadline one day at a time
  - [ ] Add admin-only quick-reset action for immediate reset when needed
  - [ ] Enforce role-based permissions so only admins can extend or force-reset trial instances
  - [ ] Document env vars, reset semantics, and admin-control behavior for local and CapRover deployments

- [ ] **try.sage.is Experience and Insights**: (Alexander Somma + Izzy Plante)
  - [ ] Show a persistent top-of-screen try.sage banner with a clear countdown to next reset
  - [ ] Show admin-specific reset controls in the user-bar area when logged in as admin
  - [ ] Non admin should see messaging that admins can reset this timer etc...
  - [ ] Add user-bar switching between the three try.sage personas: admin, facilitator, and user
  - [ ] Add onboarding/tutorial guidance for workshop access, model switching, chat map, artifacts, and other key try.sage features, including how to build a Bialik Sage example agent
  - [ ] Publish a Bialik Sage tutorial content package: three short videos plus a follow-up email with system prompts so users can experiment with their own version
  - [ ] Keep system prompt disclosure only in the dedicated system-prompt video and update that single short video per team session, independent of codebase releases
  - [ ] Decide which tutorial steps are dismissible versus always available from help/navigation
  - [ ] Add Matomo analytics for try.sage usage across supported platforms, including persona switching, tutorial engagement, and core feature entry points
  - [ ] Document the try.sage UX and analytics event map for product and implementation teams

---

## TODO

### Release Wrap-Up

- [x] **Homebrew Tap Release**: Finish and verify the brew install path #critical
  - [x] Test: `brew tap sage-is/apps && brew install ai-ui`
  - [x] Fix homebrew-apps Makefile `release_finish`
  - [x] git flow state got stuck on v0.1.2 release; manual merge required to complete
  - [x] celebrate!!! :D

### Privacy & Poka-Yoke #critical

- [ ] **Review & implement Poka-Yoke privacy plan**: Three structural mistake-proofing changes surfaced by panel review
  - [ ] **PK-1 — Local/External model indicator**: Add `is_external` + `provider_label` to model API response; show Local/External badge in model selector, response bubbles, and space agent messages
  - [ ] **PK-2 — Admin chat access default OFF**: Change `ENABLE_ADMIN_CHAT_ACCESS` default to `False` in `config.py:1378`; add audit log line in `routers/chats.py:86`; add visible banner when admin views a user's chats
  - [ ] **PK-3 — Workshop external model warning**: Show inline warning when an agent is created with an external-provider base model
  - [ ] Update CHANGELOG.md: document breaking change (admin chat access now opt-in)
  - [ ] Full plan at: `~/agent-planning/plans/poka-yoke-buzzing-sedgewick.md`

### Pitch & Documentation

- [ ] **Pitch — Fix Privacy Absolutes**: Audit `docs/elevator-pitch.md` for unconditional privacy claims
  - [ ] Replace "nothing phones home" → "nothing leaves your building unless you send it"
  - [ ] Replace "we don't store data" → "Sage stores nothing; schools may store by default; ephemeral mode is available"
  - [ ] Add educator-visibility default sentence: "Sage ships with educator visibility on by default. Students can toggle privacy at any time."
  - [ ] Revise model-transparency claim: "when a user is permitted to inspect an agent, they always see which model it calls"
  - [ ] Audit remaining absolute claims for similar conditionals

- [ ] **Pitch — Pick Primary Audience**: Decide family pitch vs. org pitch as the launch face
  - [ ] Choose one audience for the current pitch (family: local/budget-first, or org: sovereignty/compliance)
  - [ ] Revise opening hook for that audience only
  - [ ] Confirm cake metaphor stays in the family version only
  - [ ] Stub a second pitch outline for the other audience

- [ ] **Publish Threat Model**: One public document establishing what Sage defends and what it does not
  - [ ] Document what Sage-the-company stores (nothing) vs. what schools may store (by default)
  - [ ] Document residual risks for users of the anonymizing proxy
  - [ ] Document warrant/subpoena response sequence for school deployments
  - [ ] Written commitment: no automated behavioral flagging (hate speech, self-harm, etc.) without explicit school opt-in
  - [ ] Publish to `docs/` and link from README and elevator-pitch

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

- [ ] **Docker Image Slimming (Pinned / Paused)**: (Alexander Somma)
  - [x] Hit the ~2.5GB target (down from 9.7GB)
  - [ ] Hit the ~1.5GB base-image target after trimming heavy transitive deps

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

- [ ] **Auto Reset Mode (Trial Environments)**: Env-var controlled data/session reset with user countdown messaging
  - [ ] Define env vars for reset enablement and interval (local + CapRover compatible)
  - [ ] Add startup/runtime wiring to enforce auto-reset behavior when enabled
  - [ ] Document env var defaults and deployment examples in docs
  - [ ] Add UI messaging to show users they are in a trial environment
  - [ ] Show time remaining until reset ("n time to reset") in a visible countdown
  - [ ] Add pre-reset warning state and post-reset confirmation messaging
  - [ ] Add basic tests for reset timing logic and user-facing message visibility

- [ ] **Full Regression Testing Suite**: End-to-end coverage for core user flows, integrations, and release confidence
  - [ ] Standardize Svelte unit/integration tests on Vitest, matching current Svelte guidance
  - [ ] Add jsdom plus `@testing-library/svelte` for component regression coverage where DOM interaction matters
  - [ ] Cover high-risk Svelte components first: chat composer, microphone/transcription flow, auth forms, settings, and uploads
  - [ ] Expand the existing Cypress E2E suite to cover the core happy-path and failure-path user journeys
  - [ ] Define a deterministic test-data strategy for local and CI runs: seeded state where needed, stubs where faster and safer
  - [ ] Evaluate Playwright for cross-browser smoke coverage and trace-based CI debugging before deciding on dual-stack vs migration
  - [ ] Gate releases on a tiered regression pipeline: fast Vitest checks first, browser regressions after, smoke coverage on release builds
  - [ ] Document how to run each regression layer locally and in deployment pipelines

- [ ] **Audio Regression Testing Suite**: Deterministic voice-input coverage across recorder, transcription, and chat-input handoff
  - [ ] Define the audio test pyramid: unit logic, component behavior, browser E2E, and limited real-device smoke coverage
  - [ ] Build a golden audio corpus for regression runs: clean speech, silence, noisy input, clipped speech, accented speech, and low-volume samples
  - [ ] Add deterministic browser audio tests that feed known audio files as fake microphone input instead of relying on a live human mic in CI
  - [ ] Auto-grant microphone permissions in browser test runs and verify recording state transitions, processing UI, and transcript insertion into chat input
  - [ ] Cover failure paths explicitly: permission denied, empty transcript, transcription failure, canceled recording, and timeout handling
  - [ ] Add transcript assertions using normalized text matching where exact punctuation is not stable
  - [ ] Decide which audio paths run full end-to-end against the real backend transcription flow versus mocked/stubbed transcription responses
  - [ ] Evaluate Playwright specifically for browser-level media permission control, fake microphone input, cross-browser smoke tests, and trace debugging
  - [ ] Keep a small manual or staged real-microphone smoke suite for supported devices instead of making live microphone capture a required CI gate
  - [ ] Document how to run audio regression tests locally, in CI, and on staging with the required browser flags, fixtures, and expected assertions
---

## Bugs

- [ ] **Chat Microphone Recording Does Not Populate Message Input**: Recording from the microphone icon in chat does not process speech into the text field used to send messages #bug
  - [ ] Reproduce the issue in the chat interface and confirm whether capture, transcription, or input binding is failing
  - [ ] Trace the microphone/transcription flow from recorder output into the chat composer state
  - [ ] Fix the handoff so completed recordings populate the message input field
  - [ ] Add regression coverage for microphone-to-input behavior in chat

*(Surfaced by user report in chat, 2026-04-27.)*



---

## Done

> Completed items are moved to `docs/completed-todos.md` periodically.
> Check off items with `- [x]` and leave them in place until the next cleanup.

- [x] TodoScope Alignment
  - [x] Restructure TODO.md to TodoScope conventions
  - [x] Fix duplicate rows in `.todoscope-exclude.csv`
  - [x] Run TodoScope scanner and verify kanban board matches expectations
