---
title: "Docker Build Optimization Plan"
description: "Strategy for reducing Docker build times through runtime model downloads and multi-stage builds."
date: 2025-11-28
tags:
  - docker
  - optimization
  - build
  - infrastructure
---

# Docker Build Optimization Plan

## Current Performance Issues

**Build Time Analysis:**
- Full build: 10+ minutes
- Major bottlenecks:
  - PyTorch installation: 120+ seconds
  - `SentenceTransformer` model download: 148+ seconds
  - `WhisperModel` download: 10+ seconds
  - `tiktoken` encoding download: 5+ seconds
  - Node.js build: 113+ seconds
  - Python dependencies: 46+ seconds

**Development Impact:**
- Debugging static file issues requires full rebuilds
- Each iteration takes 10+ minutes
- Blocks rapid development workflow

## Optimization Strategy

### 1. Move Model Downloads to Runtime (Immediate Win)

**Current Approach (Build Time):**
```dockerfile
RUN TORCH_URL="https://download.pytorch.org/whl/cpu"; \
    if [ "$USE_CUDA" = "true" ]; then \
    TORCH_URL="https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER"; \
    fi &&\
    pip3 install torch torchvision torchaudio --index-url $TORCH_URL --no-cache-dir --break-system-packages
RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')"
RUN python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"
RUN python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])"
```

**Proposed Approach (Runtime Init):**
- Remove these RUN commands from Dockerfile
- Add startup script that downloads models on first run
- Use volume-mounted cache directories
- Models persist between container restarts

**Implementation:**
```bash
# In startup script (runtime)
python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" &
python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])" &
python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])" &
wait  # Wait for all downloads to complete
```

**Volume Mounts for Caching:**
```yaml
volumes:
  - model-cache:/app/backend/data/cache/embedding/models
  - whisper-cache:/app/backend/data/cache/whisper/models
  - tiktoken-cache:/app/backend/data/cache/tiktoken
```

### 2. Multi-Stage Build with Development Target

**Current: Single Stage Build**
- Everything built every time
- No separation of concerns

**Proposed: Multi-Stage Build**
```dockerfile
# Stage 1: Base dependencies
FROM node:22-bookworm AS base
# System packages, basic setup

# Stage 2: Python dependencies
FROM base AS python-deps
# Python packages, uv install

# Stage 3: Frontend build
FROM python-deps AS frontend
# Node build, static assets

# Stage 4: Development target
FROM frontend AS development
# Fast rebuild for dev changes
# Skip model downloads

# Stage 5: Production target
FROM frontend AS production
# Optimized for production
# Include model pre-downloads if needed
```

### 3. Improve Docker Build Context

**Current Issues:**
- Large build context transferred to Docker
- No .dockerignore optimizations

**Proposed .dockerignore:**
```
node_modules
.git
.vscode
*.md
docs/
submodules/
.env*
build/
dist/
coverage/
.pytest_cache/
__pycache__/
*.pyc
.DS_Store
```

### 4. Layer Optimization

**Current Layer Structure:**
- Frequent invalidation of expensive layers
- Model downloads in middle of build

**Proposed Layer Order:**
1. System packages (rarely change)
2. Python requirements.txt (change occasionally)
3. Node package.json (change occasionally)
4. Source code (change frequently)
5. Static files (change frequently)

### 5. Development Workflow Optimizations

**Fast Development Build Target:**
```dockerfile
FROM python-deps AS dev-fast
# Skip expensive operations
# Use bind mounts for source code
# Models downloaded at runtime
```

**Development Makefile Target:**
```makefile
dev-fast:
	docker build --target=dev-fast -t sage-dev:fast .
	docker run --rm -p 8080:8080 \
		-v $(pwd)/app/src:/app/src \
		-v $(pwd)/app/static:/app/static \
		-v model-cache:/app/backend/data/cache \
		sage-dev:fast
```

## Implementation Plan

### Phase 1: Runtime Model Downloads (Immediate)
- [ ] Create model initialization script
- [ ] Move model downloads to runtime
- [ ] Test with volume mounts
- [ ] Measure build time improvement

### Phase 2: Multi-Stage Build
- [ ] Design stage separation
- [ ] Create development target
- [ ] Optimize layer ordering
- [ ] Add .dockerignore

### Phase 3: Development Workflow
- [ ] Fast rebuild commands
- [ ] Source code bind mounts
- [ ] Hot reload optimization

## Expected Performance Gains

**Build Time Reduction:**
- Remove 163+ seconds of model downloads
- From ~10 minutes to ~3-4 minutes
- Development rebuilds: ~30 seconds with bind mounts

**Development Experience:**
- Rapid iteration on static file changes
- No waiting for model downloads during debugging
- Persistent model cache between rebuilds

## Risks and Mitigations

**Risk: Runtime Startup Delay**
- Mitigation: Parallel downloads, cached volumes
- First run: 2-3 minutes (one-time)
- Subsequent runs: instant (cached)

**Risk: Model Download Failures**
- Mitigation: Retry logic, fallback downloads
- Better error handling and logging

**Risk: Cache Invalidation**
- Mitigation: Version-pinned model URLs
- Explicit cache management commands
