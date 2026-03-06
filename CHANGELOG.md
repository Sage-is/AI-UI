# Changelog

This file records what changed in Sage.is AI-UI. Not what we did — what you can now do. Each entry names a capability that moved, a control that shifted, or a constraint that was removed. Implementation details belong in commit messages. This is a record of the software's relationship with the people running it.

All notable changes to Sage.is AI-UI are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Sage.is AI-UI is released under the GNU Affero General Public License v3. Every change listed here belongs to anyone running the code.

---

## [Unreleased]

### Added

**Messaging Bridges — WhatsApp, Telegram, Signal, Email**
Users can now send messages to the AI from whichever platform their conversations already happen on: WhatsApp via WAHA, Telegram via Bot API, Signal via signal-cli-rest-api, Email via IMAP/SMTP. No new account. No new app. No new login. The same model, reachable from wherever the person already is. Admins configure each bridge from the admin panel; credentials stay on the server, not in user configuration. New adapters require no frontend changes — the bridge architecture is extensible without touching the UI.

**PDF Ingestion Modes**
Three configurable modes for how PDF documents enter the knowledge base: fast text extraction, structured page parsing, and AI-assisted parsing. Institutions can match processing depth to document importance, for example a scanned court filing warrants different handling than a plain-text report. The mode is configurable per-deployment and per-request.

**AI Document Parsing**
AI-powered document parsing is now configurable with structured output options. Documents that resist clean extraction (mixed-layout PDFs, scanned images embedded in pages) can be passed through a model for structured interpretation before indexing.

**Home Dashboard**
Recent and pinned conversations appear at first load. The interface surfaces what the user was working on without requiring them to navigate to find it. Pinned conversations persist across sessions.

**Sidebar Search**
Global conversation search is accessible from the sidebar. The cursor enters the search field immediately on open — one keystroke to search, not a click and then a keystroke. Search does not require a separate page or route.

**Collapsible Sidebar Folders and Date Groups**
Folder and date group expansion state is user-controlled. Large conversation histories stay organized without hiding content by default. Fold and unfold controls are visible without hovering.

### Changed

**Package Identity: `open_webui` → `sage_is_ai`**
The backend Python package is being renamed from `open_webui` to `sage_is_ai`. Every import path, log line, environment variable prefix, and deployment artifact will carry the software's own name. A fork that has diverged this far in architecture and purpose should say so in its namespace. We're Sage.is AI-UI, the AGPL tool that's forever open under the strongest of Copy Left policies.

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
