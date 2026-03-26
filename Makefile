# =============================================================================
# Sage-is-AI CI/CD Framework
# =============================================================================
# This Makefile is the project's Continuous Integration and Continuous
# Deployment (CI/CD) system. It is provider-agnostic — no GitHub Actions,
# no GitLab CI, no vendor lock-in.
#
# Runs on: Linux, macOS, Windows (WSL)
# Requires: make, bash, git, container runtime (podman or docker)
#
# Quick start:
#   make install_dev    — install dev/security tools
#   make scan           — run all security scans
#   make lint           — run all linters
#   make it_build       — build container image
#   make scan_container — scan built image for vulnerabilities
#   make it_run         — run the container
#   make help           — list all targets
# =============================================================================

# Load environment variables from .env if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Auto-detect container runtime (prefer podman, fall back to docker)
CONTAINER_RUNTIME ?= $(shell command -v podman 2>/dev/null || echo docker)

# Derive org/repo from git remote (e.g. git@github.com:Sage-is/AI-UI.git -> sage-is/ai-ui)
GIT_REPO_SLUG := $(shell git remote get-url origin 2>/dev/null | sed -E 's|\.git$$||; s|.*[:/]([^/]+/[^/]+)$$|\1|' | tr '[:upper:]' '[:lower:]')

# Configuration variables with defaults (override with .env file)
# Variables using ?= are only set if not already defined — so any value in
# .env (loaded above) takes priority.  This lets existing installs keep their
# current VOLUME_DATA (e.g. "sage-open-webui:/app/backend/data") while fresh
# installs get the new default.
IMAGE_NAME ?= $(GIT_REPO_SLUG)
GHCR_IMAGE_NAME ?= ghcr.io/$(GIT_REPO_SLUG)
GIT_TAG := $(shell git tag --sort=-v:refname | sed 's/^v//' | head -n 1)
IMAGE_TAG := $(if $(GIT_TAG),$(GIT_TAG),latest)
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
ifeq ($(GIT_BRANCH),HEAD)
    GIT_BRANCH := $(shell git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
endif
SAFE_GIT_BRANCH := $(subst /,-,$(GIT_BRANCH))
SAFE_GIT_BRANCH := $(shell echo $(SAFE_GIT_BRANCH) | tr '[:upper:]' '[:lower:]')
CONTAINER_NAME ?= $(shell echo $(GIT_REPO_SLUG) | tr '/' '-')
PORT_MAPPING ?= 8080:8080
VOLUME_DATA ?= sage-is-ai:/app/backend/data
ENV_FILE := $$(pwd)/.env:/app/.env
FRONTEND_SRC := $$(pwd)/app/src/:/app/src/
STATIC_SRC := $$(pwd)/app/static/:/app/static/
BACKEND_SRC := $$(pwd)/app/backend/:/app/backend/

# Release version detection (prefers release/* branch name, falls back to latest tag)
RELEASE_VERSION := $(shell git rev-parse --abbrev-ref HEAD | sed -n 's/^release\///p')
ifeq ($(RELEASE_VERSION),)
	RELEASE_VERSION := $(GIT_TAG)
endif

# Architectures to build for
ARCHITECTURES ?= amd64 arm64 # Not used at the moment

# ---------------------------------------------------------------------------
# Security & Dev Tool Paths
# ---------------------------------------------------------------------------
# Auto-detected from PATH. Override via .env or CLI:
#   make scan_sast SEMGREP=/opt/opengrep/bin/opengrep
#
# SEMGREP tries semgrep first, falls back to opengrep (the LGPL community fork).
# Both accept identical CLI flags and rule syntax.
GITLEAKS   ?= $(shell command -v gitleaks 2>/dev/null)
SEMGREP    ?= $(shell command -v semgrep 2>/dev/null || command -v opengrep 2>/dev/null)
BANDIT     ?= $(shell command -v bandit 2>/dev/null)
TRIVY      ?= $(shell command -v trivy 2>/dev/null)

# Guard macro: prints a helpful error if a required tool is missing.
# Usage: $(call require_tool,VAR_NAME,tool-name)
define require_tool
	@if [ -z "$($(1))" ]; then \
		echo "Error: $(2) not found in PATH. Run: make install_dev"; \
		exit 1; \
	fi
endef

help:
	@echo "======================================================="
	@echo "  $(IMAGE_NAME) by Startr.Cloud and Startr LLC "
	@echo ""
	@echo 'This is the default make command.'
	@echo "This command lists available make commands."
	@echo ""
	@echo "Usage examples:"
	@echo "  0) Setup .env:     make setup_env"
	@echo "  1) Build:          make it_build"
	@echo "  2) Run:            make it_run"
	@echo ""
	@echo "Available make commands:"
	@echo ""
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null \
		| awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$$@$$'
	@echo ""

# Environment setup helpers
setup_env:
	@chmod +x tools/setup_project_env.sh
	@tools/setup_project_env.sh

setup_env_auto:
	@chmod +x tools/setup_project_env.sh
	@tools/setup_project_env.sh --auto

setup_env_template:
	@chmod +x tools/setup_project_env.sh
	@tools/setup_project_env.sh --template

# Common docker run arguments
DOCKER_RUN_ARGS := --rm -p $(PORT_MAPPING) \
	--add-host=host.docker.internal:host-gateway \
	-v $(VOLUME_DATA) \
	-v $(ENV_FILE) \
	--name $(CONTAINER_NAME)

DEV_RUN_ARGS := --rm -p $(PORT_MAPPING) \
	--add-host=host.docker.internal:host-gateway \
	-p 5173:5173 \
	-v $(VOLUME_DATA) \
	-v $(ENV_FILE) \
	-v $(FRONTEND_SRC) \
	-v $(STATIC_SRC) \
	--name $(CONTAINER_NAME)

it_stop:
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME)

it_clean:
	$(CONTAINER_RUNTIME) system prune -f
	$(CONTAINER_RUNTIME) builder prune --force

it_gone:
	@echo "Forcefully stopping and removing $(CONTAINER_NAME)..."
	$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) || true
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) || true
	@echo "Container $(CONTAINER_NAME) has been removed"

# Build Docker Image with Branch Name
it_build:
	@echo "Building Docker image with BuildKit enabled..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --load -t $(IMAGE_NAME):$(IMAGE_TAG) \
	            -t $(IMAGE_NAME):latest \
	            -t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
	            -t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
	            .
	afplay /System/Library/Sounds/Glass.aiff

# Build Docker Image without Cache and with Branch Name
it_build_no_cache:
	@echo "Building Docker image without cache and with BuildKit enabled..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --no-cache --load -t $(IMAGE_NAME):$(IMAGE_TAG) \
	                     -t $(IMAGE_NAME):latest \
	                     -t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
	                     -t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
	                     .
	afplay /System/Library/Sounds/Glass.aiff


build_slim:
	# Build a slim version of the image from the Dockerimage
	# Note at the moment manual use of the site is required to build the slim version
	# we need to add selenium automation to the build process to automate this
	# see https://github.com/slimtoolkit/slim
	slim build --http-probe  --include-path /app/backend --include-path /app/static --continue-after=160  $(IMAGE_NAME)

it_run_slim:
	# Run the slim version of the image
	$(CONTAINER_RUNTIME) run $(DOCKER_RUN_ARGS) $(IMAGE_NAME).slim:latest


dev_run:
	$(CONTAINER_RUNTIME) run $(DEV_RUN_ARGS) $(IMAGE_NAME):$(IMAGE_TAG) bash -c "/app/backend/restore_backup_start.sh dev"

# Run targets
it_run:
	$(CONTAINER_RUNTIME) run $(DOCKER_RUN_ARGS) $(IMAGE_NAME):$(IMAGE_TAG)

# Combine build and dev run targets
it_build_n_dev_run: it_build
	afplay /System/Library/Sounds/Glass.aiff
	@make dev_run

# Combined build and run targets
it_build_n_run: it_build
	@make it_run

it_build_n_run_no_cache: it_build_no_cache
	@make it_run

# ---------------------------------------------------------------------------
# DB Upgrade Smoke Test
# ---------------------------------------------------------------------------
# Verifies that migrations (Peewee + Alembic) apply cleanly against a prior-
# version database snapshot.  Archives live in tools/db_snapshots/ (gitignored,
# synced via SyncThing / Backblaze B2).
#
# Usage:
#   make it_build            # build current image first
#   make test_db_upgrade     # run migration against archived DB
#
# The test copies the snapshot to a temp directory so the original is never
# mutated, boots the app inside Docker, and exits after migrations complete.
DB_SNAPSHOT_DIR := tools/db_snapshots
DB_TEST_CONTAINER := sage-db-upgrade-test

test_db_upgrade:
	@if [ ! -d "$(DB_SNAPSHOT_DIR)" ] || [ -z "$$(ls $(DB_SNAPSHOT_DIR)/*.sqlite 2>/dev/null)" ]; then \
		echo "Error: No .sqlite files found in $(DB_SNAPSHOT_DIR)/"; \
		echo "Place a DB snapshot (e.g. webui.1.1.1.db.sqlite) there first."; \
		echo "See $(DB_SNAPSHOT_DIR)/README.md for details."; \
		exit 1; \
	fi
	@echo "=== DB Upgrade Smoke Test ==="
	@# Copy snapshot to temp dir so container writes don't mutate the original
	@TMPDIR=$$(mktemp -d) && \
	SNAPSHOT=$$(ls -1 $(DB_SNAPSHOT_DIR)/*.sqlite | head -1) && \
	cp "$$SNAPSHOT" "$$TMPDIR/webui.db" && \
	echo "Source: $$SNAPSHOT ($$(du -h "$$SNAPSHOT" | cut -f1))" && \
	echo "Testing migrations against $(IMAGE_NAME):$(IMAGE_TAG)..." && \
	$(CONTAINER_RUNTIME) run --rm \
		-v "$$TMPDIR:/app/backend/data" \
		-v $(ENV_FILE) \
		--add-host=host.docker.internal:host-gateway \
		--name $(DB_TEST_CONTAINER) \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		bash -c '. /app/.env 2>/dev/null; [ -z "$$WEBUI_SECRET_KEY" ] && export WEBUI_SECRET_KEY=db-upgrade-test; cd /app/backend && timeout 60 python -c "from sage_is_ai.config import run_migrations; print(\"Migrations OK\")"' \
	&& echo "DB upgrade test PASSED ✓" \
	|| { echo "DB upgrade test FAILED ✗"; rm -rf "$$TMPDIR"; exit 1; }; \
	rm -rf "$$TMPDIR"

# Fresh DB smoke test — verifies clean schema creation from scratch.
test_db_fresh:
	@echo "=== Fresh DB Smoke Test ==="
	@TMPDIR=$$(mktemp -d) && \
	echo "Testing fresh schema creation against $(IMAGE_NAME):$(IMAGE_TAG)..." && \
	$(CONTAINER_RUNTIME) run --rm \
		-v "$$TMPDIR:/app/backend/data" \
		-v $(ENV_FILE) \
		--add-host=host.docker.internal:host-gateway \
		--name $(DB_TEST_CONTAINER)-fresh \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		bash -c '. /app/.env 2>/dev/null; [ -z "$$WEBUI_SECRET_KEY" ] && export WEBUI_SECRET_KEY=db-upgrade-test; cd /app/backend && timeout 60 python -c "from sage_is_ai.config import run_migrations; print(\"Fresh DB OK\")"' \
	&& echo "Fresh DB test PASSED ✓" \
	|| { echo "Fresh DB test FAILED ✗"; rm -rf "$$TMPDIR"; exit 1; }; \
	rm -rf "$$TMPDIR"

# GHCR login via gh CLI (requires write:packages scope)
ghcr_login:
	@echo "=== Logging into GHCR via gh CLI ==="
	@gh auth status >/dev/null 2>&1 || { echo "Error: gh CLI not authenticated. Run: gh auth login"; exit 1; }
	@gh auth token | docker login ghcr.io -u $$(gh api user -q .login) --password-stdin
	@echo "Logged into ghcr.io as $$(gh api user -q .login)"
	@echo ""
	@echo "If push is denied, ensure your token has write:packages scope:"
	@echo "  gh auth refresh -s write:packages"

# Ensure builder target
ensure_builder:
	@docker buildx inspect multi-arch-builder >/dev/null 2>&1 || docker buildx create --name multi-arch-builder --use

# Multi-architecture build+push helper
# Builds amd64 and arm64, creates manifest list, and pushes in one step.
# Replaces the old per-arch build → docker manifest create → push pattern
# which broke with buildx v0.10+ (provenance attestation wraps every push
# in a manifest list, and docker manifest create rejects manifest-list sources).
define build_multi_arch
	@make it_clean
	@make ensure_builder
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t $(1):$(IMAGE_TAG) \
		-t $(1):latest \
		--push .
endef

# Bring down container instances on each SAGE_HOST
it_down_sage_hosts:
	@echo "Bringing down instances on SAGE_HOSTS from .env file..."
	@if [ -f .env ]; then \
		grep -E "^SAGE_HOSTS=" .env | cut -d '=' -f2 | tr ',' '\n' | while read host; do \
			echo "Stopping containers on $$host..."; \
			ssh "$$host" "docker stop $$(docker ps -aqf 'name=sage*') && docker rm $$(docker ps -aqf 'name=sage*')" || echo "Failed to stop containers on $$host"; \
		done; \
	else \
		echo ".env file not found. Cannot read SAGE_HOSTS."; \
		exit 1; \
	fi

# Check for running Sage instances on each SAGE_HOST
it_check_sage_hosts:
	@echo "Checking for running Sage instances on SAGE_HOSTS from .env file..."
	@if [ -f .env ]; then \
		echo "Host                 | Container ID    | Name             | Image                | Status           | Created"; \
		echo "-------------------- | --------------- | ---------------- | -------------------- | ---------------- | ---------------"; \
		grep -E "^SAGE_HOSTS=" .env | cut -d '=' -f2 | tr ',' '\n' | while read host; do \
			echo "$$host:"; \
			ssh "$$host" "docker ps --format '{{.ID}} | {{.Names}} | {{.Image}} | {{.Status}} | {{.CreatedAt}}' -f 'name=sage*'" || echo "   Failed to connect to $$host"; \
			echo ""; \
		done; \
	else \
		echo ".env file not found. Cannot read SAGE_HOSTS."; \
		exit 1; \
	fi

# Main multi-arch build targets
it_build_multi_arch_push_docker_hub:
	@echo "Building multi-arch and pushing to Docker Hub"
	$(call build_multi_arch,$(IMAGE_NAME))
	@echo "Completed Docker Hub multi-arch push for version $(IMAGE_TAG)"

# Builds and pushes to the GitHub Container Registry
it_build_multi_arch_push_GHCR: ghcr_login
	@echo "Building multi-arch and pushing to GHCR"
	$(call build_multi_arch,$(GHCR_IMAGE_NAME))
	@echo "Completed GHCR multi-arch push for version $(IMAGE_TAG)"

# Build both registries
it_build_multi_arch_all: it_build_multi_arch_push_docker_hub it_build_multi_arch_push_GHCR
	@echo "Completed all multi-arch builds and pushes for version $(IMAGE_TAG)"

# Utility target to show current version
show-version:
	@echo "Current version: $(IMAGE_TAG)"

bump_release_version:
	@if [ -z "$(RELEASE_VERSION)" ]; then \
		echo "Error: RELEASE_VERSION not defined. Are you on a release/ branch?"; \
		exit 1; \
	fi
	@echo "Bumping version to $(RELEASE_VERSION)..."
	@# Update package.json using python (strip 'v' prefix if present)
	@python3 -c "import json; f='app/package.json'; d=json.load(open(f)); d['version']='$(RELEASE_VERSION)'.lstrip('v'); json.dump(d, open(f,'w'), indent='\t'); f2=open(f,'a'); f2.write('\n'); f2.close(); print(f'Updated {f}')"
	@# Update README.md header (ensure single 'v' prefix)
	@python3 -c "import re; f='README.md'; ver='$(RELEASE_VERSION)'.lstrip('v'); c=open(f).read(); n=re.sub(r'^## v.*', f'## v{ver}', c, count=1, flags=re.MULTILINE); open(f,'w').write(n); print(f'Updated {f}')"
	@echo "Version bumped to $(RELEASE_VERSION)"

# WAHA (WhatsApp HTTP API) for Messaging Bridges
WAHA_PORT ?= 3000
WAHA_CONTAINER_NAME ?= sage-waha
WAHA_IMAGE ?= devlikeapro/waha
WAHA_API_KEY ?=
WAHA_DASHBOARD_USER ?= admin
WAHA_DASHBOARD_PASSWORD ?= admin

waha_start:
	@echo "Starting WAHA (WhatsApp HTTP API) on port $(WAHA_PORT)..."
	$(CONTAINER_RUNTIME) run -d --rm \
		--name $(WAHA_CONTAINER_NAME) \
		-p $(WAHA_PORT):3000 \
		$(if $(WAHA_API_KEY),-e WHATSAPP_API_KEY=$(WAHA_API_KEY),) \
		-e WAHA_DASHBOARD_ENABLED=true \
		-e WAHA_DASHBOARD_USERNAME=$(WAHA_DASHBOARD_USER) \
		-e WAHA_DASHBOARD_PASSWORD=$(WAHA_DASHBOARD_PASSWORD) \
		$(WAHA_IMAGE)
	@echo ""
	@echo "WAHA is running:"
	@echo "  API:       http://localhost:$(WAHA_PORT)/api/"
	@echo "  Dashboard: http://localhost:$(WAHA_PORT)/dashboard"
	@echo "  Swagger:   http://localhost:$(WAHA_PORT)/api/docs"
	@echo ""
	@echo "Configure your Sage bridge with:"
	@echo "  WAHA API URL: http://host.docker.internal:$(WAHA_PORT)"
	@echo "  (use http://localhost:$(WAHA_PORT) if Sage is not in Docker)"

waha_stop:
	@echo "Stopping WAHA..."
	$(CONTAINER_RUNTIME) stop $(WAHA_CONTAINER_NAME) || true
	@echo "WAHA stopped"

waha_logs:
	$(CONTAINER_RUNTIME) logs -f $(WAHA_CONTAINER_NAME)

waha_status:
	@$(CONTAINER_RUNTIME) inspect --format='{{.State.Status}}' $(WAHA_CONTAINER_NAME) 2>/dev/null || echo "WAHA container is not running"

# signal-cli-rest-api for Signal Messaging Bridge
SIGNAL_PORT ?= 8081
SIGNAL_CONTAINER_NAME ?= sage-signal
SIGNAL_IMAGE ?= bbernhard/signal-cli-rest-api
SIGNAL_DATA_DIR ?= $(HOME)/.local/share/signal-cli-sage

signal_start:
	@echo "Starting signal-cli-rest-api on port $(SIGNAL_PORT)..."
	@mkdir -p $(SIGNAL_DATA_DIR)
	$(CONTAINER_RUNTIME) run -d --rm \
		--name $(SIGNAL_CONTAINER_NAME) \
		-p $(SIGNAL_PORT):8080 \
		-v $(SIGNAL_DATA_DIR):/home/.local/share/signal-cli \
		-e 'MODE=json-rpc' \
		$(SIGNAL_IMAGE)
	@echo ""
	@echo "signal-cli-rest-api is running:"
	@echo "  API:     http://localhost:$(SIGNAL_PORT)"
	@echo "  Swagger: http://localhost:$(SIGNAL_PORT)/v1/about"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Register a number or link a device:"
	@echo "     Link:     open http://localhost:$(SIGNAL_PORT)/v1/qrcodelink?device_name=sage-bridge"
	@echo "     Register: curl -X POST http://localhost:$(SIGNAL_PORT)/v1/register/+1234567890"
	@echo "  2. Configure your Sage bridge with:"
	@echo "     API URL: http://host.docker.internal:$(SIGNAL_PORT)"
	@echo "     (use http://localhost:$(SIGNAL_PORT) if Sage is not in Docker)"

signal_stop:
	@echo "Stopping signal-cli-rest-api..."
	$(CONTAINER_RUNTIME) stop $(SIGNAL_CONTAINER_NAME) || true
	@echo "signal-cli-rest-api stopped"

signal_logs:
	$(CONTAINER_RUNTIME) logs -f $(SIGNAL_CONTAINER_NAME)

signal_status:
	@$(CONTAINER_RUNTIME) inspect --format='{{.State.Status}}' $(SIGNAL_CONTAINER_NAME) 2>/dev/null || echo "signal-cli-rest-api container is not running"

# ===========================================================================
# Developer Setup & Security Scanning (CI)
# ===========================================================================
# All scanning tools run 100% locally with no cloud endpoints.
# Tools: gitleaks (secrets), semgrep/opengrep (SAST), bandit (Python SAST),
#        trivy (dependency & container vulnerabilities).
#
# Workflow:
#   make install_dev     — one-time setup: install tools + git hooks
#   make scan            — run all security scans (safe anytime, no build needed)
#   make scan_container  — scan a built container image (run after make it_build)
#   make lint            — run all linters (eslint, prettier, black)
# ===========================================================================

# install_dev: Install all security/dev tools and wire up pre-commit git hooks.
# Homebrew is the universal package manager — works on macOS, Linux, and WSL.
# If brew isn't installed, we install it first, then use it for everything.
install_dev:
	@echo "=== Installing security & dev tools ==="
	@echo ""
	@# --- Ensure Homebrew is available (macOS, Linux, WSL) ---
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "Homebrew not found — installing (https://brew.sh)..."; \
		echo ""; \
		/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
		echo ""; \
		echo "NOTE: You may need to restart your shell or run the commands"; \
		echo "      printed above to add brew to your PATH, then re-run:"; \
		echo "      make install_dev"; \
		echo ""; \
	fi
	@# --- All tools via brew (single package manager, DRY) ---
	@echo "Installing tools via Homebrew..."
	brew install gitleaks trivy semgrep pre-commit
	@# bandit is Python-only, not in brew — install via pip
	@echo ""
	@echo "Installing bandit (Python SAST)..."
	pip install --user bandit
	@echo ""
	@# --- Wire up pre-commit git hooks ---
	@echo "Installing pre-commit git hooks (.pre-commit-config.yaml)..."
	pre-commit install
	@echo ""
	@echo "Done. Verify with: make scan"

# ---------------------------------------------------------------------------
# Security Scanning Targets
# ---------------------------------------------------------------------------

# scan: Run all security scans (secrets + SAST + dependency).
# Does NOT include scan_container (requires a built image) or scan_dast (future).
scan: scan_secrets scan_sast scan_deps
	@echo ""
	@echo "=== All scans complete ==="

# scan_secrets: Detect accidentally committed secrets, API keys, tokens.
# Uses gitleaks against the full git history. Config: .gitleaks.toml
scan_secrets:
	$(call require_tool,GITLEAKS,gitleaks)
	@echo "=== Secrets scan (gitleaks) ==="
	$(GITLEAKS) detect --source . --config .gitleaks.toml --verbose

# scan_sast: Static Application Security Testing.
# - semgrep/opengrep: JS/TS/Svelte frontend + Python backend (offline rules in .semgrep/)
# - bandit: Python-specific security checks (config: .bandit.yaml)
scan_sast:
	$(call require_tool,SEMGREP,semgrep/opengrep)
	$(call require_tool,BANDIT,bandit)
	@echo "=== SAST: JS/TS/Svelte (semgrep) ==="
	$(SEMGREP) scan --config .semgrep/ --include="*.js" --include="*.ts" --include="*.svelte" app/src/
	@echo ""
	@echo "=== SAST: Python (bandit) ==="
	$(BANDIT) -r app/backend/sage_is_ai/ -c .bandit.yaml -ll
	@echo ""
	@echo "=== SAST: Python (semgrep) ==="
	$(SEMGREP) scan --config .semgrep/ --include="*.py" app/backend/sage_is_ai/

# scan_deps: Scan lockfiles/requirements for known vulnerabilities (CVEs).
# Targets specific manifest files — does NOT crawl node_modules.
scan_deps:
	$(call require_tool,TRIVY,trivy)
	@echo "=== Dependency scan: Python (trivy) ==="
	$(TRIVY) fs --scanners vuln app/backend/requirements.txt
	@echo ""
	@echo "=== Dependency scan: Node (trivy) ==="
	$(TRIVY) fs --scanners vuln app/package-lock.json

# scan_container: Scan a built container image for OS-level & library vulnerabilities.
# Run after 'make it_build'. Uses the same IMAGE_NAME/IMAGE_TAG as build targets.
scan_container:
	$(call require_tool,TRIVY,trivy)
	@echo "=== Container image scan (trivy) ==="
	$(TRIVY) image --severity HIGH,CRITICAL $(IMAGE_NAME):$(IMAGE_TAG)

# scan_dast: Dynamic Application Security Testing (STUB — future TODO).
# Requires a running staging environment. See TODO.md for the full plan:
# staging CapRover + Selenium/SikuliX regression + OWASP ZAP proxy.
scan_dast:
	@echo "=== DAST scan ==="
	@echo "[STUB] DAST scanning requires a running staging environment."
	@echo "TODO: staging CapRover + Selenium/SikuliX + OWASP ZAP proxy."
	@echo "See TODO.md for the full plan."

# trivy_db_update: Pre-cache the Trivy vulnerability database for offline use.
# After running this, scans work offline with: TRIVY_SKIP_DB_UPDATE=true make scan_deps
trivy_db_update:
	$(call require_tool,TRIVY,trivy)
	@echo "Downloading/updating Trivy vulnerability database..."
	$(TRIVY) image --download-db-only
	@echo "DB cached at: ~/.cache/trivy/db/"
	@echo "For offline scans: TRIVY_SKIP_DB_UPDATE=true make scan_deps"

# ---------------------------------------------------------------------------
# Linting (CI)
# ---------------------------------------------------------------------------
# Rollup target that calls existing lint scripts from package.json + black.
# Complements (does not replace) the per-tool npm scripts.

# lint: Run all linters — eslint, svelte-check, prettier, black.
lint:
	@echo "=== Frontend lint (eslint + svelte-check) ==="
	cd app && npm run lint:frontend
	cd app && npm run lint:types
	@echo ""
	@echo "=== Format check (prettier + black) ==="
	cd app && npx prettier --check "**/*.{js,ts,svelte,css,md,html,json}" || true
	cd app && black --check --exclude ".venv/|/venv/" backend/ || true

# ===========================================================================

.PHONY: it_build it_build_no_cache dev_run it_run it_build_n_run it_build_n_run_no_cache \
	ghcr_login \
	it_build_multi_arch_push_docker_hub it_build_multi_arch_push_GHCR \
	it_build_multi_arch_all show-version setup_env setup_env_auto setup_env_template \
	bump_release_version release_and_push_GHCR hotfix_and_push_GHCR \
	waha_start waha_stop waha_logs waha_status \
	signal_start signal_stop signal_logs signal_status \
	install_dev scan scan_secrets scan_sast scan_deps scan_container scan_dast \
	trivy_db_update lint test_db_upgrade test_db_fresh


# Version Management with Git Flow
# --------------------------------
# These commands manage semantic versioning with Git Flow workflow.
# All version tags start with 'v' (e.g., v1.2.3) following semantic versioning principles:
# - major_release: Increments the first number (e.g., v1.2.3 -> v2.0.0)
# - minor_release: Increments the second number (e.g., v1.2.3 -> v1.3.0)
# - patch_release: Increments the third number (e.g., v1.2.3 -> v1.2.4)
# - hotfix: Adds or increments a fourth number (e.g., v1.2.3 -> v1.2.3.1)
#
# The 'v' prefix is consistently preserved in all version tags and branches.

minor_release:
	@# Start a minor release with incremented minor version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2+1".0"}')
	@echo ""
	@echo "=== Release branch created ==="
	@echo "Next steps:"
	@echo "  1. make bump_release_version     # Update package.json + README.md"
	@echo "  2. Update CHANGELOG.md with release notes"
	@echo "  3. git add -A && git commit      # Commit version bump + changelog"
	@echo "  4. make it_build                 # Build Docker image"
	@echo "  5. make test_db_upgrade          # Verify DB migrations"
	@echo "  6. make test_db_fresh            # Verify fresh DB creation"
	@echo "  7. make it_run                   # Smoke test the app"
	@echo "  8. make ghcr_login               # Authenticate with GHCR"
	@echo "  9. make release_and_push_GHCR    # Finish release + push to GHCR"

patch_release:
	@# Start a patch release with incremented patch version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}')
	@echo ""
	@echo "=== Release branch created ==="
	@echo "Next steps:"
	@echo "  1. make bump_release_version     # Update package.json + README.md"
	@echo "  2. Update CHANGELOG.md with release notes"
	@echo "  3. git add -A && git commit      # Commit version bump + changelog"
	@echo "  4. make it_build                 # Build Docker image"
	@echo "  5. make test_db_upgrade          # Verify DB migrations"
	@echo "  6. make test_db_fresh            # Verify fresh DB creation"
	@echo "  7. make it_run                   # Smoke test the app"
	@echo "  8. make ghcr_login               # Authenticate with GHCR"
	@echo "  9. make release_and_push_GHCR    # Finish release + push to GHCR"

major_release:
	@# Start a major release with incremented major version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1+1".0.0"}')
	@echo ""
	@echo "=== Release branch created ==="
	@echo "Next steps:"
	@echo "  1. make bump_release_version     # Update package.json + README.md"
	@echo "  2. Update CHANGELOG.md with release notes"
	@echo "  3. git add -A && git commit      # Commit version bump + changelog"
	@echo "  4. make it_build                 # Build Docker image"
	@echo "  5. make test_db_upgrade          # Verify DB migrations"
	@echo "  6. make test_db_fresh            # Verify fresh DB creation"
	@echo "  7. make it_run                   # Smoke test the app"
	@echo "  8. make ghcr_login               # Authenticate with GHCR"
	@echo "  9. make release_and_push_GHCR    # Finish release + push to GHCR"

hotfix:
	@# Start a hotfix with incremented patch.patch version (fourth component)
	git flow hotfix start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{if (NF < 4) print $$1"."$$2"."$$3".1"; else print $$1"."$$2"."$$3"."$$4+1}')
	@echo ""
	@echo "=== Hotfix branch created ==="
	@echo "Next steps:"
	@echo "  1. Fix the issue"
	@echo "  2. make bump_release_version     # Update package.json + README.md"
	@echo "  3. git add -A && git commit      # Commit fix + version bump"
	@echo "  4. make it_build                 # Build Docker image"
	@echo "  5. make test_db_upgrade          # Verify DB migrations"
	@echo "  6. make it_run                   # Smoke test the app"
	@echo "  7. make ghcr_login               # Authenticate with GHCR"
	@echo "  8. make hotfix_and_push_GHCR     # Finish hotfix + push to GHCR"

release_finish:
	@echo "=== Finishing release ==="
	@echo "Merging to master, tagging, pushing..."
	git flow release finish "$$(git branch --show-current | sed 's/release\///')" && git push origin develop && git push origin master && git push --tags && git checkout develop
	@echo ""
	@echo "=== Release complete ==="
	@echo "Tag: v$(IMAGE_TAG)"
	@echo "Pushed: develop, master, tags"

hotfix_finish:
	@echo "=== Finishing hotfix ==="
	@echo "Merging to master, tagging, pushing..."
	git flow hotfix finish "$$(git branch --show-current | sed 's/hotfix\///')" && git push origin develop && git push origin master && git push --tags && git checkout develop
	@echo ""
	@echo "=== Hotfix complete ==="

release_and_push_GHCR: release_finish
	@echo ""
	@echo "=== Building and pushing to GHCR ==="
	@make it_build_multi_arch_push_GHCR
	@echo ""
	@echo "=== Release $(IMAGE_TAG) published ==="
	@echo "Verify: docker pull $(GHCR_IMAGE_NAME):$(IMAGE_TAG)"
	@echo "Verify: docker pull $(GHCR_IMAGE_NAME):latest"

hotfix_and_push_GHCR: hotfix_finish
	@echo ""
	@echo "=== Building and pushing to GHCR ==="
	@make it_build_multi_arch_push_GHCR
	@echo ""
	@echo "=== Hotfix $(IMAGE_TAG) published ==="
	@echo "Verify: docker pull $(GHCR_IMAGE_NAME):$(IMAGE_TAG)"

things_clean:
	git clean --exclude=!.env -Xdf


it_deploy:
	caprover deploy --default

it_start:
	$(CONTAINER_RUNTIME) start $(CONTAINER_NAME)

it_start_and_build: it_build
	$(CONTAINER_RUNTIME) start $(CONTAINER_NAME)

it_update:
	@echo "Pulling latest changes and rebuilding container..."
	@git pull
	$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) || true
	@make it_build
	@make it_run