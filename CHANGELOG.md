# Changelog

All notable changes to [Sage.is AI-UI](https://github.com/Sage-is/AI-UI) are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Sage.is AI-UI ships under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.html).

---

## [2.3.2] — 2026-05-29

### Added

**UpdateInfoToast Carries Auto-Update Guidance**
When the in-app update toast fires it now tells the user how to apply the update for their install path — `ai-ui update --tag X.Y.Z` for brew, a redeploy click for CapRover, `docker pull` + `docker run` for self-host. Translations land for the new strings across the existing locale set, so the toast speaks the user's language instead of falling back to English.

### Fixed

**OAuth Provider Config Takes Effect Without a Restart**
Saving an OAuth client_id / client_secret in the admin panel required a container restart before the change was honored. Two bugs cooperated. `SessionMiddleware` only mounted at boot when `OAUTH_PROVIDERS` was non-empty, so a provider added later via the UI hit the callback with no session middleware and a generic 500. And `PersistentConfig` treated blank stored values as set, so an empty DB row blocked the env-var fallback. `SessionMiddleware` is now unconditional — the cookie cost is invisible on installs that never enable OAuth — blank stored values fall back to env defaults, and `OAuthManager.reload()` rebuilds the authlib registry from the live `OAUTH_PROVIDERS` dict so admins can add or swap providers from the UI without bouncing the container.

**OAuth Merge and Signup Toggles Visible in Admin Panel**
The OAuth Settings form gated `Merge Accounts by Email` and `Enable New Sign Ups` behind a `compact && adminConfig` check that only the setup wizard satisfied. The admin panel rendered the same component without `compact={true}` and the toggles vanished. Operators rediscovered them by re-running the wizard. The gate is now `{#if adminConfig}` so both surfaces render the same controls.

### Changed

**`OAUTH_MERGE_ACCOUNTS_BY_EMAIL` Defaults to `True` on Fresh Installs**
The default flipped from `False` to `True`. Workshop deployments and self-host single-admins almost always want OAuth identities auto-linked to the matching local account — the old default left first-time OAuth sign-ins blocked with an opaque 403. Existing installs keep their saved value through `PersistentConfig`; only fresh installs see the new default. The per-provider link-mode work tracked in the OAuth UX & Identity Linking TODO will eventually deprecate this global toggle in favor of `silent_merge_by_email` / `verify_via_magic_link` / `disabled` per provider.

**`WEBUI_SECRET_KEY` Now Persists Across Container Recreates**
The auto-generated secret key moved from `.webui_secret_key` in the container's working directory to `data/.webui_secret_key` in the persistent data volume. Previously a fresh container generated a new secret key and invalidated every existing JWT — sessions silently logged out after every `docker rm` + `docker run`. The key now survives container recreates as long as the data volume sticks around. Operators who want to inject their own key can still pass `WEBUI_SECRET_KEY` via run-time env, and the Makefile's `it_run` / `dev_run` recipes now forward it as `-e WEBUI_SECRET_KEY=<value>` automatically when set.

**Cross-Platform Build Notifications**
The Makefile's build-complete notification used `afplay` (macOS-only) which exited non-zero on Linux and Windows and broke build chains there. A portable `NOTIFY_DONE` macro wraps `terminal-notifier` on macOS, `notify-send` on Linux, and falls back to a no-op elsewhere. The build no longer fails when the notifier is missing.

**Makefile DX Pass**
`COMMON_RUN_ARGS` is factored out of three `docker run` recipes so a flag change lands in one place instead of three. `LOCAL_PORT` is now its own variable. `SAGE_HOSTS` guards block the try.sage targets when the host file is misconfigured, replacing a silent no-op with a loud error. The `|| true` that swallowed lint failures is removed — lint now stops the build instead of marching on with a stale image. New `_pin_server_tag` helper rewrites `SERVER_TAG` in the canonical `distribution.env` via a `cat tmp > target` pattern that preserves the hardlink chain inode across all three sibling repos.

**Auto-Pin `SERVER_TAG` in `distribution.env` After GHCR Push**
`release_and_push_GHCR` and `hotfix_and_push_GHCR` now write the released `IMAGE_TAG` into the canonical `distribution.env` once the multi-arch image is confirmed on GHCR, via the inode-preserving `_pin_server_tag` helper. The pin propagates instantly to the homebrew-apps tap and the Sage.Education docs sibling repos through the hardlink chain. Operators no longer run a separate pin step after release — `distribution.env` can only describe a `SERVER_TAG` that exists on GHCR.

### Security

**`.dockerignore` Adopts the Hidden-Artifact Allowlist Pattern**
The build context now denies all dotfiles and dotfolders by default (`.*` wildcard) and explicitly re-includes only the artifacts the image actually needs. Mirrors the repo-wide allowlist already in `.gitignore` and the contributor rule in `CONVENTION.instructions.md`. Closes the silent-leak path where a new `.env.local`, `.secrets/`, or `.aws/` at the repo root could ride into the image without anyone noticing.

---

## [2.3.1] — 2026-05-18

### Added

**Shared `distribution.env` Contract Across Three Repos**
Sage.is AI-UI, the homebrew-apps tap, and the Sage.Education docs now read canonical distribution facts — image, server tag, volume name, install command, CLI version — from a single hardlinked `distribution.env`. Edit once, three repos see it. The first Jidoka (自働化) primitive: drift across the three repos is mechanically impossible instead of a memory tax. Each repo's Makefile runs `distribution_verify` as a release gate; `distribution_sync` re-establishes the hardlink chain on a fresh clone.

**Automated Wizard Smoke (`scripts/wizard-smoke.sh`)**
End-to-end tester drives the AI Engine setup wizard via API on a clean container — signup → install trigger → embedding model download → import smoke → file upload → add-to-knowledge-base. Replaces the manual browser dance. Wired into `make wizard_smoke`. The smoke also doubles as the harness for the 2.4 bundle work.

**Convention: `test@example.com` / `zaq12wsx` is the Sage.is Automated Smoke User**
Canonical fixture for `wizard-smoke`, Selenium, ZAP DAST proxy runs, and any future automated harness. Documented in `CONVENTION.instructions.md`. Production deployments never create this user.

### Fixed

**Try.sage `/llm-status` Honors `ENABLE_TRY_SAGE=false`**
The admin-only `/api/v1/sage/runtime/llm-status` endpoint returns 404 when the trial-mode flag is off. The router-level gate ran in the wrong dependency order — auth fired before the env check, so the route leaked through with a 403 instead of disappearing. Same fix applied to `/extend` and `/reset`. The gate now sits ahead of the auth dependency for every trial-mode admin handler. Documented as a contract in `CONVENTION.instructions.md`.

**Unregistered `/api/*` Paths Return JSON 404**
Curl-driven smoke tests see proper 404s for missing backend routes. The SvelteKit static catch-all was serving `index.html` for any unmatched path, including `/api/*`, which masked router-registration bugs and broke automated checks. The SPA fall-through skips `/api/*` and returns a JSON 404 instead. Frontend routing for non-api paths is unchanged.

**ML Wizard No Longer Shadows System bcrypt and Breaks Login** *(transitional fix)*
The ML wizard installs framework packages — `bcrypt`, `uvicorn`, `click`, `anyio`, `pydantic` — into the data volume as transitive dependencies of `sentence-transformers`. Until now those packages loaded ahead of the system versions, so a freshly installed `bcrypt 5.0.0` shadowed the system `bcrypt 4.3.0` and broke password verification. Three changes restore the correct precedence: the wizard appends ml_packages to `sys.path` instead of inserting at the front (`app/backend/sage_is_ai/routers/retrieval.py`); the container loads ml_packages via `sitecustomize.py` after `site-packages` instead of via `PYTHONPATH` ahead of it (`Dockerfile`, `app/backend/start.sh`); and the install itself moves off raw `pip` onto `uv` driven by a hashed lockfile so the resolver cannot deliver a self-inconsistent set at wizard time.

**ML Wizard Switches to `uv` + Hashed Lockfile** *(transitional fix)*
The wizard previously ran two `pip install --target` passes — one for `torch`, one for `requirements-ml.txt` — and pip's silent `--target` collision left a stale `torch 2.1.2` next to a fresh `transformers 4.57.6` and `numpy 2.4.5`. The combination threw on import (`AttributeError: torch.utils._pytree has no register_pytree_node` and a NumPy 1.x/2.x ABI break). The fix swaps `pip` for `uv` (pinned at base-image build) driven by a hashed `requirements-ml.lock` generated once at edit time. `uv`'s resolver refuses self-inconsistent closures, so the failure mode moves from user wizard runs back to dev-host commits, where it belongs. torch comes from the PyTorch CPU index — no `nvidia-*` wheel chain dragged along.

**Base Image Pins `tokenizers`, `huggingface-hub`, `numpy` Inside transformers' Range**
The system site-packages picks up `tokenizers`, `huggingface-hub`, and `numpy` transitively from `chromadb` and `langchain-community`. Since `sitecustomize.py` keeps system ahead of ml_packages on `sys.path` (protecting bcrypt and friends), the system versions are the ones `transformers 4.57.6` imports at runtime. Pinning them to `<=0.23.0`, `<1.0`, and `<2` keeps the import-time version checks satisfied. Removable once the 2.4 bundle owns the full ML stack.

**This fix is transitional.** The structural fix is a signed per-arch × per-accel tarball bundle published on GitHub Releases, pulled into the container at wizard-activation time and verified against SHA256s declared in `distribution.env`. That work ships in **2.4** under the kaizen (改善) banner — and reuses the same `requirements-ml.lock` as its build input. Until then, ml_packages remains a runtime install, just a well-behaved one.

### Security

**Bump `langchain` to 0.3.30** (CVE-2026-45134 — HIGH)
LangSmith SDK public prompt pull deserialized untrusted manifests without a trust boundary warning. Fixed upstream in 0.3.30.

**Bump `python-multipart` to 0.0.27** (CVE-2026-42561 — HIGH)
Streaming parser issue pre-0.0.27. Bumped past the affected range.

### Changed

**Makefile: `try_sage_stop` Dropped, `try_sage_reset` Cleans Up Inline**
The standalone `try_sage_stop` target ran `docker rm` against a hardcoded container name that didn't match the brew CLI's name. Removed. `try_sage_reset` drops any stale trial container itself before rebuilding. Brew users continue with `ai-ui stop`.

**Makefile Reads `distribution.env` Defaults**
`VOLUME_DATA` and `IMAGE_TAG` defaults come from `distribution.env` when present. Explicit `make VAR=value` overrides still win.

**CUDA Path Temporarily Off in the Wizard** *(deferred to 2.4)*
The `USE_CUDA_DOCKER=true` branch is removed from `retrieval.py` for 2.3.1. The wizard installs CPU-only torch from the locked manifest regardless of the env flag. CUDA returns in **2.4** as one cell of the per-arch × per-accel bundle matrix, where it can be tested as a first-class artifact rather than an env-flag escape hatch. Users running CUDA today should hold on `:2.3.0` or watch the 2.4 release notes for the bundle URL.

### Docs

**Env-Gate Dependency-Order Contract**
`CONVENTION.instructions.md` documents the FastAPI ordering rule: env-gate `Depends()` must precede auth `Depends()` so a disabled feature looks like 404, not 403. Right and wrong patterns shown side by side. Reference: the `/llm-status` fix above.

---

## [2.3.0] — 2026-05-01

### Added

**ChromaDB Embedding Engine**
A ChromaDB-backed embedding engine joins the retrieval options. Pick it from Admin > Settings > Documents. The ONNX bundle persists to `/app/backend/data` so restarts skip the re-download.

**Try.sage Welcome Page**
Trial sessions open on a dedicated landing page. The page introduces the workshop, points to the persona picker, and sets expectations for the 24-hour reset cycle.

### Changed

**Mermaid Diagrams Render Bigger in Chat**
Mind maps, flowcharts, and sequence diagrams open at a readable size by default. The chat passes a `40vh` minimum height through to the SVG viewport. Pan, zoom, reset, and download still work.

**Sage Strawberry Knows Mind Maps**
The try.sage onboarding agent now answers mind-map requests with a fenced mermaid `mindmap` block. Other diagram requests get the matching grammar — `flowchart`, `sequenceDiagram`, `stateDiagram`. The agent nudges trial users toward live workshops and the Sage.is team when they want to go deeper.

**Try.sage Trial Polish**
Persona tutorials end with a try.sage.is reference so participants know where they are. Persona descriptions and trial-mode UI settings tighten up. Tutorial flow and persona switcher behave better on first run. Trial tool-server registration is more reliable across resets.

**Conversation Map Labels**
Node labels in the conversation map strip raw markdown markup before rendering. Branch names read cleanly.

**File Upload Disabled Message**
"Model(s) do not support file upload" rewritten to "File upload turned off" across all locales. Shorter, plainer.

**OAuth Callback Handling**
Sign-in callbacks handle edge cases more gracefully. Affects Google and GitHub OAuth flows added in 2.1.0.

**SVG and Icon Handling**
Internal refactor of SVG and icon imports. Lays groundwork for the diagram-rendering changes above. No user-facing change on its own.

### Fixed

**Documentation Typos**
Corrected typos and improved descriptions across documentation files.

---

## [2.2.0] — 2026-04-29

### Added

**Persona Magic Links**
Magic links now carry a persona. An operator hands out one URL before a workshop. The link drops the participant into a pre-configured account with the right tutorial, system prompt, and tool servers already wired up. No signup. No configuration step. The link works.

**Embedded Tutorials**
Tutorials ship inside the persona. Astropi AI Tutor, Sage Startr Style, and Sage Strawberry each open with their own walkthrough on first load. The tutorial knows what tools the persona has and what the participant should try first.

**Persona Switcher**
Participants switch between personas mid-session without losing the link. Useful for facilitators demoing more than one workshop track from the same browser.

**Stable Persona URLs Across Resets**
Account resets wipe chats and files but leave the persona link intact. Operators print URLs ahead of time and reuse them across sessions. Link TTL is 7 days by default and configurable via `TRY_SAGE_PERSONA_LINK_TTL_DAYS`.

**Trial Tool Server Registration**
Personas register their own tool servers on activation. Each tutorial gets the tools it expects without admin intervention.

---

## [2.1.0] — 2026-03-28

### Added

**OAuth Admin UI (Beta)**
Admins configure Google and GitHub OAuth from the setup wizard or Admin > Settings > Auth. Each provider section expands to show setup instructions, a direct link to the provider's developer console, and the correct callback URL for the deployment. Credentials save to the database and activate immediately — no restart required.

**Email Magic Link Login (Beta)**
Existing users sign in by clicking a link sent to their email. No password needed. Admin enables it and configures SMTP in Admin > Settings > Auth. A "Sign in with Email Link" button appears on the login page alongside any OAuth buttons.

**"Forgetting your password(s)?" hint**
The login page shows a help message below the password field when no OAuth providers are configured. A tooltip suggests the admin enable Google, GitHub, or LDAP sign-in.

**Developer Onboarding**
Added DeveloperStep component and DevMissionReminderModal for onboarding developers. Enhanced WelcomeStep with Developer Mode setup instructions. Implemented reminders for developers who signed up for the mission but remain in production mode.

**DEV_MODE Environment Variable**
Added DEV_MODE environment variable to toggle development features.

### Changed

**Setup Wizard**
Authentication is now the first optional step. The welcome screen offers four checkboxes: Authentication (Beta), Model Connections, Users, and Features. Admins choose what to configure; unchecked steps are skipped.

**CompleteStep Component**
Updated to reflect model download status and added polling for downloads.

**CI/CD Workflow**
Enhanced with fresh DB smoke test and detailed release process instructions.

**Feature Checkbox Handling**
Streamlined checkbox input handling for community sharing, message rating, notes, spaces, and webhooks.

**Authentication UI**
Updated button styles and translation text in magic link section.

**Makefile**
Enhanced multi-architecture build process and added GHCR login target. Added newline echo in it_clean target for better output readability.

**Backend Scripts**
Refactored backend startup script and enhanced model management.

**Component Layouts**
Updated various components to improve layout and user experience.

### Fixed

**Slideshow Image Paths**
Updated image paths to use static assets directory.

**Changelog Release Dates**
Corrected release dates for versions 2.0.0 and 1.0.0.

**Environment Handling**
Set default package version to "0.0.0" if not found. Updated latest release version retrieval from GitHub API.

**Docker Environment**
Suppressed onnxruntime warnings in Docker environments.

**Code Cleanup**
Removed unused DEV_MODE toggle and related setup code from Dockerfile. Removed unused downloadLiteLLMConfig API endpoint. Simplified .dockerignore and .gitignore by removing unnecessary exclusions. Removed unused downloadLiteLLMConfig import from Database.

**Translations**
Updated translations to replace "wherever you are" with "with Sage.is AI-UI" across multiple languages.

---

## [2.0.0] — 2026-03

### Added

**Spaces**
Multi-user rooms where people and AI agents talk in real time. @mention an agent to pull it into the conversation. If the agent's last message ended with a question, it responds to follow-ups without another @mention. Threads, reactions, and typing indicators work the way team chat should. Thinking indicators rotate through short status phrases while agents reason, so no one stares at static dots for ninety seconds.

**Space Member Management**
Admins and facilitators add or remove users from a Space through the three-dot menu. Access control is per-space, stored in `access_control.read.user_ids`. The existing `updateSpaceById` API already accepts these payloads. No backend changes needed.

**Messaging Bridges**
Users send messages to the AI from [WhatsApp](https://waha.devlike.pro/) (WAHA), [Telegram](https://core.telegram.org/bots/api) (Bot API), [Signal](https://github.com/bbernhard/signal-cli-rest-api) (signal-cli-rest-api), or Email (IMAP/SMTP). No new account. No new app. No new login. The same model, reachable from wherever the person already is. Admins configure each bridge from the admin panel. Credentials stay on the server. New adapters require no frontend changes.

**PDF Ingestion Modes**
Three modes for how PDFs enter the knowledge base: fast text extraction, structured page parsing, and AI-assisted parsing. A scanned court filing warrants different handling than a plain-text report. The mode is configurable per-deployment and per-request.

**AI Document Parsing**
Documents that resist clean extraction — mixed-layout PDFs, scanned images embedded in pages — pass through a model for structured interpretation before indexing. Output format is configurable.

**Knowledge Base**
Multi-collection document storage with per-collection embedding configuration. Documents link to specific knowledge bases and chat skills. Models draw on the right context for the right task.

**Home Dashboard**
Recent and pinned conversations appear at first load. Pinned conversations persist across sessions.

**Sidebar Search**
Global conversation search lives in the sidebar. The cursor enters the search field on open. One keystroke to search.

**Collapsible Sidebar Folders**
Folder and date-group expansion state is user-controlled. Fold and unfold controls are visible without hovering.

**[Setup Wizard](https://sage.is/docs/admin/setup-wizard)**
First-run configuration walks through connection setup ([Ollama](https://ollama.com/), OpenAI-compatible endpoints) with live verification. Admins see whether their API key or local model server is reachable before finishing setup.

**Chat Sharing**
Users share conversations with other users or groups. Shared chats appear under "Shared with me" and "Shared by me" in the sidebar.

**[Magic Links](https://sage.is/docs/admin/magic-links)**
Passwordless authentication via one-time links. Admins configure allowed email domains. Useful where managing passwords creates more friction than it removes.

**Note Editor**
Persistent notes with title management. Notes live alongside chats in the sidebar.

**[Security Scanning](https://sage.is/docs/dev/security-scanning)**
Provider-agnostic CI/CD scanning via Makefile targets. `make scan` runs [gitleaks](https://github.com/gitleaks/gitleaks) (secrets), [semgrep](https://semgrep.dev/) (JS/TS/Svelte SAST), [bandit](https://bandit.readthedocs.io/) (Python SAST), and [trivy](https://trivy.dev/) (dependency vulnerabilities). `make install_dev` installs all tools via [Homebrew](https://brew.sh/). Pre-commit hooks catch issues before they reach the repo. Runs on Linux, macOS, and Windows (WSL). No GitHub Actions. No vendor lock-in.

**DB Upgrade Smoke Test**
`make test_db_upgrade` boots the app against an archived database snapshot to verify that [Peewee](http://docs.peewee-orm.com/) and [Alembic](https://alembic.sqlalchemy.org/) migrations apply cleanly. The original snapshot is never mutated.

### Changed

**Package Identity: `open_webui` to `sage_is_ai`**
The backend Python package is renamed. Every import path, log line, environment variable prefix, and deployment artifact carries the project's own name. A fork that has diverged this far in architecture and purpose should say so in its namespace.

**"Channel" to "Space"**
The UI, API routes, and socket events now say "Space" instead of "Channel." The database schema still uses the old column names. Migration planned for v2.1.0.

**Dependency Security Upgrades**
Updated [authlib](https://authlib.org/), unstructured, [nltk](https://www.nltk.org/), python-multipart, [PyJWT](https://pyjwt.readthedocs.io/), [pillow](https://pillow.readthedocs.io/), [black](https://black.readthedocs.io/), [aiohttp](https://docs.aiohttp.org/), [langchain-community](https://python.langchain.com/), and [jspdf](https://rawgit.com/MrRio/jsPDF/master/docs/index.html) to patch known CVEs at CRITICAL and HIGH severity.

**Agent Thinking Timeout**
Thinking indicator timeout extended from 30 seconds to 2 minutes. Slower models no longer have their status silently cleared before they finish responding.

### Fixed

**Rich Text Editor State**
The rich text editor clears correctly when the prompt is set to an empty string. Switching Spaces no longer leaves stale content in the input.

**Space Participant Loading**
Participant loading for @mention autocomplete fails gracefully with a console warning instead of breaking the Space.

---

## [1.1.1] — 2025

### Added

**Branding Configuration**
Self-hosted deployments configure name, colors, logo, and visual identity through the admin panel. No fork required. No custom build. The configuration persists in the database and survives container rebuilds.

**Static File Injection**
The `SKIP_STATIC_CLEANUP` environment variable preserves custom static assets (favicons, fonts, injected CSS) across container rebuilds. The `STATIC_SRC` Makefile variable maps host directories into the container at build time.

**Theme Configuration**
The theme layer exposes [CSS custom properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties) at the root level. Color, spacing, and typographic decisions propagate from a single configuration point. Change one token, see it everywhere.

### Changed

**[Startr.Style](https://startr.style/) Migration**
Hardcoded color values removed from components across the frontend. Components reference CSS custom properties instead of literal values. A self-hoster who sets a primary color once does not need to hunt through component files to find where it was hardcoded.

**Makefile: Image Names from Git Remote**
Docker image names derive from the git remote URL. Deployment scripts stay consistent across forks and organizations without manual editing. `make it_build` builds the right image for whichever repo it runs from.

### Fixed

**Auth Flow: Spurious 403 Errors**
The auth page no longer triggers 403 errors during session validation. The errors were noise — they appeared in logs without indicating a real failure.

---

## [1.0.0] — 2025-04

### Added

**Granular Voice Permissions**
Admins enable or disable speech-to-text, text-to-speech, and tool-call voice features separately for each user group. An institution that allows transcription but not synthesis controls those independently.

**VAD Toggle for Whisper STT**
Voice Activity Detection for the built-in [Whisper](https://github.com/openai/whisper) engine can be disabled per deployment. Useful where VAD filtering introduces unwanted silence trimming in structured audio.

**Copy Formatted Responses**
Users enable copy-with-formatting in Settings > Interface. AI responses paste into documents with Markdown structure intact — headers, lists, code blocks, links. Plain-text copy remains the default.

### Fixed

**LDAP Authentication**
Resolved an attribute parsing failure that prevented login when optional LDAP attributes were absent or formatted outside expected parameters.

**Image Generation in Temporary Chats**
Visual outputs generate correctly in temporary sessions. Chat mode no longer restricts which capabilities are available.

---

*[Sage.is AI](https://sage.is) is built by [Startr LLC](https://startr.com). Licensed under [AGPL-3](https://www.gnu.org/licenses/agpl-3.0.html). Source at [github.com/Sage-is/AI-UI](https://github.com/Sage-is/AI-UI).*
