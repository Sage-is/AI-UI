# Knowledge Base PDF Ingestion Modes — Implementation Plan

**Date**: 2026-03-05
**Status**: Planned
**Priority**: High

## Problem Statement

Currently, PDF ingestion into Knowledge Bases uses a **single global extraction engine** configured in Admin > Settings > Documents. Users have no per-upload choice over how their PDFs are processed. There is also no LLM-based post-processing step to improve the quality of extracted text before it gets chunked and embedded.

## Proposed Solution: Three Ingestion Modes

When uploading a PDF (or any document) to a Knowledge Base, users should be able to choose from three ingestion modes:

### Mode 1: Plain (Current Behavior)

- **What it does**: Uses the currently configured extraction engine (PyPDFLoader by default) to extract raw text from the PDF. Text goes straight to chunking and embedding.
- **When to use**: Quick uploads, simple text-heavy PDFs, when speed matters more than formatting quality.
- **Changes needed**: None — this is the existing pipeline. Just needs to be labeled as "Plain" in the UI.

### Mode 2: AI Parsed (NEW)

- **What it does**: After extracting text via the configured engine, passes the extracted content through a chosen LLM with a configurable prompt to reorganize, clean up, and reformat the content (e.g., proper markdown headings, table reconstruction, list formatting, removal of extraction artifacts).
- **When to use**: Academic papers, reports, complex documents where structure matters for retrieval quality.
- **Pipeline**:
  ```
  PDF → Extraction Engine → Raw Text → LLM Processing → Cleaned Markdown → Chunking → Embedding
  ```
- **Configurable parameters** (admin-level defaults, overridable per-upload):
  - **LLM Model**: Which model to use for processing (dropdown of available models)
  - **Processing Prompt**: System prompt that instructs the LLM how to reformat (admin sets default, power users can customize)
  - **Chunk-before-LLM**: Option to split into page-sized chunks before LLM processing (handles token limits for large docs)

- **Default prompt** (admin-configurable):
  ```
  You are a document formatting assistant. Take the following raw text extracted
  from a PDF and reorganize it into clean, well-structured Markdown. Preserve all
  factual content exactly. Apply these rules:
  - Add appropriate heading levels (# ## ###) based on document structure
  - Format tables as proper Markdown tables
  - Convert bullet points and numbered lists to proper Markdown lists
  - Remove page headers/footers, page numbers, and extraction artifacts
  - Preserve code blocks with proper fencing
  - Clean up broken words from line breaks
  - Keep all citations and references intact
  Output ONLY the reformatted content, no commentary.
  ```

### Mode 3: External PDF API (Enhanced)

- **What it does**: Sends the PDF to a specialized external parsing service for high-quality extraction with layout analysis, table detection, OCR, and image description.
- **When to use**: Scanned PDFs, complex layouts with tables/figures, when maximum extraction quality is needed.
- **Already partially exists**: The backend supports Datalab Marker, Docling, Tika, Azure Document Intelligence, Mistral OCR, and a generic External endpoint. However, these are currently configured globally — not selectable per-upload.
- **Changes needed**: Surface the available (configured) external engines as selectable options during upload.

## Architecture

### Current Flow (simplified)
```
Upload → Storage → process_file() → Loader.load() → save_docs_to_vector_db() → Done
                                      ↑ global engine
```

### Proposed Flow
```
Upload (with mode selection)
  → Storage
  → process_file(ingestion_mode=...)
     ├─ mode="plain"     → Loader.load()          → save_docs_to_vector_db()
     ├─ mode="ai_parsed" → Loader.load() → LLM()  → save_docs_to_vector_db()
     └─ mode="external"  → ExternalLoader.load()   → save_docs_to_vector_db()
```

### Key Files to Modify

| Layer | File | Changes |
|-------|------|---------|
| **Frontend** | `KnowledgeBase.svelte` | Add ingestion mode selector to upload flow |
| **Frontend** | `AddContentMenu.svelte` | Pass mode selection through upload chain |
| **Frontend** | `apis/files/index.ts` | Add `ingestion_mode` to upload metadata |
| **Backend** | `routers/files.py` | Accept `ingestion_mode` in upload metadata |
| **Backend** | `routers/retrieval.py` | Route `process_file()` based on ingestion mode |
| **Backend** | `retrieval/loaders/main.py` | Add AI-parsed post-processing step |
| **Backend** | `config.py` | Add AI parsing defaults (model, prompt, enabled modes) |
| **Frontend** | `admin/Settings/Documents.svelte` | Add AI Parsing config section (default model, prompt) |

### New Backend Components

#### 1. AI Parsing Service (`retrieval/processors/ai_parser.py` — NEW)

```python
async def ai_parse_content(
    raw_text: str,
    model: str,           # LLM model ID
    prompt: str,           # Processing prompt
    chunk_pages: bool,     # Split by pages before sending to LLM
    user: UserModel,       # For auth/rate limiting
) -> str:
    """
    Post-process extracted text through an LLM for better formatting.

    Uses generate_chat_completion() internally (same as chat pipeline),
    so it works with any configured model (Ollama, OpenAI, etc.)
    """
```

#### 2. Ingestion Mode Schema

```python
class IngestionMode(str, Enum):
    PLAIN = "plain"
    AI_PARSED = "ai_parsed"
    EXTERNAL = "external"

class IngestionConfig(BaseModel):
    mode: IngestionMode = IngestionMode.PLAIN
    ai_model: Optional[str] = None        # Override admin default
    ai_prompt: Optional[str] = None       # Override admin default
    external_engine: Optional[str] = None # Which external engine
```

#### 3. Admin Configuration Additions

```python
# New PersistentConfig entries
AI_PARSE_ENABLED = PersistentConfig("AI_PARSE_ENABLED", "rag.ai_parse.enabled", True)
AI_PARSE_DEFAULT_MODEL = PersistentConfig("AI_PARSE_DEFAULT_MODEL", "rag.ai_parse.model", "")
AI_PARSE_DEFAULT_PROMPT = PersistentConfig("AI_PARSE_DEFAULT_PROMPT", "rag.ai_parse.prompt", DEFAULT_AI_PARSE_PROMPT)
AI_PARSE_CHUNK_BEFORE_LLM = PersistentConfig("AI_PARSE_CHUNK_BEFORE_LLM", "rag.ai_parse.chunk_before_llm", True)
AI_PARSE_MAX_CHUNK_SIZE = PersistentConfig("AI_PARSE_MAX_CHUNK_SIZE", "rag.ai_parse.max_chunk_size", 4000)
```

### Frontend UX

#### Upload Flow Change

When a user clicks "Upload files" in a Knowledge Base, a lightweight mode selector appears (either inline or as a pre-upload step):

```
┌─────────────────────────────────────────┐
│  Upload Documents                       │
│                                         │
│  Ingestion Mode:                        │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ │
│  │  Plain   │ │ AI Parse │ │ API      │ │
│  │ (fast)   │ │ (smart)  │ │ (best)   │ │
│  └─────────┘ └──────────┘ └──────────┘ │
│                                         │
│  [Select files...]                      │
└─────────────────────────────────────────┘
```

- **Plain**: Default, no extra UI
- **AI Parse**: Shows model dropdown + optional prompt override (collapsed by default with "Advanced" toggle)
- **API**: Shows available configured engines (only engines that the admin has configured with valid credentials appear)

#### Admin Settings Addition

New section in Documents.svelte under "Content Extraction":

```
AI Document Parsing
├── Enable AI Parsing mode for users  [toggle]
├── Default Model  [dropdown — same model list as chat]
├── Default Processing Prompt  [textarea]
├── Chunk before LLM processing  [toggle]
└── Max chunk size for LLM  [number input]
```

## Implementation Phases

### Phase 1: Backend Infrastructure
1. Create `IngestionMode` enum and `IngestionConfig` schema
2. Add AI parsing config entries to `config.py`
3. Create `retrieval/processors/ai_parser.py` service
4. Modify `process_file()` in `retrieval.py` to accept and route by ingestion mode
5. Add ingestion mode to `ProcessFileForm`
6. Wire AI parsing into the extraction → chunking pipeline
7. Update `/retrieval/config` endpoints to include AI parse settings

### Phase 2: Admin Settings UI
1. Add AI Parsing section to `Documents.svelte`
2. Add model selection dropdown (reuse existing model list components)
3. Add prompt textarea with default value
4. Add chunk/size toggles
5. Wire to `/retrieval/config/update` endpoint

### Phase 3: Upload Flow UI
1. Add ingestion mode selector to `KnowledgeBase.svelte` upload flow
2. Pass mode in upload metadata through `apis/files/index.ts`
3. Show/hide mode options based on admin config (if AI parse disabled, hide it)
4. Show available external engines (only configured ones)
5. Add optional prompt override for AI Parse mode (collapsible "Advanced")

### Phase 4: Testing & Polish
1. Test all three modes with various PDF types (text-heavy, scanned, tables, mixed)
2. Test LLM processing with different models (Ollama local, OpenAI API)
3. Test external engine selection per-upload
4. Verify chunking quality differences between modes
5. Performance testing (AI parse adds latency — ensure good UX with progress indicators)

## Considerations

### Token Limits
Large PDFs can exceed LLM context windows. The "chunk before LLM" option splits extracted text into page-sized segments, processes each through the LLM, then concatenates. This ensures even 500-page PDFs can be AI-parsed.

### Cost Awareness
AI Parsing uses LLM tokens. Admin should be aware that enabling this for all users could increase API costs. The per-upload opt-in model (rather than always-on) keeps costs predictable.

### Retrieval Quality
AI-parsed content with proper markdown headings enables the `markdown_header` text splitter to work optimally — splitting on semantic boundaries rather than arbitrary character counts. This should significantly improve retrieval relevance.

### Backward Compatibility
- Existing knowledge bases and files are unaffected (they used "plain" mode implicitly)
- The default mode remains "plain" unless admin changes it
- No database migration needed — ingestion mode stored in file metadata JSON

## Related Files Reference

- Frontend KB: `app/src/lib/components/workshop/Knowledge/KnowledgeBase.svelte`
- Frontend Upload API: `app/src/lib/apis/files/index.ts`
- Frontend Admin Docs Settings: `app/src/lib/components/admin/Settings/Documents.svelte`
- Backend File Upload: `app/backend/open_webui/routers/files.py`
- Backend Processing: `app/backend/open_webui/routers/retrieval.py`
- Backend Loaders: `app/backend/open_webui/retrieval/loaders/main.py`
- Backend Config: `app/backend/open_webui/config.py`
- Chat Completion (reused for AI parse): `app/backend/open_webui/utils/chat.py`
