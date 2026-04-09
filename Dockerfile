# syntax=docker/dockerfile:1.5
# =============================================================================
# Three-stage build: frontend → python-build → runtime
#   1. frontend:     Bun (deps) + Node.js (vite build)
#   2. python-build: Python + build tools — pip install (compilation)
#   3. runtime:      Python slim — copies from both, no Node, no gcc (~1.5GB)
# =============================================================================

# Build args
ARG USE_CUDA=false
ARG USE_OLLAMA=false
ARG USE_CUDA_VER=cu121
ARG USE_EMBEDDING_MODEL=intfloat/multilingual-e5-large
ARG USE_RERANKING_MODEL=""
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"
ARG BUILD_HASH=dev-build
ARG UID=0
ARG GID=0

# =============================================================================
# Stage 1: FRONTEND — Bun for deps, Node.js for vite build
# =============================================================================
FROM node:22-bookworm AS frontend
ARG BUILD_HASH

# Install bun (fast dependency management; vite build stays on Node.js for memory)
RUN npm install -g bun

WORKDIR /app

# Install dependencies via bun (cache layer)
COPY app/package.json /app/package.json
COPY app/bun.lock /app/bun.lock
RUN bun install --frozen-lockfile

# Setup Pyodide (cache layer)
COPY app/scripts/prepare-pyodide.js /app/scripts/prepare-pyodide.js
RUN mkdir -p /app/static/pyodide && \
    NODE_OPTIONS="--max-old-space-size=4096" node scripts/prepare-pyodide.js

# Copy files needed for frontend build
COPY app/postcss.config.js /app/postcss.config.js
COPY app/pyproject.toml /app/pyproject.toml
COPY app/svelte.config.js /app/svelte.config.js
COPY app/tailwind.config.js /app/tailwind.config.js
COPY app/tsconfig.json /app/tsconfig.json
COPY app/vite.config.ts /app/vite.config.ts

# Copy static files into build dir for vite
COPY app/static/ /app/build/
COPY app/src /app/src

# Build frontend (Node.js runtime — bun's JSC OOMs on large Svelte builds)
RUN NODE_OPTIONS="--max-old-space-size=4096" npx vite build

# Copy custom.css after vite build (SvelteKit clears output dir during build)
COPY app/static/assets/custom.css /app/build/assets/custom.css


# =============================================================================
# Stage 2: PYTHON-BUILD — compile Python packages with build tools
# =============================================================================
FROM python:3.11-bookworm AS python-build

# Build tools needed for native extensions (chromadb/hnswlib, psycopg2, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential gcc g++ python3-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install core Python dependencies (ML packages installed at runtime via wizard)
COPY app/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Pre-download tiktoken encoding (~1MB)
RUN mkdir -p /app/backend/tiktoken_cache && \
    TIKTOKEN_CACHE_DIR=/app/backend/tiktoken_cache \
    python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"


# =============================================================================
# Stage 3: RUNTIME — slim image, no Node.js, no build tools
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID=0
ARG GID=0
ARG BUILD_HASH

# Runtime-only system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates curl jq \
    ffmpeg \
    cron rclone && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # Symlink python3 for scripts that reference it
    ln -sf /usr/local/bin/python /usr/local/bin/python3

# Copy Python packages from python-build stage (paths match: both use site-packages)
COPY --from=python-build /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=python-build /usr/local/bin/ /usr/local/bin/

# Copy tiktoken cache
COPY --from=python-build /app/backend/tiktoken_cache/ /app/backend/tiktoken_cache/

# Copy vite build output (frontend)
COPY --from=frontend /app/build/ /app/build/

# Copy static files (single copy — config.py syncs from /app/build/static at startup)
COPY app/static/ /app/static/

# Copy backend source
COPY app/backend/ /app/backend/

# Copy changelog and package.json (version string)
COPY CHANGELOG.md /app/CHANGELOG.md
COPY app/package.json /app/package.json

WORKDIR /app/backend

## Environment variables ##
ENV ENV=prod \
    PORT=8080 \
    STATIC_DIR=/app/static \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false \
    CHROMA_TELEMETRY=false \
    USER_AGENT="Sage-is-AI/2.0" \
    ORT_LOG_LEVEL=3

ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

ENV RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"

ENV USE_TIKTOKEN_ENCODING_NAME="o200k_base"
ENV TIKTOKEN_ENCODING_NAME="$USE_TIKTOKEN_ENCODING_NAME" \
    TIKTOKEN_CACHE_DIR="/app/backend/tiktoken_cache"

ENV HF_HOME="/app/backend/data/cache/embedding/models"

ENV BACKUP_PATH="" \
    BACKUP_CRON="0 2 *"

ENV HOME=/root

# Create user if not root
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then addgroup --gid $GID app; fi; \
    adduser --uid $UID --gid $GID --home $HOME --disabled-password --no-create-home app; \
    fi

# Disable chroma telemetry
RUN mkdir -p $HOME/.cache/chroma && \
    echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id

# Fix ownership if not root
RUN if [ $UID -ne 0 ]; then \
    chown -R $UID:$GID /app $HOME; \
    fi

# Conditional Ollama install
RUN if [ "$USE_OLLAMA" = "true" ]; then \
    curl -fsSL https://ollama.com/install.sh | sh; \
    fi

# Create data directory
RUN mkdir -p /app/backend/data && \
    if [ $UID -ne 0 ]; then chown -R $UID:$GID /app/backend/data/ /app/backend/tiktoken_cache/; fi

EXPOSE 8080

HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

USER $UID:$GID

ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

CMD [ "bash", "restore_backup_start.sh", "server" ]
