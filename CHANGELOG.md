# Changelog

All notable changes to [Sage.is AI-UI](https://github.com/Sage-is/AI-UI) are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Sage.is AI-UI ships under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.html).

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
