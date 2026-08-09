# Sprig™ capabilities

What each capability is, what grafting one changes, and what it takes to add another.

The inventory below is **emitted from the code** by
`scripts/gates/sprig-capabilities/generate.py` and gated by
`make sprig_capabilities_check`. Editing it by hand accomplishes nothing; the
next run overwrites it and the gate fails until someone regenerates. Everything
under [Adding a capability](#adding-a-capability) is prose and is maintained by
hand.

Why it is generated: `BONSAI/sprig-spec/IMPLEMENTATION.md` records eleven
divergences between the drafted spec and the shipped subsystem, and one of them
is this document's subject — the draft reserves `whisper-` for speech-to-text
while the code ships `stt`, and six live capabilities appear nowhere in it. The
one section of that spec which matches the code exactly is Theme Sprigs™, and
the reason is recorded in the same file: it was written *from* the
implementation. This is that, mechanised.

The spec gets a fold, not a copy. `make sprig_capabilities_publish` splices a
**vocabulary view** into `sprig-spec/v1.md` — which reserved prefixes ship,
which shipped names are unreserved, which reservations are still empty — and
nothing else. Prune gaps and config field names are implementation status and
stay here. Both sides of that comparison are derived: the reserved prefixes are
read out of `v1.md` itself, so reserving a prefix there corrects the delta on
the next publish with nothing to maintain by hand in either repo.

<!-- BEGIN GENERATED — edits here are overwritten by `make sprig_capabilities` -->

Derived from `app/backend/sage_is_ai/sprigs/supervisor.py`, `app/backend/sage_is_ai/routers/sprigs.py`, and `sprigs/*_dispatch.py`.

**16 capabilities, 21 catalog entries.**

## What each capability does

| Capability | Entries | Changes on graft | Survives restart | Reverses on prune |
|---|---|---|---|---|
| `backup` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |
| `browser-ml` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |
| `calendar` | 1 | nothing — the capability is enabled, then wired | n/a — no process | n/a — nothing to reverse |
| `code` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |
| `dev` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |
| `docling` | 1 | `CONTENT_EXTRACTION_ENGINE`, `DOCLING_SERVER_URL` | yes | **no** |
| `embedding` | 5 | `RAG_EMBEDDING_ENGINE`, `RAG_EMBEDDING_MODEL`, `RAG_OPENAI_API_BASE_URL`, `RAG_OPENAI_API_KEY` | yes | yes |
| `export` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |
| `media` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |
| `rag` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |
| `reranker` | 1 | `RAG_EXTERNAL_RERANKER_API_KEY`, `RAG_EXTERNAL_RERANKER_URL`, `RAG_RERANKING_ENGINE`, `RAG_RERANKING_MODEL` | yes | yes |
| `stt` | 1 | `STT_ENGINE`, `STT_MODEL`, `STT_OPENAI_API_BASE_URL`, `STT_OPENAI_API_KEY` | yes | yes |
| `theme` | 2 | `SPRIG_ACTIVE_THEME` | n/a — no process | yes |
| `tika` | 1 | `CONTENT_EXTRACTION_ENGINE`, `TIKA_SERVER_URL` | yes | **no** |
| `ui` | 1 | `SPRIG_ACTIVE_UI` | n/a — no process | yes |
| `vector` | 1 | nothing — delivery only | n/a — no process | n/a — nothing to reverse |

*Survives restart* means the capability re-dispatches in `SprigSupervisor._reconcile`. Without it a respawned child gets a fresh loopback port and the config still names the old one. Capabilities that run no process are marked n/a: `_reconcile` gates its dispatch on `handle.process is not None`, and they rely on the persisted config pointer instead, which does not move.

*Reverses on prune* means `prune_sprig` resets what the graft changed. Without it the config keeps pointing at a released port.

## Gaps

- `docling` writes `CONTENT_EXTRACTION_ENGINE`, `DOCLING_SERVER_URL` on graft and reverses nothing on prune. After pruning, those values point at a released port.
- `tika` writes `CONTENT_EXTRACTION_ENGINE`, `TIKA_SERVER_URL` on graft and reverses nothing on prune. After pruning, those values point at a released port.

## Capabilities in detail

### `backup`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `backup-rclone` | `deliver` | oci-artifact | amd64, arm64 | `rclone (cloud backup)` | `/health` |

### `browser-ml`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `browser-ml` | `deliver` | oci-artifact | neutral | `onnxruntime-web wasm (in-browser ML)` | `/health` |

### `calendar`

No dispatch module and nothing to deliver. The code ships in the image; grafting makes the capability available so it can be wired.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `calendar` | `none` | built in | neutral | `iCalendar feeds` | n/a — nothing runs |

### `code`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `code-pyodide` | `deliver` | oci-artifact | neutral | `pyodide browser code interpreter` | `/health` |

### `dev`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `dev-svelte` | `deliver` | oci-artifact | amd64, arm64 | `svelte dev/build toolchain (node_modules + bun)` | `/health` |

### `docling`

Dispatch: `sprigs/docling_dispatch.py` → `point_docling_at()` (line 18).

Writes on graft:

- `CONTENT_EXTRACTION_ENGINE`
- `DOCLING_SERVER_URL`

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `docling` | `docling-serve` | oci-artifact | amd64, arm64 | `IBM Docling (docling-serve, CPU)` | `/health` |

### `embedding`

Dispatch: `sprigs/embedding_dispatch.py` → `point_embedding_at()` (line 22).

Writes on graft:

- `RAG_EMBEDDING_ENGINE`
- `RAG_EMBEDDING_MODEL`
- `RAG_OPENAI_API_BASE_URL`
- `RAG_OPENAI_API_KEY`

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `bge-large-en-v1.5` | `embedding` | oci-artifact | amd64, arm64 | `BAAI/bge-large-en-v1.5` | `/health` |
| `e5-large-gguf` | `llama-binary` | oci-artifact | amd64, arm64 | `intfloat/multilingual-e5-large (GGUF Q8_0)` | `/health` |
| `minilm-onnx-inhoused` | `embedding` | oci-artifact | amd64, arm64 | `all-MiniLM-L6-v2` | `/health` |
| `mock-embedding` | `mock` | built in | neutral | `mock-embedding` | `/health` |
| `multilingual-e5-large` | `embedding` | oci-artifact | amd64, arm64 | `intfloat/multilingual-e5-large` | `/health` |

### `export`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `export-document` | `deliver` | oci-artifact | amd64, arm64 | `PDF export (fpdf2 + CJK fonts)` | `/health` |

### `media`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `media-ffmpeg` | `deliver` | oci-artifact | amd64, arm64 | `static ffmpeg + ffprobe 7.0.2` | `/health` |

### `rag`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `rag-loaders` | `deliver` | oci-artifact | amd64, arm64 | `langchain RAG engines + document loaders (overlay)` | `/health` |

### `reranker`

Dispatch: `sprigs/reranker_dispatch.py` → `point_reranker_at()` (line 20).

Writes on graft:

- `RAG_EXTERNAL_RERANKER_API_KEY`
- `RAG_EXTERNAL_RERANKER_URL`
- `RAG_RERANKING_ENGINE`
- `RAG_RERANKING_MODEL`

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `bge-reranker-v2-m3-gguf` | `llama-binary` | oci-artifact | amd64, arm64 | `BAAI/bge-reranker-v2-m3 (GGUF Q8_0)` | `/health` |

### `stt`

Dispatch: `sprigs/stt_dispatch.py` → `point_stt_at()` (line 20).

Writes on graft:

- `STT_ENGINE`
- `STT_MODEL`
- `STT_OPENAI_API_BASE_URL`
- `STT_OPENAI_API_KEY`

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `whisper-base-ggml` | `whisper-binary` | oci-artifact | amd64, arm64 | `whisper base multilingual (ggml q8_0)` | `/health` |

### `theme`

Dispatch: `sprigs/theme_dispatch.py` → `point_theme_at()` (line 89).

Writes on graft:

- `SPRIG_ACTIVE_THEME`

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `theme-workshop-bio` | `deliver` | oci-artifact | neutral | `Workshop theme — Bio (green)` | `/health` |
| `theme-workshop-math` | `deliver` | oci-artifact | neutral | `Workshop theme — Math (blue)` | `/health` |

### `tika`

Dispatch: `sprigs/tika_dispatch.py` → `point_tika_at()` (line 18).

Writes on graft:

- `CONTENT_EXTRACTION_ENGINE`
- `TIKA_SERVER_URL`

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `tika` | `tika-jar` | oci-artifact | amd64, arm64 | `Apache Tika Server (standard)` | `/tika` |

### `ui`

Dispatch: `sprigs/ui_dispatch.py` → `point_ui_at()` (line 194).

Writes on graft:

- `SPRIG_ACTIVE_UI`

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `ui-workshop-welcome` | `deliver` | oci-artifact | neutral | `Workshop welcome card` | `/health` |

### `vector`

No dispatch module. Grafting delivers bytes and changes no configuration.

| Entry | Server | Delivery | Arch | Model | Health |
|---|---|---|---|---|---|
| `vector-chroma` | `deliver` | oci-artifact | amd64, arm64 | `chromadb vector DB + ML runtime (site-packages overlay)` | `/health` |

<!-- END GENERATED -->

## Adding a capability

Hand-written. The generator does not touch anything below this line.

A capability is not a row in a dict. It is a row in a dict plus five other
edits, three of which fail silently if you skip them.

### The traps, in the order they bite

**`dim` is required even when it is meaningless.** `_build_argv` reads
`str(spec["dim"])` unconditionally, before it switches on the server kind. A
completions or tunnel capability must carry `"dim": 0` — exactly as `reranker`,
`stt`, `tika` and `docling` already do — or grafting raises `KeyError` from a
line that has nothing to do with the capability you are adding.

**`graft()` does not dispatch.** The callers do, and there are two of them:
`routers/sprigs.py` on a fresh graft and `SprigSupervisor._reconcile` on boot.
They are hand-maintained copies of the same table. Add your branch to the first
and forget the second and the capability works perfectly until the first
restart, at which point the respawned child gets a new loopback port and the
config still names the old one. Nothing errors. The table above is the
mechanical check on this: your capability must read *yes* under **Survives
restart**, or say why it is n/a.

**Prune is a third copy.** `supervisor.prune()` reverses nothing; the reset
lives in `prune_sprig` beside the five that already have one. Skip it and your
capability joins `tika` and `docling` in the Gaps section — config pointing at a
released port, and `diagnostics/boot.py` reporting it unreachable for the rest
of the container's life.

**A connection is not a scalar.** Every dispatch that exists today flips one or
two values. If your capability seeds an OpenAI connection it is appending to
three index-parallel structures — `OPENAI_API_BASE_URLS`, `OPENAI_API_KEYS`,
`OPENAI_API_CONFIGS`, the last keyed by stringified list index — so seeding
means remembering the index and teardown means removing by value and re-keying.
Budget for that; nothing in the tree does it yet.

**Children are silenced.** Sprig processes are `DEVNULL`'d on both stdout and
stderr. A server that dies on boot tells you nothing at all; you get a health
timeout and no reason. Debug it by running the module by hand before you graft
it.

### The change list

Required: a `CATALOG` entry; a `_build_argv` branch if the server kind is new; a
`_reconcile` branch if it runs a process; a `<capability>_dispatch.py` with a
`point_<capability>_at(app, handle)`; a graft branch in `routers/sprigs.py`
before the `!= "embedding"` catch-all; a prune reset beside the other five; and
a server module if it is built in — `sprigs/mock_embedding_server.py` is 93
lines and is the template.

Conditional: the top-graft exclusivity tuple if only one may root at a time; a
`child_env` branch if the payload is OCI-delivered and is not a binary server,
since the `else` there sets an embedding-shaped cache variable; a restart
backstop in `main.py` if the seeded config carries a `sprig-local` sentinel; a
`CAPABILITY_SUMMARY_KEYS` entry plus locale strings for a specific how-to-fix
sentence, without which diagnostics falls back to a generic one; a build recipe
and a `Makefile` registration if it ships as an artifact.

Needs nothing: the admin panels. Both the server-rendered panel and the Svelte
one are catalog-driven, so a new capability appears and grafts with no
front-end work at all.

### What does not follow from the code

The generator reports what the code does, not whether it is right. Two things
it cannot tell you:

- **Whether a capability should be exclusive.** `embedding`, `reranker` and
  `stt` terminate their siblings on graft. Whether yours should is a product
  decision.
- **What a capability is *for*.** The inventory says `media` delivers ffmpeg. It
  does not say why anyone would want it. If that matters for your capability,
  write it here.
