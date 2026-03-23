# Changelog

This file records what changed in Sage.is AI-UI. All notable changes to Sage.is AI-UI are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Sage.is AI-UI is released under the GNU Affero General Public License v3. Every change listed here belongs to anyone running the code.

---

## [Unreleased]

---

## [2.0.0] — 2026-03-23

### Added

**Spaces — Collaborative AI Rooms**
Multi-user rooms where people and AI agents interact in real time. @mention an agent to pull it into the conversation. Agents respond to follow-up questions without requiring another @mention when their last message ended with a question. Threads, reactions, and typing indicators work the way you'd expect from a team chat — except some of the participants are models. Thinking indicators rotate through playful status messages while agents work, because staring at static dots during a 90-second reasoning chain is no fun.

**Spaces: Member Management**
Admins and facilitators can add or remove users from a Space via the three-dot menu. Access control is per-space, stored in `access_control.read.user_ids`. No backend changes needed — the existing `updateSpaceById` API already accepts access control payloads.

**Messaging Bridges — WhatsApp, Telegram, Signal, Email**
Users can now send messages to the AI from whichever platform their conversations already happen on: WhatsApp via WAHA, Telegram via Bot API, Signal via signal-cli-rest-api, Email via IMAP/SMTP. No new account. No new app. No new login. The same model, reachable from wherever the person already is. Admins configure each bridge from the admin panel; credentials stay on the server, not in user configuration. New adapters require no frontend changes — the bridge architecture is extensible without touching the UI.

**PDF Ingestion Modes**
Three configurable modes for how PDF documents enter the knowledge base: fast text extraction, structured page parsing, and AI-assisted parsing. Institutions can match processing depth to document importance, for example a scanned court filing warrants different handling than a plain-text report. The mode is configurable per-deployment and per-request.

**AI Document Parsing**
AI-powered document parsing is now configurable with structured output options. Documents that resist clean extraction (mixed-layout PDFs, scanned images embedded in pages) can be passed through a model for structured interpretation before indexing.

**Knowledge Base**
Multi-collection document storage with per-collection embedding configuration. Documents can be assigned to specific knowledge bases and linked to chat skills, so models draw on the right context for the right task.

**Home Dashboard**
Recent and pinned conversations appear at first load. The interface surfaces what the user was working on without requiring them to navigate to find it. Pinned conversations persist across sessions.

**Sidebar Search**
Global conversation search is accessible from the sidebar. The cursor enters the search field immediately on open — one keystroke to search, not a click and then a keystroke. Search does not require a separate page or route.

**Collapsible Sidebar Folders and Date Groups**
Folder and date group expansion state is user-controlled. Large conversation histories stay organized without hiding content by default. Fold and unfold controls are visible without hovering.

**Setup Wizard**
First-run configuration walks through connection setup (Ollama, OpenAI-compatible endpoints) with live verification. Admins see whether their API key or local model server is reachable before finishing setup, not after.

**Chat Sharing**
Users can share conversations with other users or groups. Shared chats appear in "Shared with me" and "Shared by me" sidebar categories.

**Magic Links**
Passwordless authentication via one-time links. Admins can configure allowed email domains. Useful for deployments where managing passwords is more friction than it's worth.

**Note Editor**
Persistent notes with title management and save functionality. Notes live alongside chats in the sidebar.

**Security Scanning Framework**
Provider-agnostic CI/CD scanning via Makefile targets. `make scan` runs gitleaks (secrets), semgrep (JS/TS/Svelte SAST), bandit (Python SAST), and trivy (dependency vulnerabilities). `make install_dev` installs all tools via Homebrew. Pre-commit git hooks catch issues before they reach the repo. No GitHub Actions, no vendor lock-in — runs on Linux, macOS, and Windows (WSL).

**DB Upgrade Smoke Test**
`make test_db_upgrade` boots the app against an archived database snapshot to verify that Peewee and Alembic migrations apply cleanly. The original snapshot is never mutated.

### Changed

**Package Identity: `open_webui` → `sage_is_ai`**
The backend Python package is renamed from `open_webui` to `sage_is_ai`. Every import path, log line, environment variable prefix, and deployment artifact carries the software's own name. A fork that has diverged this far in architecture and purpose should say so in its namespace. We're Sage.is AI-UI, the AGPL tool that's forever open under the strongest of Copy Left policies.

**"Channel" → "Space"**
The UI, API routes, and socket events now use "Space" instead of "Channel". The database schema still uses the old names (migration planned for v2.1.0) — this is a cosmetic rename that doesn't touch stored data.

**Dependency Security Upgrades**
Updated authlib, unstructured, nltk, python-multipart, PyJWT, pillow, black, aiohttp, langchain-community, and jspdf to patch known CVEs (CRITICAL and HIGH severity).

**Agent Thinking Timeout**
Thinking indicator timeout extended from 30 seconds to 2 minutes. Slower models no longer have their "thinking" status silently cleared before they finish responding.

### Fixed

**Rich Text Editor State**
The rich text editor now clears correctly when the prompt is externally set to an empty string. Previously, switching Spaces could leave stale content in the input.

**Space Participant Loading**
Participant loading for @mention autocomplete now fails gracefully with a console warning instead of breaking the Space. A TODO marks this for user-facing error reporting in a future release.

---

## [1.1.1] — 2025

### Added

**Branding Configuration**
Self-hosted deployments can configure name, colors, logo, and visual identity through the admin panel. No fork required. No custom build required. No upstream divergence required. The configuration persists in the database and survives container rebuilds.

**Static File Injection**
The `SKIP_STATIC_CLEANUP` environment variable lets self-hosters preserve custom static assets (favicons, custom fonts, injected CSS) across container rebuilds. Branding assets survive updates. The `STATIC_SRC` Makefile variable maps host directories into the container at build time.

**Theme Configuration and CSS Variables**
The theme layer now exposes CSS custom properties at the root level. Color, spacing, and typographic decisions propagate from a single configuration point. Self-hosters adjusting one token see the change across the interface.

### Changed

**Startr.Style Migration**
Hardcoded color values have been removed from components throughout the frontend. Components now reference CSS custom properties rather than literal values. This is not a cosmetic change — it means a self-hoster who sets a primary color once does not need to hunt through component files to find where that color was hardcoded elsewhere!

**Makefile: Image Names from Git Remote**
Docker image names are now derived from the git remote URL rather than hardcoded. Deployment scripts stay consistent across forks and organizations without manual editing. `make it_build` builds the right image for whichever repository it is run from.

### Fixed

**Auth Flow: 403 Errors on Session Validation Removed**
The auth page no longer triggers spurious 403 errors during session validation. The errors were noise — they appeared in logs and monitoring systems without indicating a real failure. They no longer appear.

---

## [1.0.0] — 2025-04-28

### Added

**Granular Voice Permissions Per User Group**
Admins can separately enable or disable speech-to-text, text-to-speech, and tool call voice features for each user group. Voice access matches institutional policy without requiring separate deployments. An institution that allows transcription but not synthesis controls those independently.

**VAD Toggle for Whisper STT**
Voice Activity Detection for the built-in Whisper speech-to-text engine can be disabled per deployment. Useful for consistent transcription in structured-audio environments where VAD filtering introduces unwanted silence trimming.

**Copy Formatted Response Mode**
Users can enable copy-with-formatting in Settings > Interface. AI responses paste into documents with Markdown structure intact — headers, lists, code blocks, links. The alternative (stripping formatting on copy) remains available as the default for users who paste into plain-text contexts.

### Fixed

**LDAP Authentication**
Resolved an attribute parsing failure that prevented login in LDAP configurations where certain optional attributes were absent or formatted outside expected parameters. Enterprise identity providers now authenticate as configured.

**Image Generation in Temporary Chats**
Visual outputs now generate correctly in temporary chat sessions. The chat mode (temporary vs. persistent) no longer restricts which capabilities are available. Temporary sessions are now full-featured sessions that simply do not write to conversation history.

---

*Sage AI is a product of Startr LLC. Licensed under AGPL-3. Source available at [github.com/Sage-is/AI-UI](https://github.com/Sage-is/AI-UI). Full disclosure and transparency is a feature, not a bug.*
