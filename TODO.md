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

- [ ] **try.sage Manual Regression Testing**: (Alexander Somma + Izzy Plante) #critical — Phase A backend and Phase B frontend shipped 2026-04-27. Smoke before merge.
  - [ ] Run `make try_sage_start` in a clean checkout. Container boots and `/api/v1/sage/runtime/status` responds.
  - [ ] `GET /api/v1/sage/runtime/personas` returns 5 entries with non-empty `login_url` JWTs.
  - [ ] Open a persona magic link in incognito. Sign-in lands on the home route as the right user.
  - [x] Banner shows live countdown. Admin extend/reset CTAs work. Non-admin sees the info line.
  - [x] Persona switcher in the user menu lists all 5 personas. Click navigates as expected.
  - [ ] Persona switcher should be cleaned
  - [x] Tutorial modal opens on first persona sign-in. Steps render placeholder cards. Dismiss works.
  - [x] Admin → Settings → Trial Mode tab opens. "Reopen setup wizard" + "Replay tutorial" both fire.
  - [ ] `GET /api/v1/configs/connections` as admin does NOT list the hidden try.sage connection.
  - [ ] `GET /api/models` shows only the IDs in `TRY_SAGE_LLM_MODELS`. Chat completions against those models work.
  - [ ] `make try_sage_stop` cleanly removes the container.
  - [ ] Set `ENABLE_TRY_SAGE=false`. Confirm `/api/v1/sage/runtime/*` all 404.
  - [ ] File one bug per defect found against the list above.

- [ ] **try.sage Production Decisions**: (Alexander Somma + Izzy Plante) — Surfaced by Docker exploration. Block CapRover one-click rollout.
  - [ ] Decide where `TRY_SAGE_LLM_API_KEY` lives in production: plain env, Docker secret mount, or external vault. Recommend Docker secret for try.sage.is itself, plain env for self-hosted workshops.
    - [ ] note:As we use cap rover and the system injects env vars we're leaning this way
  - [ ] Decide whether to publish a `:latest-try-sage` image tag or stick to one tag stream gated by env var.
  - [ ] Decide whether trial deployments use a separate named volume (`sage-try-data`) to keep production state clean. Recommend yes.
  - [ ] Land the runtime-variant approach (one image, env-gated) per `docs/try-sage-docker-exploration.md`.
  - [ ] Add the dummy-tools server question to the same review: keep, remove, or replace with real preview capability (web search, sandboxed runner).

- [ ] **try.sage Tutorial Video Production**: (Alexander Somma + Izzy Plante) — Content work, not code.
  - [ ] Pick individual videos from the [working playlist](https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u) for each of the 6 default tutorial steps.
  - [ ] Populate `TRY_SAGE_TUTORIAL_STEPS_JSON` per workshop deployment with the chosen URLs and step descriptions.
  - [ ] Publish the Bialik Sage tutorial content package: three short videos plus a follow-up email with system prompts.
  - [ ] Keep system-prompt disclosure only in the dedicated system-prompt video. Swap that one video per team session without a codebase release.

- [ ] **try.sage Runtime and Admin Controls**: (Alexander Somma + Izzy Plante) — Shipped Phase A 2026-04-27. Pending regression sign-off.
  - [x] Gate try.sage.is ai behind env vars
  - [x] Seed default try.sage agents: Sage Strawberry, Sage Startr.Style, AstroPi AI tutor (with KBs)
  - [x] Register `https://markdown-search.production.openco.ca` in `TOOL_SERVER_CONNECTIONS`
  - [x] Add a dummy-tools server with placeholder endpoints (revisit later — see Production Decisions)
  - [x] Trial helper endpoints: status, personas, limits, llm-status, extend, reset
  - [x] Auto-reset every 24h via env-configurable settings; selective wipe preserves persona accounts and KBs
  - [x] Admin-only extend (capped at one extension per window) and force-reset
  - [x] RBAC via existing `get_admin_user` dependency on protected endpoints
  - [x] Hidden OpenAI-compatible LLM connection (memory-only, never persisted, never echoed in any response)
  - [x] Model allowlist via `TRY_SAGE_LLM_MODELS`
  - [x] Document env vars, reset semantics, admin controls in `docs/try-sage-deployment.md`
  - [x] Makefile targets `try_sage_start` / `try_sage_stop`

- [ ] **try.sage.is Experience and Insights**: (Alexander Somma + Izzy Plante) — Shipped Phase B 2026-04-27. Pending regression sign-off.
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

- [ ] **Auto Reset Mode (Trial Environments)**: Mostly delivered by try.sage. Two gaps remain — see subitems. Reference: `docs/try-sage-deployment.md`.
  - [x] Env vars for reset enablement and interval — `ENABLE_TRY_SAGE`, `TRY_SAGE_RESET_INTERVAL_HOURS`
  - [x] Lifespan task fires the reset selectively (chats + files only; KBs and accounts persist)
  - [x] Banner countdown + pre-reset warning state (blue → amber when `hours_until_reset < 1`)
  - [x] Admin extend/reset endpoints with audit log lines
  - [ ] **Post-reset confirmation messaging** — when the auto-reset fires, signed-in users currently see no signal. Add a one-shot toast or banner state: "Trial reset complete — chats and uploads cleared." Drive it from a `try_sage.last_reset_at` timestamp the frontend compares against `localStorage.try_sage_last_seen_reset`.
  - [ ] **Tests for reset timing and message visibility** — pytest spec for `periodic_try_sage_reset` (mock the clock, assert selective wipe runs at the right tick); Vitest spec for `TrySageBanner` countdown formatting and color-shift threshold.

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
