---
title: "DRY/KISS Roadmap"
description: "Code deduplication, dependency cleanup, and architecture simplification plan."
date: 2026-02-24
tags:
  - roadmap
  - refactoring
  - dependencies
  - dry
  - kiss
---

# DRY/KISS Roadmap — 2026-02-24

Audit of code duplication, dead dependencies, and simplification opportunities across the Sage WebUI codebase.

---

## Phase 1: Dead Dependency Removal (Zero Risk)

Remove packages with zero imports in the codebase. No code changes needed — just delete from manifest files.

### Frontend (`package.json`) — 5 packages, ~680KB gzipped

| Package | Imports Found | Est. Size |
|---------|---------------|-----------|
| `async` | 0 | ~50KB |
| `chart.js` | 0 | ~300KB |
| `@floating-ui/dom` | 0 (bits-ui handles this) | ~30KB |
| `@mediapipe/tasks-vision` | 0 | ~200KB |
| `@pyscript/core` | 0 | ~100KB |

### Backend (`requirements.txt`) — 23 packages, ~1.1GB

| Package | Category | Est. Size |
|---------|----------|-----------|
| `pymongo` | DB driver | ~50MB |
| `pytube` | YouTube | ~5MB |
| `ddgs` | Search | ~10MB |
| `docx2txt` | Document processing | ~2MB |
| `unstructured` | Document processing | ~500MB |
| `pypdf` | PDF | ~20MB |
| `openpyxl` | Excel | ~30MB |
| `pyxlsb` | Excel binary | ~5MB |
| `xlrd` | Excel legacy | ~5MB |
| `RestrictedPython` | Sandboxing | ~5MB |
| `fake-useragent` | HTTP spoofing | ~2MB |
| `tencentcloud-sdk-python` | Tencent Cloud | ~200MB |
| `posthog` | Analytics | ~10MB |
| `langfuse` | Tracing | ~15MB |
| `argon2-cffi` | Hashing (passlib already used) | ~5MB |
| `APScheduler` | Scheduling | ~5MB |
| `nltk` | NLP | ~50MB |
| `rapidocr-onnxruntime` | OCR | ~100MB |
| `rank-bm25` | Ranking | ~2MB |
| `accelerate` | ML | ~100MB |
| `einops` | Tensors | ~5MB |
| `sentencepiece` | Tokenization | ~20MB |
| `PyMySQL` | DB driver (never imported) | ~5MB |

---

## Phase 2: Code DRY Refactoring (~376 lines saved)

Extract repeated patterns into shared helpers.

### P0 — Quick wins

| # | What | Where | Duped Lines | Savings |
|---|------|-------|-------------|---------|
| 1 | Extract `_build_mock_request()` helper | `bridges/pipeline.py:139-152, 285-298` | 28 | **12** |
| 2 | Extract `_extract_assistant_content()` helper | `bridges/pipeline.py:162-178, 307-323` | 34 | **15** |
| 3 | Move `github_url_to_raw_url()` to shared utils | `routers/tools.py:120-136, functions.py:63-79` | 34 | **17** |

### P1 — Router & model patterns

| # | What | Where | Duped Lines | Savings |
|---|------|-------|-------------|---------|
| 4 | Extract `filter_by_role()` helper | `routers/tools.py, prompts.py, knowledge.py` (6 instances) | ~100 | **~70** |
| 5 | Extract `get_or_404()` helper | All routers (7 instances) | ~35 | **~27** |

### P2 — Bridges architecture

| # | What | Where | Duped Lines | Savings |
|---|------|-------|-------------|---------|
| 6 | Abstract polling loop into `base.py` | `bridges/adapters/email.py, telegram.py` | ~62 | **~27** |
| 7 | Extract SSL connection helper | `bridges/adapters/email.py` | ~24 | **~10** |

### P3 — Frontend

| # | What | Where | Duped Lines | Savings |
|---|------|-------|-------------|---------|
| 8 | Use existing `Modal.svelte` in Bridges | `Bridges.svelte:316-553` | 238 | **~198** |

---

## Phase 3: Dependency Consolidation

Requires code changes but eliminates architectural duplication.

| Issue | Current State | Target | Savings |
|-------|---------------|--------|---------|
| Dual ORM | SQLAlchemy + Peewee (legacy migrations only) | Remove `peewee` + `peewee-migrate` after converting to Alembic | ~30MB + complexity |
| Triple HTTP client | `requests` (18 files) + `aiohttp` (17 files) + `httpx` (1 file) | Consolidate to `aiohttp` (already async-native for FastAPI) | ~15MB + consistency |

---

## Phase 4: Optional Extras (Future)

Move heavy single-purpose dependencies into install groups to slim the default image.

| Group | Packages | Size | Install Command |
|-------|----------|------|-----------------|
| Cloud: AWS | `boto3` | ~100MB | `pip install sage[aws]` |
| Cloud: Azure | `azure-identity`, `azure-storage-blob` | ~50MB | `pip install sage[azure]` |
| Cloud: GCP | `google-*` (4 packages) | ~80MB | `pip install sage[gcp]` |
| ML/Audio | `transformers`, `faster-whisper`, `sentence-transformers` | ~4GB | `pip install sage[ml]` |
| Vector DBs | `chromadb`, `qdrant-client`, `pinecone`, `pymilvus`, `opensearch-py` | ~200MB | `pip install sage[vectordb]` |

---

## Phase 5: Signal Bridge Adapter (New Feature)

Add Signal as the 4th messaging bridge, using [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) as a separate Docker container (same pattern as WAHA for WhatsApp).

### Architecture

```
[Signal users] <-> [signal-cli-rest-api :8081] <-> [Sage :8080]
                    separate Docker container       webhook/websocket
```

- signal-cli-rest-api runs in its own container (`bbernhard/signal-cli-rest-api`)
- Sage adapter connects via HTTP REST API (aiohttp) — no new Python dependencies
- Incoming messages via webhook (`RECEIVE_WEBHOOK_URL`) or WebSocket fallback
- Outgoing messages via `POST /v2/send`
- Attachments via base64 (send) and `GET /v1/attachments/{id}` (receive)

### Tasks

- [ ] Create `bridges/adapters/signal.py` — subclass `MessageBridge`, decorate with `@register_adapter("signal")`
- [ ] Implement webhook mode (primary) — `handle_webhook()` parses envelope JSON from signal-cli-rest-api
- [ ] Implement WebSocket mode (fallback) — background `asyncio.Task` connects to `ws://signal-api/v1/receive/{number}`
- [ ] Implement `send_message()` — `POST /v2/send` with text and base64 attachments
- [ ] Implement `download_media()` — `GET /v1/attachments/{id}`
- [ ] Implement `health_check()` — `GET /v1/about` or `GET /v1/accounts`
- [ ] Define `get_platform_info()` config schema (api_url, phone_number, receive_mode, webhook_url)
- [ ] Add import to `manager.py` (`_load_adapters()` + `get_available_platforms()`)
- [ ] Add Make targets for signal-cli-rest-api container lifecycle (done)
- [ ] Update `docs/bridges.md` with Quick Start (done)
- [ ] Test: webhook receive, websocket receive, send text, send attachment, groups

### Config Fields

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `api_url` | url | Yes | `http://localhost:8081` |
| `phone_number` | text | Yes | — |
| `receive_mode` | select | Yes | `webhook` |
| `webhook_url` | url | No | — |

### Notes

- No HMAC webhook verification — signal-cli-rest-api doesn't sign payloads. Secure via Docker network isolation.
- No new Python dependencies — uses aiohttp (already in the project)
- `Platform.SIGNAL` already exists in `types.py`
- Risk profile matches WAHA (unofficial third-party API wrapper)

---

## Summary

| Phase | Action | Impact | Risk |
|-------|--------|--------|------|
| 1 | Remove 28 dead dependencies | **~1.8GB** off install | None |
| 2 | Extract 8 helpers/patterns | **~376 lines** removed | Low |
| 3 | ORM + HTTP client consolidation | **~45MB** + cleaner arch | Medium |
| 4 | Optional extras split | **~4.5GB** off default | Medium |
