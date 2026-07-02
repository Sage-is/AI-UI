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

# Runtime static tree (8.I.1 dedup, claims verified against a live container):
#   - /static/pyodide is dead weight — every worker loads with indexURL
#     '/pyodide/', served from /app/build/pyodide (62MB saved).
#   - The hashed ort-wasm copy in _app/immutable/assets is dead weight — both
#     consumers (Leaderboard.svelte, kokoro.worker.ts) set
#     env.backends.onnx.wasm.wasmPaths = '/wasm/', served from /app/build/wasm
#     (22MB saved). Keep /app/build/wasm itself!
COPY app/static/ /app/static-runtime/
RUN rm -rf /app/static-runtime/pyodide && \
    rm -f /app/build/_app/immutable/assets/ort-wasm-*.wasm


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
# Stage 3: RUNTIME — Wolfi rootstock (Decision #20, 2026-07-01 research round)
# glibc 2.43 base at ~15MB: every manylinux Sprig™ overlay (onnxruntime et al.)
# runs unchanged, bash entrypoint keeps working, Python 3.11 pinned via apk.
# Digest-pinned (rolling :latest) — treat every bump as a tested release:
#   docker buildx imagetools inspect cgr.dev/chainguard/wolfi-base:latest
# Pinned: latest as of 2026-07-02 (multi-arch index, amd64+arm64).
# =============================================================================
FROM cgr.dev/chainguard/wolfi-base@sha256:2f7a5c164eafbdbe46fe1d91bd1ab4c8cb5c2bdbd10641c3d61bd39962384cdb AS runtime

ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID=0
ARG GID=0
ARG BUILD_HASH

# Runtime system packages.
#   - gnutar (GNU tar at /usr/bin/tar): sprig extraction uses
#     `tar --use-compress-program=zstd` (artifact.py) which busybox tar lacks.
#   - libstdc++/tzdata: manylinux wheels may link system libstdc++; tzdata for
#     Debian-parity time handling.
#   - ffmpeg (~110MB of codec libs), rclone (51MB), cron are NOT baked into the
#     base rootstock. Graft the `media-ffmpeg` / `backup-rclone` Sprigs™ to
#     deliver static binaries on demand.
RUN apk add --no-cache python-3.11 bash ca-certificates curl jq zstd gnutar libstdc++ tzdata && \
    # Wolfi's own pip/setuptools out — the exact Debian-built closure from the
    # python-build stage lands below; mixing the two corrupts dist metadata.
    rm -rf /usr/lib/python3.11/site-packages/* && \
    # wolfi-base ships no /usr/local tree
    mkdir -p /usr/local/bin /usr/local/lib && \
    # ORAS CLI — graft #3 OCI-artifact Sprig™ delivery (arch-aware: amd64/arm64).
    # Bump ORAS_VERSION to the latest release shipping both linux artifacts:
    #   curl -s https://api.github.com/repos/oras-project/oras/releases/latest | jq -r .tag_name
    ORAS_VERSION=1.2.0 && \
    ARCH=$(uname -m) && \
    case "$ARCH" in \
      x86_64) ORAS_ARCH=amd64 ;; \
      aarch64) ORAS_ARCH=arm64 ;; \
      *) echo "Unsupported arch for oras: $ARCH" >&2 && exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/oras_${ORAS_VERSION}_linux_${ORAS_ARCH}.tar.gz" \
      | tar -xz -C /usr/local/bin oras && \
    oras version

# Copy Python packages from python-build stage. The wheels are built on Debian
# glibc 2.36 (manylinux-compatible) and run on Wolfi's 2.43 — same rule as
# Sprig™ overlays: build on the older glibc, run on the newer.
COPY --from=python-build /usr/local/lib/python3.11/site-packages/ /usr/lib/python3.11/site-packages/
COPY --from=python-build /usr/local/bin/ /usr/local/bin/

# The /usr/local/bin COPY above smuggles in Debian's python3.11 ELF + config —
# an interpreter with no stdlib on this image (its /usr/local/lib/python3.11 is
# absent) that would shadow Wolfi's python on PATH. Remove it and point every
# console-script shebang (#!/usr/local/bin/python3.11: uvicorn, pip, ...) at
# the real interpreter.
RUN rm -f /usr/local/bin/python /usr/local/bin/python3 /usr/local/bin/python3.11 \
      /usr/local/bin/python3-config /usr/local/bin/python3.11-config \
      /usr/local/bin/idle3 /usr/local/bin/idle3.11 \
      /usr/local/bin/pydoc3 /usr/local/bin/pydoc3.11 \
      /usr/local/bin/2to3 /usr/local/bin/2to3.11 && \
    ln -s /usr/bin/python3.11 /usr/local/bin/python && \
    ln -s /usr/bin/python3.11 /usr/local/bin/python3 && \
    ln -s /usr/bin/python3.11 /usr/local/bin/python3.11

# Two append-after-base sys.path extensions (base site-packages always wins):
#   - /usr/local/lib/python3.11/site-packages — Sprig™ overlay dir. The
#     vector-chroma CATALOG target keeps this exact path (supervisor.py), so
#     existing signed artifacts extract unchanged; overlays live apart from the
#     base closure and prune cleanly.
#   - ml_packages (data-volume install via wizard) — transitional: the 2.4
#     bundle replaces this with a signed tarball pulled into the data volume.
RUN printf 'import sys, os\nfor _p in ("/usr/local/lib/python3.11/site-packages", "/app/backend/data/ml_packages"):\n    if os.path.isdir(_p) and _p not in sys.path:\n        sys.path.append(_p)\n' \
    > /usr/lib/python3.11/sitecustomize.py

# Install `uv` for the runtime ML wizard install. Pinned so a 0.x breaking
# change cannot ship via the base image. The release artifact name uses the
# same arch tokens as `uname -m` on Linux (x86_64, aarch64) — both Docker
# buildx targets are covered. Bump UV_VERSION to the latest release that has
# both x86_64 and aarch64 Linux gnu artifacts at edit time:
#   curl -s https://api.github.com/repos/astral-sh/uv/releases/latest | jq -r .tag_name
ARG UV_VERSION=0.5.18
RUN ARCH=$(uname -m) && \
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${ARCH}-unknown-linux-gnu.tar.gz" \
      | tar -xz -C /usr/local/bin --strip-components=1 "uv-${ARCH}-unknown-linux-gnu/uv" && \
    uv --version

# Copy tiktoken cache
COPY --from=python-build --chown=${UID}:${GID} /app/backend/tiktoken_cache/ /app/backend/tiktoken_cache/

# Dev toolchain (bun ~92MB + node_modules ~1.1GB) is NOT baked into the base
# rootstock — the `dev-svelte` Sprig™ delivers both into /app on demand. The
# dangling symlink keeps `bun` on PATH once the sprig lands at /app/bun.
RUN ln -s /app/bun /usr/local/bin/bun

# Copy vite build output (frontend). --chown at COPY time: a post-hoc
# `chown -R /app` duplicates the whole tree into a new layer on non-root builds.
COPY --from=frontend --chown=${UID}:${GID} /app/build/ /app/build/

# Static tree, pre-pruned in the frontend stage (pyodide dedup — see the
# static-runtime block there). /app/static must still EXIST at boot: the
# StaticFiles mount requires it, and favicon/loader.js live ONLY here
# (/app/build has no static/ subdir — config.py's sync source never exists).
COPY --from=frontend --chown=${UID}:${GID} /app/static-runtime/ /app/static/

# Copy backend source
COPY --chown=${UID}:${GID} app/backend/ /app/backend/

# Copy changelog and package.json (version string)
COPY --chown=${UID}:${GID} CHANGELOG.md /app/CHANGELOG.md
COPY --chown=${UID}:${GID} app/package.json /app/package.json

WORKDIR /app/backend

## Environment variables ##
# LANG parity with the former python:3.11-slim base (Wolfi sets no default)
ENV LANG=C.UTF-8
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

# Create user if not root (busybox adduser syntax on Wolfi)
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then \
      addgroup -g $GID app && adduser -D -H -h $HOME -u $UID -G app app; \
    else \
      adduser -D -H -h $HOME -u $UID -G root app; \
    fi; \
    fi

# Persist chroma's local cache (telemetry id + ONNX embedding model bundle)
# in the data volume. chromadb constructs paths via `Path.home() / ".cache"
# / "chroma" / ...` — Python's `Path.home()` reads the HOME env var, not
# XDG_CACHE_HOME, so the only reliable redirect is at the filesystem layer.
# Symlinking $HOME/.cache/chroma into the persisted /app/backend/data/cache
# tree matches the existing convention for libraries that don't expose a
# cache-path env var (sentence-transformers, HF, whisper, tiktoken all
# point at /app/backend/data/cache via their respective env vars). Survives
# fresh container starts AND CapRover redeploys as long as the volume is
# mounted at /app/backend/data — which is the standard mount path in both
# the Makefile workflow and the docs/try-sage-deployment.md CapRover guide.
RUN mkdir -p /app/backend/data/cache/chroma && \
    mkdir -p $HOME/.cache && \
    ln -s /app/backend/data/cache/chroma $HOME/.cache/chroma && \
    echo -n 00000000-0000-0000-0000-000000000000 > /app/backend/data/cache/chroma/telemetry_user_id

# Fix ownership of RUN-created trees if not root. /app is NOT chowned here —
# every /app COPY carries --chown; a recursive chown of copied trees would
# duplicate ~400MB into this layer.
RUN if [ $UID -ne 0 ]; then \
    chown -R $UID:$GID $HOME; \
    fi

# Conditional Ollama install (Debian-oriented installer; untested on the Wolfi
# base — the supported path is a sidecar Ollama container or a future Sprig™)
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
