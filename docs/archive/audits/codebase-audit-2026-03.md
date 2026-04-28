---
title: "Codebase Audit Report"
description: "Audit findings on component structure, state management, and code redundancy from Codebase Audit — March 2026."
date: 2026-03-05
tags:
  - audit
  - architecture
  - technical-debt
  - review
---


# Codebase Audit — March 2026

Full-stack audit of the Sage.is AI-UIproject (excluding `submodules/`).

---

## Critical Findings (Fix Immediately)

| # | Issue | Location | Detail |
|---|-------|----------|--------|
| **C1** | Hardcoded JWT secret `"t0p-s3cr3t"` — if `WEBUI_SECRET_KEY` env var is unset, any attacker can forge tokens | `backend/open_webui/env.py:401-405` | Check on :426 only catches empty string, not the default |
| **C2** | `exec()` on user-provided Python code — admin tools/functions loaded via `exec(content, module.__dict__)` with no sandboxing | `backend/open_webui/utils/plugin.py:101,145` | Compromised admin = full RCE |
| **C3** | Arbitrary pip install via frontmatter — `subprocess.check_call([pip, install, ...])` with unsanitized package names | `backend/open_webui/utils/plugin.py:225-238` | Supply-chain attack vector |
| **C4** | docker-compose sets `WEBUI_SECRET_KEY=` (empty) — cascades to `"t0p-s3cr3t"` fallback | `docker-compositions/docker-compose.yaml:27` | Combined with C1 |

---

## High Severity

| # | Issue | Location |
|---|-------|----------|
| **H1** | Open redirect on auth page — `?redirect=` param used without same-origin validation | `src/routes/auth/+page.svelte:51,77,186` |
| **H2** | XSS via unsanitized SVG — `{@html svg}` with DOMPurify imported but never called | `src/lib/components/common/SVGPanZoom.svelte:53` |
| **H3** | SSRF via magic link webhook URL — admin-set `webhook_url` POSTed to with no allowlist | `backend/open_webui/routers/magic_links.py:352-368` |
| **H4** | Webhook signature bypass — WhatsApp/Telegram adapters return `True` when no secret configured | `bridges/adapters/whatsapp.py:216`, `telegram.py:205` |
| **H5** | Bridge API exposes secrets — `GET /bridges/` returns raw `config` dict with API keys, bot tokens, SMTP passwords | `backend/open_webui/routers/bridges.py:26-28` |
| **H6** | CORS `*` with credentials — default `CORS_ALLOW_ORIGIN="*"` + `allow_credentials=True` | `backend/open_webui/main.py:1143-1149` |
| **H7** | Docker defaults to root (UID=0) | `Dockerfile:23-24` |
| **H8** | No CI/CD — zero GitHub Actions workflows; no automated tests, scanning, or lint enforcement | `.github/` (missing workflows/) |
| **H9** | `python-jose==3.4.0` — unmaintained, CVE-2024-33663 (ECDSA bypass) and CVE-2024-33664 (DoS) | `app/pyproject.toml:15` |
| **H10** | Major version drift — `requirements.txt` vs `pyproject.toml` disagree on 17 package versions | Both files |
| **H11** | XSS via admin custom CSS — `{@html $config.ui.custom_css}` without sanitization | `src/routes/+layout.svelte:619` |

---

## Medium Severity

| # | Issue | Location |
|---|-------|----------|
| **M1** | Bridge messages bypass safety filters (`bypass_filter=True`) | `bridges/pipeline.py:158,304` |
| **M2** | No size limit on media downloads — OOM possible | `bridges/base.py:67-79` |
| **M3** | `_process_media()` downloads files but never stores them — media silently lost | `bridges/pipeline.py:462-485` |
| **M4** | Race condition in magic link redemption (use_count check not atomic) | `routers/magic_links.py:300-303` |
| **M5** | JWT tokens never expire by default (`JWT_EXPIRES_IN=-1`) | `config.py:292` |
| **M6** | Rate limiter is in-memory, doesn't work across multiple workers | `bridges/pipeline.py:27,493-506` |
| **M7** | `WEBUI_SESSION_COOKIE_SECURE` defaults to `false` | `env.py:410-412` |
| **M8** | Rclone config (with credentials) printed to container logs | `restore_backup_start.sh:47-49` |
| **M9** | `eval "$BACKUP_HOOK"` — arbitrary command execution via env var | `restore_backup_start.sh:139,194` |
| **M10** | 4 memory leaks from unsubscribed Svelte store `.subscribe()` calls | `Sidebar.svelte:447,465,484`, `Artifacts.svelte:198`, `Chat.svelte:504` |
| **M11** | 8 bare `except:` clauses (catches `SystemExit`, `KeyboardInterrupt`) | Various backend files |
| **M12** | Email adapter allows TLS `"none"` — credentials sent in plaintext | `bridges/adapters/email.py:327-331` |
| **M13** | Outgoing bridge has no loop prevention despite docstring claiming it | `bridges/outgoing.py:41-67` |
| **M14** | Dependabot targets branch `dev`, but project uses `develop` | `.github/dependabot.yml:7` |
| **M15** | `innerHTML` injection in notes PDF export via `note.title` | `src/lib/utils/notes.ts:42` |
| **M16** | No SvelteKit error hooks (`hooks.client.ts`/`hooks.server.ts`) | `src/` (missing) |
| **M17** | IMAP search injection via `subject_prefix` config value | `bridges/adapters/email.py:183-184` |
| **M18** | `TRUSTED_SIGNATURE_KEY` defaults to empty string | `env.py:115` |

---

## Low Severity

| # | Issue | Location |
|---|-------|----------|
| **L1** | 18 duplicated `api()` helper functions (~1000 lines of copy-paste) | `src/lib/apis/*/index.ts` |
| **L2** | 192 `any` type usages across 52 files | Various frontend files |
| **L3** | 416 `console.log` statements across 100 files | Various frontend files |
| **L4** | `sanitizeResponseContent` has dead regex on line 94 (runs after `<`/`>` already escaped) | `src/lib/utils/index.ts:87-96` |
| **L5** | Pyodide (~25MB WASM) imported eagerly at root layout level | `src/routes/+layout.svelte:4` |
| **L6** | Source maps enabled in production build | `app/vite.config.ts:47` |
| **L7** | 43 suppressed `a11y-*` warnings across 23 files | Various Svelte components |
| **L8** | Several overly large components (`Chat.svelte` 2,298 lines) | `src/lib/components/chat/Chat.svelte` |
| **L9** | `pytest` in production dependencies instead of dev-dependencies | `app/pyproject.toml:113-114` |
| **L10** | Auth page uses plain `<script>` instead of `<script lang="ts">` | `src/routes/auth/+page.svelte:1` |
| **L11** | Dead `chatIdUnsubscriber` variable — declared but never assigned | `Chat.svelte:116` |
| **L12** | `chats.subscribe(() => {})` — no-op subscription that leaks | `Chat.svelte:527` |
| **L13** | Timestamp inconsistency — bridges use `time_ns()`, magic links use `time()` | `models/bridges.py` vs `models/magic_links.py` |
| **L14** | No foreign key constraints on bridge tables | `models/bridges.py` |
| **L15** | Duplicate backend copy layer in Dockerfile (line 72 and 239) | `Dockerfile` |
| **L16** | Dead `getUserFriendlyErrorMessage()` function never called | `src/lib/apis/base.ts:152` |
| **L17** | Triplicated JSON response parsing logic (`generateTitle`, `generateFollowUps`, `generateTags`, `generateQueries`) | `src/lib/apis/index.ts` |
| **L18** | Unused CSS `.modal-content` class and `@keyframes scaleUp` | `src/lib/components/common/ConfirmDialog.svelte:168-183` |
| **L19** | Unused imports in root layout (`spring`, `onDestroy`, `getLanguages`, `WEBUI_HOSTNAME`) | `src/routes/+layout.svelte` |
| **L20** | `pytest` and `pytest-docker` in main dependencies, not dev-only | `app/pyproject.toml:113-114` |
| **L21** | Tailwind config variable misspelled: `containerQuries` → `containerQueries` | `app/tailwind.config.js:2` |

---

## Recommended Fix Priority

1. **C1/C4 — JWT secret**: Add startup check that refuses to run with default value when `WEBUI_AUTH=true`
2. **H1 — Open redirect**: Validate `redirect` param starts with `/` and not `//`
3. **H2 — SVG XSS**: Apply `DOMPurify.sanitize()` (already imported)
4. **H4 — Webhook bypass**: Make webhook secret required or log prominent warning
5. **H5 — Secret exposure**: Mask sensitive config fields in GET responses
6. **H8 — CI/CD**: Add lint, type-check, and test workflows
7. **H9 — python-jose**: Remove from `pyproject.toml` (already replaced by PyJWT in requirements.txt)
8. **H10 — Dep drift**: Reconcile `requirements.txt` and `pyproject.toml` to one source of truth
9. **M10 — Memory leaks**: Store unsubscribe functions; call in `onDestroy`
10. **M3 — Dead media code**: Implement file storage or remove
