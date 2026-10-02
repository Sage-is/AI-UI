# LocalMind deep-exam plan

Goal: steal the good parts for AI-UI, and make LocalMind a flexible satellite of AI-UI instances. Read-only first, code second.

Source: the LocalMind checkout (`app/` 29 modules, ~1.1M). Targets: PDF ingestion, document creation, copy tooling.

## Phase 0 — Map the territory [WE]

1. Inventory `app/*.py` + `static/*.js` + `config/*.json`: inputs, outputs, owner of each.
2. Trace the three golden paths end-to-end: add-PDF → ask → cite; ask → download-as; template → fill-blanks → copy.
3. Baseline on a sample pack (PDF, scanned PDF, docx, xlsx, epub, URL): ingest success/failure, export fidelity per format, copy-action inventory (`static/app.js`: 25 copy hooks, 7 `navigator.clipboard` uses).

## Phase 1 — Deep dives

**A. PDF ingestion** (`app/ingest.py`, 519 lines / 23 fns)
- Per-page segments with `p. N` labels; scanned-PDF fail-loud path (tells user to OCR); table-adjacent docx walker as contrast.
- Chunking: `_split_long` + `chunk_segments` (paragraph → sentence → hard-cut, overlap tail), `_loc_range` (`pp. x–y`). Compare vs AI-UI `retrieval/loaders` on the same pack.
- Output: gap list + port proposal (2–3 functions into AI-UI loaders, with tests).

**B. Document creation** (`app/exporter.py` 646 lines / 29 fns, `app/slides.py` 873 lines / 39 fns)
- Single markdown-IR `parse()` → `to_docx/to_pdf/to_xlsx/to_csv/to_pptx`; `_drop_chatter`; `split_sections` (per-section downloads); content-shaped slides (`classify`: cards, stats, process, chart, quote).
- Output: fidelity matrix per format + proposal for AI-UI's download path; slides classifier as shared-module candidate.

**C. Copy tooling** (`static/app.js`, templates)
- `{{Blank}}` fill-in model; Copy email/subject vs Open-in-Mail; per-answer + per-section copy/download; code-zip with executable bits; Read-aloud/Read-selection pattern.
- Output: interaction spec AI-UI can adopt (buttons, clipboard fallbacks, i18n strings — `i18n-fr.js` as model).

## Phase 2 — Port to AI-UI [WE]

4. One small PR per adopted piece behind existing AI-UI seams (loader, export route, component), with sample-pack tests.
5. Kill-or-keep: `pandas`-based `extract_sheet` (replace with `openpyxl`/`csv`?) vs `trafilatura` chain weight.
6. One docs page per port: what was borrowed, what was deliberately not.

## Phase 3 — Connect LocalMind ↔ AI-UI [WE], [MANUALLY] ships first seam

7. Satellite contract: LocalMind keeps local-first KB + team features; AI-UI is the heavy backend. Thinnest seams first:
   - **STT**: LocalMind POSTs audio to AI-UI's whisper sprig (`/v1/audio/transcriptions`) instead of in-process `mlx-whisper` — deletes ~1G venv weight (pattern exists: `sprigs/stt_dispatch.py`).
   - **Embeddings/chat overflow**: `ollama.py` client pointed at an AI-UI instance URL for big models; local Ollama stays default.
   - **Docling extraction**: layout-hard PDFs to AI-UI's Docling sprig; keep `pypdf` fast path local.
8. Auth: API key / per-user token, read-only scopes first; nothing leaves the school network without explicit config.
9. Ship order: STT first (biggest weight loss, smallest behavior change), then wire + test on the school server.

## Done when

- Sample-pack report exists (ingest + export matrices).
- ≥1 port merged into AI-UI with tests.
- LocalMind transcribes via AI-UI sprig with no local `torch`/`mlx` (fresh-venv size proves it).
- No more 1.4G zips: repo is git-shared, `.venv` rebuilt via `install.sh`.
