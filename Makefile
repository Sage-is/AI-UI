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
# REGISTRY is the ONE knob for where the app image AND the Sprig™ catalog publish.
# Default ghcr.io/sage-is (current public home). Point it at the in-house
# registry later — `make ship REGISTRY=sprigs.sage.is/sage-is` (sage-branded
# name; the metal may be the CapRover cluster) — and nothing else changes:
# sha256 pins guarantee the same bytes from any host.
REGISTRY ?= ghcr.io/sage-is
# Image repo derives from REGISTRY so the image and catalog track the same host.
# notdir(sage-is/ai-ui)=ai-ui, so the default stays byte-identical to the old
# `ghcr.io/$(GIT_REPO_SLUG)`.
GHCR_IMAGE_NAME ?= $(REGISTRY)/$(notdir $(GIT_REPO_SLUG))
# Host architectures the catalog builds for. Both by default (all platforms).
ARCHES ?= arm64 amd64
GIT_TAG := $(shell git tag --sort=-v:refname | sed 's/^v//' | head -n 1)

# Release version detection. Prefers release/X.Y.Z or hotfix/X.Y.Z branch name
# so that `make it_build` on a release branch tags the *new* version, not the
# *previous* one. Falls back to GIT_TAG so off-release-branch behavior is
# unchanged.
RELEASE_VERSION := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null | awk '/^(release|hotfix)\// { sub(/^(release|hotfix)\//, ""); print }')
ifeq ($(RELEASE_VERSION),)
    RELEASE_VERSION := $(GIT_TAG)
endif

# Precedence: release/hotfix branch version, else the newest git tag, else latest.
#
# SERVER_TAG used to sit in this chain and it never once fired. Line 71 collapses
# RELEASE_VERSION to GIT_TAG, so the third arm was unreachable in any repo holding
# a single v* tag — it documented a precedence that could not happen, which is
# worse than documenting none. Deleted rather than reordered.
#
# SERVER_TAG is NOT a fallback for this, and must never be compared against it.
# It answers a different question: IMAGE_TAG is what is being built, SERVER_TAG is
# what is published. They differ legitimately between cutting a tag and pushing
# an image, which is exactly the window 3.1.0 spent five attempts inside.
# _pin_server_tag is its only writer, and it writes only after a verified push.
IMAGE_TAG := $(if $(RELEASE_VERSION),$(RELEASE_VERSION),latest)
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
# The Python package, for the same reason app/src is mounted: dev.sh already
# runs uvicorn with --reload, so without this a one-line change to a
# server-rendered page costs a full image build. Only the package, not all of
# app/backend, so the data volume mounted at /app/backend/data stays clear of it.
BACKEND_SRC := $$(pwd)/app/backend/sage_is_ai/:/app/backend/sage_is_ai/
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
	@echo "  Working on the frontend? Two commands:"
	@echo "    building        make dev      # everything live: Svelte, Python, pages/"
	@echo "    judging it      make review   # the BAKED image, nothing mounted"
	@echo ""
	@echo "    make review LIVE=1     # + pages/ mounted and watched"
	@echo "    make review REBUILD=1  # + it_build first, for Svelte changes"
	@echo ""
	@echo "  A review of your working tree is not a review of the artifact you"
	@echo "  ship, so plain 'make review' is the pass that decides."
	@echo ""
	@echo "  'make dev' seeds admin@example.com / password on its OWN volume"
	@echo "  (sage-ai-dev-data). Use another with: DEV_VOLUME=<name> make dev"
	@echo "  It does NOT graft the example ui-Sprig: one unnamed slot means the"
	@echo "  fragment lands on every page. Working on it? DEV_GRAFT_UI=1 make dev"
	@echo ""
	@echo "Available make commands:"
	@echo ""
	@awk '{ \
		line = line $$0; \
		if (sub(/\\$$/, "", line)) next; \
		if (line ~ /^[a-zA-Z0-9_-]+:.*## /) { \
			split(line, a, /:.*## /); \
			printf "  %-32s %s\n", a[1], a[2]; \
		} \
		line = ""; \
	}' $(firstword $(MAKEFILE_LIST)) | LC_ALL=C sort
	@echo ""
	@echo "  make help_all   every target, including the undocumented ones"
	@echo ""

# The listing above scans `## ` comments rather than dumping Make's target
# database. The dump listed all 137 targets as bare names with no idea what any
# of them did, which is the same as listing none.
#
# It is also half of a Poka-Yoke. A target whose name starts with `_` carries no
# `## ` comment, so it cannot appear here — that is how the irreversible release
# steps stay unreachable by accident. Adding a `## ` comment to one would
# advertise a door that is meant to stay shut.
help_all:  ## Every target, including undocumented internals
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null \
		| awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$$@$$'
	@echo ""

# Environment setup helpers
setup_env:  ## Write .env only
	@chmod +x tools/setup_project_env.sh
	@tools/setup_project_env.sh

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
setup: setup_env setup_siblings  ## Fresh setup: .env + sibling hardlinks
	@echo ""
	@echo "=== Setup complete ==="
	@echo "    Next: make it_build && make it_run"

# Base flags every container run needs. DOCKER_RUN_ARGS and
# TRY_SAGE_DOCKER_RUN_ARGS both extend this — add a flag here and it
# applies to both production and trial runs.
COMMON_RUN_ARGS := --rm -p $(PORT_MAPPING) \
	--add-host=host.docker.internal:host-gateway \
	-v $(ENV_FILE) \
	$(if $(SPRIG_REGISTRY),-e SPRIG_REGISTRY=$(SPRIG_REGISTRY),) \
	$(if $(SPRIG_REGISTRY_INSECURE),-e SPRIG_REGISTRY_INSECURE=$(SPRIG_REGISTRY_INSECURE),) \
	--name $(CONTAINER_NAME)

# Production run: COMMON + secret-key pass-through + prod volume.
DOCKER_RUN_ARGS := $(COMMON_RUN_ARGS) \
	$(if $(WEBUI_SECRET_KEY),-e WEBUI_SECRET_KEY=$(WEBUI_SECRET_KEY),) \
	-v $(VOLUME_DATA)

# The dev loop gets its OWN volume, and that is load-bearing rather than tidy.
# `make dev` seeds an administrator, and a user is only made admin when they are
# the FIRST to sign up — every later one lands on DEFAULT_USER_ROLE, which is
# `pending`. Sharing sage-ai-data with `it_run` meant the seed silently produced
# a pending account on any volume that had ever been used, and the ui-Sprig graft
# was then refused with a permissions error.
#
# Overridden by DEV_VOLUME, deliberately NOT by VOLUME: that one is set project
# wide in distribution.env, so reusing it here would silently point dev back at
# the shared volume — which is the bug this variable exists to prevent.
# Reach a specific one when you mean to:  DEV_VOLUME=sage-open-webui make dev
VOLUME_DEV_DATA ?= $(or $(DEV_VOLUME),sage-ai-dev-data):$(or $(DATA_MOUNT),/app/backend/data)

# EXTENDS COMMON_RUN_ARGS, like DOCKER_RUN_ARGS does. It used to restate those
# flags by hand, and it had drifted: SPRIG_REGISTRY was added to COMMON and
# never copied here, so `make dev` reached for ghcr.io and every graft was
# denied. That is the cost of a near-duplicate, and it is why this now extends.
#
# The network and the registry match what e2e and manual-check.sh already do —
# `local-registry` is a container name, so it only resolves on sage-network.
DEV_RUN_ARGS := $(COMMON_RUN_ARGS) \
	--network sage-network \
	-e SPRIG_REGISTRY=$(or $(SPRIG_REGISTRY),local-registry:5000) \
	-p 5173:5173 \
	$(if $(WEBUI_SECRET_KEY),-e WEBUI_SECRET_KEY=$(WEBUI_SECRET_KEY),) \
	-v $(VOLUME_DEV_DATA) \
	-v $(FRONTEND_SRC) \
	-v $(STATIC_SRC) \
	-v $(BACKEND_SRC) \
	-v $$(pwd)/app/svelte.config.js:/app/svelte.config.js \
	-v $$(pwd)/app/vite.config.ts:/app/vite.config.ts \
	-v $$(pwd)/app/tsconfig.json:/app/tsconfig.json \
	-v $$(pwd)/app/postcss.config.js:/app/postcss.config.js \
	-v $$(pwd)/app/tailwind.config.js:/app/tailwind.config.js \
	-v $$(pwd)/app/package.json:/app/package.json \
	-e PAGES_RELOAD_DIRS=/app/backend/sage_is_ai/pages

it_stop:  ## Stop the running container
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
it_build:  ## Build the Docker image
	@echo "Building Docker image with BuildKit enabled..."
	@START=$$(date +%s) && export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --load $(OCI_LABELS) -t $(IMAGE_NAME):$(IMAGE_TAG) \
	            -t $(IMAGE_NAME):latest \
	            -t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
	            -t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
	            . && \
	END=$$(date +%s) && \
	printf "⏱  it_build: %dm%02ds\n" $$(( (END-START)/60 )) $$(( (END-START)%60 ))
	@$(NOTIFY_DONE)
	@echo ""

# Build Docker Image without Cache and with Branch Name
it_build_no_cache:  ## Build the image from scratch, no layer cache
	@echo "Building Docker image without cache and with BuildKit enabled..."
	@START=$$(date +%s) && export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --no-cache --load $(OCI_LABELS) -t $(IMAGE_NAME):$(IMAGE_TAG) \
	                     -t $(IMAGE_NAME):latest \
	                     -t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
	                     -t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
	                     . && \
	END=$$(date +%s) && \
	printf "⏱  it_build_no_cache: %dm%02ds\n" $$(( (END-START)/60 )) $$(( (END-START)%60 ))
	@$(NOTIFY_DONE)
	@echo ""

## dev — the one dev loop. Svelte HMR on 5173, uvicorn --reload on 8080,
## pages/ mounted and watched, an admin seeded and the example ui-Sprig™
## grafted, so the instance is usable with no follow-up step. Everything is
## live; nothing needs a rebuild or a teardown.
dev: sprig_registry  ## Everything live: Svelte HMR, Python reload, pages/
	$(CONTAINER_RUNTIME) run $(DEV_RUN_ARGS) $(IMAGE_NAME):$(IMAGE_TAG) bash -c "/app/backend/restore_backup_start.sh dev"

dev_run: dev

# Run targets
it_run:  ## Run the built image
	$(CONTAINER_RUNTIME) run $(DOCKER_RUN_ARGS) $(IMAGE_NAME):$(IMAGE_TAG)

it_run_ghcr:
	$(CONTAINER_RUNTIME) run $(DOCKER_RUN_ARGS) $(GHCR_IMAGE_NAME):$(IMAGE_TAG)

# Combine build and dev run targets

# Combined build and run targets
it_build_n_run: it_build
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
wizard_smoke:  ## Install-wizard smoke
	@scripts/wizard-smoke.sh $(IMAGE_NAME):$(IMAGE_TAG)

## sprig_registry — idempotent: ensures the local OCI registry (dev-machine
## artifact store for `oras`-delivered Sprigs™) is up on sage-network. Does
## NOT seed it — a fresh registry is empty; see TODO.md for the packaging-
## script gap (only sprig-embedding-minilm-onnx has a build script in git;
## the other 11 catalog artifacts on this machine have no in-repo recipe).
sprig_registry:
	@$(CONTAINER_RUNTIME) network inspect sage-network >/dev/null 2>&1 || $(CONTAINER_RUNTIME) network create sage-network >/dev/null
	@$(CONTAINER_RUNTIME) ps --format '{{.Names}}' | grep -qx local-registry || { \
		echo "== starting local-registry (sage-network, NAMED volume sprig-registry-data) =="; \
		$(CONTAINER_RUNTIME) rm -f local-registry >/dev/null 2>&1 || true; \
		$(CONTAINER_RUNTIME) run -d --name local-registry --network sage-network -p 5000:5000 \
			-v sprig-registry-data:/var/lib/registry registry:2 >/dev/null; \
		for i in $$(seq 1 30); do curl -fsS http://localhost:5000/v2/ >/dev/null 2>&1 && break; sleep 0.5; done; \
	}
	@echo "local-registry: up ($$(curl -fsS http://localhost:5000/v2/_catalog 2>/dev/null || echo 'unreachable'))"

## sprig_smoke — the Sprig™ lifecycle gate: bare boot, clean 503s with graft
## pointers, every capability grafts back (fresh container each run).
sprig_smoke: it_build sprig_registry  ## Sprig lifecycle: graft, restart, refuse, graft back
	@scripts/smoke/sprig-lifecycle.sh $(IMAGE_NAME):$(IMAGE_TAG)

## e2e_both — run the suite against BOTH implementations of every migrated
## surface: once with SURFACE_TARGET=legacy (the SvelteKit routes users reach
## today) and once with =nobuild (the server-rendered replacements). The
## migration's core rule is that a spec is green against both; running it twice
## by hand is how that rule quietly becomes "green against whichever one was
## checked last". Surfaces are registered in app/cypress/support/surfaces.ts.
e2e_both: it_build sprig_registry  ## Cypress against BOTH surfaces: legacy and nobuild
	@echo "===== SURFACE_TARGET=legacy ====="
	@CYPRESS_SURFACE_TARGET=legacy scripts/e2e/run-cypress.sh $(IMAGE_NAME):$(IMAGE_TAG)
	@echo ""
	@echo "===== SURFACE_TARGET=nobuild ====="
	@CYPRESS_SURFACE_TARGET=nobuild scripts/e2e/run-cypress.sh $(IMAGE_NAME):$(IMAGE_TAG)

## pipefail_lint — refuse `docker logs|curl | grep -q` in scripts/. Under
## `set -o pipefail` a MATCH returns 141 (grep exits, writer takes SIGPIPE), so
## the assertion inverts. Cost two gates before it was chased; the mechanism is
## proved both ways by scripts/smoke/pipefail-grep-fixture.sh.
pipefail_lint:  ## Gate: no unbounded-writer `| grep -q` in scripts/
	@scripts/lint-pipefail-grep.sh

## pipefail_fixture — proves BOTH that the trap is real and that gate.sh's
## helpers fix it. A device that fixes nothing looks identical to one that works
## unless the broken shape is asserted too.
pipefail_fixture:  ## Fixture: prove the pipefail trap is real
	@scripts/smoke/pipefail-grep-fixture.sh

## ui_sprig_gate — what the ui-Sprig™ contract REFUSES: off-origin references,
## framing, interpreted script attributes, script without an admin's per-Sprig
## grant, and anything framework-sized. The Cypress spec walks the happy path;
## this walks the side that matters for a marketplace.
ui_sprig_gate: it_build  ## Gate: ui-Sprig refusals (off-origin, framing, script)
	@scripts/smoke/ui-sprig-validator.sh $(IMAGE_NAME):$(IMAGE_TAG)

## sprig_durability — grafts survive a FULL container recreation, restored
## offline from the data volume (state.json + boot reconcile + cached tar).
## Stops local-registry mid-test to prove no-network restore; restarts it after.
sprig_durability: it_build sprig_registry  ## Gate: grafts survive a full container recreation, offline
	@scripts/smoke/sprig-durability.sh $(IMAGE_NAME):$(IMAGE_TAG)

## sprig_publish — push every local sprig tag to ghcr.io/sage-is and GATE on
## public visibility (fails with fix URLs for any non-public package; GitHub
## has no API for the flip). Idempotent — run after any build-sprig-*.sh.
## After signing (sprig_sign), run with FORCE=1: manifests changed digest.
sprig_publish: sprig_registry  ## Push every local Sprig tag to the registry, gate on public pull
	@DEST=$(REGISTRY) ORG=$(notdir $(REGISTRY)) scripts/publish-sprigs.sh

## sprig_sign — minisign-sign every artifact tag in the local registry, in
## place (SIGN_KEY=<secret key> required; tar bytes unchanged so sha256 pins
## hold). Then: FORCE=1 make sprig_publish. Third parties verify: minisign -Vm.
sprig_sign: sprig_registry
	@scripts/sign-sprigs.sh

# ---------------------------------------------------------------------------
# Catalog orchestration — build + sign + publish the WHOLE Sprig™ catalog in
# one command, multi-arch, to $(REGISTRY). The connective tissue over the
# per-artifact build-sprig-*.sh recipes and the sprig_sign/sprig_publish gates.
# ---------------------------------------------------------------------------

## catalog_prep — one-time-ish prerequisites for catalog_build: the shared
## Docker network + local registry (via sprig_registry). Cheap + idempotent.
## The GGUF/whisper recipes also need their static server binaries staged first
## — see each scripts/build-sprig-*.sh header (LLAMA_BIN, etc.).
catalog_prep: sprig_registry
	@echo "== catalog_prep: sage-network + local-registry:5000 up =="

# Neutral artifacts build ONCE (arch-independent bytes); arch-bound artifacts
# build per entry in $(ARCHES). As the recipe-less artifacts get their
# build-sprig-*.sh (roadmap 8.J), add them to the matching list.
CATALOG_NEUTRAL_RECIPES := build-sprig-minilm.sh
CATALOG_ARCH_RECIPES    := build-sprig-vector-chroma.sh build-sprig-rag-loaders.sh \
	build-sprig-export-document.sh build-sprig-reranker.sh build-sprig-whisper.sh

## catalog_build — build EVERY Sprig™ artifact into the local registry
## (localhost:5000), the staging area sign+publish read from. Idempotent — re-run
## after editing a recipe. Heavy: pulls models + runs buildx per arch. ARCHES
## selects host arches (default: arm64 amd64). Each recipe prints the tar.zst
## sha256 to pin in the supervisor CATALOG (per-arch entries -> arches overrides).
catalog_build: catalog_prep
	@echo "== catalog_build -> local-registry:5000 (arches: $(ARCHES)) =="
	@env REGISTRY=localhost:5000 INSECURE=1 NETWORK=sage-network THEME=workshop-bio  scripts/build-sprig-theme.sh
	@env REGISTRY=localhost:5000 INSECURE=1 NETWORK=sage-network THEME=workshop-math scripts/build-sprig-theme.sh
	@for r in $(CATALOG_NEUTRAL_RECIPES); do \
	  echo "-- neutral: $$r --"; \
	  env REGISTRY=localhost:5000 INSECURE=1 NETWORK=sage-network scripts/$$r || exit 1; \
	done
	@for a in $(ARCHES); do for r in $(CATALOG_ARCH_RECIPES); do \
	  echo "-- $$a: $$r --"; \
	  env REGISTRY=localhost:5000 INSECURE=1 NETWORK=sage-network ARCH=$$a PLATFORM=linux/$$a scripts/$$r || exit 1; \
	done; done
	@echo "== catalog_build complete; pins printed above -> app/backend/sage_is_ai/sprigs/supervisor.py CATALOG =="

## catalog_release — build -> sign -> publish the whole Sprig™ catalog to
## $(REGISTRY). This is the SPRIGS-CHANGED path (new sprig, tag bump, new
## arch) — NOT part of a platform release: artifacts are immutable per tag and
## the image ships sha256 pins, so redistributing the platform never rebuilds
## sprigs (see `ship`). SIGN_KEY=<secret key> signs every artifact (else
## publishes UNSIGNED). Reuses the sprig_sign + sprig_publish gates.
catalog_release: catalog_build
	@if [ -n "$(SIGN_KEY)" ]; then \
	  $(MAKE) sprig_sign && FORCE=1 $(MAKE) sprig_publish; \
	else \
	  echo "NOTE: SIGN_KEY unset -> publishing UNSIGNED artifacts to $(REGISTRY)"; \
	  $(MAKE) sprig_publish; \
	fi
	@echo "== catalog_release complete -> $(REGISTRY) =="

## ship — the ONE button for a PLATFORM release: publish the app VERSION
## (multi-arch image + gitflow finish) to $(REGISTRY), then VERIFY the Sprig™
## catalog the image pins is published there (sprig_publish is idempotent —
## copies only missing tags, gates anonymous pullability; already-published
## artifacts are untouched, nothing is rebuilt). Cleanly modular: the image
## and the catalog version independently — upgrading the deployment is `ship`;
## changing a sprig is `catalog_release`. Run from a release/hotfix branch —
## _release_and_push_GHCR gates on release_smoke, which accepts both shapes.
##
## THIS IS THE ONLY PUBLIC WAY TO PUBLISH, and that is the point. The steps below
## it are private (leading underscore, absent from `make help`) because three
## doors existed here and the documented one skipped sprig_publish, which shipped
## a Sprig that nobody outside could pull. Hotfixes come through here too.
ship: _release_and_push_GHCR sprig_publish  ## Publish a release or hotfix: image to GHCR + Sprig catalog
	@echo ""
	@echo "=== ship complete: image published + catalog verified at $(REGISTRY) ==="

## upgrade_gate — boot THIS image on a COPY of a production data snapshot
## (default: newest tools/db_snapshots/*) and prove the upgrade path: DB
## migrations, user/chat survival, legacy RAG config degrading cleanly,
## chromadb opening the production vector store post-graft, themes, and the
## amd64 arch-guard rehearsal. SNAPSHOT=path overrides; KEEP=1 leaves it up
## for the Cypress half (cypress/e2e/upgrade/). Snapshots are read-only.
##
## IMAGE_TAG is optional: on a release/hotfix branch it is inferred from the
## branch name (release/3.0.0 -> 3.0.0), else the latest git tag, else latest.
## Override with IMAGE_TAG=X.Y.Z to gate an arbitrary tag.
upgrade_gate: sprig_registry  ## Boot this image on a copy of a production snapshot
	@echo "[upgrade_gate] gating $(IMAGE_NAME):$(IMAGE_TAG)  (IMAGE_TAG inferred from branch; override with IMAGE_TAG=X.Y.Z)"
	@scripts/smoke/upgrade-gate.sh $(IMAGE_NAME):$(IMAGE_TAG) $(SNAPSHOT)

## sprig_signing — the artifact-signing gate: signs two small artifacts with
## the committed DEV fixture key, boots with SPRIG_REQUIRE_SIGNED=1, and
## proves all four paths — verified graft, unsigned refused, tampered-sig
## refused, and restart re-verifying the cached signature offline.
sprig_signing: it_build sprig_registry  ## Gate: the four Sprig signing paths
	@scripts/smoke/sprig-signing.sh $(IMAGE_NAME):$(IMAGE_TAG)

## parity_gate — GGUF embedding cultivars vs sentence-transformers reference
## (Poka-Yoke: the Korean-probe canary; rerun on every llama.cpp tag bump).
parity_gate:  ## Gate: GGUF embedding parity (needs 8.I.3 artifacts; llama.cpp bumps)
	@scripts/gates/embedding-parity/run-gate.sh

## reload_gate — proves the development reloader's ON state.
## `pages-dev-reload.cy.ts` covers the OFF state in the normal suite; the ON
## state needs a container booted with PAGES_RELOAD_DIRS and a tree mounted over
## the image, which no browser driver can arrange. Boots its own throwaway
## container and edits a COPY of pages/, never the working tree.
reload_gate:  ## Prove the development reloader's ON state
	@scripts/gates/dev-reload/run-gate.sh

## surface_budget — a migrated surface must weigh LESS than the one it replaces,
## and the app-wide floor must not grow. Boots this image on a COPY of a
## production snapshot (~3 min), measures every route three times via
## cypress/e2e/upgrade/route-payload.cy.ts, then judges the medians.
##
## BYTES ONLY, on purpose: decoded bytes repeat to within 0.1 kB, while times
## swing 2x on the same route. Gating a noisy quantity produces a flaky gate, and
## a flaky gate gets disabled — taking the real check with it.
##
## Registering a surface in cypress/support/surfaces.ts is what enrols it here.
## There is no second list to keep in step.
surface_budget: it_build  ## Gate: a migrated surface weighs less than the one it replaces
	@scripts/gates/surface-budget/run-gate.sh $(IMAGE_NAME):$(IMAGE_TAG)

## review / review_live / review_rebuild — bring up a Rootstock™ for a HUMAN.
##
## Phase S made the human pass a standing condition: a green suite is the
## weakest evidence on an interactive surface. These three are the same script
## in three modes, and which one you want depends on what you are doing:
##
##   review          the BAKED image, nothing mounted. This is the pass that
##                   decides whether something ships, because a review of your
##                   working tree is not a review of the artifact.
##   review_live     pages/ mounted AND watched. Save a .css and the stylesheet
##                   swaps in place; save a .py and the app restarts itself and
##                   the tab reloads. No rebuild, no manual restart.
##   review_rebuild  it_build first — the escape hatch for the one thing a mount
##                   cannot cover, which is the SPA bundle.
##
## Both non-rebuild targets keep the data volume (REUSE_DATA=1), so flipping
## between them costs a boot rather than a boot plus re-seeding an admin and
## re-grafting the ui-Sprig.
##
## THE GATES DELIBERATELY HAVE NO SUCH SWITCH. `e2e`, `e2e_both` and
## `wizard_smoke` always boot the baked image with nothing mounted, because a
## guard-rail that ran against a working tree would be testing something we do
## not ship. Do not add a live mode to them.
review:  ## Review the BAKED image, nothing mounted
	@if [ "$(REBUILD)" = "1" ]; then $(MAKE) it_build; fi
	@KEEP=1 REUSE_DATA=1 $(if $(LIVE),LIVE=1,) scripts/manual-check.sh --graft-ui

# Aliases. The three targets above were three preset calls to one script that
# already reads LIVE/KEEP/REUSE_DATA from the environment, so they collapsed
# into `review` plus two flags. These stay because six docs and a month of
# muscle memory point at them, and an alias costs one line.
review_live:
	@$(MAKE) review LIVE=1

review_rebuild:
	@$(MAKE) review REBUILD=1

## e2e — headless Cypress from a pinned sibling container (no npm on host);
## videos land in app/cypress/videos. e2e_watch — same, but interactive GUI
## served at http://localhost:6080/vnc.html (noVNC; WebRTC alt backlogged).
## Depends on sprig_registry for the same reason e2e_heavy does: run-cypress.sh
## points the app at SPRIG_REGISTRY=local-registry:5000, so with that container
## stopped the vector-chroma deliver test waits 180s and then reports
## "expected 'sprouted' to equal 'delivered'" — a message that names everything
## except the reason. The target is idempotent, so this costs a `docker ps`.
e2e: sprig_registry  ## Cypress against the built image
	@scripts/e2e/run-cypress.sh $(IMAGE_NAME):$(IMAGE_TAG)

## e2e_heavy — opt-in heavy cultivar grafts through the real admin UI:
## bge-large-en-v1.5 (~600MB+ OCI artifact) top-grafted by minilm-onnx-inhoused
## with the 1024→384 width warning asserted. Zero egress (registry-only) since
## the all-MiniLM-onnx live-pull entry was retired 2026-07-05.
## Deliberately in NO gauntlet — run it when you want the big ones proven.
e2e_heavy: sprig_registry
	@SPEC='cypress/e2e/heavy/*.cy.ts' scripts/e2e/run-cypress.sh $(IMAGE_NAME):$(IMAGE_TAG)

e2e_watch:
	@scripts/e2e/run-cypress-watch.sh $(IMAGE_NAME):$(IMAGE_TAG)

## gauntlet — build the image and walk the Sprig™ lifecycle against it.
gauntlet: it_build sprig_smoke  ## Build + Sprig lifecycle smoke

## gauntlet_fast — every gate that runs on a bare checkout with nothing but this
## host. No image, no container, no recorded state. Seconds, not minutes.
##
## This is the pre-push hook (.pre-commit-config.yaml, pre-push stage). Speed is
## the whole design: the full gauntlet was wired to a pre-push hook once and
## never switched on, because a hook costing minutes is a hook people bypass,
## and a bypassed hook protects nothing. Everything heavier runs in gauntlet_full
## and on the CI runner.
##
## The *_teeth members are the point. They prove their gate can still fail. Until
## now not one of them was wired into anything, which left this repo full of
## gates nobody had watched fail.
##
## THE TWO RATCHETS ARE DELIBERATELY ABSENT. `cognitive_complexity` and
## `chat_path_structure` both need a baseline.json that .gitignore excludes and
## that has never been committed, so both hard-fail on any checkout that has not
## recorded one locally — every fresh clone, and every CI runner. They stay
## hand-run tools; run them yourself after `--tighten` records a baseline.
## `chat_path_structure_teeth` DOES belong here: it builds its own sample and
## proves the structural detectors still fire without needing a baseline at all.
gauntlet_fast: pipefail_lint pipefail_fixture ruff_gate docs_gate \
               sprig_capabilities_check startr_swap_check \
               distribution_heal_fixture distribution_verify tags_annotated \
               chat_path_structure_teeth sprig_capabilities_teeth \
               startr_swap_teeth tags_annotated_teeth docs_gate_teeth  ## Gate: host-only gates, seconds (pre-push hook)

## tags_annotated — refuse to publish a lightweight v* tag.
##
## finish_flow cuts tags with `git tag -a`. A human typing `git tag -f` does not,
## which is how v3.1.0 became the only lightweight tag in this repo's history.
## Scoped to tags NOT yet on origin, so an already-published one does not block
## every push. See the script header for why this is not a reference-transaction
## hook: that one fires on fetch and would break `git fetch` here.
tags_annotated:  ## Gate: no lightweight v* tag may be published
	@scripts/hooks/no-lightweight-tags.sh

tags_annotated_teeth:  ## Prove the lightweight-tag gate can fail
	@scripts/hooks/no-lightweight-tags.sh --self-test

# gauntlet_full = gauntlet_fast + everything that needs a built image or the
# network. The host-only list is named ONCE, above, so the two cannot drift.
#
# Order no longer carries meaning for correctness: every member below declares
# `it_build` itself, so a clean machine builds once and runs the lot. It used to
# matter and it used to be wrong — the image fixtures sat 8th-12th while the only
# thing that built an image sat 13th.
#
# surface_budget stays last. It costs ~3 minutes for its snapshot boot and it is
# the only member that judges what the migration CLAIMS — that a server-rendered
# surface is lighter than the SvelteKit one it replaces — rather than whether the
# code runs.
#
# parity_gate is NOT a member, deliberately. It exits 0 when its multi-gigabyte
# GGUF artifacts are absent, which is right on a laptop and fatal in a rollup: on
# any machine that has never built them it reports success forever and the
# Korean-probe canary watches nothing. A permanently-skipping member is worse
# than no member, because it turns an absence into a green tick. Run it where its
# own header says it belongs — on a llama.cpp tag bump — with `make parity_gate`.
gauntlet_full: gauntlet_fast manifest_verify_fixture \
               reasoning_finalizer_fixture tool_call_accumulator_fixture \
               serialize_blocks_fixture serialize_blocks_fixture_teeth \
               chat_response_oracle chat_response_oracle_teeth \
               gauntlet sprig_durability sprig_signing ui_sprig_gate \
               e2e_both scan_container surface_budget  ## Gate: the full local suite (builds an image)

## it_build_amd64 — build an amd64 image via buildx + --load.
##
## Useful on Apple Silicon to validate the same image teammates will run
## on x86_64 Linux hosts (CapRover, GHCR consumers, etc). Slower than the
## native build because layers are emulated. Tag is suffixed `-amd64` so
## it sits beside the host-arch image without overwriting it.
it_build_amd64:  ## Build an amd64 image via buildx (validates x86_64 hosts)
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
## Use this AS the last step before `make ship`.
release_smoke:  ## Release gate: version checks + native and amd64 smoke
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
	@echo "    Next: prove the upgrade path on a copy of a production snapshot —"
	@echo "            make upgrade_gate            # gates $(IMAGE_NAME):$(RELEASE_VERSION) (tag inferred; override with IMAGE_TAG=X.Y.Z)"
	@echo "          then deploy to staging, verify, then 'make ship'."
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
#
# `create --use` only selects the builder on the run that CREATES it. Once it
# exists, a bare create-or-nothing leaves whatever builder is currently selected
# in charge -- so multi-arch builds silently ran on the docker driver instead.
# Select it unconditionally, every time.
ensure_builder:
	@docker buildx inspect multi-arch-builder >/dev/null 2>&1 || docker buildx create --name multi-arch-builder
	@docker buildx use multi-arch-builder

# Multi-architecture build+push helper
# Builds amd64 and arm64, creates manifest list, and pushes in one step.
# Replaces the old per-arch build → docker manifest create → push pattern
# which broke with buildx v0.10+ (provenance attestation wraps every push
# in a manifest list, and docker manifest create rejects manifest-list sources).
#
# The cache wipe is OPT-IN (CLEAN_BUILD=1). It used to run unconditionally, which
# forced every release build to re-download all ~940 npm tarballs on both arches
# at once -- one registry hiccup then cost a full cold rebuild. It burned 3.1.0
# on "Fail extracting tarball for mermaid". Keep the escape hatch, lose the tax.
define build_multi_arch
	@[ -z "$(CLEAN_BUILD)" ] || make it_clean
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

# PRIVATE (leading underscore, no ## comment, so `make help` cannot list it).
# Pushes a multi-arch image to a public registry. Reached through `make ship`.
#
# The Docker Hub twin and the build-both-registries target that used to sit here
# are gone: nothing called either, REGISTRY already defaults to ghcr.io/sage-is,
# and every extra publishing door is a door somebody can take by mistake.
_it_build_multi_arch_push_GHCR: ghcr_login
	@echo "Building multi-arch and pushing to GHCR"
	$(call build_multi_arch,$(GHCR_IMAGE_NAME))
	@echo "Completed GHCR multi-arch push for version $(IMAGE_TAG)"

# Poka-yoke: after the push, prove the GHCR image is PRESENT (not a 404) and a
# real multi-arch (amd64+arm64) index — so a missing/single-arch push fails the
# release here, not later at CapRover. Verifies both pushed tags.
verify_ghcr_manifest:  ## Assert the pushed GHCR image is a present, multi-arch (amd64+arm64) index
	@scripts/verify-image-manifest.sh $(GHCR_IMAGE_NAME):$(IMAGE_TAG) $(GHCR_IMAGE_NAME):latest

# Prove the manifest guard's logic against known public images (no push needed)
manifest_verify_fixture:  ## Fixture: exercise verify-image-manifest.sh (good/single-arch/absent)
	@scripts/smoke/manifest-verify-fixture.sh

# Prove distribution_heal resolves a severed hardlink chain by itself: newest
# SERVER_TAG wins, propagation is forward only, and the target never exits
# non-zero. Runs against throwaway files in a temp directory — the three sibling
# path variables are `?=`, so the real repos are never touched. The older-side
# no-op is the row that matters: it is what keeps release_finish alive.
distribution_heal_fixture:  ## Fixture: distribution_heal — newest wins, forward only, never fails
	@python3 scripts/smoke/distribution-heal-fixture.py

# Reproduce the reasoning-tag defects that swallow or leak the model's answer.
#
# DELIBERATELY NOT in gauntlet or gauntlet_full. It fails today, by design —
# it is the reproduction for an open bug, not a gate. Wire it into gauntlet_full
# in the same commit that fixes the bug, and not before, or every run goes red
# for a reason nobody is acting on.
reasoning_tag_fixture:  ## Fixture: reasoning blocks that swallow or leak the answer (FAILS until fixed)
	@python3 scripts/smoke/reasoning-tag-fixture.py

# Gate: a stream may never end with a content block left open, and the answer
# may never be sealed inside one. Drives the shipped finalize_content_blocks
# against block lists shaped as the streaming loop leaves them. Deterministic on
# purpose — the trigger in the wild is model compliance variance.
#
# `it_build` is declared here, and on every other target below that mounts into
# $(IMAGE_NAME):$(IMAGE_TAG), because the dependency is REAL and Make should
# know it. It was implicit before, satisfied only by list position: these ran
# 8th-12th in gauntlet_full while `gauntlet` — which calls it_build — ran 13th,
# so a clean machine died at the 8th with a missing image. Reordering the list
# would have fixed that one instance and left the trap armed for the next target
# added in the wrong place. `it_build` is phony, so gauntlet_full still builds
# exactly once and position stops mattering for good.
reasoning_finalizer_fixture: it_build  ## Fixture: no content block left open at end of stream
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts:ro" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/reasoning-finalizer-fixture.py

# First test of tool-call accumulation anywhere in the tree — no oracle golden
# carries a tool_calls delta.
tool_call_accumulator_fixture: it_build  ## Fixture: streamed tool-call deltas merge by index
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts:ro" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/tool-call-accumulator-fixture.py

# Covers the two regions the oracle goldens never execute: the tool_calls branch
# (no golden carries a tool_calls delta) and the whole raw=True axis (no golden
# sets features.code_interpreter, and the code-interpreter continuation is the
# only raw=True call site). The golden deliberately freezes the raw tool-call
# hole from the bug ledger; it goes red the day that fix lands.
serialize_blocks_fixture: it_build  ## Fixture: block renderer byte-identical across every block shape
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts:ro" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/serialize-blocks-fixture.py

serialize_blocks_fixture_update: it_build  ## Re-record the block-renderer golden (intentional changes only)
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/serialize-blocks-fixture.py --update

serialize_blocks_fixture_teeth: it_build  ## Prove the block-renderer fixture can fail
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts:ro" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/serialize-blocks-fixture.py --teeth

# Gate: the chat path may get simpler, never more tangled.
#
# Asserts six structural ceilings that only ratchet DOWN — largest function,
# nesting depth, lines at 6+ levels, `nonlocal` count, commented-out code, and
# silent `except: pass` — plus zero citation rot in the charts and bug ledger.
# Baseline recorded 2026-08-04, before any restructuring commit, so the effort
# has a number to beat rather than a memory to argue with.
#
# Runs on the host: no image, no container. A gate that needs a build gets
# skipped locally and only fails in CI, long after the commit that broke it.
# These call measure.py directly rather than through run-gate.sh. The wrapper is
# a convenience for running the gate by path from any directory; make already
# runs from the repo root, so depending on it here would only add a second file
# that must exist for gauntlet_full to work.
chat_path_structure:  ## Gate: chat-path structure ceilings + citation rot
	@python3 scripts/gates/chat-path-structure/measure.py

# Lower the ceilings to what the code achieves right now. Run this in the same
# commit as the refactor that earned it, never on its own.
chat_path_structure_tighten:  ## Ratchet the chat-path ceilings down to today's numbers
	@python3 scripts/gates/chat-path-structure/measure.py --tighten

# Where did the fences move to? Report only, nothing is rewritten. Turns a stale
# citation from an afternoon of line-hunting into a lookup table.
chat_path_structure_relocate:  ## Report where each chat-path fence moved to
	@python3 scripts/gates/chat-path-structure/measure.py --relocate

# Prove every detector fires on a sample built to trip it.
chat_path_structure_teeth:  ## Prove the structure ratchet can fail
	@python3 scripts/gates/chat-path-structure/measure.py --self-test

# Markdown prose hygiene: authored .md must be one line per paragraph, no stray
# unicode spaces. The checker is the machine-local ~/bin/mdprose, so this target
# skips (does not fail) when it is absent — e.g. inside Docker or CI. To make it
# a hard gate in gauntlet_full, vendor the script into scripts/gates/ first.
md_prose:  ## Gate: authored markdown is normalized (skips if mdprose absent)
	@if command -v mdprose >/dev/null 2>&1; then \
		mdprose check . ; \
	else \
		echo "md_prose: mdprose not on PATH — skipped (install ~/bin/mdprose)" ; \
	fi

md_prose_fix:  ## Fold hard-wrapped paragraphs in authored markdown (writes files)
	@mdprose fix .

# The Sprig capability reference is emitted from the catalog and the three
# dispatch fan-outs, never hand-written. Same host-only discipline as the
# ratchet above: it parses source with ast and imports nothing, because
# importing the supervisor pulls config.py, and config.py runs migrations.
sprig_capabilities:  ## Rewrite docs/sprigs/capabilities.md from the code
	@python3 scripts/gates/sprig-capabilities/generate.py

# Gate: the reference still describes the code. Fails with a diff when a
# capability is added, a dispatch changes what it writes, or a prune reset is
# forgotten — the last of which is otherwise silent until a user hits it.
sprig_capabilities_check:  ## Gate: capability reference matches the code
	@python3 scripts/gates/sprig-capabilities/generate.py --check

sprig_capabilities_teeth:  ## Prove the capability gate can fail
	@python3 scripts/gates/sprig-capabilities/generate.py --self-test

# Startr Swap is written to be published for other projects, including static
# sites. That claim decays the first time somebody reaches for `/pages/` to fix
# a bug: it still works here and silently stops working anywhere else.
startr_swap_check:  ## Gate: the swap library names nothing in this application
	@python3 scripts/gates/startr-swap/check.py --check

startr_swap_teeth:  ## Prove the swap-library gate can fail
	@python3 scripts/gates/startr-swap/check.py --self-test

# Release-time only. The reference is generated and gated HERE, where it can see
# the catalog it describes. The spec gets a FOLD, not a copy: a vocabulary view
# spliced into v1.md's reserved-prefix section, listing which reservations ship,
# which shipped names are unreserved, and which reservations are still empty.
#
# Deliberately not the whole reference. The spec states a contract; prune gaps
# and config field names are implementation status and stay on this side. Both
# halves of the comparison are derived — the reserved prefixes are read out of
# v1.md itself — so adding a reservation there corrects the delta on the next
# publish, with nothing to maintain by hand in either repo.
SPRIG_SPEC_DIR ?= ../BONSAI/sprig-spec
sprig_capabilities_publish:  ## Fold the capability vocabulary into the Sprig spec
	@test -f "$(SPRIG_SPEC_DIR)/v1.md" || { \
	  echo "sprig-capabilities: $(SPRIG_SPEC_DIR)/v1.md not found."; \
	  echo "Set SPRIG_SPEC_DIR=<path> or check the spec repo out beside this one."; \
	  exit 1; }
	@python3 scripts/gates/sprig-capabilities/generate.py
	@python3 scripts/gates/sprig-capabilities/generate.py --check
	@python3 scripts/gates/sprig-capabilities/generate.py \
	  --publish-spec "$(SPRIG_SPEC_DIR)/v1.md"

# Gate: the chat path emits what it emitted yesterday.
#
# Replays recorded upstream SSE streams through the real process_chat_response
# and diffs the whole ordered transcript — every socket event and every DB write,
# in call order — against a golden file. This is the oracle the chat-path chart's
# behaviour freeze depends on: without it, "the same bytes on the wire" is a
# promise nobody can check.
#
# A red run means the chat path changed. If the change was deliberate, re-record
# with `make chat_response_oracle_update` and READ the golden diff before
# committing it — that diff is the behaviour change, stated in full.
chat_response_oracle: it_build  ## Gate: replayed chat streams emit byte-identical transcripts
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts:ro" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/chat-response-oracle.py

# Re-record the goldens. Only after an INTENTIONAL behaviour change, and the
# resulting diff belongs in the commit message.
chat_response_oracle_update: it_build  ## Re-record the chat-path goldens (intentional changes only)
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts:rw" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/chat-response-oracle.py --update

# Prove the gate can fail. Disables finalize_content_blocks in memory and
# asserts the transcript moves, then asserts it moves back. A gate nobody has
# seen fail is a gate nobody should trust.
chat_response_oracle_teeth: it_build  ## Prove the chat-path oracle fails when behaviour changes
	@$(CONTAINER_RUNTIME) run --rm -e WEBUI_SECRET_KEY=fixture \
	  -v "$$(pwd)/app/backend/sage_is_ai:/app/backend/sage_is_ai:ro" \
	  -v "$$(pwd)/scripts:/scripts:ro" --entrypoint python3 \
	  $(IMAGE_NAME):$(IMAGE_TAG) /scripts/smoke/chat-response-oracle.py \
	  --self-test --case reasoning-field-never-closed

# Park a finished or dormant chart: move it under charts/_archive/ (excluded in
# .todoscope-exclude.csv, so its cards leave the kanban board) and prepend a
# stub the operator fills in. Refuses to clobber an existing archive entry.
#
# The stub is the point. An archived chart that does not say why it stopped
# cannot be told apart from an abandoned one, and the next reader either redoes
# settled work or trusts something that was never finished.
chart_archive:  ## Archive a chart: make chart_archive CHART=<name>
	@test -n "$(CHART)" || { echo "usage: make chart_archive CHART=<name>"; \
	  echo "available:"; find charts -mindepth 2 -maxdepth 2 -name TODO.md -not -path 'charts/_archive/*' \
	    | sed 's|charts/||; s|/TODO.md||; s|^|  |'; exit 1; }
	@test -d "charts/$(CHART)" || { echo "no such chart: charts/$(CHART)"; exit 1; }
	@test ! -e "charts/_archive/$(CHART)" || { echo "already archived: charts/_archive/$(CHART)"; exit 1; }
	@mkdir -p charts/_archive
	@mv "charts/$(CHART)" "charts/_archive/$(CHART)"
	@printf '> **Archived %s.** Finished or parked: FILL IN.\n> Shipped: FILL IN (commit or decision record).\n> Left open: FILL IN, and whether anyone should care.\n\n' "$$(date +%Y-%m-%d)" \
	  | cat - "charts/_archive/$(CHART)/TODO.md" > "charts/_archive/$(CHART)/TODO.md.tmp"
	@mv "charts/_archive/$(CHART)/TODO.md.tmp" "charts/_archive/$(CHART)/TODO.md"
	@echo "archived -> charts/_archive/$(CHART)/TODO.md"
	@echo "NOW: fill in the three FILL IN lines at the top, or the archive says nothing."

# Utility target to show current version
# ONE WRITER, ONE FILE. The version used to live in five places: the git tag,
# app/package.json, a `## v3.1.0` heading in README.md, SERVER_TAG in
# distribution.env, and a CHANGELOG heading. Three writers and a human kept them
# in step, and release_smoke inspected two of the five for agreement — a check
# standing guard over a redundancy that did not need to exist.
#
# app/pyproject.toml already showed the way: `dynamic = ["version"]`, read out of
# package.json by hatch. Zero writers, cannot drift. The README heading now works
# the same way, as a shields badge reading origin's tags, so this target no
# longer touches README.md.
#
# The README rewrite was deleted in the SAME change as the heading, deliberately.
# Removing a copy while leaving its writer behind leaves a writer that silently
# no-ops: `re.sub` with no match returns its input unchanged and the recipe
# writes the file back identical — no error, no exit code, and the writer goes on
# claiming to maintain something that is gone.
bump_release_version:  ## Write RELEASE_VERSION into app/package.json
	@if [ -z "$(RELEASE_VERSION)" ]; then \
		echo "Error: RELEASE_VERSION not defined. Are you on a release/ branch?"; \
		exit 1; \
	fi
	@echo "Bumping version to $(RELEASE_VERSION)..."
	@python3 -c "import json; f='app/package.json'; d=json.load(open(f)); d['version']='$(RELEASE_VERSION)'.lstrip('v'); json.dump(d, open(f,'w'), indent='\t'); f2=open(f,'a'); f2.write('\n'); f2.close(); print(f'Updated {f}')"
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
install_dev:  ## Install the dev toolchain and wire the git hooks
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
#   pre-push        scan-tree (whole-tree private-data gitleaks pass)
#   post-checkout   distribution-chain-heal (silent re-link if chain broken
#                   and content matches; warn if content diverges)
#   post-merge      distribution-chain-heal
#   post-rewrite    distribution-chain-heal (covers rebase + commit --amend)
install_hooks:  ## Wire the pre-commit hooks, all five stages
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "ERROR: pre-commit not installed. Run: make install_dev"; \
		exit 1; \
	}
	@echo "Installing pre-commit hooks (commit + push + checkout + merge + rewrite stages)..."
	pre-commit install
	pre-commit install --hook-type pre-push
	pre-commit install --hook-type post-checkout
	pre-commit install --hook-type post-merge
	pre-commit install --hook-type post-rewrite
	@echo "Hooks wired. distribution.env hardlink chain is now self-healing."

# ---------------------------------------------------------------------------
# Security Scanning Targets
# ---------------------------------------------------------------------------

# scan: Run all security scans (secrets + SAST + dependency).
# Does NOT include scan_container (requires a built image) or scan_dast (future).
scan: scan_secrets scan_sast scan_deps  ## Scan manifests: secrets, SAST, dependencies
	@echo ""
	@echo "=== All scans complete ==="

# scan_secrets: Detect accidentally committed secrets, API keys, tokens.
# Uses gitleaks against the full git history. Config: .gitleaks.toml
scan_secrets:
	$(call require_tool,GITLEAKS,gitleaks)
	@echo "=== Secrets scan (gitleaks) ==="
	$(GITLEAKS) detect --source . --config .gitleaks.toml --verbose

# scan_tree: Private-data scan of the tracked tree at HEAD. Scans a `git archive`
# (only tracked files — no node_modules to trudge through, no history noise), so
# it is fast enough for the pre-push hook. Full-history auditing stays in
# scan_secrets; the commit-stage gitleaks hook covers the staged diff.
scan_tree:  ## Private-data scan of the tracked tree (pre-push hook)
	$(call require_tool,GITLEAKS,gitleaks)
	@echo "=== Private-data scan: tracked tree at HEAD (gitleaks) ==="
	@tmp=$$(mktemp -d); \
	git archive HEAD | tar -x -C "$$tmp"; \
	$(GITLEAKS) detect --no-git --source "$$tmp" --config .gitleaks.toml --verbose; \
	rc=$$?; rm -rf "$$tmp"; exit $$rc

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
#
# Deliberately NOT a member of `scan`. `scan` reads manifests and answers "is
# there a newer safe version of something we declare"; this reads the artifact
# and answers "what is actually inside the thing we ship". Those are different
# questions, and the gap between them is where this repo's real exposure has
# been sitting: 136 of 194 Dependabot alerts are filed against app/pyproject.toml,
# which is pip-installed nowhere, while pypdf==4.3.1 ships inside a sprig closure
# pinned in a shell script no manifest scanner will ever read. Adding this to
# `scan` would also make a documented manifest-level check require a build.
# It belongs in gauntlet_full, which builds an image anyway.
scan_container: it_build  ## Gate: trivy over the BUILT image (HIGH/CRITICAL)
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
## docs_gate — a doc that names a make target which does not exist fails here.
## Added 2026-08-02 after a scripted diff found in seconds what months of reading
## had missed: five phantom `make test_*` commands in a Testing Standards section
## describing a DJANGO project (this is FastAPI), and three claims that
## `try_sage_stop` already existed. It never did.
## Extended 2026-08-12 to scan document trees OUTSIDE the repo — agent memory
## stores, notes vaults, sibling checkouts. They issue instructions the same way
## a runbook does and rot the same way, with nobody reviewing them: one such file
## was still saying "release with `make release_and_push_GHCR`" days after that
## door was made private, and it was found by hand. Which trees exist is data,
## in scripts/gates/docs-targets.roots, not logic in the gate. An absent root is
## announced and skipped, so a fresh clone still runs.
docs_gate:  ## Gate: every `make X` named in a scanned document exists
	@scripts/gates/docs-targets.sh

docs_gate_teeth:  ## Prove the doc-target gate can fail
	@scripts/gates/docs-targets.sh --self-test

## ruff_gate — the Python linter. Nothing else in this repo reads Python
## semantics: bandit reads security, black reads formatting, and the chat-path
## ratchet reads six shapes of one file. Ruff read all 218 backend files in 40ms
## and found the one undefined name in the tree — the frozen NameError at
## middleware.py:1209. Config and the reasoning behind every ignored rule live in
## app/pyproject.toml under [tool.ruff].
ruff_gate:  ## Gate: ruff clean
	@scripts/gates/ruff/run-gate.sh check

## ruff_format_check — reports formatter drift. NOT wired into lint yet: 83 of
## 218 backend files are unformatted, and one of them is middleware.py, whose
## line numbers are anchored by nine fences and 64 chart citations. Reformatting
## it is a sequenced job, not a side effect of turning a gate on.
ruff_format_check:
	@scripts/gates/ruff/run-gate.sh format-check

## ruff_format_fix — applies the formatter. Run it deliberately, then re-point
## the chat-path fences and citations before committing.
ruff_format_fix:
	@scripts/gates/ruff/run-gate.sh format-fix

## cognitive_complexity — the depth ratchet for the whole backend. Cyclomatic
## complexity sat flat at F (58) across the three passes that cut
## process_chat_response by 30%; radon's maintainability index moved the WRONG
## way on a commit that changed no code at all. Cognitive complexity was the only
## measure of the five benched that registered the work: 826 to 578.
cognitive_complexity:  ## Ratchet: cognitive complexity (needs a local baseline)
	@scripts/gates/cognitive-complexity/run-gate.sh

## cognitive_complexity_tighten — lower the baseline to what the tree earns today.
cognitive_complexity_tighten:
	@scripts/gates/cognitive-complexity/run-gate.sh --tighten

## cognitive_complexity_teeth — prove the ratchet still fails a worsened tree.
cognitive_complexity_teeth:
	@scripts/gates/cognitive-complexity/run-gate.sh --self-test

lint: docs_gate pipefail_lint ruff_gate cognitive_complexity  ## Lint: docs, pipefail, ruff, eslint, svelte-check, prettier, black
	@echo "=== Frontend lint (eslint + svelte-check) ==="
	cd app && bun run lint:frontend
	cd app && bun run lint:types
	@echo ""
	@echo "=== Format check (prettier + black) ==="
	cd app && bunx prettier --check "**/*.{js,ts,svelte,css,md,html,json}"
	cd app && black --check --exclude ".venv/|/venv/" backend/

# ===========================================================================

.PHONY: $(shell grep -hoE '^[a-zA-Z_][a-zA-Z0-9_-]*:' $(MAKEFILE_LIST) | tr -d ':')
## Derived, not hand-listed. There were 104 targets and 14 declarations, so
## 90 were one same-named file away from silently not running.


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
	@echo "  1. make bump_release_version     # Write the version into app/package.json"
	@echo "  2. Edit CHANGELOG.md with release notes, then commit"
	@echo "  3. make release_smoke            # Build :X.Y.Z + smoke native + amd64"
	@echo "  4. (Staging deploy + verify against :X.Y.Z image)"
	@echo "  5. make ghcr_login               # Authenticate with GHCR"
	@echo "  6. make ship                     # Finish, push image, publish catalog"
endef

# Hotfix variant — same shape, hotfix-flavored copy.
define next_steps_hotfix
	@echo ""
	@echo "=== Hotfix branch created ==="
	@echo "Next steps:"
	@echo "  1. Fix the issue, then commit"
	@echo "  2. make bump_release_version     # Write the version into app/package.json (+ commit)"
	@echo "  3. make release_smoke            # Build :X.Y.Z + smoke native + amd64"
	@echo "  4. (Staging deploy + verify)"
	@echo "  5. make ghcr_login"
	@echo "  6. make ship                     # Same door as a release; finish_flow knows"
endef

minor_release: require_gitflow_next  ## Start a git-flow release branch, minor bump
	@# Start a minor release with incremented minor version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2+1".0"}')
	$(next_steps_release)

patch_release: require_gitflow_next  ## Start a git-flow release branch, patch bump
	@# Start a patch release with incremented patch version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}')
	$(next_steps_release)

major_release: require_gitflow_next  ## Start a git-flow release branch, major bump
	@# Start a major release with incremented major version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1+1".0.0"}')
	$(next_steps_release)

hotfix: require_gitflow_next  ## Start a git-flow hotfix branch
	@# Start a hotfix with incremented patch.patch version (fourth component)
	git flow hotfix start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{if (NF < 4) print $$1"."$$2"."$$3".1"; else print $$1"."$$2"."$$3"."$$4+1}')
	$(next_steps_hotfix)

# Finish a release or hotfix with plain git — NOT git-flow-next's finish.
#
# git-flow-next's finish repeatedly stranded releases: it committed a
# fast-forward as an empty merge, misread skipped pre-commit hooks as a
# failure, and (3.0.0) ran a remote-branch sync check that dies when the
# topic branch was never pushed — leaving a half-done finish plus a stale
# state file. We drove the merges by hand to recover every time, so that is
# the default now. git flow release/hotfix START still creates branches.
#
# The version comes from the in-progress release/*|hotfix/* branch, which is
# authoritative; RELEASE_VERSION (a make var that falls back to the latest tag
# off-branch) is only the fallback for the re-push case after the branch is
# gone. Every step is idempotent — a merge already in master or develop is
# skipped, an existing tag is skipped — so a conflict-and-retry RESUMES rather
# than double-merging or wedging. No git-flow state file exists, so no
# self-heal target is needed. The topic branch is never pushed; results push
# explicitly at the end. distribution_verify still guards the hardlink chain.
define finish_flow
	@set -e; \
	br="$$(git for-each-ref --format='%(refname:short)' refs/heads/release refs/heads/hotfix 2>/dev/null | head -1)"; \
	if [ -n "$$br" ]; then ver="$${br#*/}"; else ver="$(RELEASE_VERSION)"; fi; \
	test -n "$$ver" || { echo "Nothing to finish: no release/*|hotfix/* branch and no version (already complete?)."; exit 0; }; \
	tag="v$$ver"; \
	master="$$(git config --get gitflow.branch.master 2>/dev/null || echo master)"; \
	develop="$$(git config --get gitflow.branch.develop 2>/dev/null || echo develop)"; \
	if [ -n "$$(git status --porcelain --untracked-files=no)" ]; then \
		echo "ERROR: working tree has uncommitted tracked changes — commit or stash first."; \
		git status --short; exit 1; \
	fi; \
	echo "=== Finishing $$ver (plain git; no git-flow finish) ==="; \
	if [ -n "$$br" ]; then echo "  $$br -> $$master + $$develop, tag $$tag"; \
	else echo "  branch already merged/gone — resuming push (tag $$tag)"; fi; \
	if [ -n "$$br" ]; then \
		git checkout "$$master"; \
		if git merge-base --is-ancestor "$$br" HEAD; then echo "  $$master already contains $$br — skip merge"; \
		else git merge --no-ff --no-verify -m "Merge branch '$$br'" "$$br"; fi; \
	fi; \
	if git rev-parse -q --verify "refs/tags/$$tag" >/dev/null; then echo "  tag $$tag exists — skip"; \
	else git tag -a "$$tag" -m "Release $$tag"; fi; \
	if [ -n "$$br" ]; then \
		git checkout "$$develop"; \
		if git merge-base --is-ancestor "$$br" HEAD; then echo "  $$develop already contains $$br — skip merge"; \
		else git merge --no-ff --no-verify -m "Merge branch '$$br'" "$$br"; fi; \
		git branch -d "$$br"; \
	fi; \
	git checkout "$$develop"; \
	git push origin "$$develop"; \
	git push origin "$$master"; \
	git push --tags; \
	echo ""; \
	echo "=== $$ver complete — pushed $$develop + $$master + tag $$tag ==="
endef

# Minimum Docker memory for the multi-arch build, in GiB. 2.3.0 died with buildx
# OOM mid-push, leaving a tag on origin and no image behind it. Override on the
# command line if your host genuinely needs less.
RELEASE_MIN_DOCKER_GIB ?= 8

## release_preflight — the four things that can only be checked against the
## outside world. Everything else this used to hold has been designed away.
##
## It deliberately does NOT compare SERVER_TAG to the version being released.
## Those are different facts (see the IMAGE_TAG comment at the top of this file),
## and an earlier draft of this target got that wrong.
##
## Runs BEFORE release_smoke, not after: a preflight that fires at the end of a
## twenty-minute build has already wasted the twenty minutes.
release_preflight:  ## Release gate: gh auth, docker memory, tag not published, CHANGELOG entry
	@set -e; \
	ver="$(RELEASE_VERSION)"; \
	if [ -z "$$ver" ]; then \
		echo "release_preflight: RELEASE_VERSION is empty. Are you on a release/ or hotfix/ branch?"; exit 1; \
	fi; \
	echo "=== release_preflight for $$ver ==="; \
	if ! gh auth status >/dev/null 2>&1; then \
		echo "  FAIL  gh CLI is not authenticated. The push would fail after the tag is cut."; \
		echo "        Fix: gh auth login"; exit 1; \
	fi; \
	echo "  ok    gh authenticated"; \
	mem=$$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0); \
	need=$$(( $(RELEASE_MIN_DOCKER_GIB) * 1024 * 1024 * 1024 )); \
	if [ "$$mem" = "0" ]; then \
		echo "  FAIL  docker daemon is not reachable."; exit 1; \
	elif [ "$$mem" -lt "$$need" ]; then \
		echo "  FAIL  docker has $$(( mem / 1024 / 1024 / 1024 ))GiB, and the multi-arch build wants $(RELEASE_MIN_DOCKER_GIB)GiB."; \
		echo "        2.3.0 OOMed here, after the tag was already on origin."; \
		echo "        Fix: raise the VM memory, or override RELEASE_MIN_DOCKER_GIB=<n>."; exit 1; \
	fi; \
	echo "  ok    docker up with $$(( mem / 1024 / 1024 / 1024 ))GiB"; \
	if [ -n "$$(git ls-remote --tags origin "refs/tags/v$$ver" 2>/dev/null)" ]; then \
		echo "  FAIL  tag v$$ver is already on origin. This release has been cut before."; \
		echo "        Both 2.3.0 and 3.1.0 reached this state and were recovered by hand."; \
		echo "        Fix: publish the existing tag's image, or release a new version."; exit 1; \
	fi; \
	echo "  ok    v$$ver is not yet on origin"; \
	if ! grep -qE "^## \[$$ver\]" CHANGELOG.md; then \
		echo "  FAIL  CHANGELOG.md has no '## [$$ver]' section."; \
		echo "        Nothing can derive this one: it is prose, and it has to be written."; exit 1; \
	fi; \
	echo "  ok    CHANGELOG.md has a [$$ver] section"; \
	echo "=== release_preflight passed ==="

release_finish: distribution_verify  ## Merge the release branch to master + develop, tag, push
	$(finish_flow)

# finish_flow discovers release/ vs hotfix/ from the branch itself, so these two
# recipes were byte-identical. One body now, and the name survives because it is
# an affordance: a hotfix operator who types a target that does not exist reaches
# for `git` by hand, and hand-typed git is what cut this repo's only lightweight tag.
hotfix_finish: release_finish  ## Same as release_finish; finish_flow self-discovers

# PRIVATE (leading underscore, no ## comment, so `make help` cannot list it).
#
# This is the irreversible half of a release: it pushes a multi-arch image to a
# public registry under a tag that other people will pull. There were three doors
# into it and the documented one skipped sprig_publish, which is how a new Sprig
# shipped internal-only and unpullable. The fix is not another check placed
# nearby — it is that the door is no longer reachable by accident. `ship` is the
# way in, for releases and hotfixes alike, because release_smoke accepts both
# branch shapes and finish_flow works out which it is on.
_release_and_push_GHCR: release_preflight release_smoke release_finish
	@echo ""
	@echo "=== Building and pushing to GHCR ==="
	@$(MAKE) _it_build_multi_arch_push_GHCR
	@echo ""
	@echo "=== Verifying the pushed manifest is present + multi-arch ==="
	@$(MAKE) verify_ghcr_manifest
	@echo ""
	@echo "=== Pinning SERVER_TAG=$(IMAGE_TAG) in distribution.env ==="
	@$(MAKE) _pin_server_tag IMAGE_TAG=$(IMAGE_TAG)
	@echo ""
	@echo "=== $(IMAGE_TAG) published ==="
	@echo "Verify: docker pull $(GHCR_IMAGE_NAME):$(IMAGE_TAG)"
	@echo "Verify: docker pull $(GHCR_IMAGE_NAME):latest"

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

distribution_sync:  ## Re-link distribution.env across the sibling repos
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

# ONE DERIVATION, TWO CALLERS. distribution_verify and distribution_heal each
# worked out the expected link count for themselves, and spelled it in opposite
# directions: verify started at 3 and dropped to 2 when the docs sibling was
# missing, heal started at 2 and raised to 3 when it was present. Same answer,
# two ways to get it wrong independently, on the one file that has already broken
# two releases. They also each open-coded the BSD/GNU `stat` fallback.
#
# Defined as a shell prelude rather than a Make define because both callers are a
# single `\`-continued shell block, and a define would inject line breaks into it.
# The count is DERIVED, not assumed. It used to start at 2 and rise to 3 when the
# docs sibling existed, which silently assumed homebrew-apps was always there. On
# a clone with no siblings, distribution.env is an ordinary 1-link file and the
# gate FAILED — it could not pass on a fresh machine. That went unnoticed only
# because the pre-commit hook was gated on the file being staged, so it almost
# never ran. Two defects hiding each other. Count the locations that exist and
# the gate is right everywhere, including the machine that has none of them.
DIST_LINK_PRELUDE = links_of() { stat -f "%l" "$$1" 2>/dev/null || stat -c "%h" "$$1"; }; \
	expected_links=0; \
	for d in "$(SIBLING_HOMEBREW)" "$(SIBLING_AI_UI)" "$(SIBLING_DOCS)"; do \
		if [ -d "$$d" ]; then expected_links=$$((expected_links + 1)); fi; \
	done; \
	if [ "$$expected_links" -lt 1 ]; then expected_links=1; fi;

distribution_verify:  ## Assert the distribution.env hardlink chain is intact
	@set -e; $(DIST_LINK_PRELUDE) \
	for f in $(DIST_SOURCE) $(SIBLING_AI_UI)/distribution.env $(SIBLING_DOCS)/distribution.env; do \
		test -e "$$f" || continue; \
		links=$$(links_of "$$f"); \
		if [ "$$links" != "$$expected_links" ]; then \
			echo "FAIL: $$f has $$links links, expected $$expected_links"; \
			echo "  Run 'make distribution_sync' to re-establish the chain."; \
			exit 1; \
		fi; \
	done; \
	echo "OK: distribution.env hardlink chain intact ($$expected_links links)."

# Repair the distribution.env hardlink chain after a git operation (checkout /
# merge / rebase / amend) rewrote the file in place.
#
# distribution.env is ONE file with three names -- a single inode with directory
# entries in AI-UI, homebrew-apps and WEB-Sage.Education-docs. A hardlink has no
# original. While the link holds there is no ownership question to answer. Once
# git severs it there are three independent files and no repo has standing to
# overrule another; DIST_SOURCE is merely the path this Makefile reads at
# startup, not an authority. So a break cannot be settled by asking who owns the
# file. Only the content can settle it, and the content carries a version.
#
# The rule: NEWEST WINS, FORWARD ONLY.
#
#   links intact                 -> silent, exit 0
#   cut, content equal           -> relink peers
#   cut, this repo's tag NEWER   -> this repo wins, relink peers
#   cut, this repo's tag OLDER   -> no-op; the merge brings this repo forward
#                                   and the post-merge run relinks
#   cut, same tag, other content -> no-op; nothing to rank on, so do not guess
#
# Two constraints are load-bearing. Undo either and the release breaks again.
#
# 1. NEWEST MEANS HIGHEST VERSION, NEVER NEWEST MTIME. `git checkout` stamps the
#    file it writes with the current time, so the STALE content is always the
#    freshest file on disk. A timestamp comparison picks the wrong side every
#    single time.
#
# 2. NEVER WRITE INTO THIS REPO'S WORKTREE. Heal fires from a hook in the repo
#    that just checked out. Writing the newer value in here dirties a file the
#    next `git merge` must touch, and git refuses with "Your local changes would
#    be overwritten by merge" -- a hard stop where there was only a warning.
#    The older-side no-op is what keeps release_finish alive.
#
# The older-side no-op is also the regression guard: a checkout of an old branch
# must never push a stale SERVER_TAG out into the other two repos.
#
# ADVISORY, ALWAYS -- exits 0 whatever it finds. Git propagates a non-zero
# post-checkout hook to `git checkout` itself, and `set -e` inside finish_flow
# reads that as a dead release. This target therefore does NOT call
# distribution_verify; that call is what halted 3.1.0 three times. Verification
# stays where it belongs: the distribution-chain-verify pre-commit hook, and
# release_finish / hotfix_finish.
#
# One shell, deliberately. As separate recipe lines an `exit 0` ends only its
# own line and Make carries on into the next one.
#
# Proof: make distribution_heal_fixture
distribution_heal:
	@set -e; $(DIST_LINK_PRELUDE) \
	self=$(SIBLING_AI_UI)/distribution.env; \
	if [ ! -f "$$self" ]; then exit 0; fi; \
	links=$$(links_of "$$self"); \
	if [ "$$links" = "$$expected_links" ]; then exit 0; fi; \
	mine=$$(grep -E '^SERVER_TAG=' "$$self" 2>/dev/null | head -1 | cut -d= -f2); \
	held=""; \
	for peer in $(DIST_SOURCE) $(SIBLING_DOCS)/distribution.env; do \
		if [ ! -e "$$peer" ]; then continue; fi; \
		if cmp -s "$$self" "$$peer"; then ln -f "$$self" "$$peer"; continue; fi; \
		theirs=$$(grep -E '^SERVER_TAG=' "$$peer" 2>/dev/null | head -1 | cut -d= -f2); \
		newest=$$(printf '%s\n%s\n' "$$mine" "$$theirs" \
		          | sort -t. -k1,1n -k2,2n -k3,3n | tail -1); \
		if [ -n "$$mine" ] && [ "$$mine" != "$$theirs" ] && [ "$$newest" = "$$mine" ]; then \
			ln -f "$$self" "$$peer"; \
		else \
			held="$$held $$peer"; \
		fi; \
	done; \
	if [ -n "$$held" ]; then \
		echo "distribution.env: holding at SERVER_TAG=$$mine; a newer copy exists in:$$held"; \
		echo "  A checkout severed the link. The merge that lands the newer tag reconciles it."; \
	fi; \
	exit 0

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
