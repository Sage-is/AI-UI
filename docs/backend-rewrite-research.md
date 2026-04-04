# Backend Rewrite Research: From Python to Go or Rust

> **Status:** Research document for team review.
> **Location:** `docs/backend-rewrite-research.md`
> **Next step:** Review with team, then decide on Phase -1 (contract test suite).

---

## Why This Matters

The current backend is a 53,000-line Python application. It works, but it carries years of accumulated complexity: two different database libraries running side by side (SQLAlchemy and Peewee), 104 Python dependencies, a three-stage Docker build that produces a 1.5 GB image, and a startup sequence that loads machine learning models before serving a single request.

A rewrite in a compiled language would cut that image to roughly 20 MB and produce a binary that starts in milliseconds rather than seconds. A rewrite in Django would clean up the architecture while keeping the Python ecosystem. The question is which path best fits this team.

**PostgreSQL is not in use.** The app defaults to SQLite (`sqlite:///data/webui.db`) and no `DATABASE_URL` is set in the project's `.env`.[^1] PostgreSQL support exists in the codebase — including dialect-aware raw SQL in the chat search module[^2] — but it is not active. The `webui.db` snapshot used for migration smoke tests is the live database format. The `psycopg2-binary` and `pgvector` packages are always installed in the Docker image but only used when explicitly configured.[^3]

**pgvector is separate.** The RAG vector store optionally connects to a PostgreSQL instance via `PGVECTOR_DB_URL`, independent of the main application database.[^4] This means the main schema is clean SQLite, but the retrieval pipeline has an optional PostgreSQL dependency that would stay in any Python microservice.

---

## What the Backend Actually Does

The Python backend splits into two kinds of work. That split is the key to planning any migration.

The first kind is **data management**: storing and retrieving users, chat histories, files, notes, prompts, and knowledge bases. This is standard web-application work — authentication, database reads and writes, file uploads. It accounts for roughly 15 of the 27 routers and all 21 database models. It is well-understood, well-tooled, and the easiest part to replace.

The second kind is **AI proxying and pipelines**: forwarding streaming requests to Ollama and OpenAI APIs, running retrieval-augmented generation (RAG) pipelines with LangChain and vector databases, transcribing audio, generating images, and executing user-defined Python functions in a sandboxed environment. This work accounts for roughly 12 routers and 15,000 lines of code. It is deeply tied to the Python ecosystem. There is no Go or Rust equivalent for LangChain, and rewriting it from scratch would take months.

Any migration plan that ignores this split will fail.

---

## Option G1: Go and PocketBase

PocketBase is an open-source Go framework that bundles a SQLite database, an automatically generated REST API, built-in authentication (email/password, OAuth2, magic links), file storage, a real-time event system via Server-Sent Events, and an admin interface — all in a single ~20 MB binary.[^5] The admin UI is a pre-built SvelteKit SPA compiled into the binary via Go's `embed` package; no separate build step is required.[^6] PocketBase is built on the Echo HTTP framework,[^7] and custom Go routes have full access to the underlying `http.ResponseWriter`, enabling SSE streaming for LLM proxy endpoints.[^8]

PocketBase is currently at **v0.25.x and has not reached v1.0.**[^9] This means the API can change between minor versions. Teams should pin the version and expect some churn.

For this project, PocketBase handles everything in the data management category with almost no custom code. The 21 SQLAlchemy models become PocketBase collections. The Alembic migration system is replaced by PocketBase's own versioned schema management. Authentication, which currently spans 1,381 lines of Python, is reduced to configuration.

**Important caveat:** PocketBase creates and manages its own SQLite schema. It does not read an arbitrary existing SQLite database.[^10] The existing `webui.db` file cannot be opened directly by PocketBase. A data migration step — exporting rows from the current schema and importing them into PocketBase collections — is required. This is not a blocker, but it is not free.

The AI proxy layer is straightforward in Go — Ollama and OpenAI proxying is pure HTTP with SSE streaming, and Go handles it well. Audio and image endpoints are also simple HTTP calls to external services. The hard cases are RAG, collaborative document editing (Y.js), and custom Python function execution. These should remain in a slimmed-down Python microservice.

The result is a two-process system: a Go binary handling authentication, data, and AI proxying; and a small Python service handling retrieval and function execution. The Docker image shrinks from 1.5 GB to under 100 MB.

---

## Option R1: Rust and Loco

Loco is a Rust web framework modeled after Ruby on Rails.[^11] It runs on Axum (Tokio-based, high-performance HTTP), uses SeaORM for database access, and includes a CLI that generates models, migrations, and controllers. Its "SaaS" starter ships with JWT-based authentication including registration, login, email verification, and password reset, using bcrypt for password hashing.[^12]

Loco is currently at approximately **v0.13.x and is pre-v1.0.**[^13] The project describes itself as suitable for "side projects and startups."[^14] Breaking API changes can still occur between minor versions.

Loco does not include an admin interface or a built-in real-time event system. SSE streaming works natively through the underlying Axum HTTP layer. A team comfortable with Rust could have a working spike in three days. A team new to Rust should not start here.

---

## Option R2: Rust and Axum with SQLx

Axum with SQLx is the lowest-level option: maximum control, maximum boilerplate. SQLx checks SQL queries at compile time, catching schema mismatches before the application ships.[^15] The tradeoff is that every feature PocketBase and Loco provide for free must be written by hand. This approach makes sense for teams that want to own every decision and have the time to make them. Axum consistently ranks among the highest-throughput frameworks in TechEmpower benchmarks.[^16]

---

## Option R3: Rust and SurrealDB

SurrealDB is a Rust-native multi-model database (SQL, graph, and document) that can run embedded in a Rust application using a RocksDB-backed storage engine.[^17] It includes built-in authentication, real-time WebSocket subscriptions, and a REST API. Its query language, SurrealQL, is non-standard.

SurrealDB reached **v2.0 in late 2024**, which represented a stability milestone. However, there were breaking changes to SurrealQL and the storage engine between v1.x and v2.0. Community reports of data durability issues in earlier versions exist.[^18] The project is younger than SQLite or PostgreSQL and has fewer production war stories.

---

## Option P1: Python and Django

Django is the other direction entirely: stay in Python, fix the architecture. Rewrite the FastAPI monolith as a Django application using Django REST Framework for the API. Django's ORM replaces the current SQLAlchemy + Peewee dual-ORM tangle. Django's migration system replaces both Alembic and Peewee-migrate.

The biggest advantage is that there is no language change. The team already knows Python. LangChain, Whisper, vector databases, and custom function execution stay in the same codebase — no separate Python microservice needed. The transition is architectural, not linguistic.

Django **supports streaming HTTP responses natively under ASGI** via `StreamingHttpResponse` with async generator views, available since Django 4.2.[^19] Running under an ASGI server (Uvicorn, Daphne, Hypercorn), an async view can yield SSE chunks for LLM proxy streaming without Django Channels. Channels is only needed for full-duplex WebSocket communication (collaborative editing, presence).[^20]

The current stable version is **Django 5.1.x**, with Django 5.2 LTS approaching release.[^21]

The Django admin is a genuine asset: one of the most capable auto-generated admin interfaces in any framework. It would serve the super-admin / technical-admin role while the existing Svelte admin panel handles the product-level interface.

The biggest disadvantage is that the Docker image stays large (~800 MB), startup time stays slow (3–8 seconds), and throughput is roughly 10–50x lower than Go or Rust for CRUD-heavy work, per TechEmpower benchmarks.[^22]

---

## Options at a Glance

| | Go + PocketBase | Rust + Loco | Rust + Axum + SQLx | Rust + SurrealDB | Python + Django |
|---|---|---|---|---|---|
| **Binary / image size** | ~20 MB | ~15 MB | ~10 MB | ~30 MB | ~800 MB |
| **Startup time** | ~50 ms | ~15 ms | ~10 ms | ~80 ms | ~3–8 s |
| **CRUD throughput**[^22] | ~30k req/s | ~60k req/s | ~80k req/s | ~25k req/s | ~3k req/s |
| **LLM streaming proxy** | SSE via Echo | SSE via Axum | SSE via Axum | SSE via Axum/WS | ASGI StreamingHttpResponse |
| **Built-in admin UI** | Yes (super-admin) | No | No | No | Yes (very capable) |
| **Built-in auth** | Yes | JWT scaffold | No | Yes | Yes (full) |
| **Built-in migrations** | Yes | Yes (SeaORM) | Yes (compile-time) | Yes | Yes (Django ORM) |
| **Realtime / SSE** | Built-in SSE | Axum SSE | Axum SSE | WebSocket built-in | Django Channels (WS) |
| **Database** | SQLite (own schema) | SQLite / Postgres | SQLite / Postgres | SurrealDB (embedded) | SQLite / Postgres |
| **Reads existing webui.db** | No — migration needed | Via SQLx | Via SQLx | No — migration needed | Direct (Django ORM) |
| **RAG / ML libraries** | Python microservice | Python microservice | Python microservice | Python microservice | Native (same image) |
| **Framework maturity** | Pre-v1.0 | Pre-v1.0 | Production (Tokio) | v2.0, young | Very mature (v5.1) |
| **Time to working spike** | 1–2 days | 3 days | 5 days | 3 days | 1–2 days |
| **Language change** | Yes (Go) | Yes (Rust) | Yes (Rust) | Yes (Rust) | No |
| **Team skill required** | Go | Rust | Rust | Rust + SurrealQL | Python (already have it) |

*Throughput figures are approximate from TechEmpower Round 22 JSON benchmarks. LLM proxy performance is network-bound in all cases.*

---

## Recommendation

Start with Go and PocketBase. It is the fastest path to a working system with the smallest footprint, the admin interface is included, and the Go ecosystem handles every part of the AI proxy layer without friction. The pre-v1.0 status is a risk that should be acknowledged and pinned.

If the team has strong Rust expertise, Loco is the next best option — but plan for a longer spike and more boilerplate.

Django deserves serious consideration if the team values architectural cleanup over deployment size. It is the only option that keeps everything — including RAG — in a single process with no microservice split. The tradeoff is that the Docker image stays large and throughput stays low.

The Python microservice (in the Go/Rust options) is not a compromise. Keeping RAG and function execution in Python is the correct decision. Those features depend on a mature ecosystem that does not exist in Go or Rust. Forcing a rewrite of LangChain is a distraction from the real goal: a simpler, faster, smaller backend for everything else.

---

## Risks

The most significant risk is the configuration system. The current `config.py` is 3,172 lines and maps over 200 environment variables to runtime behavior.[^1] Every variable must be accounted for in the new system, or features will silently break in production.

The second risk is the API contract. The Svelte frontend makes calls to 30 separate API modules. Every endpoint path, request shape, and response format must match exactly, or the frontend breaks.

The third risk is the Y.js collaborative editing protocol. PocketBase's real-time system uses Server-Sent Events, not the WebSocket-based Y.js sync protocol. Whether they can be reconciled, or whether the Python service must remain responsible for collaboration, should be resolved before any cutover.

The fourth risk is PocketBase's schema ownership. The existing `webui.db` cannot be read directly by PocketBase.[^10] Data migration tooling must be written and tested against the production snapshot.

---

## A Realistic Migration Path

**This is a planning document for team review. None of the phases below should begin until the team has signed off.**

### Phase -1 — Contract Test Suite (prerequisite for everything else)

Before rewriting a single line of the backend, the team must have a test suite that defines what the backend is supposed to do. Without it, there is no way to know whether the rewrite is correct. With it, the migration becomes largely mechanical: run the tests against the Python backend, then run them against the new backend, and compare.

FastAPI generates an OpenAPI specification at runtime (`/api/openapi.json`). That specification is the contract. The test suite can be generated from it automatically using tools like **Schemathesis** (property-based API testing from OpenAPI specs) or **Dredd** (contract testing). The result is a suite of HTTP tests that exercise every endpoint with valid and invalid inputs, verify response shapes, and check status codes — all without writing tests by hand.

The test suite should live in a **private Git submodule** — separate from this repo, not shipped in the Docker image, and accessible only to the team. This keeps proprietary test fixtures, credentials, and edge-case scenarios out of the public codebase while still allowing the suite to be pinned to a specific commit alongside the main repo.

Streaming endpoints (Ollama and OpenAI proxies) and WebSocket events cannot be covered by OpenAPI-generated tests. Those require targeted integration tests written by hand. They are the highest-risk endpoints in any migration.

### Phase 0 — Spike (one to two weeks)

Stand up the chosen framework with the core collections. Write a route that proxies a streaming Ollama chat completion. Confirm that the real-time system can replace Socket.io events. If streaming and real-time both work cleanly, proceed. If not, revisit.

### Phase 1 — Data layer (three to four weeks)

Define the full schema. Write the data migration tooling (export from `webui.db`, import into the new schema). Port authentication. Run the Svelte frontend against the new backend and confirm the API contract holds.

### Phase 2 — AI proxy layer (two to three weeks)

Port Ollama and OpenAI proxy routes with streaming, audio endpoints, and image generation endpoints. All HTTP-in, HTTP-out with no ML logic.

### Phase 3 — Python microservice (parallel with Phase 2)

Extract RAG, retrieval, and custom function execution into a standalone FastAPI service. This becomes a small, focused dependency rather than the entire backend.

### Phase 4 — Real-time and collaborative editing

Evaluate whether the new real-time system can replace Y.js, or whether the Python service must continue to handle it.

### Phase 5 — Cutover

Ship the new binary plus slim Python microservice. Run the database upgrade smoke test. Deploy to staging CapRover, run regression tests, then promote to production.

---

## What We Get When It Works

The Docker image drops from 1.5 GB to under 100 MB. The database stays SQLite — nothing changes there. The backend starts in under 100 milliseconds. CapRover deployments become faster and simpler.

The current Svelte admin panel stays. It is a product interface built for the people running AI workloads — model management, user administration, knowledge bases, configuration. The new backend's admin UI (PocketBase or Django) serves a different audience: developers and infrastructure operators who need direct database access, schema inspection, and low-level record editing. A super-admin backstage, not a replacement for the product interface.

The codebase that was 53,000 lines of Python becomes a fraction of that size, in a language that catches more errors at compile time — or, in the Django case, a cleaner, better-organized Python codebase that eliminates the dual-ORM problem.

---

## Implementation Steps

1. Save this document to `docs/backend-rewrite-research.md`
2. Add to `TODO.md` under `v3.0 — Future`:
   ```
   ### Backend Rewrite Research
   - [ ] Review docs/backend-rewrite-research.md with team
   - [ ] Phase -1: Generate contract test suite from OpenAPI spec (private submodule)
   - [ ] Phase 0 spike: chosen framework + streaming Ollama proxy
   - [ ] Team decision: Go + PocketBase, Rust + Loco, or Python + Django?
   ```

## Critical Files Before Starting

- `app/backend/sage_is_ai/config.py` (3,172 lines) — every environment variable and its default
- `app/backend/sage_is_ai/main.py` (1,970 lines) — middleware stack and router mounting
- `app/backend/sage_is_ai/routers/auths.py` (1,381 lines) — full authentication contract
- `app/backend/sage_is_ai/routers/ollama.py` (1,847 lines) — streaming proxy pattern to validate
- `app/src/lib/apis/` — 30 TypeScript modules defining the complete frontend API contract

---

## Sources

### Codebase references

[^1]: [`app/backend/sage_is_ai/env.py:318`](../app/backend/sage_is_ai/env.py) — `DATABASE_URL` defaults to `sqlite:///{DATA_DIR}/webui.db`
[^2]: [`app/backend/sage_is_ai/models/chats.py:640–737`](../app/backend/sage_is_ai/models/chats.py) — dialect-aware raw SQL with separate SQLite (`json_each`) and PostgreSQL (`json_array_elements`) code paths
[^3]: [`app/backend/requirements.txt:25–26`](../app/backend/requirements.txt) — `psycopg2-binary==2.9.9` and `pgvector==0.4.0` installed unconditionally
[^4]: [`app/backend/sage_is_ai/retrieval/vector/dbs/pgvector.py:82–103`](../app/backend/sage_is_ai/retrieval/vector/dbs/pgvector.py) — separate `PGVECTOR_DB_URL` connection, falls back to main DB URL

### PocketBase

[^5]: [PocketBase — Introduction](https://pocketbase.io/docs/)
[^6]: [PocketBase — Going to Production](https://pocketbase.io/docs/going-to-production/)
[^7]: [PocketBase — Custom Go Routes](https://pocketbase.io/docs/go-routing/)
[^8]: [PocketBase — Realtime API](https://pocketbase.io/docs/realtime/)
[^9]: [PocketBase — GitHub Releases](https://github.com/pocketbase/pocketbase/releases)
[^10]: [PocketBase — Dao / Database](https://pocketbase.io/docs/go-database/) — PocketBase creates and manages its own SQLite schema; existing databases require data migration

### Loco (Rust)

[^11]: [Loco — website](https://loco.rs/)
[^12]: [Loco — Starters / Authentication](https://loco.rs/docs/getting-started/starters/)
[^13]: [Loco — crates.io](https://crates.io/crates/loco-rs)
[^14]: [Loco — Getting Started](https://loco.rs/docs/getting-started/guide/)

### Axum / SQLx (Rust)

[^15]: [SQLx — crates.io](https://crates.io/crates/sqlx)
[^16]: [TechEmpower Framework Benchmarks — Round 22 JSON serialization](https://www.techempower.com/benchmarks/#hw=ph&test=json&section=data-r22)

### SurrealDB (Rust)

[^17]: [SurrealDB — Rust SDK / Embedding](https://surrealdb.com/docs/sdk/rust)
[^18]: [SurrealDB — GitHub Releases](https://github.com/surrealdb/surrealdb/releases) and [SurrealDB — v2.0 release blog](https://surrealdb.com/blog)

### Django (Python)

[^19]: [Django — StreamingHttpResponse](https://docs.djangoproject.com/en/5.1/ref/request-response/#streaminghttpresponse-objects)
[^20]: [Django — Async views](https://docs.djangoproject.com/en/5.1/topics/async/)
[^21]: [Django — Downloads](https://www.djangoproject.com/download/)

### Benchmarks

[^22]: [TechEmpower Framework Benchmarks — methodology and results](https://github.com/TechEmpower/FrameworkBenchmarks)
