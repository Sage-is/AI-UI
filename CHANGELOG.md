# Changelog

All notable changes to [Sage.is AI-UI](https://github.com/Sage-is/AI-UI) are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Sage.is AI-UI ships under the [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.html).

---

## [Unreleased]

### Added

**The Sprig™ capability reference is generated from the code, never written by hand**
`docs/sprigs/capabilities.md` describes every capability the catalog ships: what each one delivers, whether it runs a process, what it writes into the running configuration, and what a prune reverses. The document is emitted by reading the catalog and the three dispatch fan-outs with a parser, so it cannot drift from the code that defines it. `make sprig_capabilities_check` runs inside `gauntlet_full` and fails with a diff when a capability is added, a dispatch changes what it writes, or a prune reset is forgotten. The gate has its own self-test, which perturbs the committed document three ways and asserts the check notices each one — a gate nobody has watched fail is a gate nobody should trust.

The reference reports what the code does rather than what it should do, and the first run said so: pruning the Tika or Docling Sprig leaves `CONTENT_EXTRACTION_ENGINE` pointing at a released port. That was not known before the document existed. It is logged, not fixed.

`make sprig_capabilities_publish` folds a vocabulary view into the Sprig specification next door — which reserved prefixes ship, which shipped names have no reservation, which reservations are still empty. A view, not a copy: the specification states a contract, and prune gaps are implementation status that stays on this side. Both halves of the comparison are derived, the reserved list from the specification's own prose, so a reservation added there corrects the delta on the next publish with nothing to maintain by hand.

### Changed

**The chat path's largest function lost a third of its lines, with the behaviour frozen**
`process_chat_response` fell from 1,511 lines to 1,108, and the file's deeply nested lines fell from 1,009 to 773 — from half the code to two fifths. Three mechanical passes did it: thirteen dead imports dropped, five pure functions lifted out of the closure to module level, and eleven hand-spelled `chat:completion` payloads collapsed onto two helpers. Four of those eleven were identical character for character.

Nothing about the behaviour changed, and the replay oracle proves it: every recorded stream emits a byte-identical transcript before and after each pass. The structure ratchet's ceilings were lowered to what the passes earned, so they cannot drift back.

The lift needed no design decision. A symbol-table pass showed the five functions close over nothing but each other, so they could leave the closure without disturbing the two `nonlocal` accumulators that the rest of the restructure still waits on. `CACHE_DIR` went with the dead imports, and with it the chat path's only edge to the configuration module — which runs database migrations when imported. That edge is what stood between these functions and a test that could drive them directly.

**The reasoning-block replay net gained a case, recorded from a live failure**
A model can close a thinking tag that the reader never saw open. The provider routes the model's opening tag into its reasoning field, so the content stream never carries one, and the block opens and closes correctly through that path; the model then closes the tag the only way it can, in the content stream, and the orphan renders as text beside a perfectly good reasoning block. The oracle now replays that shape and pins it. The golden records the leak as it stands, not as it should be, and its job is to fail the day someone treats an unpaired closing tag as an implicit opening — which here would open a second reasoning block and seal the answer inside it, turning a cosmetic leak into the one that swallows the answer.

**Release finish runs on plain git, not git-flow-next**
`make release_finish` and `make hotfix_finish` now merge the release branch into master and develop, tag it, and delete it with plain git. git-flow-next's finish stranded three releases: it committed a fast-forward as an empty merge, misread skipped pre-commit hooks as a failure, and ran a remote-branch sync check that died when the release branch was never pushed to origin. Each time the fix was to finish the merge by hand, so the Makefile does that by default now. `git flow release start` still opens branches. Every step is idempotent — an already-merged branch or an existing tag is skipped — so a merge conflict resolves and the finish resumes instead of wedging. The self-heal target that dropped git-flow's stale state files is gone; there are no state files left to clean.

### Fixed

**The try.sage welcome page scrolls on phones**
The welcome page pinned a full-screen layer at 100vh and centered its content with flexbox. On a phone, 100vh includes the strip behind the browser chrome, so the bottom of the page hid behind the toolbar. Centered overflow was cut off both ends with no way to scroll to it. The page is now server-rendered as a normal document: it scrolls whenever it is taller than the screen, full height means the height you can see (dvh), and the safe-area inset keeps the footer clear of the home indicator. First response is the whole page — 5 KB, no JavaScript bundle.

The cycling backgrounds and the rotating welcome heading came with it. Four images crossfade under the same gradient and dim as before, and three phrases rotate in the heading, driven by fourteen lines of plain JavaScript instead of two Svelte components. Without JavaScript the first image and the first phrase stay put, which is a whole page rather than a broken one. The background layer is still pinned to the viewport, which is correct for a backdrop and was only ever wrong for content.

Signed-in readers get the app exactly as before. A visitor who lands on `/auth` with no invite goes to the welcome page; an explicit sign-in link — the `?next=` an admin follows from a server-rendered page — still opens the real form, and so does a magic link that turned out to be expired, so the reader can read why instead of watching the welcome page reappear. Deploys without `ENABLE_TRY_SAGE` are untouched: the routes are only registered when the trial subsystem is on.

**Server-rendered pages pick up an edited stylesheet or script within a release**
Assets under `/pages/_assets/` ship with a week-long cache and used to carry the release version in their URL, on the reasoning that the version changes whenever the file could have. It does not: a file edited twice inside one release keeps one URL, so a browser that loaded the first version runs it for a week while the server serves the second. The operator ships a fix and watches the old behaviour. The URL now carries eight characters of the file's own hash, read at first use — no build step, sixteen small files, once per process — so it changes when and only when the bytes do. Found the hard way: a fixed page kept rendering the broken script.

## [3.0.0] — 2026-07-15

### Added

**The Sprig™ grafting subsystem**
Capabilities now arrive as OCI artifacts. The server pulls each one from a registry with a dockerized oras, verifies its sha256 against a pin baked into the image, and grafts it at runtime. The catalog in `sprigs/supervisor.py` is the allowlist. A route whose capability is not grafted returns 503 with a pointer to the graft, not a crash. Grafts survive full container recreation: state records on the data volume, boot reconciles, cached tars restore offline. The admin panel shows every catalog entry as a card with its compatibility and graft state.

**A seventeen-entry catalog across twelve capabilities, zero external pulls**
Embedding (ONNX and GGUF cultivars), vector store (chromadb), RAG loaders (langchain), PDF export (fpdf2 + CJK fonts), speech-to-text (whisper.cpp), reranker, workshop themes, pyodide code interpreter, in-browser ML wasm, media (ffmpeg), backup (rclone), and the Svelte dev toolchain. Every artifact ships from `ghcr.io/sage-is` — no HuggingFace, S3, or third-party pull at runtime.

**Multi-arch catalog: the whole catalog runs on amd64 and arm64**
The catalog schema gains per-arch overrides: `arches: {arch: {tag, binary_sha256}}`. Every one of the seventeen entries grafts on both architectures — document search, ingestion, PDF export, local embedding, STT, reranker, media transcode, backup, and the dev toolchain. The ONNX embedding weights are arch-neutral bytes; the python-wheel closures build per-arch; the static GGUF/whisper servers build headless in musl (any libc); the ffmpeg and rclone binaries come from pinned, checksum-verified upstream releases. Each recipe (`scripts/build-sprig-*.sh`) runs its sanity gate on the target arch under QEMU before packing — the ffmpeg recipe transcodes the real wav→webm/opus→wav voice-note path, the GGUF servers boot and answer a live embedding/rerank request. The headless llama-server (`LLAMA_BUILD_UI=OFF`+`LLAMA_USE_PREBUILT_UI=OFF`) drops the web UI that otherwise blocked the static amd64 cross-build.

**Fail-closed architecture guard**
Every catalog entry must declare a host binding or neutrality through the `_sprig(spec, arch=...)` constructor. A forgotten declaration fails at import, in CI, not on a customer host. A mismatched host refuses the graft before any bytes move: the sprig wilts to a per-capability 503 and the rest of the server keeps serving. No more `Exec format error`.

**Artifact signing with minisign**
Artifacts carry a detached minisign signature as a second OCI layer, verified offline after the sha256 gate and before extraction. A present signature is always verified. `signed: True` per entry or `SPRIG_REQUIRE_SIGNED=1` globally makes it mandatory.

**Upgrade gate**
`make upgrade_gate` boots the new image on a copy of a production snapshot and proves the upgrade: migrations run, users and chats survive, legacy RAG config degrades cleanly, the vector store opens post-graft, and every production-critical capability grafts on the target arch. Any refusal fails the gate.

**Release and catalog automation**
One `REGISTRY` variable points the image and the catalog at the same host — swap to an in-house registry with a flag, no code edits. `make ship` releases the platform: multi-arch image push plus an idempotent catalog verify that rebuilds nothing. `make catalog_release` is the sprigs-changed path: build, sign, publish. The publish gate derives its repo list from the catalog and fails loudly on any package the world cannot pull anonymously. All oras use is containerized; nothing installs on the host.

**Real embedding server with ONNX and sentence-transformers backends**
Local embedding without torch on a slim image: the ONNX path rides the vector-chroma runtime. GGUF cultivars serve through an in-house static llama-server where parity gates pass.

**Sprig™-first wizard**
The AI Engine wizard now delivers the whole RAG story as Sprigs before falling back to the legacy install: the vector store (chromadb), the embedding model (a catalog cultivar matching the configured model — pre-seeded, sha256-pinned weights served by a supervised child), the document loaders (rag-loaders — without them every upload 503s), and STT (the static whisper-server). The wizard's HuggingFace downloads and its multi-gigabyte torch install now run only for models with no cultivar. This closed the last live HF pulls in the product.

**Workshop themes as Sprigs**
Bio (green) and Math (blue) design-token themes graft like any other capability. A theme is one self-contained `theme.css` — no process, no executable code. The CSS is validated at graft time and fails closed; the active theme serves at `/themes/active.css`. The last grafted theme wins; pruning the active one restores the default look. Built for workshops where two Spaces must not be mistaken for each other.

**Provider logos for remote models**
Remote models now show their provider's logo in the model list.

**Cypress coverage for chat flow, settings, and the upgrade path**
New specs exercise chat, settings, and the post-upgrade surface, with `data-cy` attributes across Sprigs, UserList, and AddUserModal for stable selectors.

### Changed

**Slim rootstock — BREAKING for operators**
chromadb, langchain, pypdf, docx2txt, fpdf2, and the whisper and embedding runtimes left the base image. They return as Sprigs. After upgrading, an admin grafts the capabilities the deployment uses; until then those routes answer 503 with a graft pointer. Chat, auth, and all stored data are untouched. This is the change that makes this release 3.0.0.

**Sprig registry is env-driven**
`SPRIG_REGISTRY` (default `ghcr.io/sage-is`) replaces any hardcoded registry. `SPRIG_REGISTRY_INSECURE` gates plain HTTP and auto-enables only for loopback hosts. The registry is probed at boot — unreachable is one loud log line, not a per-graft surprise. The local dev registry moved to a named volume (`sprig-registry-data`) that `docker volume prune` cannot wipe.

**Production builds no longer emit sourcemaps.**

### Fixed

**Document search activates the moment the vector-store Sprig grafts — no restart**
Five modules imported the vector-DB client by value (`from factory import VECTOR_DB_CLIENT`), capturing `None` at boot on a slim image. After a runtime graft the shared client went live but those copies stayed `None`, so indexing and search raised `'NoneType' object has no attribute 'query'` until a restart — the "restart to activate document search" caveat. Every consumer now reads the client through the factory module, so a fresh graft serves reads and writes immediately. The wizard's own file-index step proves it end to end.

**The wizard's "ready" signal now means uploads work**
The wizard grafted the document loaders after it flipped the embedding status to ready. A user who uploaded the instant the wizard reported ready hit a 503 — the loaders overlay had not landed. The wizard now grafts the loaders first, before it signals ready. Loaders are a fast overlay; the embedding weights are the slow pull. Front-loading the loaders costs nothing and closes the window.

**Zero runtime egress for capability delivery**
Every capability byte comes from `ghcr.io/sage-is`, pinned by sha256 in the image. No HuggingFace, S3, or third-party download runs on an operator's machine. The pull happens once, at packaging time, on the build host.

**CVE pins travel with the closures**
The sprig recipes pin `langchain==0.3.30` (CVE-2026-45134), `langchain-community==0.3.27` (CVE-2025-6984), `pypdf==4.3.1`, and `pillow==12.2.0`. Dependency CVE response now means rebuilding one artifact and bumping one pin — not rebuilding the platform image.

**Fail-closed everywhere in the graft path**
A wrong sha256 refuses before extraction. A present-but-invalid signature refuses. An artifact with no declared architecture refuses rather than guessing. Each refusal wilts one capability to a 503; none of them can take the server down.

---

## [2.3.4] — 2026-06-14

### Added

**How-to-fix modals on `/admin/diagnostics`**
Each failing diagnostic row now carries a "Show me how to fix this" button. The button opens a modal with deployment-shape-aware steps. The backend already detects the deployment shape (CapRover, Docker Compose, Homebrew, or unknown) and reports a confidence level; the modal reads both. When confidence is high, the modal renders the detected shape's steps inline plus a "Not on CapRover? Show other deployment types" expander that opens the alternatives below. When confidence is low or unknown, the modal opens with radio buttons asking the operator to pick their deployment shape before showing any steps. Steps cite specific UI paths (`Apps → App Configs → Environmental Variables`) and ship copy-to-clipboard commands (`head -c 32 /dev/random | base64`). A fix registry covers nine `issue_type` values the diagnostics router emits: `endpoint_unreachable`, `endpoint_degraded`, `secret_key_ephemeral`, `alembic_pending`, `alembic_ahead`, `data_not_writable`, `static_asset_missing`, `permissions_policy_invalid`, `csp_missing`. An undocumented `issue_type` falls back to a "documentation coming" message rather than rendering blank.

**Command library at the bottom of `/admin/diagnostics`**
Six recovery snippets surface as collapsible rows with copy-to-clipboard buttons. The catalog covers opening SQLite inside the container, inspecting stale OpenAI and Ollama base-URL history rows, generating a `WEBUI_SECRET_KEY`, running pending Alembic migrations (with an inline warning that this MUST NOT run when `alembic_ahead` is the diagnostic), and restarting the container. There is no run button anywhere. The library never executes a command on the operator's behalf. The previous generation of the diagnostics page considered an arbitrary-shell run surface; the design rejected that as anti-poka-yoke and the snippet catalog replaces it.

**62 new i18n keys in `en-US/translation.json`**
The `diagnostics.fix.*` namespace covers 49 step descriptions and plain-English summaries across nine issue types. The `diagnostics.library.*` namespace covers 13 titles, descriptions, and the migration warning text. Around 17 modal and library UI strings (deployment-shape labels, `Copy`, `Copied to clipboard`, `Steps for CapRover`, and similar) land alongside. Other locales lag without blocking; the keys are scoped so a translator can fill them at any cadence.

### Fixed

**"Documentation coming in 2.3.4" placeholder buttons now work**
Phase 3b in 2.3.3 shipped the "Show me how to fix this" button stub in `DiagnosticRow.svelte` and the Issues banner with `disabled aria-disabled="true" title="Documentation coming in 2.3.4"`. The buttons are now functional. The disabled-button styling is replaced with the standard outlined-button styling. The click handler routes through a new `onFix(issueType)` prop in `DiagnosticRow.svelte` to an `openFixModal(issueType)` handler in `Diagnostics.svelte`, which sets the modal's `issueType`, `defaultShape`, and `shapeConfidence` props from the diagnostics response.

### Security

**No arbitrary-shell run surface in the diagnostics page**
The command library is copy-only by design. Every snippet renders as a `<pre>` block with a Copy button next to it; the operator pastes into their own terminal and runs under their own audit trail. The earlier generation of the diagnostics page considered embedding a run surface; that was rejected because the admin token plus a freeform shell box is a remote-code-execution primitive. The catalog covers the same six recovery cases without the primitive.

---

## [2.3.3] — 2026-06-07

### Added

**Admin Diagnostics Page at `/admin/diagnostics`**
A read-only operator dashboard. One page renders every external endpoint the container talks to: OpenAI, Ollama, Tika, Docling, the reranker, the embedding service. Boot status sits beside it: data writable, secret key persisted, Alembic at head. Static-asset health and live browser headers round out the page. Each row carries a plain-English summary. Technical detail collapses open underneath. Issues sort worst-first across all sections. URLs the operator removed from config show up in a separate "Previously configured" group. Re-probe-all and per-row re-probe both work. Refresh is manual. The header shows "Last refreshed N ago" via a dayjs ticker.

**`EndpointHealth` Registry**
Every HTTP-backed capability reports the outcome of each call into one in-memory registry keyed by URL. Boot probes seed it at startup. Runtime calls keep it fresh. Save-time probes populate it when an admin adds a URL. The registry snapshots to `data/diagnostics.json` so the dashboard survives container restarts. The diagnostics page reads from it as the single source of truth.

**Structured `EndpointUnreachable → 503` Boundary**
A new `EndpointUnreachable(url, underlying, capability)` exception replaces the silent-failure pattern at every HTTP boundary. A FastAPI exception handler maps it to 503 with a structured body: `{detail, url, capability, underlying, fix}`. The `fix` field points at `/admin/diagnostics`. HTTP wrappers raise the exception. Routers let it pass through. The boundary handler ships the response.

**Lifespan Boot Probes**
Startup fans out probe calls across every configured external URL in a thread pool with a 5-second timeout, populates the registry, then yields to uvicorn. The port binds without waiting on slow DNS. A `BootProbeProgress` object exposes started_at, completed_at, total, completed, in_flight. The dashboard reads it and suppresses the "issues at top" alarm while probes are still in flight, so an operator who opens the page two seconds after boot doesn't see misleading red.

**Save-Time URL Probe Pre-Check**
Admin saves on `/openai/config/update` and `/ollama/config/update` probe every URL in the submitted list. A newly-added unreachable URL refuses with `400 {detail, url, capability, suggestion}`. The bad URL can't reach the database. Existing-but-now-broken URLs don't block the save, because the operator may be editing an unrelated field. Those land in the registry instead. Stale Cloudflare tunnel URLs can no longer enter persisted config via the admin flow.

**Self-Healing `distribution.env` Hardlink Chain**
A `make install_hooks` target wires four pre-commit-framework hook stages: `pre-commit`, `post-checkout`, `post-merge`, `post-rewrite`. The commit hook refuses to record a chain break and names the fix. The post-* hooks silently re-link siblings to AI-UI's content when git itself rewrites the file via checkout, merge, rebase, or amend. Editors that atomic-save broke the chain invisibly. The next commit only updated one repo and drift crept in. The chain heals itself now.

**Self-Healing `release_finish`**
The Makefile target detects stale `.git/gitflow/state/*.json` when safe and drops it before driving a fresh finish. The operator who Ctrl-C'd a release attempt last week can re-run `make release_finish` today without manual surgery. Heal refuses when a real merge or rebase is in progress, the working tree is dirty, the recorded release branch is missing, or master already contains it. All three `git flow finish` invocations now pass `--no-ff --no-verify` to sidestep the fast-forward empty-commit bug and the misclassified pre-commit-hooks-skipped failure mode in git-flow-next 1.0.0.

### Fixed

**Misleading `400: 'NoneType' object is not iterable` on Knowledge Upload**
The sage.startr.cloud knowledge upload returned this TypeError when its embedding endpoint was unreachable. The cause was three stack frames downstream of the user-visible error. `generate_openai_batch_embeddings` caught every exception, logged it, and returned `None`. The caller called `embeddings.extend(None)` and crashed. The same `Exception → return None` pattern lived in the Ollama and Azure OpenAI siblings. The three batch-embedding functions now raise `EndpointUnreachable` instead of swallowing exceptions. The retrieval router lets the new exception pass through to the 503 handler instead of converting it to a generic 400. The dispatcher gets an explicit `else: raise ValueError` so unknown engines fail loud. Two pre-existing Python 3 bugs got fixed in the same pass — `raise "string"` statements that would themselves crash. try.sage.is on the same 2.3.2 image never hit this because its embedding engine is `chroma`: a different dispatcher branch with no HTTP boundary.

**Admin `verify_connection` Reports a Useful Error**
The admin "Verify connection" buttons in OpenAI and Ollama settings returned `500 "Server Connection Error"` when the URL was unreachable. The error didn't name the URL or hint at a fix. They return 503 with the structured body now. The operator sees which URL failed, what underlying error fired, and the pointer to `/admin/diagnostics`. The TTS engines get the same treatment. Connection-class failures raise `EndpointUnreachable`. HTTP-error responses keep the existing detail-extraction so the engine's own error message still surfaces.

**`/assets/loader.js` 404**
Operators upgrading from older deployments hit 404 on `/assets/loader.js` because the SPA expected the file under `/assets` but the container only mounted `/static/assets`. A second mount at `/assets` serves the same directory. Confirmed live on both sage.startr.cloud and try.sage.is before this landed.

**Ad-Tech Feature Names in Permissions-Policy Trigger Browser Console Warnings**
Most operators copy-pasted "comprehensive" Permissions-Policy headers from blog posts that included `browsing-topics`, `run-ad-auction`, `join-ad-interest-group`, `private-state-token-*`, `private-aggregation`, `attribution-reporting`, and `interest-cohort`. Browsers reject every one of these or treat them as origin-trial-only. The operator got noise in the console and no security benefit. A lean default allowlist replaces the previous fallback, which was the invalid string `"none"`. A reject list catches the ad-tech names. If any appear in the operator's value, the header falls back to the lean default. The allowed-features regex now covers `display-capture`, `encrypted-media`, `publickey-credentials-get`, and `screen-wake-lock` so modern operators don't trip the validator.

**CapRover Deploy History Shows `n/a` Instead of Git Hash**
Multi-arch images previously shipped without OCI provenance labels. CapRover's deploy-history column couldn't compute a commit hash. A DRY `OCI_LABELS` Makefile variable lands `org.opencontainers.image.revision/source/version/created/title/licenses` on every `it_build`, `it_build_no_cache`, `it_build_amd64`, and `build_multi_arch` invocation. The hash populates on the next release.

**git-flow-next 1.0.0 Failures During `release_finish`**
Three failure modes the operator hit while shipping 2.3.2 are now closed. First, git-flow-next preserved per-step state at `.git/gitflow/state/*.json` after an aborted release. The next finish errored with "a merge is already in progress" even when the working tree was clean. The new `_release_finish_heal` target drops the stale state when safe. Second, git-flow-next tried to commit a fast-forward merge as a real merge commit. `git commit` reported "nothing to commit" and the finish failed. `--no-ff` forces a real merge commit. Third, git-flow-next's internal merge commit triggered the pre-commit framework with no staged files. Hooks reported `Skipped` for every entry. git-flow-next misread `Skipped` as a commit failure. `--no-verify` bypasses hooks for git-flow's plumbing commits while keeping them in force for every operator commit.

### Changed

**`start.sh` Hardening**
The boot script now runs under `set -euo pipefail` and emits CapRover-readable failure messages when something refuses to work. The format is "WHAT HAPPENED / WHAT THIS BREAKS / HOW TO FIX" per deployment shape. A pre-flight check tests data directory writability and names the running uid if the test fails. Key generation validates the persisted file is exactly 44 chars (32 random bytes base64-encoded with padding) before trusting it. An ephemeral-mount detector reads `/proc/mounts` and warns if `data/` is on tmpfs, overlay, overlay2, or aufs. The secret key persisted to that filesystem will regenerate on every restart, silently logging every user out.

**Connection-Class Failures Across Audio, Ollama, Pipelines**
Same treatment as the OpenAI and Ollama config endpoints. TTS (OpenAI, ElevenLabs, Azure) records each call's outcome into the registry. Pipelines filters surface failures into the registry without raising, because one bad filter shouldn't crash the whole filter chain. Every `requests.*` call in `pipelines.py` got a `timeout=10` (or `60` for the file upload site). Closes the CWE-400 bandit findings on the seven control-plane admin endpoints there.

### Security

**`record_success` Now Persists, Rate-Limited**
The Phase 2 EndpointHealth registry had a subtle bug. `record_success` updated the in-memory record but never called `_save_snapshot()`. After a container restart, a long-healthy endpoint resurrected as whatever its last failure state was. The fix rate-limits writes to one per 30 seconds via a single class-level timestamp the existing RLock serializes. The success path no longer hits disk on every healthy call, but the registry reflects current reality across restarts. Failure paths still flush synchronously and don't reset the success timer, so a failure burst can't starve the periodic flush.

**Diagnostics Response Carries No Secret Material**
The new `/api/v1/diagnostics/health` endpoint is built only from `endpoint_health.snapshot()`, which holds URLs but never key material. The secret-key check returns length, presence boolean, and filesystem type. Never the key value itself. A top-of-file invariant comment and a CI grep assertion enforce it. The POST `/api/v1/diagnostics/probe` endpoint rejects any URL not in the active config set, closing the SSRF surface that an admin-gated arbitrary-URL prober would otherwise expose.

**Pre-Commit Bandit Catches `requests` Without Timeout**
The bandit B113 hook caught seven `requests.*` calls in `pipelines.py` shipping with no timeout. A CWE-400 unbounded-wait vector. All seven now carry an explicit `timeout=10` or `timeout=60`. The hook runs on every commit going forward.

---

## [2.3.2] — 2026-05-29

### Added

**UpdateInfoToast Carries Auto-Update Guidance**
When the in-app update toast fires it now tells the user how to apply the update for their install path — `ai-ui update --tag X.Y.Z` for brew, a redeploy click for CapRover, `docker pull` + `docker run` for self-host. Translations land for the new strings across the existing locale set, so the toast speaks the user's language instead of falling back to English.

### Fixed

**OAuth Provider Config Takes Effect Without a Restart**
Saving an OAuth client_id / client_secret in the admin panel required a container restart before the change was honored. Two bugs cooperated. `SessionMiddleware` only mounted at boot when `OAUTH_PROVIDERS` was non-empty, so a provider added later via the UI hit the callback with no session middleware and a generic 500. And `PersistentConfig` treated blank stored values as set, so an empty DB row blocked the env-var fallback. `SessionMiddleware` is now unconditional — the cookie cost is invisible on installs that never enable OAuth — blank stored values fall back to env defaults, and `OAuthManager.reload()` rebuilds the authlib registry from the live `OAUTH_PROVIDERS` dict so admins can add or swap providers from the UI without bouncing the container.

**OAuth Merge and Signup Toggles Visible in Admin Panel**
The OAuth Settings form gated `Merge Accounts by Email` and `Enable New Sign Ups` behind a `compact && adminConfig` check that only the setup wizard satisfied. The admin panel rendered the same component without `compact={true}` and the toggles vanished. Operators rediscovered them by re-running the wizard. The gate is now `{#if adminConfig}` so both surfaces render the same controls.

### Changed

**`OAUTH_MERGE_ACCOUNTS_BY_EMAIL` Defaults to `True` on Fresh Installs**
The default flipped from `False` to `True`. Workshop deployments and self-host single-admins almost always want OAuth identities auto-linked to the matching local account — the old default left first-time OAuth sign-ins blocked with an opaque 403. Existing installs keep their saved value through `PersistentConfig`; only fresh installs see the new default. The per-provider link-mode work tracked in the OAuth UX & Identity Linking TODO will eventually deprecate this global toggle in favor of `silent_merge_by_email` / `verify_via_magic_link` / `disabled` per provider.

**`WEBUI_SECRET_KEY` Now Persists Across Container Recreates**
The auto-generated secret key moved from `.webui_secret_key` in the container's working directory to `data/.webui_secret_key` in the persistent data volume. Previously a fresh container generated a new secret key and invalidated every existing JWT — sessions silently logged out after every `docker rm` + `docker run`. The key now survives container recreates as long as the data volume sticks around. Operators who want to inject their own key can still pass `WEBUI_SECRET_KEY` via run-time env, and the Makefile's `it_run` / `dev_run` recipes now forward it as `-e WEBUI_SECRET_KEY=<value>` automatically when set.

**Cross-Platform Build Notifications**
The Makefile's build-complete notification used `afplay` (macOS-only) which exited non-zero on Linux and Windows and broke build chains there. A portable `NOTIFY_DONE` macro wraps `terminal-notifier` on macOS, `notify-send` on Linux, and falls back to a no-op elsewhere. The build no longer fails when the notifier is missing.

**Makefile DX Pass**
`COMMON_RUN_ARGS` is factored out of three `docker run` recipes so a flag change lands in one place instead of three. `LOCAL_PORT` is now its own variable. `SAGE_HOSTS` guards block the try.sage targets when the host file is misconfigured, replacing a silent no-op with a loud error. The `|| true` that swallowed lint failures is removed — lint now stops the build instead of marching on with a stale image. New `_pin_server_tag` helper rewrites `SERVER_TAG` in the canonical `distribution.env` via a `cat tmp > target` pattern that preserves the hardlink chain inode across all three sibling repos.

**Auto-Pin `SERVER_TAG` in `distribution.env` After GHCR Push**
`release_and_push_GHCR` and `hotfix_and_push_GHCR` now write the released `IMAGE_TAG` into the canonical `distribution.env` once the multi-arch image is confirmed on GHCR, via the inode-preserving `_pin_server_tag` helper. The pin propagates instantly to the homebrew-apps tap and the Sage.Education docs sibling repos through the hardlink chain. Operators no longer run a separate pin step after release — `distribution.env` can only describe a `SERVER_TAG` that exists on GHCR.

### Security

**`.dockerignore` Adopts the Hidden-Artifact Allowlist Pattern**
The build context now denies all dotfiles and dotfolders by default (`.*` wildcard) and explicitly re-includes only the artifacts the image actually needs. Mirrors the repo-wide allowlist already in `.gitignore` and the contributor rule in `CONVENTION.instructions.md`. Closes the silent-leak path where a new `.env.local`, `.secrets/`, or `.aws/` at the repo root could ride into the image without anyone noticing.

---

## [2.3.1] — 2026-05-18

### Added

**Shared `distribution.env` Contract Across Three Repos**
Sage.is AI-UI, the homebrew-apps tap, and the Sage.Education docs now read canonical distribution facts — image, server tag, volume name, install command, CLI version — from a single hardlinked `distribution.env`. Edit once, three repos see it. The first Jidoka (自働化) primitive: drift across the three repos is mechanically impossible instead of a memory tax. Each repo's Makefile runs `distribution_verify` as a release gate; `distribution_sync` re-establishes the hardlink chain on a fresh clone.

**Automated Wizard Smoke (`scripts/wizard-smoke.sh`)**
End-to-end tester drives the AI Engine setup wizard via API on a clean container — signup → install trigger → embedding model download → import smoke → file upload → add-to-knowledge-base. Replaces the manual browser dance. Wired into `make wizard_smoke`. The smoke also doubles as the harness for the 2.4 bundle work.

**Convention: `test@example.com` / `zaq12wsx` is the Sage.is Automated Smoke User**
Canonical fixture for `wizard-smoke`, Selenium, ZAP DAST proxy runs, and any future automated harness. Documented in `CONVENTION.instructions.md`. Production deployments never create this user.

### Fixed

**Try.sage `/llm-status` Honors `ENABLE_TRY_SAGE=false`**
The admin-only `/api/v1/sage/runtime/llm-status` endpoint returns 404 when the trial-mode flag is off. The router-level gate ran in the wrong dependency order — auth fired before the env check, so the route leaked through with a 403 instead of disappearing. Same fix applied to `/extend` and `/reset`. The gate now sits ahead of the auth dependency for every trial-mode admin handler. Documented as a contract in `CONVENTION.instructions.md`.

**Unregistered `/api/*` Paths Return JSON 404**
Curl-driven smoke tests see proper 404s for missing backend routes. The SvelteKit static catch-all was serving `index.html` for any unmatched path, including `/api/*`, which masked router-registration bugs and broke automated checks. The SPA fall-through skips `/api/*` and returns a JSON 404 instead. Frontend routing for non-api paths is unchanged.

**ML Wizard No Longer Shadows System bcrypt and Breaks Login** *(transitional fix)*
The ML wizard installs framework packages — `bcrypt`, `uvicorn`, `click`, `anyio`, `pydantic` — into the data volume as transitive dependencies of `sentence-transformers`. Until now those packages loaded ahead of the system versions, so a freshly installed `bcrypt 5.0.0` shadowed the system `bcrypt 4.3.0` and broke password verification. Three changes restore the correct precedence: the wizard appends ml_packages to `sys.path` instead of inserting at the front (`app/backend/sage_is_ai/routers/retrieval.py`); the container loads ml_packages via `sitecustomize.py` after `site-packages` instead of via `PYTHONPATH` ahead of it (`Dockerfile`, `app/backend/start.sh`); and the install itself moves off raw `pip` onto `uv` driven by a hashed lockfile so the resolver cannot deliver a self-inconsistent set at wizard time.

**ML Wizard Switches to `uv` + Hashed Lockfile** *(transitional fix)*
The wizard previously ran two `pip install --target` passes — one for `torch`, one for `requirements-ml.txt` — and pip's silent `--target` collision left a stale `torch 2.1.2` next to a fresh `transformers 4.57.6` and `numpy 2.4.5`. The combination threw on import (`AttributeError: torch.utils._pytree has no register_pytree_node` and a NumPy 1.x/2.x ABI break). The fix swaps `pip` for `uv` (pinned at base-image build) driven by a hashed `requirements-ml.lock` generated once at edit time. `uv`'s resolver refuses self-inconsistent closures, so the failure mode moves from user wizard runs back to dev-host commits, where it belongs. torch comes from the PyTorch CPU index — no `nvidia-*` wheel chain dragged along.

**Base Image Pins `tokenizers`, `huggingface-hub`, `numpy` Inside transformers' Range**
The system site-packages picks up `tokenizers`, `huggingface-hub`, and `numpy` transitively from `chromadb` and `langchain-community`. Since `sitecustomize.py` keeps system ahead of ml_packages on `sys.path` (protecting bcrypt and friends), the system versions are the ones `transformers 4.57.6` imports at runtime. Pinning them to `<=0.23.0`, `<1.0`, and `<2` keeps the import-time version checks satisfied. Removable once the 2.4 bundle owns the full ML stack.

**This fix is transitional.** The structural fix is a signed per-arch × per-accel tarball bundle published on GitHub Releases, pulled into the container at wizard-activation time and verified against SHA256s declared in `distribution.env`. That work ships in **2.4** under the kaizen (改善) banner — and reuses the same `requirements-ml.lock` as its build input. Until then, ml_packages remains a runtime install, just a well-behaved one.

### Security

**Bump `langchain` to 0.3.30** (CVE-2026-45134 — HIGH)
LangSmith SDK public prompt pull deserialized untrusted manifests without a trust boundary warning. Fixed upstream in 0.3.30.

**Bump `python-multipart` to 0.0.27** (CVE-2026-42561 — HIGH)
Streaming parser issue pre-0.0.27. Bumped past the affected range.

### Changed

**Makefile: `try_sage_stop` Dropped, `try_sage_reset` Cleans Up Inline**
The standalone `try_sage_stop` target ran `docker rm` against a hardcoded container name that didn't match the brew CLI's name. Removed. `try_sage_reset` drops any stale trial container itself before rebuilding. Brew users continue with `ai-ui stop`.

**Makefile Reads `distribution.env` Defaults**
`VOLUME_DATA` and `IMAGE_TAG` defaults come from `distribution.env` when present. Explicit `make VAR=value` overrides still win.

**CUDA Path Temporarily Off in the Wizard** *(deferred to 2.4)*
The `USE_CUDA_DOCKER=true` branch is removed from `retrieval.py` for 2.3.1. The wizard installs CPU-only torch from the locked manifest regardless of the env flag. CUDA returns in **2.4** as one cell of the per-arch × per-accel bundle matrix, where it can be tested as a first-class artifact rather than an env-flag escape hatch. Users running CUDA today should hold on `:2.3.0` or watch the 2.4 release notes for the bundle URL.

### Docs

**Env-Gate Dependency-Order Contract**
`CONVENTION.instructions.md` documents the FastAPI ordering rule: env-gate `Depends()` must precede auth `Depends()` so a disabled feature looks like 404, not 403. Right and wrong patterns shown side by side. Reference: the `/llm-status` fix above.

---

## [2.3.0] — 2026-05-01

### Added

**ChromaDB Embedding Engine**
A ChromaDB-backed embedding engine joins the retrieval options. Pick it from Admin > Settings > Documents. The ONNX bundle persists to `/app/backend/data` so restarts skip the re-download.

**Try.sage Welcome Page**
Trial sessions open on a dedicated landing page. The page introduces the workshop, points to the persona picker, and sets expectations for the 24-hour reset cycle.

### Changed

**Mermaid Diagrams Render Bigger in Chat**
Mind maps, flowcharts, and sequence diagrams open at a readable size by default. The chat passes a `40vh` minimum height through to the SVG viewport. Pan, zoom, reset, and download still work.

**Sage Strawberry Knows Mind Maps**
The try.sage onboarding agent now answers mind-map requests with a fenced mermaid `mindmap` block. Other diagram requests get the matching grammar — `flowchart`, `sequenceDiagram`, `stateDiagram`. The agent nudges trial users toward live workshops and the Sage.is team when they want to go deeper.

**Try.sage Trial Polish**
Persona tutorials end with a try.sage.is reference so participants know where they are. Persona descriptions and trial-mode UI settings tighten up. Tutorial flow and persona switcher behave better on first run. Trial tool-server registration is more reliable across resets.

**Conversation Map Labels**
Node labels in the conversation map strip raw markdown markup before rendering. Branch names read cleanly.

**File Upload Disabled Message**
"Model(s) do not support file upload" rewritten to "File upload turned off" across all locales. Shorter, plainer.

**OAuth Callback Handling**
Sign-in callbacks handle edge cases more gracefully. Affects Google and GitHub OAuth flows added in 2.1.0.

**SVG and Icon Handling**
Internal refactor of SVG and icon imports. Lays groundwork for the diagram-rendering changes above. No user-facing change on its own.

### Fixed

**Documentation Typos**
Corrected typos and improved descriptions across documentation files.

---

## [2.2.0] — 2026-04-29

### Added

**Persona Magic Links**
Magic links now carry a persona. An operator hands out one URL before a workshop. The link drops the participant into a pre-configured account with the right tutorial, system prompt, and tool servers already wired up. No signup. No configuration step. The link works.

**Embedded Tutorials**
Tutorials ship inside the persona. Astropi AI Tutor, Sage Startr Style, and Sage Strawberry each open with their own walkthrough on first load. The tutorial knows what tools the persona has and what the participant should try first.

**Persona Switcher**
Participants switch between personas mid-session without losing the link. Useful for facilitators demoing more than one workshop track from the same browser.

**Stable Persona URLs Across Resets**
Account resets wipe chats and files but leave the persona link intact. Operators print URLs ahead of time and reuse them across sessions. Link TTL is 7 days by default and configurable via `TRY_SAGE_PERSONA_LINK_TTL_DAYS`.

**Trial Tool Server Registration**
Personas register their own tool servers on activation. Each tutorial gets the tools it expects without admin intervention.

---

## [2.1.0] — 2026-03-28

### Added

**OAuth Admin UI (Beta)**
Admins configure Google and GitHub OAuth from the setup wizard or Admin > Settings > Auth. Each provider section expands to show setup instructions, a direct link to the provider's developer console, and the correct callback URL for the deployment. Credentials save to the database and activate immediately — no restart required.

**Email Magic Link Login (Beta)**
Existing users sign in by clicking a link sent to their email. No password needed. Admin enables it and configures SMTP in Admin > Settings > Auth. A "Sign in with Email Link" button appears on the login page alongside any OAuth buttons.

**"Forgetting your password(s)?" hint**
The login page shows a help message below the password field when no OAuth providers are configured. A tooltip suggests the admin enable Google, GitHub, or LDAP sign-in.

**Developer Onboarding**
Added DeveloperStep component and DevMissionReminderModal for onboarding developers. Enhanced WelcomeStep with Developer Mode setup instructions. Implemented reminders for developers who signed up for the mission but remain in production mode.

**DEV_MODE Environment Variable**
Added DEV_MODE environment variable to toggle development features.

### Changed

**Setup Wizard**
Authentication is now the first optional step. The welcome screen offers four checkboxes: Authentication (Beta), Model Connections, Users, and Features. Admins choose what to configure; unchecked steps are skipped.

**CompleteStep Component**
Updated to reflect model download status and added polling for downloads.

**CI/CD Workflow**
Enhanced with fresh DB smoke test and detailed release process instructions.

**Feature Checkbox Handling**
Streamlined checkbox input handling for community sharing, message rating, notes, spaces, and webhooks.

**Authentication UI**
Updated button styles and translation text in magic link section.

**Makefile**
Enhanced multi-architecture build process and added GHCR login target. Added newline echo in it_clean target for better output readability.

**Backend Scripts**
Refactored backend startup script and enhanced model management.

**Component Layouts**
Updated various components to improve layout and user experience.

### Fixed

**Slideshow Image Paths**
Updated image paths to use static assets directory.

**Changelog Release Dates**
Corrected release dates for versions 2.0.0 and 1.0.0.

**Environment Handling**
Set default package version to "0.0.0" if not found. Updated latest release version retrieval from GitHub API.

**Docker Environment**
Suppressed onnxruntime warnings in Docker environments.

**Code Cleanup**
Removed unused DEV_MODE toggle and related setup code from Dockerfile. Removed unused downloadLiteLLMConfig API endpoint. Simplified .dockerignore and .gitignore by removing unnecessary exclusions. Removed unused downloadLiteLLMConfig import from Database.

**Translations**
Updated translations to replace "wherever you are" with "with Sage.is AI-UI" across multiple languages.

---

## [2.0.0] — 2026-03

### Added

**Spaces**
Multi-user rooms where people and AI agents talk in real time. @mention an agent to pull it into the conversation. If the agent's last message ended with a question, it responds to follow-ups without another @mention. Threads, reactions, and typing indicators work the way team chat should. Thinking indicators rotate through short status phrases while agents reason, so no one stares at static dots for ninety seconds.

**Space Member Management**
Admins and facilitators add or remove users from a Space through the three-dot menu. Access control is per-space, stored in `access_control.read.user_ids`. The existing `updateSpaceById` API already accepts these payloads. No backend changes needed.

**Messaging Bridges**
Users send messages to the AI from [WhatsApp](https://waha.devlike.pro/) (WAHA), [Telegram](https://core.telegram.org/bots/api) (Bot API), [Signal](https://github.com/bbernhard/signal-cli-rest-api) (signal-cli-rest-api), or Email (IMAP/SMTP). No new account. No new app. No new login. The same model, reachable from wherever the person already is. Admins configure each bridge from the admin panel. Credentials stay on the server. New adapters require no frontend changes.

**PDF Ingestion Modes**
Three modes for how PDFs enter the knowledge base: fast text extraction, structured page parsing, and AI-assisted parsing. A scanned court filing warrants different handling than a plain-text report. The mode is configurable per-deployment and per-request.

**AI Document Parsing**
Documents that resist clean extraction — mixed-layout PDFs, scanned images embedded in pages — pass through a model for structured interpretation before indexing. Output format is configurable.

**Knowledge Base**
Multi-collection document storage with per-collection embedding configuration. Documents link to specific knowledge bases and chat skills. Models draw on the right context for the right task.

**Home Dashboard**
Recent and pinned conversations appear at first load. Pinned conversations persist across sessions.

**Sidebar Search**
Global conversation search lives in the sidebar. The cursor enters the search field on open. One keystroke to search.

**Collapsible Sidebar Folders**
Folder and date-group expansion state is user-controlled. Fold and unfold controls are visible without hovering.

**[Setup Wizard](https://sage.is/docs/admin/setup-wizard)**
First-run configuration walks through connection setup ([Ollama](https://ollama.com/), OpenAI-compatible endpoints) with live verification. Admins see whether their API key or local model server is reachable before finishing setup.

**Chat Sharing**
Users share conversations with other users or groups. Shared chats appear under "Shared with me" and "Shared by me" in the sidebar.

**[Magic Links](https://sage.is/docs/admin/magic-links)**
Passwordless authentication via one-time links. Admins configure allowed email domains. Useful where managing passwords creates more friction than it removes.

**Note Editor**
Persistent notes with title management. Notes live alongside chats in the sidebar.

**[Security Scanning](https://sage.is/docs/dev/security-scanning)**
Provider-agnostic CI/CD scanning via Makefile targets. `make scan` runs [gitleaks](https://github.com/gitleaks/gitleaks) (secrets), [semgrep](https://semgrep.dev/) (JS/TS/Svelte SAST), [bandit](https://bandit.readthedocs.io/) (Python SAST), and [trivy](https://trivy.dev/) (dependency vulnerabilities). `make install_dev` installs all tools via [Homebrew](https://brew.sh/). Pre-commit hooks catch issues before they reach the repo. Runs on Linux, macOS, and Windows (WSL). No GitHub Actions. No vendor lock-in.

**DB Upgrade Smoke Test**
`make test_db_upgrade` boots the app against an archived database snapshot to verify that [Peewee](http://docs.peewee-orm.com/) and [Alembic](https://alembic.sqlalchemy.org/) migrations apply cleanly. The original snapshot is never mutated.

### Changed

**Package Identity: `open_webui` to `sage_is_ai`**
The backend Python package is renamed. Every import path, log line, environment variable prefix, and deployment artifact carries the project's own name. A fork that has diverged this far in architecture and purpose should say so in its namespace.

**"Channel" to "Space"**
The UI, API routes, and socket events now say "Space" instead of "Channel." The database schema still uses the old column names. Migration planned for v2.1.0.

**Dependency Security Upgrades**
Updated [authlib](https://authlib.org/), unstructured, [nltk](https://www.nltk.org/), python-multipart, [PyJWT](https://pyjwt.readthedocs.io/), [pillow](https://pillow.readthedocs.io/), [black](https://black.readthedocs.io/), [aiohttp](https://docs.aiohttp.org/), [langchain-community](https://python.langchain.com/), and [jspdf](https://rawgit.com/MrRio/jsPDF/master/docs/index.html) to patch known CVEs at CRITICAL and HIGH severity.

**Agent Thinking Timeout**
Thinking indicator timeout extended from 30 seconds to 2 minutes. Slower models no longer have their status silently cleared before they finish responding.

### Fixed

**Rich Text Editor State**
The rich text editor clears correctly when the prompt is set to an empty string. Switching Spaces no longer leaves stale content in the input.

**Space Participant Loading**
Participant loading for @mention autocomplete fails gracefully with a console warning instead of breaking the Space.

---

## [1.1.1] — 2025

### Added

**Branding Configuration**
Self-hosted deployments configure name, colors, logo, and visual identity through the admin panel. No fork required. No custom build. The configuration persists in the database and survives container rebuilds.

**Static File Injection**
The `SKIP_STATIC_CLEANUP` environment variable preserves custom static assets (favicons, fonts, injected CSS) across container rebuilds. The `STATIC_SRC` Makefile variable maps host directories into the container at build time.

**Theme Configuration**
The theme layer exposes [CSS custom properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties) at the root level. Color, spacing, and typographic decisions propagate from a single configuration point. Change one token, see it everywhere.

### Changed

**[Startr.Style](https://startr.style/) Migration**
Hardcoded color values removed from components across the frontend. Components reference CSS custom properties instead of literal values. A self-hoster who sets a primary color once does not need to hunt through component files to find where it was hardcoded.

**Makefile: Image Names from Git Remote**
Docker image names derive from the git remote URL. Deployment scripts stay consistent across forks and organizations without manual editing. `make it_build` builds the right image for whichever repo it runs from.

### Fixed

**Auth Flow: Spurious 403 Errors**
The auth page no longer triggers 403 errors during session validation. The errors were noise — they appeared in logs without indicating a real failure.

---

## [1.0.0] — 2025-04

### Added

**Granular Voice Permissions**
Admins enable or disable speech-to-text, text-to-speech, and tool-call voice features separately for each user group. An institution that allows transcription but not synthesis controls those independently.

**VAD Toggle for Whisper STT**
Voice Activity Detection for the built-in [Whisper](https://github.com/openai/whisper) engine can be disabled per deployment. Useful where VAD filtering introduces unwanted silence trimming in structured audio.

**Copy Formatted Responses**
Users enable copy-with-formatting in Settings > Interface. AI responses paste into documents with Markdown structure intact — headers, lists, code blocks, links. Plain-text copy remains the default.

### Fixed

**LDAP Authentication**
Resolved an attribute parsing failure that prevented login when optional LDAP attributes were absent or formatted outside expected parameters.

**Image Generation in Temporary Chats**
Visual outputs generate correctly in temporary sessions. Chat mode no longer restricts which capabilities are available.

---

*[Sage.is AI](https://sage.is) is built by [Startr LLC](https://startr.com). Licensed under [AGPL-3](https://www.gnu.org/licenses/agpl-3.0.html). Source at [github.com/Sage-is/AI-UI](https://github.com/Sage-is/AI-UI).*
