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

# Load canonical distribution facts (hardlinked from homebrew-apps).
# Missing-OK — fresh clones run `make distribution_sync` to establish it.
-include distribution.env
export

# Load environment variables from .env if it exists.
# Loaded AFTER distribution.env so per-machine .env values can override
# canonical defaults.
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Auto-detect container runtime (prefer podman, fall back to docker)
CONTAINER_RUNTIME ?= $(shell command -v podman 2>/dev/null || echo docker)

# Cross-platform "build complete" chime.
# macOS: plays the system Glass sound. Linux/WSL/Windows: silent no-op.
# Resolved once at parse time so per-site call sites stay one line.
NOTIFY_DONE := $(shell command -v afplay >/dev/null 2>&1 && echo "afplay /System/Library/Sounds/Glass.aiff" || echo "true")

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

# Release version detection. Prefers release/X.Y.Z or hotfix/X.Y.Z branch name
# so that `make it_build` on a release branch tags the *new* version, not the
# *previous* one. Falls back to GIT_TAG so off-release-branch behavior is
# unchanged.
RELEASE_VERSION := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null | awk '/^(release|hotfix)\// { sub(/^(release|hotfix)\//, ""); print }')
ifeq ($(RELEASE_VERSION),)
    RELEASE_VERSION := $(GIT_TAG)
endif

# Precedence: release/hotfix branch version > git tag > distribution.env SERVER_TAG > latest.
# RELEASE_VERSION already collapses (branch || tag), so this just adds the
# SERVER_TAG and latest fallbacks for a totally empty repo.
IMAGE_TAG := $(if $(RELEASE_VERSION),$(RELEASE_VERSION),$(or $(SERVER_TAG),latest))
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
ifeq ($(GIT_BRANCH),HEAD)
    GIT_BRANCH := $(shell git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
endif
SAFE_GIT_BRANCH := $(subst /,-,$(GIT_BRANCH))
SAFE_GIT_BRANCH := $(shell echo $(SAFE_GIT_BRANCH) | tr '[:upper:]' '[:lower:]')
# OCI image provenance labels (org.opencontainers.image.*). Applied to every
# build target below so `docker inspect` + CapRover's deploy-history git-hash
# column show source + version + creation provenance. Without these, image-pull
# deploys display `n/a` in CapRover's hash column.
OCI_LABELS := --label org.opencontainers.image.revision=$(shell git rev-parse HEAD) \
              --label org.opencontainers.image.source=https://github.com/Sage-is/AI-UI \
              --label org.opencontainers.image.version=$(IMAGE_TAG) \
              --label org.opencontainers.image.created=$(shell date -u +%Y-%m-%dT%H:%M:%SZ) \
              --label org.opencontainers.image.title=Sage.is-AI-UI \
              --label org.opencontainers.image.licenses=MIT
CONTAINER_NAME ?= $(shell echo $(GIT_REPO_SLUG) | tr '/' '-')
PORT_MAPPING ?= 8080:8080
# Host-side port from PORT_MAPPING (`HOST:CONTAINER` → HOST). Reference this
# in help text and curl URLs so they track when PORT_MAPPING is overridden.
LOCAL_PORT := $(firstword $(subst :, ,$(PORT_MAPPING)))
# Default volume comes from distribution.env (VOLUME + DATA_MOUNT). Fresh
# installs land on `sage-ai-data:/app/backend/data`; existing installs with
# a `.env` override keep their old volume name via the ?= precedence.
VOLUME_DATA ?= $(or $(VOLUME),sage-ai-data):$(or $(DATA_MOUNT),/app/backend/data)
ENV_FILE := $$(pwd)/.env:/app/.env
FRONTEND_SRC := $$(pwd)/app/src/:/app/src/
STATIC_SRC := $$(pwd)/app/static/:/app/static/
BACKEND_SRC := $$(pwd)/app/backend/:/app/backend/

# (RELEASE_VERSION defined above, near GIT_TAG, so IMAGE_TAG can read it.)

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
	@echo "  0a) Fresh setup:   make setup        # .env + sibling hardlinks"
	@echo "  0b) .env only:     make setup_env"
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

## setup_siblings — establish the distribution.env hardlink chain across siblings.
##
## Verifies that ../homebrew-apps and ../WEB-Sage.Education-docs are checked
## out as siblings. If either is missing, prints the exact `git clone` command
## and exits non-zero (machine stops itself — jidoka). If all three are
## present, calls distribution_sync to (re)establish the hardlinks.
##
## Run once on a fresh machine. Idempotent — safe to re-run.
setup_siblings:
	@chmod +x tools/setup_siblings.sh
	@tools/setup_siblings.sh

## setup — fresh-machine bootstrap. Runs setup_env + setup_siblings.
setup: setup_env setup_siblings
	@echo ""
	@echo "=== Setup complete ==="
	@echo "    Next: make it_build && make it_run"

# Base flags every container run needs. DOCKER_RUN_ARGS and
# TRY_SAGE_DOCKER_RUN_ARGS both extend this — add a flag here and it
# applies to both production and trial runs.
COMMON_RUN_ARGS := --rm -p $(PORT_MAPPING) \
	--add-host=host.docker.internal:host-gateway \
	-v $(ENV_FILE) \
	--name $(CONTAINER_NAME)

# Production run: COMMON + secret-key pass-through + prod volume.
DOCKER_RUN_ARGS := $(COMMON_RUN_ARGS) \
	$(if $(WEBUI_SECRET_KEY),-e WEBUI_SECRET_KEY=$(WEBUI_SECRET_KEY),) \
	-v $(VOLUME_DATA)

DEV_RUN_ARGS := --rm -p $(PORT_MAPPING) \
	--add-host=host.docker.internal:host-gateway \
	-p 5173:5173 \
	$(if $(WEBUI_SECRET_KEY),-e WEBUI_SECRET_KEY=$(WEBUI_SECRET_KEY),) \
	-v $(VOLUME_DATA) \
	-v $(ENV_FILE) \
	-v $(FRONTEND_SRC) \
	-v $(STATIC_SRC) \
	-v $$(pwd)/app/svelte.config.js:/app/svelte.config.js \
	-v $$(pwd)/app/vite.config.ts:/app/vite.config.ts \
	-v $$(pwd)/app/tsconfig.json:/app/tsconfig.json \
	-v $$(pwd)/app/postcss.config.js:/app/postcss.config.js \
	-v $$(pwd)/app/tailwind.config.js:/app/tailwind.config.js \
	-v $$(pwd)/app/package.json:/app/package.json \
	--name $(CONTAINER_NAME)

it_stop:
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME)

it_clean:
	$(CONTAINER_RUNTIME) system prune -f
	$(CONTAINER_RUNTIME) builder prune --force
	@echo ""

it_gone:
	@echo "Forcefully stopping and removing $(CONTAINER_NAME)..."
	$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) || true
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) || true
	@echo "Container $(CONTAINER_NAME) has been removed"

# Build Docker Image with Branch Name
it_build:
	@echo "Building Docker image with BuildKit enabled..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --load $(OCI_LABELS) -t $(IMAGE_NAME):$(IMAGE_TAG) \
	            -t $(IMAGE_NAME):latest \
	            -t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
	            -t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
	            .
	@$(NOTIFY_DONE)
	@echo ""

# Build Docker Image without Cache and with Branch Name
it_build_no_cache:
	@echo "Building Docker image without cache and with BuildKit enabled..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --no-cache --load $(OCI_LABELS) -t $(IMAGE_NAME):$(IMAGE_TAG) \
	                     -t $(IMAGE_NAME):latest \
	                     -t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
	                     -t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
	                     .
	@$(NOTIFY_DONE)
	@echo ""

dev_run:
	$(CONTAINER_RUNTIME) run $(DEV_RUN_ARGS) $(IMAGE_NAME):$(IMAGE_TAG) bash -c "/app/backend/restore_backup_start.sh dev"

# Run targets
it_run:
	$(CONTAINER_RUNTIME) run $(DOCKER_RUN_ARGS) $(IMAGE_NAME):$(IMAGE_TAG)

it_run_ghcr:
	$(CONTAINER_RUNTIME) run $(DOCKER_RUN_ARGS) $(GHCR_IMAGE_NAME):$(IMAGE_TAG)

# Combine build and dev run targets
it_build_n_dev_run: it_build
	@$(NOTIFY_DONE)
	@echo ""
	@make dev_run

# Combined build and run targets
it_build_n_run: it_build
	@make it_run

it_build_n_run_no_cache: it_build_no_cache
	@make it_run

# Build and run with a throwaway volume (fresh-install test)
# Cleans up the test volume on exit so it's ready for the next run.
it_build_n_test_fresh: it_build
	@echo "Running with fresh test volume (sage-test-data)..."
	-$(CONTAINER_RUNTIME) run --rm -p $(PORT_MAPPING) -v sage-test-data:/app/backend/data $(IMAGE_NAME):latest
	-$(CONTAINER_RUNTIME) volume rm sage-test-data 2>/dev/null || true
	@echo "Test volume cleaned up."

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
DB_SNAPSHOT ?=
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
	SNAPSHOT=$$([ -n "$(DB_SNAPSHOT)" ] && echo "$(DB_SNAPSHOT_DIR)/$(DB_SNAPSHOT)" || ls -1 $(DB_SNAPSHOT_DIR)/*.sqlite | head -1) && \
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
## wizard_smoke — drive the AI Engine setup wizard end-to-end via API.
##
## Boots a clean container off $(IMAGE_NAME):$(IMAGE_TAG), signs up the
## canonical test user (test@example.com / zaq12wsx — convention; never use
## in production), triggers the wizard, polls until the embedding model is
## ready, and exercises the file-upload → add-to-knowledge-base path that
## returns 400 when ml_packages is broken. Exits non-zero on any failure.
##
## Use this BEFORE pushing :latest to GHCR. The structural alternative
## (build-time stage that catches conflicts before tagging) lands once we
## prove this loop is stable.
wizard_smoke:
	@scripts/wizard-smoke.sh $(IMAGE_NAME):$(IMAGE_TAG)

## it_build_amd64 — build an amd64 image via buildx + --load.
##
## Useful on Apple Silicon to validate the same image teammates will run
## on x86_64 Linux hosts (CapRover, GHCR consumers, etc). Slower than the
## native build because layers are emulated. Tag is suffixed `-amd64` so
## it sits beside the host-arch image without overwriting it.
it_build_amd64:
	@echo "Building Docker image for linux/amd64 via buildx..."
	@docker buildx build --platform linux/amd64 --load $(OCI_LABELS) \
	    -t $(IMAGE_NAME):$(IMAGE_TAG)-amd64 \
	    .
	@$(NOTIFY_DONE)
	@echo ""

## cross_smoke — build the amd64 image then smoke it via QEMU.
##
## End-to-end cross-arch verification on a single host. Same flow as
## `wizard_smoke` but with PLATFORM=linux/amd64 and a longer timeout
## because QEMU emulation is 3-5x slower than native. Use this in place
## of "ask a teammate to run smoke on amd64."
cross_smoke: it_build_amd64
	@INSTALL_TIMEOUT_SEC=2700 PLATFORM=linux/amd64 \
	  scripts/wizard-smoke.sh $(IMAGE_NAME):$(IMAGE_TAG)-amd64

## release_smoke — one-button pre-flight for the current release branch.
##
## Refuses to run unless on `release/X.Y.Z`. Derives the version from the
## branch name (no IMAGE_TAG to mistype). Builds `sage-is/ai-ui:X.Y.Z`,
## smokes it natively, then builds + smokes the amd64 variant via Rosetta.
## Poka-yoke: operator can't smoke against the wrong tag, can't forget
## either arch, can't skip the rebuild before push.
##
## Use this AS the last step before `make release_and_push_GHCR`.
release_smoke:
	@case "$(GIT_BRANCH)" in \
	  release/*|hotfix/*) ;; \
	  *) echo "ERROR: release_smoke must run from a release/X.Y.Z or hotfix/X.Y.Z branch."; \
	     echo "       current branch: $(GIT_BRANCH)"; \
	     echo "       Run 'make patch_release' (or minor_release / major_release / hotfix) first."; \
	     exit 1;; \
	esac
	@if [ -z "$(RELEASE_VERSION)" ]; then \
	  echo "ERROR: RELEASE_VERSION empty despite being on a release/* branch."; \
	  echo "       Branch name parse failed? GIT_BRANCH=$(GIT_BRANCH)"; \
	  exit 1; \
	fi
	@if ! git diff --quiet HEAD; then \
	  echo "ERROR: working tree has uncommitted changes."; \
	  echo "       release_smoke must validate what release_finish will tag,"; \
	  echo "       and release_finish only pushes what's committed."; \
	  git status --short; \
	  exit 1; \
	fi
	@PKG_VER=$$(python3 -c "import json; print(json.load(open('app/package.json'))['version'])" 2>/dev/null); \
	 if [ "$$PKG_VER" != "$(RELEASE_VERSION)" ]; then \
	  echo "ERROR: app/package.json version is $$PKG_VER but RELEASE_VERSION is $(RELEASE_VERSION)."; \
	  echo "       Run 'make bump_release_version' first."; \
	  exit 1; \
	fi
	@echo ""
	@echo "=== release_smoke for $(RELEASE_VERSION) ==="
	@echo "  branch: $(GIT_BRANCH)"
	@echo "  tag:    $(IMAGE_NAME):$(RELEASE_VERSION)"
	@echo ""
	@$(MAKE) it_build IMAGE_TAG=$(RELEASE_VERSION)
	@$(MAKE) wizard_smoke IMAGE_TAG=$(RELEASE_VERSION)
	@$(MAKE) cross_smoke IMAGE_TAG=$(RELEASE_VERSION)
	@echo ""
	@echo "=== $(RELEASE_VERSION) smoke-clean on native arch + linux/amd64 ==="
	@echo "    Next: deploy to staging, verify, then 'make release_and_push_GHCR'."
	@$(NOTIFY_DONE)

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
	docker buildx build --platform linux/amd64,linux/arm64 $(OCI_LABELS) \
		-t $(1):$(IMAGE_TAG) \
		-t $(1):latest \
		--push .
endef

# Bring down container instances on each SAGE_HOST
it_down_sage_hosts:
	@echo "Bringing down instances on SAGE_HOSTS from .env file..."
	@[ -f .env ] || { echo "ERROR: .env file not found. Cannot read SAGE_HOSTS."; exit 1; }
	@hosts=$$(grep -E "^SAGE_HOSTS=" .env | cut -d '=' -f2 | tr ',' '\n' | grep -v '^$$'); \
	[ -n "$$hosts" ] || { echo "ERROR: SAGE_HOSTS missing or empty in .env"; exit 1; }; \
	echo "$$hosts" | while read host; do \
		echo "Stopping containers on $$host..."; \
		ssh "$$host" "docker stop $$(docker ps -aqf 'name=sage*') && docker rm $$(docker ps -aqf 'name=sage*')" || echo "Failed to stop containers on $$host"; \
	done

# Check for running Sage instances on each SAGE_HOST
it_check_sage_hosts:
	@echo "Checking for running Sage instances on SAGE_HOSTS from .env file..."
	@[ -f .env ] || { echo "ERROR: .env file not found. Cannot read SAGE_HOSTS."; exit 1; }
	@hosts=$$(grep -E "^SAGE_HOSTS=" .env | cut -d '=' -f2 | tr ',' '\n' | grep -v '^$$'); \
	[ -n "$$hosts" ] || { echo "ERROR: SAGE_HOSTS missing or empty in .env"; exit 1; }; \
	echo "Host                 | Container ID    | Name             | Image                | Status           | Created"; \
	echo "-------------------- | --------------- | ---------------- | -------------------- | ---------------- | ---------------"; \
	echo "$$hosts" | while read host; do \
		echo "$$host:"; \
		ssh "$$host" "docker ps --format '{{.ID}} | {{.Names}} | {{.Image}} | {{.Status}} | {{.CreatedAt}}' -f 'name=sage*'" || echo "   Failed to connect to $$host"; \
		echo ""; \
	done

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

# ---------------------------------------------------------------------------
# Dependency Management (bun — runs inside Docker)
# ---------------------------------------------------------------------------
# All npm/bun operations happen inside a container. No local Node.js needed.
#   make bun_install  — regenerate bun.lock from package.json
#   make bun_add PKG=<name>  — add a package and update lockfile
#   make bun_run CMD=<cmd>   — run an arbitrary bun command in the app dir

BUN_IMAGE ?= oven/bun:1-debian
BUN_RUN   := $(CONTAINER_RUNTIME) run --rm -v "$$(pwd)/app:/app" -w /app $(BUN_IMAGE)

# bun_install: Regenerate bun.lock from package.json (after editing versions).
bun_install:
	$(BUN_RUN) bun install

# bun_add: Add or upgrade a package. Usage: make bun_add PKG="socket.io-client@^4.8.3"
bun_add:
	@[ -n "$(PKG)" ] || { echo "Usage: make bun_add PKG=<package>"; exit 1; }
	$(BUN_RUN) bun add $(PKG)

# bun_run: Run an arbitrary bun command. Usage: make bun_run CMD="outdated"
bun_run:
	@[ -n "$(CMD)" ] || { echo "Usage: make bun_run CMD=<command>"; exit 1; }
	$(BUN_RUN) bun $(CMD)

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
	@$(MAKE) install_hooks
	@echo ""
	@echo "Done. Verify with: make scan"

# install_hooks: Wire pre-commit framework hooks for all stages we use.
# Idempotent — re-running is safe and overwrites any existing stub.
#
# Stages installed:
#   pre-commit      gitleaks, bandit, codespell, hygiene, audit-deps,
#                   distribution-chain-verify (refuse if hardlink chain broken)
#   post-checkout   distribution-chain-heal (silent re-link if chain broken
#                   and content matches; warn if content diverges)
#   post-merge      distribution-chain-heal
#   post-rewrite    distribution-chain-heal (covers rebase + commit --amend)
install_hooks:
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "ERROR: pre-commit not installed. Run: make install_dev"; \
		exit 1; \
	}
	@echo "Installing pre-commit hooks (commit + checkout + merge + rewrite stages)..."
	pre-commit install
	pre-commit install --hook-type post-checkout
	pre-commit install --hook-type post-merge
	pre-commit install --hook-type post-rewrite
	@echo "Hooks wired. distribution.env hardlink chain is now self-healing."

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
	$(TRIVY) fs --scanners vuln app/bun.lock

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
# Complements (does not replace) the per-tool bun scripts.

# lint: Run all linters — eslint, svelte-check, prettier, black.
lint:
	@echo "=== Frontend lint (eslint + svelte-check) ==="
	cd app && bun run lint:frontend
	cd app && bun run lint:types
	@echo ""
	@echo "=== Format check (prettier + black) ==="
	cd app && bunx prettier --check "**/*.{js,ts,svelte,css,md,html,json}"
	cd app && black --check --exclude ".venv/|/venv/" backend/

# ===========================================================================

.PHONY: release it_build it_build_no_cache dev_run it_run it_build_n_run it_build_n_run_no_cache \
	ghcr_login \
	it_build_multi_arch_push_docker_hub it_build_multi_arch_push_GHCR \
	it_build_multi_arch_all show-version setup setup_env setup_env_auto setup_env_template setup_siblings \
	require_gitflow_next bump_release_version release_and_push_GHCR hotfix_and_push_GHCR \
	waha_start waha_stop waha_logs waha_status \
	signal_start signal_stop signal_logs signal_status \
	install_dev scan scan_secrets scan_sast scan_deps scan_container scan_dast \
	trivy_db_update lint test_db_upgrade test_db_fresh wizard_smoke \
	it_build_amd64 cross_smoke release_smoke


# Version Management with Git Flow
# --------------------------------
# Requires git-flow-next (Go rewrite). The old bash AVH edition is not supported.
# Install: brew install git-flow-next
#
# These commands manage semantic versioning with Git Flow workflow.
# All version tags start with 'v' (e.g., v1.2.3) following semantic versioning principles:
# - major_release: Increments the first number (e.g., v1.2.3 -> v2.0.0)
# - minor_release: Increments the second number (e.g., v1.2.3 -> v1.3.0)
# - patch_release: Increments the third number (e.g., v1.2.3 -> v1.2.4)
# - hotfix: Adds or increments a fourth number (e.g., v1.2.3 -> v1.2.3.1)
#
# The 'v' prefix is consistently preserved in all version tags and branches.

require_gitflow_next:
	@if ! git flow version 2>/dev/null | grep -q 'git-flow-next'; then \
		echo "Error: git-flow-next required (Go rewrite). Install: brew install git-flow-next"; \
		exit 1; \
	fi

# Shared "Next steps" cascade for the three release-start targets.
# Single source of truth — if the release flow changes, edit here.
define next_steps_release
	@echo ""
	@echo "=== Release branch created ==="
	@echo "Next steps:"
	@echo "  1. make bump_release_version     # Update package.json + README.md"
	@echo "  2. Edit CHANGELOG.md with release notes, then commit"
	@echo "  3. make release_smoke            # Build :X.Y.Z + smoke native + amd64"
	@echo "  4. (Staging deploy + verify against :X.Y.Z image)"
	@echo "  5. make ghcr_login               # Authenticate with GHCR"
	@echo "  6. make release_and_push_GHCR    # Finish + push (gated on release_smoke)"
endef

# Hotfix variant — same shape, hotfix-flavored copy.
define next_steps_hotfix
	@echo ""
	@echo "=== Hotfix branch created ==="
	@echo "Next steps:"
	@echo "  1. Fix the issue, then commit"
	@echo "  2. make bump_release_version     # Update package.json + README.md (+ commit)"
	@echo "  3. make release_smoke            # Build :X.Y.Z + smoke native + amd64"
	@echo "  4. (Staging deploy + verify)"
	@echo "  5. make ghcr_login"
	@echo "  6. make hotfix_and_push_GHCR     # Finish + push (gated on release_smoke)"
endef

minor_release: require_gitflow_next
	@# Start a minor release with incremented minor version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2+1".0"}')
	$(next_steps_release)

patch_release: require_gitflow_next
	@# Start a patch release with incremented patch version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}')
	$(next_steps_release)

major_release: require_gitflow_next
	@# Start a major release with incremented major version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1+1".0.0"}')
	$(next_steps_release)

hotfix: require_gitflow_next
	@# Start a hotfix with incremented patch.patch version (fourth component)
	git flow hotfix start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{if (NF < 4) print $$1"."$$2"."$$3".1"; else print $$1"."$$2"."$$3"."$$4+1}')
	$(next_steps_hotfix)

# Self-heal git-flow stale state before release/hotfix finish — POKA-YOKE.
#
# git-flow-next persists per-step state in .git/gitflow/state/*.json. If a
# previous `release finish` aborted before the merge actually ran (e.g.
# operator cancelled, pre-flight failed, terminal closed), the state file
# survives. The next `release finish` then errors with "a merge is already
# in progress" — a misleading message, since no merge is in progress and
# the working tree is clean.
#
# This target detects the false-positive case and calls `--continue` so
# the finish proceeds. Two flags accompany every git-flow finish call:
#
#   --no-ff      Force a real merge commit even when release/X.Y.Z is a
#                fast-forward over master. git-flow-next 1.0.0 tries to
#                create a merge commit unconditionally; when the merge is
#                fast-forward-able, `git commit` then has nothing to
#                commit ("nothing to commit, working tree clean") and
#                git-flow-next aborts with a misleading
#                "failed to commit merge" error. Forcing --no-ff gives
#                git-commit something real to record. (Bonus: it preserves
#                the release branch shape in the master history graph.)
#
#   --no-verify  Bypass pre-commit-framework hooks on git-flow's INTERNAL
#                merge commit. Those hooks are for the operator-commit
#                surface; they have nothing to check on an auto-driven
#                merge and report Skipped for every entry. git-flow-next
#                surfaces the Skipped output even on success, which is
#                noise. Belt-and-suspenders alongside --no-ff.
#
# Heal refuses to act when ANY of these is true, kicking the decision back
# to the operator with named conditions:
#
#   - A real in-progress merge exists (.git/MERGE_HEAD present)
#   - A real in-progress rebase exists (.git/REBASE_HEAD or rebase-merge dir)
#   - The recorded release branch no longer exists
#   - The recorded parent branch (master) already contains the release
#     branch tip — meaning the merge already happened; "continue" would
#     re-run it and could cause duplicate commits
#   - Working tree is dirty
_release_finish_heal:
	@state_file=.git/gitflow/state/merge.json; \
	test -f "$$state_file" || exit 0; \
	if [ -e .git/MERGE_HEAD ]; then \
		echo "REFUSE TO HEAL: a real git merge is in progress."; \
		echo "  Resolve conflicts and: git commit"; \
		echo "  Or abort: git merge --abort"; \
		exit 1; \
	fi; \
	if [ -e .git/REBASE_HEAD ] || [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then \
		echo "REFUSE TO HEAL: a real git rebase is in progress."; \
		echo "  Continue: git rebase --continue"; \
		echo "  Or abort: git rebase --abort"; \
		exit 1; \
	fi; \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "REFUSE TO HEAL: working tree is dirty."; \
		echo "  Commit or stash before re-running release_finish."; \
		exit 1; \
	fi; \
	branch=$$(python3 -c "import json,sys; print(json.load(open('$$state_file'))['fullBranchName'])" 2>/dev/null); \
	parent=$$(python3 -c "import json,sys; print(json.load(open('$$state_file'))['parentBranch'])" 2>/dev/null); \
	step=$$(python3 -c "import json,sys; print(json.load(open('$$state_file'))['currentStep'])" 2>/dev/null); \
	if [ -z "$$branch" ] || [ -z "$$parent" ]; then \
		echo "REFUSE TO HEAL: stale gitflow state file is unparsable."; \
		echo "  Inspect: cat $$state_file"; \
		echo "  Remove manually if appropriate."; \
		exit 1; \
	fi; \
	if ! git rev-parse --verify "$$branch" >/dev/null 2>&1; then \
		echo "REFUSE TO HEAL: state file names branch '$$branch' which no longer exists."; \
		echo "  Inspect: cat $$state_file"; \
		echo "  Remove manually if appropriate (the release was likely already finished)."; \
		exit 1; \
	fi; \
	if git merge-base --is-ancestor "$$branch" "$$parent" 2>/dev/null; then \
		echo "REFUSE TO HEAL: '$$parent' already contains '$$branch'."; \
		echo "  The merge already happened in an earlier run. Running --continue"; \
		echo "  could create duplicate commits. Inspect:"; \
		echo "    git log --oneline $$parent ^$$branch | head"; \
		echo "    git log --oneline $$branch ^$$parent | head"; \
		exit 1; \
	fi; \
	echo "=== Healing stale gitflow state ==="; \
	echo "  branch: $$branch"; \
	echo "  parent: $$parent"; \
	echo "  step:   $$step"; \
	echo "  working tree clean, no real merge/rebase, parent does not"; \
	echo "  contain branch — safe to --continue."; \
	echo ""; \
	type=$$(python3 -c "import json,sys; print(json.load(open('$$state_file'))['branchType'])" 2>/dev/null); \
	name=$$(python3 -c "import json,sys; print(json.load(open('$$state_file'))['branchName'])" 2>/dev/null); \
	git flow $$type finish $$name --continue --no-ff --no-verify

# If _release_finish_heal already drove `git flow release finish --continue`
# to completion, the release branch is gone and we just need to push.
# Otherwise (no stale state), run the normal `git flow release finish` path.
release_finish: require_gitflow_next distribution_verify _release_finish_heal
	@echo "=== Finishing release ==="
	@if git branch --list 'release/*' | grep -q .; then \
		echo "Merging to master, tagging, pushing..."; \
		git flow release finish --no-ff --no-verify; \
	else \
		echo "Release branch already merged (heal completed it); pushing only."; \
	fi
	git push origin develop && git push origin master && git push --tags && git checkout develop
	@echo ""
	@echo "=== Release complete ==="
	@echo "Tag: v$(IMAGE_TAG)"
	@echo "Pushed: develop, master, tags"

hotfix_finish: require_gitflow_next distribution_verify _release_finish_heal
	@echo "=== Finishing hotfix ==="
	@if git branch --list 'hotfix/*' | grep -q .; then \
		echo "Merging to master, tagging, pushing..."; \
		git flow hotfix finish --no-ff --no-verify; \
	else \
		echo "Hotfix branch already merged (heal completed it); pushing only."; \
	fi
	git push origin develop && git push origin master && git push --tags && git checkout develop
	@echo ""
	@echo "=== Hotfix complete ==="

release_and_push_GHCR: release_smoke release_finish
	@echo ""
	@echo "=== Building and pushing to GHCR ==="
	@make it_build_multi_arch_push_GHCR
	@echo ""
	@echo "=== Pinning SERVER_TAG=$(IMAGE_TAG) in distribution.env ==="
	@$(MAKE) _pin_server_tag IMAGE_TAG=$(IMAGE_TAG)
	@echo ""
	@echo "=== Release $(IMAGE_TAG) published ==="
	@echo "Verify: docker pull $(GHCR_IMAGE_NAME):$(IMAGE_TAG)"
	@echo "Verify: docker pull $(GHCR_IMAGE_NAME):latest"

hotfix_and_push_GHCR: release_smoke hotfix_finish
	@echo ""
	@echo "=== Building and pushing to GHCR ==="
	@make it_build_multi_arch_push_GHCR
	@echo ""
	@echo "=== Pinning SERVER_TAG=$(IMAGE_TAG) in distribution.env ==="
	@$(MAKE) _pin_server_tag IMAGE_TAG=$(IMAGE_TAG)
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

# ---------------------------------------------------------------------------
# try.sage trial mode (workshop / demo deployment)
# ---------------------------------------------------------------------------
# Boots the same image as `it_run` but flips on the trial runtime: hidden LLM
# connection, persona seeds, 24h auto-reset, banner. The hidden connection
# secrets stay env-only — the API key never lands in the config DB. See
# docs/try-sage-deployment.md and docs/try-sage-docker-exploration.md.
TRY_SAGE_USER_SEAT_COUNT      ?= 3
TRY_SAGE_RESET_INTERVAL_HOURS ?= 24

# Dedicated volume for trial state. Stays separate from VOLUME_DATA so a
# workstation can run a production container and a trial container at the
# same time without cross-contamination. Override at the command line if
# you want to share the prod volume on purpose.
TRY_SAGE_VOLUME_DATA          ?= sage-try-data:/app/backend/data

# Trial run: COMMON + dedicated trial volume. No WEBUI_SECRET_KEY
# pass-through — try.sage rotates session keys per reset.
TRY_SAGE_DOCKER_RUN_ARGS := $(COMMON_RUN_ARGS) \
	-v $(TRY_SAGE_VOLUME_DATA)

try_sage_start:
	@# Fail fast on missing secrets so the operator sees the problem before
	@# the container boots into a half-configured trial. TRY_SAGE_LLM_MODELS
	@# is intentionally NOT in this list — empty means "expose the upstream
	@# provider's full model list". Operators opt in to narrowing.
	@for v in TRY_SAGE_LLM_API_URL TRY_SAGE_LLM_API_KEY; do \
		eval "val=\$$$$v"; \
		if [ -z "$$val" ]; then \
			echo "Error: $$v is not set. Put it in .env or export it before running this target."; \
			echo "       See docs/try-sage-deployment.md for the full env contract."; \
			exit 1; \
		fi; \
	done
	@echo "Starting try.sage trial container ($(CONTAINER_NAME)) in foreground. Ctrl-C to stop."
	@# WEBUI_URL drives the host portion of every persona magic-link URL
	@# the seed prints to the terminal. Forward it explicitly so what the
	@# operator sees in their shell wins over whatever's in .env. If it's
	@# unset in the shell environment the backend falls back to
	@# `http://localhost:8080` (matches PORT_MAPPING above).
	$(CONTAINER_RUNTIME) run $(TRY_SAGE_DOCKER_RUN_ARGS) \
		-e ENABLE_TRY_SAGE=true \
		$(if $(WEBUI_URL),-e WEBUI_URL="$(WEBUI_URL)",) \
		-e TRY_SAGE_LLM_API_URL="$(TRY_SAGE_LLM_API_URL)" \
		-e TRY_SAGE_LLM_API_KEY="$(TRY_SAGE_LLM_API_KEY)" \
		-e TRY_SAGE_LLM_MODELS="$(TRY_SAGE_LLM_MODELS)" \
		-e TRY_SAGE_USER_SEAT_COUNT="$(TRY_SAGE_USER_SEAT_COUNT)" \
		-e TRY_SAGE_RESET_INTERVAL_HOURS="$(TRY_SAGE_RESET_INTERVAL_HOURS)" \
		$(IMAGE_NAME):$(IMAGE_TAG)

# Rebuild image and restart. The dev loop's "I edited code, now show me"
# target. We drop any stale trial container first so `docker run --name`
# doesn't conflict (e.g. if the operator backgrounded a previous run with
# ctrl-z + bg). Foreground at the end so logs stream to the terminal.
try_sage_reset:
	@$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) 2>/dev/null || true
	$(MAKE) it_build
	$(MAKE) try_sage_start

# Print the persona magic-link URLs for the running trial container.
# Reads `/api/v1/sage/runtime/personas` and pretty-prints. Useful when
# you've forgotten which links are live and don't want to scroll back
# through container logs.
try_sage_links:
	@echo "Trial welcome URL: http://localhost:$(LOCAL_PORT)/auth (open in incognito)"
	@echo ""
	@curl -fsS http://localhost:$(LOCAL_PORT)/api/v1/sage/runtime/personas 2>/dev/null \
		| python3 -c "import json, sys;\
[print(f\"  {p['key']:12}  {p['login_url']}\") for p in json.load(sys.stdin)]" \
		|| echo "  (container not responding on :$(LOCAL_PORT) — is it running?)"
# ---------------------------------------------------------------------------
# Interactive release (full flow via ~/bin/git-release)
# ---------------------------------------------------------------------------
release:
	@scripts/release.sh

# ---------------------------------------------------------------------------
# Distribution.env hardlink chain (Jidoka 自働化 primitive)
# ---------------------------------------------------------------------------
# distribution.env is the single source of truth for canonical distribution
# facts (image, server tag, volume, install command, CLI version). It lives
# in homebrew-apps and is hardlinked into this repo and WEB-Sage.Education-docs
# so an edit in any one propagates immediately to the other two.
#
# Hardlinks don't survive a fresh `git clone` — the new clone has its own
# inode. After cloning, run `make distribution_sync` from any sibling to
# re-establish the chain.
#
# `release_finish` calls `distribution_verify` so a release halts if the
# chain has drifted (e.g. an editor wrote a copy instead of editing in place).

# Where the sibling repos live. Override SIBLING_HOMEBREW if homebrew-apps
# is checked out somewhere other than `../homebrew-apps`.
SIBLING_HOMEBREW ?= ../homebrew-apps
SIBLING_DOCS     ?= ../WEB-Sage.Education-docs
SIBLING_AI_UI    ?= .
DIST_SOURCE      := $(SIBLING_HOMEBREW)/distribution.env

distribution_sync:
	@test -f $(DIST_SOURCE) || { \
		echo "ERROR: $(DIST_SOURCE) not found."; \
		echo "       Run 'make setup_siblings' first (or clone homebrew-apps"; \
		echo "       as a sibling: git clone https://github.com/Sage-is/homebrew-apps.git $(SIBLING_HOMEBREW))"; \
		exit 1; \
	}
	@test -d $(SIBLING_DOCS) || { \
		echo "ERROR: $(SIBLING_DOCS) not found."; \
		echo "       Run 'make setup_siblings' first."; \
		exit 1; \
	}
	@ln -f $(DIST_SOURCE) $(SIBLING_AI_UI)/distribution.env
	@ln -f $(DIST_SOURCE) $(SIBLING_DOCS)/distribution.env
	@$(MAKE) distribution_verify

distribution_verify:
	@expected=3; \
	test -d $(SIBLING_DOCS) || expected=2; \
	for f in $(DIST_SOURCE) $(SIBLING_AI_UI)/distribution.env $(SIBLING_DOCS)/distribution.env; do \
		test -e "$$f" || continue; \
		links=$$(stat -f "%l" "$$f" 2>/dev/null || stat -c "%h" "$$f"); \
		if [ "$$links" != "$$expected" ]; then \
			echo "FAIL: $$f has $$links links, expected $$expected"; \
			echo "  Run 'make distribution_sync' to re-establish the chain."; \
			exit 1; \
		fi; \
	done; \
	echo "OK: distribution.env hardlink chain intact ($$expected links)."

# Self-heal the hardlink chain when a git operation (checkout / merge /
# rebase / amend) has rewritten distribution.env in place. Direction is the
# inverse of distribution_sync: we trust this repo's distribution.env as the
# new canonical because that's what git just wrote. Siblings get re-linked
# to it. If a sibling holds *different* content, we WARN and exit clean —
# silent overwrite of a divergent sibling would mask drift.
#
# Silent on the happy path: most checkouts don't touch distribution.env, so
# the inode survives and the chain is intact.
distribution_heal:
	@test -f $(SIBLING_AI_UI)/distribution.env || exit 0
	@if [ -e $(DIST_SOURCE) ]; then \
		links=$$(stat -f "%l" $(SIBLING_AI_UI)/distribution.env 2>/dev/null || \
		         stat -c "%h" $(SIBLING_AI_UI)/distribution.env); \
		expected=2; \
		test -d $(SIBLING_DOCS) && expected=3; \
		if [ "$$links" = "$$expected" ]; then exit 0; fi; \
		if ! cmp -s $(SIBLING_AI_UI)/distribution.env $(DIST_SOURCE); then \
			echo ""; \
			echo "WARN: distribution.env hardlink chain broken AND content has diverged."; \
			echo "  AI-UI:        $(SIBLING_AI_UI)/distribution.env"; \
			echo "  homebrew-apps: $(DIST_SOURCE)"; \
			echo "  Run 'diff $(SIBLING_AI_UI)/distribution.env $(DIST_SOURCE)' and reconcile."; \
			echo "  Then run 'make distribution_sync' to re-establish the chain."; \
			exit 0; \
		fi; \
		ln -f $(SIBLING_AI_UI)/distribution.env $(DIST_SOURCE); \
	fi
	@if [ -d $(SIBLING_DOCS) ] && [ -e $(SIBLING_DOCS)/distribution.env ]; then \
		if ! cmp -s $(SIBLING_AI_UI)/distribution.env $(SIBLING_DOCS)/distribution.env; then \
			echo "WARN: $(SIBLING_DOCS)/distribution.env diverges; leaving alone."; \
		else \
			ln -f $(SIBLING_AI_UI)/distribution.env $(SIBLING_DOCS)/distribution.env; \
		fi; \
	fi
	@$(MAKE) -s distribution_verify

# Rewrites SERVER_TAG in distribution.env while preserving the inode (so the
# hardlink chain stays intact) and verifies the chain afterward. `perl -i` /
# `sed -i` would rename a temp file over the target and break hardlinks.
_pin_server_tag:
	@test -n "$(IMAGE_TAG)" || { echo "ERROR: _pin_server_tag needs IMAGE_TAG=X.Y.Z"; exit 1; }
	@tmp=$$(mktemp) && \
	  perl -pe 's/^SERVER_TAG=.*/SERVER_TAG=$(IMAGE_TAG)/' $(DIST_SOURCE) > "$$tmp" && \
	  cat "$$tmp" > $(DIST_SOURCE) && \
	  rm -f "$$tmp"
	@$(MAKE) distribution_verify
	@echo "OK: distribution.env SERVER_TAG=$(IMAGE_TAG)"
