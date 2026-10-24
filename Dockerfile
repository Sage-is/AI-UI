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
#
# sharing=locked is load-bearing, not an optimisation. A multi-arch build runs
# the amd64 and arm64 frontend stages at the same time, and two concurrent bun
# installs starve each other on I/O: the run stretches from 21s to 181s and one
# arch dies with `Fail extracting tarball for "mermaid"` -- always mermaid, the
# largest tarball in the tree. It killed the 3.1.0 release twice. The lock
# serialises the two extractions; the second arch then rides the warm cache.
COPY app/package.json /app/package.json
COPY app/bun.lock /app/bun.lock
RUN --mount=type=cache,target=/root/.bun/install/cache,sharing=locked \
    bun install --frozen-lockfile

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

# Build frontend (Node.js runtime: bun's JSC OOMs on large Svelte builds)
RUN NODE_OPTIONS="--max-old-space-size=4096" npx vite build

# Copy custom.css after vite build (SvelteKit clears output dir during build)
COPY app/static/assets/custom.css /app/build/assets/custom.css

# Runtime static tree (8.I.1 dedup, claims verified against a live container):
#   - /static/pyodide is dead weight: every worker loads with indexURL
#     '/pyodide/', served from /app/build/pyodide (62MB saved).
#   - The hashed ort-wasm copy in _app/immutable/assets is dead weight: both
#     consumers (Leaderboard.svelte, kokoro.worker.ts) set
#     env.backends.onnx.wasm.wasmPaths = '/wasm/', served from /app/build/wasm
#     (22MB saved). Keep /app/build/wasm itself!
#   8.I.2: three payloads leave the image entirely, each returning as a Sprig™:
#   - /app/static-runtime/fonts (59MB CJK Noto): PDF-export only (backend
#     pdf_generator.py + frontend pdf-style.css) → export-document Sprig™.
#     UI fonts live in /app/static/assets/fonts, untouched.
#   - /app/build/pyodide (62MB): code-interpreter feature → code-pyodide
#     Sprig™; workers 404 until grafted.
#   - /app/build/wasm (22MB): onnxruntime-web for Leaderboard + kokoro TTS →
#     browser-ml Sprig™.
COPY app/static/ /app/static-runtime/
RUN rm -rf /app/static-runtime/pyodide \
      /app/static-runtime/fonts \
      /app/build/pyodide \
      /app/build/wasm && \
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

# pip, setuptools and wheel install packages; nothing imports them at run time
# (only test/dev extras name them). Since 3.2.1 uv does every runtime install,
# so they are uninstalled last, packages and console scripts, before the copy
# below. That took 16 MB and trivy's last two HIGH Python findings with them
# (jaraco.context and wheel, vendored inside setuptools).
RUN python -m pip uninstall -y -q setuptools wheel && python -m pip uninstall -y -q pip


# =============================================================================
# Stage 3: RUNTIME — Wolfi rootstock (Decision #20, 2026-07-01 research round)
# glibc 2.44 base at ~15MB. Every manylinux Sprig™ overlay (onnxruntime et al.)
# runs unchanged and the bash entrypoint keeps working. Python 3.11 via apk.
# Digest-pinned against a rolling :latest, so treat every bump as a release:
#   docker buildx imagetools inspect cgr.dev/chainguard/wolfi-base:latest
# Pinned: latest as of 2026-10-14 (multi-arch index, amd64+arm64). Bumped from
# the 2026-09-25 pin because a stale base pairs its old crypto libraries with
# whatever python-3.11 apk serves today: on 2026-10-07 that Python lost sha224.
# Before that, the 2026-07-02 pin (glibc 2.43) installed a Python whose math
# module could not load, and the image built fine and died at boot. The import
# check below fails the build on both.
# =============================================================================
FROM cgr.dev/chainguard/wolfi-base@sha256:256c88bb066424045021090932d50be93c8e3f2ce3586707702a401b146f3e43 AS runtime

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
#   - ffmpeg (~110MB of codec libs), rclone (51MB), and cron are NOT baked into
#     the base rootstock. Graft the `media-ffmpeg` / `backup-rclone` Sprigs™ to
#     deliver static binaries on demand.
#   - No curl, jq or ORAS since 3.2.1. They served the HEALTHCHECK, two shell
#     scripts and Sprig pulls; sage_is_ai/utils/localhttp.py and sprigs/oci.py
#     do those jobs in Python. A shell in the container gets no download tools.
RUN apk add --no-cache python-3.11 bash ca-certificates zstd gnutar libstdc++ tzdata && \
    # Poka-yoke: the Python apk just installed must load its C extensions on
    # this base's glibc and crypto. A skew (python built for a newer glibc or
    # OpenSSL) fails here, at build time, instead of at boot after the image
    # has shipped. sha224, sha3 and sha512 are what a stale base lost on
    # 2026-10-06/07 (TODO.md Bugs: "Today's image builds lose sha224 and sha3").
    python3 -c "import math, ssl, sqlite3, ctypes, hashlib, zlib; hashlib.sha224(b'x').hexdigest(); hashlib.new('sha224'); hashlib.sha3_256(b'x'); hashlib.sha512(b'x'); ssl.create_default_context()" && \
    # Wolfi's own pip/setuptools out. The Debian-built closure from the
    # python-build stage replaces it below; mixing the two corrupts dist
    # metadata.
    rm -rf /usr/lib/python3.11/site-packages/* && \
    # wolfi-base ships no /usr/local tree
    mkdir -p /usr/local/bin /usr/local/lib

# Copy Python packages from python-build stage. The wheels are built on Debian
# glibc 2.36 (manylinux-compatible) and run on Wolfi's 2.44. Same rule as the
# Sprig™ overlays: build on the older glibc, run on the newer.
COPY --from=python-build /usr/local/lib/python3.11/site-packages/ /usr/lib/python3.11/site-packages/
COPY --from=python-build /usr/local/bin/ /usr/local/bin/

# The /usr/local/bin COPY above smuggles in Debian's python3.11 ELF + config.
# That interpreter has no stdlib on this image (its /usr/local/lib/python3.11 is
# absent) and would shadow Wolfi's python on PATH. Remove it and point every
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
#   - /usr/local/lib/python3.11/site-packages, the Sprig™ overlay dir. The
#     vector-chroma CATALOG target keeps this exact path (supervisor.py), so
#     existing signed artifacts extract unchanged; overlays live apart from the
#     base closure and prune cleanly.
#   - ml_packages (data-volume install via wizard). Transitional: the 2.4
#     bundle replaces this with a signed tarball pulled into the data volume.
RUN printf 'import sys, os\nfor _p in ("/usr/local/lib/python3.11/site-packages", "/app/backend/data/ml_packages"):\n    if os.path.isdir(_p) and _p not in sys.path:\n        sys.path.append(_p)\n' \
    > /usr/lib/python3.11/sitecustomize.py && \
    # Pre-create the overlay dir so sitecustomize always puts it on sys.path.
    # Lazily-imported Sprig™ payloads (fpdf, langchain) then work as soon as
    # they are grafted, without a restart. vector-chroma still needs one: its
    # import bindings freeze at boot in retrieval/vector/factory.py.
    mkdir -p /usr/local/lib/python3.11/site-packages

# Install `uv` for the runtime ML wizard install. Copied from Astral's
# official image, pinned by its multi-arch index digest (linux/amd64 +
# linux/arm64), so no curl installer runs and a moved tag cannot change the
# binary. Keep this in step with the host uv that compiles
# app/backend/requirements-ml.lock. To bump: read the release's breaking
# changes when crossing a 0.N.0 line, then
#   docker buildx imagetools inspect ghcr.io/astral-sh/uv:<version>   # index digest
#   gh attestation verify oci://ghcr.io/astral-sh/uv:<version>@<digest> --owner astral-sh
COPY --from=ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a /uv /usr/local/bin/uv

# Cuts stay cut (3.2.1). Each name below left the image on purpose; a new
# requirement that quietly pulls one back (8.I.1 saw extras re-install rich and
# pygments) fails HERE, naming the package that asked for it, not in a CVE scan
# months later. To bring one back on purpose, delete its line and say why.
RUN <<'CHECK' python3
import importlib.metadata as md, importlib.util, re, shutil, sys
gone_modules = {  # module: (distribution, why it left)
    "pip": ("pip", "runtime installs use uv (utils/runtime_install.py)"),
    "setuptools": ("setuptools", "nothing imports it at run time"),
    "pkg_resources": ("setuptools", "nothing imports it at run time"),
    "wheel": ("wheel", "nothing imports it at run time"),
    "typer": ("typer", "the container starts uvicorn directly"),
    "rich": ("rich", "only typer used it"),
    "pygments": ("pygments", "only rich used it"),
    "passlib": ("passlib", "utils/passwords.py calls bcrypt directly"),
    "peewee": ("peewee", "internal/legacy_db.py replays its frozen schema"),
    "peewee_migrate": ("peewee-migrate", "internal/legacy_db.py replays its frozen schema"),
    "grpc": ("grpcio", "it rides the vector-chroma Sprig with chromadb"),
    "google.protobuf": ("protobuf", "it rides the vector-chroma Sprig with chromadb"),
    "opentelemetry.sdk": ("opentelemetry-sdk", "it rides the vector-chroma Sprig with chromadb"),
}
gone_binaries = {
    "oras": "sprigs/oci.py",
    "curl": "sage_is_ai.utils.localhttp",
    "jq": "sage_is_ai.utils.localhttp --field",
    "pip": "uv",
    "pip3": "uv",
}
def norm(name):
    return name.replace("_", "-").lower()
def who_requires(dist):
    return sorted({
        d.metadata["Name"] for d in md.distributions()
        for r in (d.requires or []) if "extra ==" not in r
        and norm(re.split(r"[ ;<>=!~\[(]", r, maxsplit=1)[0]) == norm(dist)
    })
bad = []
for mod, (dist, why) in gone_modules.items():
    try:
        found = importlib.util.find_spec(mod) is not None
    except ModuleNotFoundError:
        found = False
    if found:
        asked = who_requires(dist) or "nobody: a direct pin in requirements.txt"
        bad.append(f"{mod} ({dist}) is back, required by {asked}. It left because {why}.")
for exe, why in gone_binaries.items():
    if shutil.which(exe):
        bad.append(f"{exe} is back at {shutil.which(exe)}. Use {why} instead.")
if not shutil.which("uv"):
    bad.append("uv is missing; every runtime install needs it")
print("\n".join(bad) or "cuts stay cut: all clear")
sys.exit(1 if bad else 0)
CHECK

# Copy tiktoken cache
COPY --from=python-build --chown=${UID}:${GID} /app/backend/tiktoken_cache/ /app/backend/tiktoken_cache/

# Dev toolchain (bun ~92MB + node_modules ~1.1GB) is NOT baked into the base
# rootstock. The `dev-svelte` Sprig™ delivers both into /app on demand, and the
# dangling symlink keeps `bun` on PATH once the sprig lands at /app/bun.
RUN ln -s /app/bun /usr/local/bin/bun

# Copy vite build output (frontend). --chown at COPY time: a post-hoc
# `chown -R /app` duplicates the whole tree into a new layer on non-root builds.
COPY --from=frontend --chown=${UID}:${GID} /app/build/ /app/build/

# Static tree, pre-pruned in the frontend stage (pyodide dedup: see the
# static-runtime block there). /app/static must still EXIST at boot: the
# StaticFiles mount requires it, and favicon/loader.js live ONLY here.
# /app/build has no static/ subdir, so config.py's sync source never exists.
COPY --from=frontend --chown=${UID}:${GID} /app/static-runtime/ /app/static/

# Copy backend source
COPY --chown=${UID}:${GID} app/backend/ /app/backend/

# Translation catalogs for server-rendered pages.
#
# The backend emits translation keys rather than English (diagnostics.py is the
# reference), which works fine while only the browser renders. A server-rendered
# page has no i18next, so it reads the same catalog the SPA does instead of a
# second set of English strings. See pages/i18n.py.
#
# Every catalog, because a rendered page has to answer in the reader's language
# before it can take over a route from the SPA. 5 MB against a 604 MB image.
# `pages/i18n.py` reads this directory to learn which locales exist, so what is
# copied here IS the supported set — there is no second list to keep in step, and
# a locale absent from this COPY is refused rather than half-supported.
COPY --chown=${UID}:${GID} app/src/lib/i18n/locales/ /app/backend/locales/

# The diagnostic fix registry: 9 issue types, 40 remediation steps, all of them
# translation keys. Shipped as data rather than transcribed into Python so the
# Svelte component and the server-rendered page read the same file.
COPY --chown=${UID}:${GID} app/src/lib/components/admin/Diagnostics/fixRegistry.json /app/backend/data-registry/fixRegistry.json
COPY --chown=${UID}:${GID} app/src/lib/components/admin/Diagnostics/commandLibrary.json /app/backend/data-registry/commandLibrary.json

# Copy changelog and package.json (version string)
COPY --chown=${UID}:${GID} CHANGELOG.md /app/CHANGELOG.md
COPY --chown=${UID}:${GID} app/package.json /app/package.json

WORKDIR /app/backend

## Environment variables ##
# LANG parity with the former python:3.11-slim base (Wolfi sets no default)
ENV LANG=C.UTF-8
# One font location for both consumers: backend fpdf (env.py FONTS_DIR) and
# frontend pdf-style.css (/static/fonts URL). The export-document Sprig™
# delivers the CJK set here; env.py's default points at the backend package
# dir, which never ships fonts.
ENV FONTS_DIR=/app/static/fonts
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
# / "chroma" / ...`, and Python's `Path.home()` reads the HOME env var, not
# XDG_CACHE_HOME, so the only reliable redirect is at the filesystem layer.
# Symlinking $HOME/.cache/chroma into the persisted /app/backend/data/cache
# tree matches the existing convention for libraries that don't expose a
# cache-path env var (sentence-transformers, HF, whisper, tiktoken all
# point at /app/backend/data/cache via their respective env vars). Survives
# fresh container starts and CapRover redeploys as long as the volume is
# mounted at /app/backend/data, the standard mount path in both the Makefile
# workflow and the docs/try-sage-deployment.md CapRover guide.
RUN mkdir -p /app/backend/data/cache/chroma && \
    mkdir -p $HOME/.cache && \
    ln -s /app/backend/data/cache/chroma $HOME/.cache/chroma && \
    echo -n 00000000-0000-0000-0000-000000000000 > /app/backend/data/cache/chroma/telemetry_user_id

# Fix ownership of RUN-created trees if not root. /app is NOT chowned here.
# Every /app COPY carries --chown, and a recursive chown of copied trees would
# duplicate ~400MB into this layer.
RUN if [ $UID -ne 0 ]; then \
    chown -R $UID:$GID $HOME; \
    fi

# Conditional Ollama install (Debian-oriented installer, untested on the Wolfi
# base; the supported path is a sidecar Ollama container or a future Sprig™)
# curl comes and goes inside this one step, so the image keeps none.
RUN if [ "$USE_OLLAMA" = "true" ]; then \
    apk add --no-cache --virtual .ollama-fetch curl && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    apk del .ollama-fetch; \
    fi

# Create data directory
RUN mkdir -p /app/backend/data && \
    if [ $UID -ne 0 ]; then chown -R $UID:$GID /app/backend/data/ /app/backend/tiktoken_cache/; fi

EXPOSE 8080

# No curl or jq in the image since 3.2.1: the standard-library client checks
# that /health answers {"status": true}. Runs from WORKDIR /app/backend.
HEALTHCHECK CMD python3 -m sage_is_ai.utils.localhttp --require-true status "http://localhost:${PORT:-8080}/health" > /dev/null || exit 1

USER $UID:$GID

ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

CMD [ "bash", "restore_backup_start.sh", "server" ]
