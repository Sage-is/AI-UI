# syntax=docker/dockerfile:1.5
# Initialize device type args
# use build args in the docker build command with --build-arg="BUILDARG=true"
ARG USE_CUDA=false
ARG USE_OLLAMA=false
# Tested with cu117 for CUDA 11 and cu121 for CUDA 12 (default)
ARG USE_CUDA_VER=cu121
# any sentence transformer model; models to use can be found at https://huggingface.co/models?library=sentence-transformers
# Leaderboard: https://huggingface.co/spaces/mteb/leaderboard 
# for better performance and multilangauge support use "intfloat/multilingual-e5-large" (~2.5GB) or "intfloat/multilingual-e5-base" (~1.5GB)
# IMPORTANT: If you change the embedding model (sentence-transformers/all-MiniLM-L6-v2) and vice versa, you aren't able to use RAG Chat with your previous documents loaded in the WebUI! You need to re-embed them.
ARG USE_EMBEDDING_MODEL=intfloat/multilingual-e5-large
ARG USE_RERANKING_MODEL=""

# Tiktoken encoding name; models to use can be found at https://huggingface.co/models?library=tiktoken
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"

ARG BUILD_HASH=dev-build

# The following args are used to set the user and group id for the app user
# Override at your own risk 
# non-root configurations are untested
ARG UID=0
ARG GID=0

########### System #########
#FROM --platform=$BUILDPLATFORM node:22-bookworm AS build
FROM node:22-bookworm AS build
ARG BUILD_HASH

WORKDIR /app
# Install Node.js dependencies first (cache layer)
COPY app/package.json  /app/package.json
COPY app/package-lock.json /app/package-lock.json
RUN NODE_OPTIONS="--max-old-space-size=4096" npm install --legacy-peer-deps --loglevel verbose

# Install system packages (cache layer)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    build-essential \
    pandoc \
    netcat-openbsd \
    jq \
    gcc \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    libsm6 \
    libxext6 && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies early (cache layer)
COPY app/backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --upgrade pip --break-system-packages && \
    pip3 install --no-cache-dir uv --break-system-packages && \
    uv pip install --system -r /tmp/requirements.txt --no-cache-dir --break-system-packages

# Setup Pyodide early (cache layer - this is the build performance killer!)
COPY app/package.json /app/package.json
COPY app/scripts/prepare-pyodide.js /app/scripts/prepare-pyodide.js
RUN mkdir -p /app/static/pyodide && \
    NODE_OPTIONS="--max-old-space-size=4096" node scripts/prepare-pyodide.js


########### Copying files #########
COPY app/backend     /app/backend/
COPY app/cypress     /app/cypress/

COPY app/scripts     /app/scripts/
COPY app/test           /app/test/

#COPY app/.env  /app/.env
COPY app/.eslintrc.cjs /app/.eslintrc.cjs
COPY app/.prettierrc /app/.prettierrc

COPY app/cypress.config.ts /app/cypress.config.ts
COPY app/hatch_build.py /app/hatch_build.py
COPY app/i18next-parser.config.ts /app/i18next-parser.config.ts



########### WebUI backend #########
########## DEV_MODE Toggle #########
ARG DEV_MODE=false
ENV DEV_MODE=$DEV_MODE

# RUN echo "##### Set up dev server if DEV_MODE is true #####" && \
#     if [ "$DEV_MODE" = "true" ]; then \
#         echo "Setting up development mode..." && \
#         apt-get update && \
#         apt-get install -y --no-install-recommends unzip nodejs npm && \
#         npm install -g npm@latest && \
#         npm ci && \
#         NODE_OPTIONS="--max-old-space-size=4096" npm run build && \
#     else \
#         echo "Skipping development mode setup." && \
#         echo "Deleting unnecessary files..." && \
#         rm -rf src package.json package-lock.json; \
#     fi

######## Backup & Restore ########

RUN apt-get update && \
    apt-get install -y cron rclone bash-completion && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set default values for environment variables

ENV BACKUP_PATH=""
ENV BACKUP_CRON="0 2 *"  
# 2 AM EST (7 AM UTC)
ENV NOTIFY_URL=https://your-webhook-url.com/notify


# Use args
ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID

## Basis ##
ENV ENV=prod \
    PORT=8080 \
    STATIC_DIR=/app/static \
    # pass build args to the build
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

## Basis URL Config ##
ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

## API Key and Security Config ##
ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false

#### Other models #########################################################
## whisper TTS model settings ##
ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

## RAG Embedding model settings ##
ENV RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"


ENV USE_TIKTOKEN_ENCODING_NAME="o200k_base"
    ## Tiktoken model settings ##
ENV TIKTOKEN_ENCODING_NAME="$USE_TIKTOKEN_ENCODING_NAME" \
    TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken"

    
## Hugging Face download cache ##
ENV HF_HOME="/app/backend/data/cache/embedding/models"

## Torch Extensions ##
# ENV TORCH_EXTENSIONS_DIR="/.cache/torch_extensions"

#### Other models ##########################################################

WORKDIR /app/backend

ENV HOME=/root
# TODO: DRY improvement needed - consolidate all user creation and chown operations into single conditional block
# Create user and group if not root
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then \
        addgroup --gid $GID app; \
    fi; \
    adduser --uid $UID --gid $GID --home $HOME --disabled-password --no-create-home app; \
    fi

RUN mkdir -p $HOME/.cache/chroma
RUN echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id

# Make sure the user has access to the app and root directory (only if not root)
RUN if [ $UID -ne 0 ]; then \
    chown -R $UID:$GID /app $HOME; \
    fi


# Conditional installation of Ollama
RUN if [ "$USE_OLLAMA" = "true" ]; then \
    curl -fsSL https://ollama.com/install.sh | sh; \
    fi

# Python packages already installed above for better caching

# Model downloads moved to runtime initialization for faster builds
# See init_models.sh in backend for runtime model downloading
RUN if [ $UID -ne 0 ]; then \
    chown -R $UID:$GID /app/backend/data/; \
    fi

COPY app/postcss.config.js /app/postcss.config.js
COPY app/pyproject.toml /app/pyproject.toml

COPY app/svelte.config.js /app/svelte.config.js
COPY app/tailwind.config.js /app/tailwind.config.js

COPY app/tsconfig.json /app/tsconfig.json
COPY app/vite.config.ts /app/vite.config.ts

WORKDIR /app
# Copy static files early so they're included in frontend build
COPY app/static/ /app/build/

COPY app/src /app/src

# Build frontend (pyodide already fetched above so vite build should be much faster)
RUN NODE_OPTIONS="--max-old-space-size=4096" npx vite build 
#########################################################################################


WORKDIR /app/backend

# COPY app/backend files
COPY app/backend /app/backend

# Fix ownership only if not root (DRY improvement needed: consolidate all chown operations)
RUN if [ $UID -ne 0 ]; then \
    chown -R $UID:$GID /app/backend; \
    fi

# Copy static files to both locations to ensure they survive the config.py startup process (KISS fix)
# 1. Copy to where FastAPI initially expects them
COPY app/static/ /app/static/
# 2. Copy to build directory so config.py copies them back during startup
COPY app/static/ /app/backend/build/static/
#COPY app/backend/open_webui/static/ /app/backend/open_webui/static/

EXPOSE 8080

HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

USER $UID:$GID

ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

COPY app/CHANGELOG.md /app/CHANGELOG.md

CMD [ "bash", "restore_backup_start.sh", "server" ] \
    # To enable dev mode: \
    # 1. Set DEV_MODE=true during docker build: --build-arg DEV_MODE=true \
    # 2. Run: docker run -it --rm <image_name> npm run dev
