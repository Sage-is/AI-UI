# Roadmap

This file tracks active work only.

> Historical snapshots and completed bulk moved to `docs/completed-todos.md` and `docs/archive/` on 2026-04-09.
>
> Done cards move to `docs/completed-todos.md`; open cards untouched for a quarter move to `docs/board-dormant.md` (sweep of 2026-11-03). A card cited by title and missing here is in one of the two.
>
> **Convention** — Sections below map to kanban columns. Inline source-code tags use the same vocabulary so items stay cross-referenced between this file and the codebase. `KANBAN.canvas` auto-generates from this file and inline tags — do not hand-edit it.
>
> | Column      | Markdown section  | Inline tag  |
> |-------------|-------------------|-------------|
> | Backlog     | `## Backlog`      |             |
> | TODO        | `## TODO`         | `# TODO:`   |
> | In Progress | `## In Progress`  | `# FIXME:`  |
> | Bugs        | `## Bugs`         | `# BUG:`    |
> | Done        | `- [x]` items / `## Done` | —   |
>
> `# DEPRECATED:` tags should be tracked as TODO items for removal at the stated version.

---

## In Progress

_Items currently in progress. Move items here and or use tag source with `# FIXME:` when work begins._

- [ ] **Bugs riding in 3.3.0: fourteen small fixes through one re-gate** #bug (picked 2026-11-05 with Alexander; plan `~/.claude/plans/tingly-exploring-peach.md`)
  - [x] [WE] Chat path, one fixture each: `data: [DONE]` ends the stream; `nonlocal model_id`; the two-message title; the dead `features.web_search` branch; a `◁think▷` fixture case
  - [x] [WE] Sprigs and routers: pruning Tika or Docling resets the engine; an evicted Sprig says so; three `F811` handler names; knowledge answers a real 503, diagnostics shows `vector_db_ready`
  - [x] [WE] Svelte: code fences readable in the composer; unique `SensitiveInput` ids; the models panel stays mounted on save; one `loadModels` helper for the 36 token-first `getModels` calls
  - [x] [WE] Re-pinned `wolfi-base` (scan: 0 HIGH, 0 CRITICAL); `gauntlet_full`, `upgrade_gate` 20/0, `rootstock_test` 90 OK green 2026-11-05; logs `~/.local/share/ai-ui/gates-3.3.0/picks-*`
  - [x] [WE] Found by `upgrade_gate`: its and `sprig-lifecycle.sh`'s self-heal matched only "session expired"; a busy database answers 503 "try again in a moment" since 2026-11-02; both retry it now
  - [ ] [MANUALLY] Commit with 3.3.0: run sheet `Plans/ai-ui-3.3.0-release`, its own group

- [ ] **`.env` takes a real key or a `bw:` stub, and an env-only LLM connection keeps the key out of the DB** #security (2026-11-04)
  - [x] [MANUALLY] OpenRouter dev key in the vault: `openrouter-aiui-dev`
  - [x] [WE] Makefile: run targets pass secrets by name (`-e NAME`), never by value, and run under `sage-secret` when `.env` holds a `bw:` stub (`VAULT_REFS`, `VAULT`; `PARSE_BY_SHELL` keeps a quoted `WEBUI_SECRET_KEY` the same key); before, `make try_sage_start` printed `TRY_SAGE_LLM_API_KEY` (proven against HEAD), and `dev`/`it_run` print `WEBUI_SECRET_KEY` when set
  - [x] [WE] `restore_backup_start.sh`: values already in the environment win over `/app/.env`, as python-dotenv does
  - [x] [WE] `SAGE_LLM_API_URL` / `_KEY` / `_MODELS`: the try-sage memory-only connection, outside trial mode; `test_hidden_connections` (6) joins `image_unit_tests`
  - [x] [WE] Proven 2026-11-04: a quoted stub resolved through `sage-secret`, the container kept it over `/app/.env`, the connection registered, and OpenRouter `/key` answered 200 with a credit limit
  - [x] [MANUALLY] Guard autoenv and add the `SAGE_LLM_*` lines to `.env`: done by 2026-11-05 (`~/.bash_profile:24` skips autoenv when `$CLAUDECODE` is set; `.env` holds both lines)
  - [x] [WE] Fix found by `runtime_tests` 2026-11-05: the bare `export` expanded `VAULT` for every recipe, so with a stub in `.env` no target built where `sage-secret` is missing; `unexport VAULT PARSE_BY_SHELL VAULT_REFS`
  - [ ] [MANUALLY] Commit with 3.3.0: run sheet `Plans/ai-ui-3.3.0-release`, step 1.3 (the Makefile half rides in 1.8)

- [ ] **Left over from the Trellis-first pause** (moved out of the pause card, 2026-11-02; that card is in `docs/completed-todos.md`)
  - [ ] [MANUALLY] The tap's step-2 commit and push (the ai-ui formula follows AI-UI releases); this board's commit
  - [ ] Parked AI-UI changes Trellis may need later: forward the chatting user's identity to tool servers (`execute_tool_server` sends only the bearer today); AI-UI as identity provider (own card since 2026-10-15, under OAuth UX & Identity Linking)

- [ ] **Rootstock: a clean-room Django core at about a seventh of today's code, strangled in surface by surface** #rootstock (Alexander, 2026-10-23; rewrite approved 2026-10-24; on `develop`, forward only): plan `~/.claude/plans/silverbullet/rootstock-platypus.md`; F0 (3.3.0) fixes 18 security bugs where they live
  - Held 2026-11-03 (Alexander): F1 starts once 3.3.0 ships, one phase per release; the Workshop apps tab stays in F5; dropped 2026-11-12, web Tinker replaces it
  - [ ] [MANUALLY] Release and deploy 3.3.0 by run sheet `Plans/ai-ui-3.3.0-release` (everything in the tree ships, decided 2026-11-05; gates green 2026-11-05); then the steps below
    - [ ] [MANUALLY] Tell both box owners (the note says the hole "is closed")
    - [ ] [MANUALLY] Rotate `WEBUI_SECRET_KEY` and `PRIVACY_KEY` on both apps and the try.sage.is admin password (dry run clean 2026-11-06); the backup remote's B2 key moved to Backlog card "Rotate the B2 key that 3.2.x printed into sage.startr.cloud's start log" (2026-11-06)
    - [ ] [MANUALLY] Bump the tap formula
    - Why the order: 3.2.2 still prints the remote config at start and hands the key to Sprig children, so a rotation before the deploy re-leaks the new values. Prepared 2026-10-24: `~/.local/share/ai-ui/rotation/rotate-3.3.0-secrets.sh` (dry run, then `--go`; README beside it) mints the box-owned keys into the vault and pushes them with `cr-deploy ensure`; it refuses anything below 3.3.0; the B2 key and the demo's provider keys are created by hand and put into the vault first; try.sage.is persona links die with the rotation, so the seed now applies an env-supplied persona password
  - [ ] [WE] Then `docs/rootstock/design.md`; OpenAPI capture and goldens from the 3.2.1 image; the parity runner
  - [ ] [WE] F1 (3.4.0): the seam, pass-through; the ten congestion fixes (card "Congestion" in Bugs); consistent backups; `make stream_load` with an asyncio mock provider
  - [ ] [WE] F2 (3.5.0): the model gateway, a plain ASGI app in its own process, behind an nginx inside the container; the Workshop agents page on Django; WAL with its own switch; Alexander's go or no-go
  - [ ] [WE] The gateway's byte path moves to Rust (Tinker's `core/src/llm`) only when `stream_load` shows a trigger: gateway CPU over 60% of a core, loop lag p99 over 50 ms, added first-token p95 over 50 ms, or more than 250 streams
  - [ ] [WE] Image diet (decided 2026-10-23: Django squeezed, containers everywhere): 3.2.1 is 390 MB on disk (123–126 MB to download); at F8 must ≤150 MB, target ≤110, stretch ≤75; `image_budget` ratchets down each release; levers measured in the plan (63 MB of `.pyc`, 37 MB `uv`, a doubled 21 MB zstandard, Django trimmed 49→24 MB)
    - [ ] [WE] Repo weight: 97 MB tracked against Tinker's 19, though the code is about the same size
      - [ ] [MANUALLY] Create both repos in the `Sage.is` org: the agent's Gitea token has no `write:organization`, so creating an org repo answers 403
      - [ ] [WE] Then upload the fonts and the `.xcf`, have the export-document recipe fetch the fonts by sha256, and drop all of them from git with a pointer note in `app/static/icons/`
  - [ ] [WE] Few libraries (Alexander, 2026-10-23; evidence in the plan): `test_dependencies.py` lists about 12 direct Python packages, about 30 installed by their closure (today 95), no npm package at runtime (today 1,160 build the SPA), vendored pinned files checked by sha256, hash-pinned locks with an `exclude-newer` cool-down
  - [ ] [WE] Install and onboarding: `install_smoke` times a fresh install to the first answer and counts the steps; it fails on any tour, modal or carousel before that answer
  - [x] [MANUALLY] SSO decision made 2026-11-12 (Alexander): a one-time code in today's backend, with a ratchet note; the contract hides the later move (card "Platform alignment")
  - [ ] [MANUALLY] Sitting 2 of the plan's decision queue: what tool servers receive and direct connections (before F3), Space rules (before F4), the default embedder and the Sprig questions (before F5)
  - Folds in: Workshop apps tab (dropped 2026-11-12), AI-UI as identity provider (OAuth UX), Backend Rewrite Research (superseded)
  - [x] _11 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **One way to deploy: `cr-deploy` + `make deploy`** #critical: plan Amendment 55, 2026-09-27
  - [ ] [MANUALLY] Commit AI-UI, Trellis, homebrew-apps; release `cr-deploy-v0.1.0` (fill the formula sha256) and `offload-v0.7.0`
  - [ ] [MANUALLY] Check chats and Spaces on sage.startr.cloud
  - [ ] [WE] Rollback drill on try.sage.is once it has two digest deploys; 2026-09-27 run refused the tag-deployed 3.1.0 by design, message now says how
  - [ ] [MANUALLY] The captain's CapRover version (decided 2026-10-04): read it (`cr-deploy info`, needs your login); below 1.14.2, go to exactly 1.14.2 after host-level copies of `/captain/data` and the app volumes; hold 1.15.x until a release restores its own backups. Evidence: Trellis `crm/docs/decisions/2026-10-04-pilot-hosting-options.md`
  - [x] _7 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **sage.startr.cloud SQLite over Syncthing**: replicas can sync torn; nightly `sqlite3 .backup` into the synced folder, Syncthing ignores live `webui.db`/`-wal`/`-shm`; Postgres later
  - The office Mac is a fourth Syncthing device; Backblaze (unlimited plan) backs up its copy off-site, with the nodes' nightly backups (four nights) beside it (checked 2026-10-15; `OPS-Sage/docs/storage.md`)
  - So a torn live file also reaches the Mac and Backblaze; a nightly `.backup` file would give that chain a clean copy too

- [ ] **Remove htmx; every consumer moves to startr-swap** (earmarked 2026-08-17): four admin panels still ride the 50.9 KB vendored `htmx.min.js` while the 11.9 KB in-house library carries every page-to-page swap — one engine, not two. #frontend #dx
  - Scheduled after the ISA pilot ships (Alexander, 2026-11-02): in house, one vendored dependency fewer.
  - [ ] Mechanics that ARE the migration: mark each panel wrapper `data-swap` (ids stay); htmx buttons become real links or one-button forms (startr-swap claims only `a[href]` and `form`); `hx-vals` JSON becomes hidden inputs.
  - [ ] Semantic shift to check per panel: htmx `outerHTML` replaces the wrapper element, startr-swap replaces its CHILDREN — server-set attributes on the wrapper itself won't land.
  - [ ] No fragment fixture exists (`fixtures/swap/` holds full documents only) — add one so the behavior is pinned before the panels lean on it.
  - [ ] Consumers to migrate, each with its e2e spec green after:
    - [ ] Sprigs (`sprigs.html`, `sprigs_panel.py`): Refresh `hx-get`, per-card `hx-post` wire + verb actions, all targeting `#sprigs-panel`/`outerHTML`.
    - [ ] Diagnostics (`diagnostics.html`, `diagnostics_panel.py`): per-row Re-probe `hx-post` carrying `hx-vals` JSON — needs a plain-form equivalent (hidden inputs) — plus Re-probe-all `hx-get`, `#diagnostics-panel`.
    - [ ] Branding (`branding.html`, `branding_panel.py`): save form `hx-post`, `#branding-panel`; its `data-swap-off` becomes a live swap.
    - [ ] Privacy (`privacy.html`, `privacy_panel.py`): five `hx-post` forms with `hx-target`/`hx-swap`, `#privacy-panel` (found 2026-11-02; it shipped after this card).
  - [ ] Delete the scaffolding: `vendor/htmx.min.js` plus its section in `vendor/README.md`; the four injection sites `router.py:385`, `:436`, `:490`, `:1267` (re-pointed 2026-11-02).
  - [ ] Re-word the prose that names htmx: `shell.py:210`, `sprigs_panel.py` and `branding_panel.py` docstrings, `router.py` comments `:566` and `:873`, `pages.css:274`, `color-pair.js` header — note its document-delegation pattern survives the engine change.
  - [ ] Cross-link: deleting the vendor file kills the bulk of the 9,609-error eslint card under Bugs — re-measure and update that card in the same sitting.
  - [ ] Guard rails: `startr_swap_check` still green; the panels' Cypress specs plus `make e2e` green; no third swap idiom — plain HTML first, per doctrine.
  - [x] _1 done step archived 2026-11-03 → docs/completed-todos.md._

---

## TODO

- [ ] **3.3.1: try.sage's dummy tools stop calling the box, and Artifacts preview one HTML block at a time** #bug #frontend (Alexander, 2026-11-06; seen live on try.sage.is 3.3.0): resume note `Plans/ai-ui-3.3.1`
  - [ ] [WE] Dummy tools: a tool server URL containing `dummy-tool` is kept in `TOOL_SERVER_CONNECTIONS` but never contacted: no spec fetch, no `/tool_servers/verify`, no `execute_tool_server`, no browser fetch
  - Why: the dummy router serves no `openapi.json`, so every tool-cache fill GETs it through the box's public URL, gets 404 and logs an error; no demo user ever saw the tools
  - [ ] [WE] Its three demo tools reach the chat tools menu from an in-app spec, with no HTTP; a call answers "not available in try mode"; the admin list and the user's tools menu both mark it a placeholder; correct `docs/try-sage-deployment.md`
  - [ ] [WE] Artifacts: the panel opens on the response's largest HTML block alone, a block's Preview shows that block alone, and CSS and JS blocks still attach. Why: `Artifacts.svelte` joins every HTML block into one page, and Preview selects the whole message
  - [ ] [WE] Code blocks start collapsed for everyone, the line count rising as the code streams; "Always Collapse Code Blocks" defaults on and becomes the opt-out
  - [ ] [WE] Found while mapping: the auto-open fires on every streamed token, so a panel closed mid-stream reopens; `AddServerModal.svelte` passes `(token, url)` to `getToolServerData(url)`, so a direct-server verify fetches the token
  - [ ] [WE] Specs first: two HTML blocks (largest shown, Preview picks), a collapsed block whose count rises, a `dummy-tool` URL that draws no request
  - [ ] [MANUALLY] Release 3.3.1: `make patch_release`, then section 2 of run sheet `Plans/ai-ui-3.3.0-release`, with `BUILDX_BUILDER=colima-build`
  - Later: a hint when someone types `dummy-tool` into a tool server URL field, saying it is never contacted

- [ ] **Client-side turns for one-on-one chats: the browser runs the turn, the gateway relays and always finishes the call** #rootstock #perf (Alexander, 2026-11-03): plan section "Client-side turns for one-on-one chats", beside the gateway contract
  - [x] Answered 2026-11-05 (plan section, "Answers"): 2,000 streams per box; hybrid byte path, direct for own-key, on-device and filter-off box connections; the box finishes the answer; record by setting, drafts ≤5 s old; budgets per user, held per turn
  - [x] The rest answered 2026-11-05 in three more rounds: plain chat first, a plain-JS island, settings per group, parity first, takeover by missed drafts, money budgets, receipts by source; 2,000 is a design target, not a gate
  - [x] [WE] Folded into the phase table: F3 shows cost and balance; a new "F3 switch", 3.6.x, ships client-side turns as soon as F3's check holds
  - [ ] [MANUALLY] Confirm the "as soon as possible" reading in the plan (`Plans/rootstock-platypus` in SilverBullet), or correct it with a `> …` line

- [ ] **`media-ffmpeg` Sprig ships GPLv3 binaries with no licence text or source offer** #critical #legal (found 2026-10-31): `scripts/build-sprig-media-ffmpeg.sh` keeps only `ffmpeg` and `ffprobe` from a tar that carries the licence
  - [ ] [MANUALLY] Publish a new tag: `TAG=v2` on arm64 and amd64 (the build VM), signed, through `publish-sprigs.sh`
  - [ ] [WE] Then point the CATALOG's `media-ffmpeg` at `v2` / `v2-amd64` with the published shas
  - [x] _1 done step archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Platform alignment: four contracts, web Tinker with AI-UI as its node** #federation #auth (Alexander, 2026-11-12): the charter is `docs/contracts/README.md`; nothing runs yet
  - Feasibility: yes, with the engine on Tinker's server; note `docs/notes/2026-11-12-web-tinker-feasibility.md` in Tinker's planning repo, whose board holds slices 1 to 3 and 5
  - [x] [WE] Slice 0, no code: point a Tinker client at a local AI-UI as a custom OpenAI-compatible provider (2026-11-12)
    - Gate: a streamed turn with a `render_ui` tool call completes, and the log shows it passed the privacy filter
    - Passed once `default_external` was on: `stop = tool_use` in 7.87 s, and two new `privacy_map` rows (email, phone) prove the filter ran; the dev log prints no INFO lines (Bugs card). The open `gateway` term is in `docs/federation.md`
  - [ ] [WE] Slice 4, one sign-in: interview, `docs/contracts/sign-in.md`, AI-UI's routes, then Trellis and Tinker's server as the two consumers
    - Gate: on Realtor M's box one sign-in opens AI-UI, Trellis and web Tinker; `/crm/aiui/` shows the contracts green
  - [ ] [WE] Slice 6: AI-UI forwards Tinker's node protocol at its own address
    - Gate: the desktop app's "Sage.is AI-UI account" entry opens the same library as the browser
  - [ ] [WE] `/api/version` lists the contract versions; each sibling checks them and shows the fit
  - [ ] [MANUALLY] Share the feasibility note with the Tinker team before slice 1's pull request opens

- [ ] **Tinker.Click integration: two products, one platform** #federation (Alexander, 2026-10-31; proposals until the team agrees): the decisions live in `AI--Tinker.Click/docs/notes/2026-10-31-integration-decisions.md`
  - [ ] [WE] Rootstock F2's gateway design names Tinker desktops as a client, as the plan already does
  - Sign-in for `tenkts-server` moved to the card "Platform alignment" (2026-11-12): a one-time code, no OIDC piece
  - [ ] [WE] `docs/federation.md`: Space theming decides Tinker's look on a box, with Tinker's credit in an About line

- [ ] **TodoScope alignment: what the 2026-11-02 pass left open** #dx: the header table, four list items with no checkbox, the duplicate lint card and the real-estate strays were fixed in place
  - [ ] [MANUALLY] Check the board in TodoScope; `KANBAN.canvas` was regenerated from `~/bin/TodoScope` (`python3 -m scanner.kanban <repo>`) on 2026-11-02
  - [ ] [MANUALLY] `.todoscope-exclude.csv`: add `app/backend/sage_is_ai/pages/assets/vendor` (vendored htmx)? Keep `docs` excluded whole, though it holds decision records and runbooks?
  - [x] _5 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Knowledge bases on sage.startr.cloud return nothing** #bug #critical (diagnosed 2026-10-20; fixes and the re-index wait on Alexander's go): all 13 knowledge bases with files answer queries 200 with 0 hits, and adding a file fails 400. Three faults stack
  - [ ] [WE] The French knowledge base's one file (130,090 characters) is not indexed: embedding it holds the event loop past the health check; index it once F1's uploads-off-the-loop and batched embedding land (Alexander, 2026-10-24: a product fix, no quiet-window gamble, no per-host tuning)
  - [x] [WE] Rides 3.3.0 (picked 2026-11-05): `query/collection`, `query/doc` and the knowledge add path answer the real 503; diagnostics shows a `vector_db` row
  - [ ] [WE] On Alexander's go: diagnostics flags a rooted `mock-embedding`; boot moves an instance off the mock (pulls an artifact, re-index needed); the registry prunes stale rows (a decision: the panel keeps "Previously configured" on purpose)
  - [ ] [WE] On Alexander's go, a gate: a real PDF into a knowledge base, a query, and a chat with the sources injected; none exists today
  - [ ] [WE] Also seen once in 72 h: a chat background task crashed with `'NoneType' object has no attribute 'find'` in `middleware.py`'s `response_handler`; recheck after the fixes
  - Verify with `scripts/kb-probe.py kbs` under `sage-secret run`: every knowledge base with files returns hits (12 of 13 on 2026-10-24). The admin key is in the vault as `sage-startr-cloud-admin-key` (Agents-edit)
  - [x] _9 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **langchain-core out of the base, and gzip for compression** #perf #security (planned 2026-10-15): 15 MB and ~170 ms of boot for six names; plan `~/.claude/plans/langchain-core-out-of-the-base.md`
  - 11 files import `langchain_core` (10 at module level) for `Document`, `BaseLoader`, `BaseRetriever`, `BaseDocumentCompressor`, two callback types; it drags in langsmith and 7 helpers
  - [x] [MANUALLY] Compression: gzip only, Starlette's `GZipMiddleware` (Alexander, 2026-11-03); the plan's step 7 still measures the three heaviest responses first
  - [ ] [WE] `retrieval/documents.py` + import fence; hybrid classes move to `retrieval/hybrid/`; `.trivyignore` loses CVE-2026-34070; then the gzip swap. On its own branch once today's tree is committed: the plan makes it its own minor release, and `retrieval/utils.py` and `routers/retrieval.py` carry 2026-11-02/03 fixes not yet committed

- [ ] **Mac upgrades offer the move to Colima** (Alexander, 2026-10-09) #ux
  - [ ] [MANUALLY] Ships with the next AI-UI release; the tap's formula follows through the tap's `ai_ui_formula` target and installs `cli/lib/`
  - [ ] [WE] Prove it on a spare macOS account: today's `ai-ui` on Docker Desktop, upgrade, accept the offer, same data on Colima, no second ask
  - [x] _2 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Fabric for work on the captain nodes; first job: backups** #critical: the hourly `APP-backup` cron has backed up nothing since 2025-11-28, and Trellis `/data` gets company mail next (2026-09-29)
  - [ ] [WE] Bug: `pipenv run ./backup.py` (crontab, :53 hourly) crashes on import, first `fabric` then `yaml`: 2,308 tracebacks in `backup_cron.log` (5.9 MB); no `config.yaml` either; retire the line or rebuild
  - [ ] [MANUALLY] `~/bin/cron/backup_openco2.sh` (daily 15:50, `root@openco2`, three `/root/backup_*.sh`, rsync to `OpenCo/Backups`) writes no log; check its files are still fresh
  - [ ] [MANUALLY] Install `brew install fabric` (3.2.3, the SSH library; `fabric-ai` is an unrelated AI tool) or pipenv; home: a new `ops` repo (decided 2026-10-04), then drop the dead `APP-backup` cron line
  - [ ] Owner open (Alexander 2026-10-04): not the intern, since the task needs production SSH; pick a senior
  - [ ] SSH: one dedicated key, used from the Studio only, not root where avoidable; scope it before any task runs (the cluster was compromised 2026-08-11)
  - [ ] Inventory = the rosters we have: `deploy/instances.toml` + Trellis `crm/deploy/*.yaml` (app, node); no third list; merge the two when the new client instances land
  - [ ] First task `backup`: `sqlite3 .backup` per app volume on its node (`trellis-data`, AI-UI `webui.db`), pulled to the Studio, integrity check, keep N; covers the Syncthing card's nightly backup
  - [ ] Rule: deploys stay on `cr-deploy`; a Fabric task never changes a CapRover service behind the captain's back
  - [ ] Later tasks: disk and health sweep of the 3 nodes, the OpenCo IR detection scripts, fail2ban

- [ ] **Converge the two deployed instances**: `try-sage-is` vs `sage-startr-cloud` #critical
  - Both run `ghcr.io/sage-is/ai-ui:3.1.0` on the same host (openco2), yet their runtime state differs materially. Surfaced 2026-08-15 during an infrastructure backup audit.
  - [ ] `try-sage-is` carries **5.4 GB** of sprig-installed `ml_packages` (190 packages); `sage-startr-cloud` carries none. Establish which is intended.
  - [ ] Storage shapes differ: `try-sage-is` uses a docker volume, `sage-startr-cloud` a bind mount into `/root/Sync`. Pick one.
  - [x] If both need the same wheels, evaluate a shared read-only wheelhouse volume — feasible since both run on the same node, and pays the 5.4 GB once not twice.
  - [ ] Mark `ml_packages` and `cache` as regenerable so infrastructure backups can exclude them (they are ~36% of one node's nightly backup today)

### Real-estate segment engagement — first paid deployment (opened 2026-07-30)

_The first paid real-estate deployment of AI-UI, and deliberately the beachhead for a real-estate vertical rather than a one-off. Client identities, commercial terms, dates, and the external commitment live in [.clients.md](.clients.md) — untracked by design (`.gitignore:3` denies dotfiles), so that link is dead in a fresh clone and is meant to be. **Codenames only in this file:** **Realtor M** (our peer), **School B** (the prior demo tenant whose data is still on try.sage.is), **Reviewer T** (internal reviewer). Never write a real client name into a tracked file._

**How success is measured here** — our peer's own definition, and worth adopting as the segment's: (1) their assistant and VA stop having to ask the principal things, (2) hours back in the principal's week. They explicitly rejected "deals closed" (market forces dominate; attribution is fiction) and "nothing falls through the cracks" (humans stay in the loop and humans drop things). We measure what the software determines and nothing more. Any dashboard or report we build should hold that line.

**Shape of the delivery** — configs lead, code follows: ship value as Agents, prompts, knowledge bases, and Spaces configuration first; add features only where configuration genuinely cannot reach; then package the whole arrangement as **autoconfig Sprigs** so the next agent in the segment is a graft rather than a rebuild. That last step is what makes this a beachhead instead of a consulting job.

**Chart** — the **Monday 2026-08-10, 13:00** kickoff and product tour is charted separately at [charts/friday-demo/TODO.md](charts/friday-demo/TODO.md): ten decision cards, four on the frontier, decision records under `docs/decisions/`. That chart decides which no-build work rides the pre-demo deploy; it does not reorder the migration.

#### Moving him off the shared box

- [ ] **Move Realtor M off the shared demo box onto his own AI-UI** (decided 2026-07-30): it ends tenant cleanup, uncapped shared spend, and his data beside strangers'. Since 2026-10-04 it runs on his own Mac (private Trellis board, card "Realtor M's Mac mini").
  - [x] His AI-UI is up on the box, :8080, loopback only (2026-10-20)
  - [ ] [MANUALLY] The Cloudflare Tunnel on a startr.cloud codename host behind Access (decided 2026-10-22; his domain later); then he signs in there, not on try.sage.is

#### Platform unlocks pulled forward by this engagement

All four were backlog items before 2026-07-30 and are now customer-blocking. **Sequence them; do not run them in parallel.**

Since 2026-10-24 the no-build strangler runs inside the Rootstock card; its phases set the order.

The external November commitment is signage and materials only, so it imposes **no ship-by date** and must not be used to justify parallelising these.

- [ ] **Platform unlocks, in this order**: Spaces multi-user, spend budgets, the Sprig catalog, the job queue
  - [ ] **1. Spaces multi-user** — three people (principal, assistant, VA) share one workspace from day one, and our peer's primary success metric is unreachable without it. Highest value, do first. Now under `## In Progress` → _Spaces Enhancements_; mechanics e2e-verified 2026-08-18, remaining work is agent context modes + productization.
  - [ ] **2. Spend budgets per user AND per API key** — required before a customer instance goes live with hosted models and three sharers. See the backlog item; the try.sage uncapped-Groq note there is now a live commercial exposure, not a hypothetical.
    - 2026-10-24 (Alexander): every provider on every instance has an API spend limit at the provider, so no key runs uncapped; per-user and per-key budgets in the app are still to build
  - [ ] **3. Sprig catalog de-hardcoding (marketplace M1)** — prerequisite for shipping the tooling as autoconfig Sprigs, and therefore for the segment story rather than just this customer. The blocker is the hardcoded Python `CATALOG` in `supervisor.py`.
  - [ ] **4. Job queue** — last on purpose. The demo is staged-and-labelled and November needs no software, so nothing forces real proactive nudges until the configs and features have landed. Promote it when a staged beat has to become a real one.

### Repo Hygiene & Security

- [ ] **Community-share leak + dead wiring**: fix the leak and the dead wiring the flag currently hides before `ENABLE_COMMUNITY_SHARING` goes back on for the sharing site (this winter) (Switch 1 of the 2026-08-15 poka-yoke resolution). #security #critical ([dossier](docs/board-dossiers.md))
  - [ ] Every model Share click sent the full model record — `params.system` included — as a query string to a public request bin, live since the initial commit with the flag defaulted on.
  - [ ] Scope: try.sage.is (3.0.0) and every deployed instance.
  - [ ] Full evidence in `charts/sprig-creator-program/TODO.md`.
  - [ ] [MANUALLY] Treat as an incident first: check whether the bin captured traffic and rotate anything a shared system prompt disclosed — before any code fix.
    - [ ] Check whether the bin captured traffic
  - [ ] [WE] Add a `source`/`origin` field to shared items so a bad one can be enumerated and revoked; under review as a pub/sub design (Alexander, 2026-11-03).
  - [x] _10 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **CSP-configured gate**: assert a CSP is set — an unset header and a deliberate omission look identical to the process (charted 2026-08-15 in the poka-yoke pass). #security #critical ([dossier](docs/board-dossiers.md))
  - [ ] `CONTENT_SECURITY_POLICY` is unset in `.env.example`, the `Dockerfile`, `docker-compose.yaml`, and `distribution.env`.
  - [ ] `SecurityHeadersMiddleware` (`main.py:1468`, `utils/security_headers.py::set_security_headers()`) builds headers purely from env vars.
  - [ ] `routers/diagnostics.py:602-618` already grades the absence "degraded" — the system knows and cannot stop anything.
  - [ ] Stakes rose twice this month: the marketplace renders third-party listings, and community.sage.is opens in weeks.
  - [ ] Ship a `scripts/gates/` check on the `startr-swap/check.py` `--check`/`--self-test` shape, asserting `distribution.env` sets a policy.
    - [ ] Gate on `Content-Security-Policy-Report-Only`, NOT enforcement — gating on enforcement pressures somebody into shipping an untested policy, and this app has never run one.
  - [ ] Sequence: report-only first, collect violations from a real session, then enforce.
    - [ ] Exceptions the policy must carry: `https://startr.style/style.css` in both frontends (`app/src/app.html:31`, `pages/shell.py:206`), Artifacts `srcdoc` frames, Pyodide, the WASM sprigs, every inline style.
  - [ ] **Write and ship the policy itself; omit `unsafe-eval` on purpose** (Switch 2 of the 2026-08-15 poka-yoke resolution; "not a today thing"). The gate proves a policy is set; this is the policy. #security
    - [ ] Omitting `unsafe-eval` makes `new Function(...)` throw — closes the browser half of the `execute` door with one directive.
    - [ ] Keep `'unsafe-inline'` for now: the branding panel, `pages/assets/*.js`, `sprigs/ui_dispatch.py`, and `SetupDialog.svelte` depend on inline handlers; nonce-based CSP is its own later job.
    - [ ] Acceptance test already wired: `routers/diagnostics.py` flips `csp_missing` off on a stock deploy.
    - [ ] Report-only first, per the parent.
- [ ] **HTMLToken raw-text invariant — document and gate it, do NOT "fix" the asymmetry** (Note 2 of the 2026-08-15 poka-yoke resolution): branching on `html` silently breaks five features, not three. #security #bonsai ([dossier](docs/board-dossiers.md))
  - [ ] `HTMLToken.svelte:17` computes `html = DOMPurify.sanitize(token.text)`, but the iframe / `<file>` / `<status>` / `<source_id>` branches (lines 55, 72, 87, 105, 123) test raw `token.text` on purpose.
  - [ ] DOMPurify's stock profile removes `<iframe>` with its contents (`ALLOWED_TAGS` omits it, `DEFAULT_FORBID_CONTENTS` includes it) and erases the four custom tags (no hyphen, so the custom-element regex rejects them).
  - [ ] The invariant: every raw-text branch either pins its origin or renders with bare `sandbox` (the generic branch, whose `src` is unvalidated).
    - [ ] YouTube hardcodes `youtube.com/embed/` + an 11-char id regex; file uses a same-origin admin-gated endpoint.
  - [x] One comment at line 17 stating why `html` is only for `<video>`/`<audio>`. Done 2026-11-02.
  - [ ] `scripts/gates/` check on the `startr-swap/check.py` `--check`/`--self-test` shape, keyed on the `src={iframeSrc}` binding (not a line number). ~60 lines, belongs in `gauntlet_fast`.
    - [ ] Assert the generic branch keeps bare `sandbox` and `allow-scripts`+`allow-same-origin` never co-occur.
  - [ ] Trap for the fixer: the line-82 `onload` autosizer is already broken under bare sandbox (opaque-origin `SecurityError`) — exactly the "just make the height work" bait that weakens the sandbox.
    - [ ] Coverage is zero: grep of all 46 Cypress specs for `sandbox|iframe|HTMLToken` returns nothing.
    - [ ] If the app-pane work lands first, add the line-73 origin allowlist BEFORE gating, so the gate does not freeze a `sandbox` we mean to change.
- [ ] **`sprig_publish` must verify against the committed pin before pushing** (found 2026-07-27 running the gauntlet): `make sprig_publish` pushes whatever sits in the LOCAL registry up to GHCR; nothing checks those bytes against the `binary_sha256` in the supervisor CATALOG. #security #bonsai #critical
  - [ ] Live supply-chain hole: the local registry had drifted to a divergent build of `sprig-rag-loaders:v1` (local `0a1ae588…` vs pinned `f2075370…`).
  - [ ] Publishing in that state would have overwritten the canonical artifact and broken the pin for every consumer, silently.
  - [ ] The graft path ALREADY fails closed on exactly this check (`artifact.py` refuses to extract on mismatch — it is what caught this); publish needs the same rule in the opposite direction.
  - [ ] Device: in `scripts/publish-sprigs.sh`, hash each artifact and refuse to push any whose digest does not match the catalog pin.
  - [ ] Worth doing before the Sprig marketplace makes publishing routine.

### OAuth UX & Identity Linking

- [ ] **AI-UI as the single sign-on for our other projects** #auth #federation (Alexander, 2026-10-15; plan after the Brokerage H demo): one AI-UI login opens Trellis, the Tinker.Click library server and later projects, so no project keeps its own user list
  - Decided 2026-11-12 (card "Platform alignment", charter `docs/contracts/README.md`): a one-time code, then the sibling asks AI-UI server to server; no OIDC provider
  - Why siblings hold no key: AI-UI signs sessions with HS256 and `WEBUI_SECRET_KEY` (`utils/auth.py:38`), so any project that verifies them with that key can also mint a session for any user, admin included
  - [ ] Today AI-UI signs people in only as a client: OAuth/OIDC providers (`utils/oauth.py`), LDAP, and the trusted e-mail header (`WEBUI_AUTH_TRUSTED_EMAIL_HEADER`)
  - [ ] Consumers: Trellis (its card "AI-UI is the identity provider", decided 2026-09-17; personas on try.sage.is, amendment 44), the Tinker.Click library server (upstream; a `sign-in` consumer), community.sage.is
  - [ ] Ties to the federation plan's "identity across boxes" flow, and its open question: how a box proves who it is

### Release Wrap-Up

- [ ] **Release pipeline: what the tag-build card left open** — moved out of the closed 3.2.0 card (now in `docs/completed-todos.md`) on 2026-11-02, so its open work shows on the board
  - [ ] **The 2.3.0 driver recurred verbatim in 3.1.0 (2026-08-10)**: second occurrence of a known, carded failure mode. #critical
    - [ ] 2.3.0: buildx OOMed mid-push — tag on origin with no GHCR image.
    - [ ] 3.1.0: `release_finish` pushed tag `v3.1.0`, then the build failed — tag published, no matching GHCR image, the exact state this card was opened for.
    - [ ] Recovery was hand-driven: `it_build_multi_arch_push_GHCR`, then `verify_ghcr_manifest`, then `_pin_server_tag`.
  - [ ] **`wizard_smoke` cold-cache false-fail (2.3.2, 2026-05-29)**: 15-min `INSTALL_TIMEOUT_SEC` too short for ~5 GB wheels + ~2 GB embedding model — evaluate, any removes the failure at the root:
    - [ ] Smoke false-failed on residential bandwidth while uv downloaded and `models/status` showed `error: null`.
    - [ ] `SKIP_SMOKE=1` is NOT poka-yoke; until a root fix ships, a cold-cache false-fail blocks the release — the gate doing its job.
    - [ ] Bake uv wheel cache + embedding model into the smoke image at build time (image grows ~5-7 GB; smoke turns deterministic, runs in minutes).
    - [ ] Move smoke to the staging CapRover app once it exists (datacenter bandwidth; ties into the 2.3.3 staging-smoke design).
    - [ ] Make smoke resumable across container restarts.
  - [ ] **Both ratchets are unrunnable on a fresh clone (2026-08-12)** #critical: `cognitive_complexity` and `chat_path_structure` hard-fail "no baseline" on every clone and CI runner, and `make lint` fails with them.
    - [ ] `.gitignore:46` excludes `/scripts/gates/*/baseline.json` and none was ever committed.
    - [ ] Baselines stay out of git (Alexander, 2026-08-12); `chat_path_structure_teeth` stays in `gauntlet_fast`.
    - [ ] Remaining: either track the baselines or drop the ratchets from every rollup — a fresh clone still starts fence-less, and ceilings seeded from a regressed tree bless the regression.
  - [ ] **Dependency-CVE scanning belongs on CI loop, not commit hook** (deferred 2026-08-12): keep the hook as lockfile early warning; stop counting it as CVE coverage.
    - [ ] `audit-deps` gates on `files: (bun\.lock|requirements\.txt)$`, so a CVE against an untouched dependency never triggers it — the normal case.
    - [ ] `always_run` is the wrong device (trivy every commit, staleness untouched).
    - [ ] Schedule `make scan_deps` + `scan_container` on a CI runner (see Gitea-vs-Woodpecker).
  - [x] _1 done step archived 2026-11-03 → docs/completed-todos.md._

### Privacy & Poka-Yoke #critical

- [ ] **Review & implement Poka-Yoke privacy plan**: Three structural mistake-proofing changes surfaced by panel review
  - [ ] **PK-1 — Local/External model indicator**: Add `is_external` + `provider_label` to model API response; show Local/External badge in model selector, response bubbles, and space agent messages
  - [ ] **PK-2 — Admin chat access default OFF**: Change `ENABLE_ADMIN_CHAT_ACCESS` default to `False` in `config.py:1488`; add audit log line in `routers/chats.py:94`; add visible banner when admin views a user's chats
  - [ ] **PK-3 — Workshop external model warning**: Show inline warning when an agent is created with an external-provider base model
  - [ ] Update CHANGELOG.md: document breaking change (admin chat access now opt-in)
  - [ ] Full plan at: `~/agent-planning/plans/poka-yoke-buzzing-sedgewick.md`

- [ ] **Privacy-layer poka-yoke (branch `feature/batter-agents-in-spaces`)**: all five reproduced defects fixed 2026-09-23, merge unblocked; what is left is housekeeping #security
  - [ ] **Follow-on found while fixing DRIFT**: this dev instance runs with an empty `WEBUI_SECRET_KEY` (`.env:22` is blank, and PID 1 carries it empty). Harmless while privacy is OFF; with the new guard, switching privacy ON here now fails loudly. Set a real key before enabling. #security
  - [ ] Two low left (`reverse_tool_calls` str-only fixed 2026-11-02 with the tool-argument card in Bugs): Spaces `TOOL_SERVERS` check-then-act (`routers/spaces.py:382`), manifest `"id"` comment with no gate (`main.py`). None is request-path; none blocks the merge.
  - [x] _7 done steps archived 2026-11-03 → docs/completed-todos.md._

### Pitch & Documentation

- [ ] **Growth: invite codes and social posts** (Alexander, 2026-11-03): four goals (Tinker makers, AI-UI stars, paid pilots, hub contributors); an AI-UI code books a pilot box, not an account #launch
  - [ ] [MANUALLY] Order the four goals: one push at a time, so someone answers every reply on launch day
  - [ ] [MANUALLY] Pilot box terms: who builds and runs each box, the price, how many a month
  - [ ] [WE] Pilot request form on sage.is with a code field; the lead lands in Trellis with its code as source (TODO.md first in WEB-Sage.is)
  - [ ] [WE] Codes per channel or per person, so each pilot traces to the post or the person who sent it
  - [ ] [WE] Post kit from what ships: the privacy test bench, one brew line, a Space agent; captions and alt text, no third-party pixels
  - [ ] [MANUALLY] Launch posts after the social card upload (card "Homebrew core"): Show HN, r/selfhosted, r/LocalLLaMA, awesome-selfhosted
  - [ ] [MANUALLY] Tinker sign-up: closed until the waitlist videos ship, then one wave; a proposal until the team agrees (Tinker board)
  - [ ] [MANUALLY] Review the proposal in SilverBullet: roles, code names, the floor price, the fee band; Tinker's side waits for the team's agreement
  - [x] _3 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Homebrew core: earn the self-submission bar on AI-UI** (decided 2026-09-30; paused 2026-10-01, Trellis first): 225 stars, 90 forks or 90 watchers; 11, 2 and 1 on 2026-11-02 (`make brew_notability`) #launch
  - Pause kept 2026-11-03 (Alexander): outside contributors cannot open PRs while the repo is members-only
  - [ ] [MANUALLY] Ship the CLI inside the next AI-UI release, then run the tap's `ai_ui_formula` target; CLI-only `3.2.0_N` revisions end
  - [ ] [MANUALLY] Upload the card: Settings, Social preview (GitHub's API cannot set it)
  - [ ] [MANUALLY] 11 live Dependabot PRs: groups #59 #60 after an image build and e2e; majors #57 #58 #39–#42; tw2startr #13 #47 #51 after `npm test`
  - [ ] [MANUALLY] Decide the 7 Sage Notes issues from 2025-11 (#1, #3 to #8): product calls first, then label real starter work
  - [ ] [MANUALLY] Issues for collaborators only: Settings, General, Features, Issues, Creation allowed by. Pinned 2026-10-01: GraphQL `updateRepository` takes `issueCreationPolicy`, so it can be automated
  - [ ] [WE] Paused while members only: issue templates and 10–15 real `good first issue` + `help wanted` issues
  - [ ] [MANUALLY] "Make Sage yours" workshop: teams fork AI-UI, change something real and run it with `ai-ui dev`; participants self-organize
  - [ ] [WE] Paused while members only: `ai-ui dev --fork` and a fork-and-PR path for outside contributors (forks and stars stay open to all)
  - [ ] [MANUALLY] Launch: an awesome-selfhosted entry "(fork of Open WebUI)" written by hand; a Show HN on "one brew line, no Docker Desktop"; r/selfhosted, r/LocalLLaMA
  - [ ] [MANUALLY] README: a plain star line, and "Watch → Custom → Releases" for release notes. Alexander words it: a line asking for stars meets the no-solicited-stars rule
  - [ ] [MANUALLY] Submit to homebrew-core once one bar clears and `brew audit --new --strict --online` passes; route and rules in homebrew-apps `docs/official-homebrew.md`
  - [x] _11 done steps archived 2026-11-03 → docs/completed-todos.md._

### Sprig B1 — finish extraction (audit backlog, sequenced next)

- [ ] **Bring sprig hosting in-house — replace GitHub's package store as primary** (captured 2026-07-06; escalated to NEAR-TERM 2026-07-08 on community pushback over GitHub-only hosting, per Alexander). ([dossier](docs/board-dossiers.md)) #bonsai
  - [ ] GHCR holds the first artifacts, but the specs and the sage.is/sprigs page word it as "current publish target, not the permanent home"
  - [ ] GitHub rate-limits anonymous pulls, can change package policy, and a Microsoft-hosted registry undercuts the zero-egress/self-sovereign story
  - [ ] The env-driven registry host (prod-cutover item above) should make this a zero-code swap: publish to GHCR now, migrate freely later
  - [ ] Weigh self-hosted `registry:2` or Zot on openco.ca CapRover — Zot is OCI-artifact-native (built for the oras/sprig.yaml case); both fit the existing infra + Caddy TLS pattern
  - [ ] Weigh Forgejo/Gitea packages (self-hosted, free UI + auth story) and Cloudflare R2 behind a registry (cheap egress for big artifacts, matches the Cloudflare Pages footprint)
  - [ ] Docker Hub rejected by default — pull limits worse than GHCR
  - [ ] Decide on anonymous-pull bandwidth for ~600MB artifacts, and paged-for uptime vs sovereignty
- [ ] **Sprig artifact packaging — reproducible recipe gap down to ~4 of 17 repos** (surfaced 2026-07-03; most closed 2026-07-13/15): write the ~4 missing recipes so every `binary_sha256` is regenerable/auditable end-to-end. #bonsai #critical
  - [ ] In-repo build scripts exist for the original three: `sprig-embedding-minilm-onnx`, `sprig-reranker-bge-gguf`, `sprig-stt-whisper-base`
  - [ ] Plus `sprig-vector-chroma`, `sprig-rag-loaders`, `sprig-export-document`, `sprig-media-ffmpeg`, `sprig-backup-rclone`, `sprig-dev-svelte` (`build-sprig-*.sh`)
  - [ ] Plus the shared `scripts/build-llama-static.sh` — the static llama-server prereq the GGUF sprigs stage
  - [ ] Still recipe-less (~4):
    - [ ] `sprig-browser-ml`
    - [ ] `sprig-code-pyodide` — extract wasm/js from the frontend build stage (arch-neutral)
    - [ ] `sprig-embedding-e5-large-onnx` + `sprig-embedding-bge-onnx` — HF→ONNX export; weights arch-neutral
  - [ ] `sprig-embedding-e5-gguf` has no standalone recipe but is regenerable from `build-llama-static.sh` + the convert/quantize step (rescued at `~/sprig-rescue/convert.sh`)
  - [x] _**(b) named registry volume** `sprig-registry-data` SHIPPED 2026-07-12._

### Sprig B2 — non-technical clarity (audit backlog; data model before UI)

- [ ] **Sprigs admin UI redesign** (`app/src/lib/components/admin/Sprigs.svelte`): group cards by capability. #bonsai
  - [ ] Collapse the six embedding cultivars into one "Embedding" choice with a cultivar picker
  - [ ] Disclose consequences BEFORE Graft/Prune: size, restart-required, "replaces X" / "this breaks document search"
  - [x] Hide `pid`/`base_url` (2026-11-02)
  - [ ] Explain the Sprig/Graft/Prune/Wilted metaphor inline (tooltip or docs link)
  - [ ] Add first-run guidance instead of a wall of 14 cards

- [ ] **Sprig™ marketplace — simple selling of Sprigs** (captured 2026-07-08; now a PUBLIC commitment): support paid and proprietary Sprigs with selling as simple as Etsy made it for makers. ([dossier](docs/board-dossiers.md)) #bonsai #marketplace
  - [ ] Public commitment: the sage.is/bonsai FAQ says "A Sprig marketplace is on our roadmap to make selling one simple"
  - [ ] Alexander (CTO) was a founding engineer at Etsy (employee #5), named on the page
  - [ ] Methodology = Etsy for maker-simple selling + Shopify's developer playbook (partner program, first-class SDKs/docs — the MIT `sage-is-sprig-sdk-py` is the seed — builder-favoring revenue share)
  - [ ] Interacts with the in-house registry cutover — paid artifacts need authenticated pulls
  - [ ] Interacts with catalog schema enrichment (license/tier/price)
  - [ ] Interacts with `delivery: service-endpoint` — hosted paid Sprigs need no artifact download
  - [ ] Scope TBD: payments, publisher identity/verification, revenue split, how a purchase lands in an operator's catalog
  - [ ] **Architecture approved 2026-07-19 (roadmap-only, no code yet)**: spine = catalog-as-data — a new source of entries, not a new trust model. #bonsai #marketplace
    - [ ] The one hard blocker is `SprigSupervisor.CATALOG`, a hardcoded Python dict (`supervisor.py` ~222-625)
    - [ ] Extract the `_sprig()` entry schema to a validated model; merge entries from three runtime sources into the unchanged graft pipeline (allowlist → arch guard → pull → sha256 → minisign → extract → spawn)
    - [ ] Three lanes = a trust ladder: S1 first-party curated signed index; S2 curated community, publisher-signed via the per-entry `pubkey`
    - [ ] S3 admin self-load: any OCI ref at runtime, volume-persisted, graftable with no image rebuild; `SPRIG_REQUIRE_SIGNED=1` ratchets an instance to signed-only
    - [ ] Phase M1: catalog-as-data + admin self-load — also redacts `repo/tag/binary_sha256/insecure` from the browser catalog
    - [ ] Phases M2-M5: M2 remote storefront + in-house registry cutover (Zot), M3 discovery UX, M4 community submission, M5 commerce
    - [ ] Open: storefront name, M1 index shape, self-load sha-pin default, Zot vs GHCR-proxy, entitlement binding
    - [ ] Design: memory `project_sprig_marketplace.md`
  - [ ] **Quarter slice, scoped 2026-08-15 against a social push**: the push needs the store to exist. #bonsai #marketplace
    - [ ] M1 stays at position 3 in the `#### Platform unlocks` sequence, so the push date depends on Spaces multi-user and spend budgets — book no announcement against a date those two control
    - [ ] Ships: M1 catalog-as-data, M1b admin self-load (`POST …/sprigs/load`, `sprigs.d/*.json` on the volume), `/catalog` redaction
    - [ ] Ships: schema enrichment (`display_name`, `description`, `size_mb`, `license`, `tier`, `publisher`, `homepage` — once, with M1)
    - [ ] Ships: browse/search UI over the 20 shipped sprigs
    - [ ] Should: remote signed `catalog.json` on a Sage.is URL, artifacts staying on GHCR
    - [ ] Does not ship: public submission lane, storefront index, M5 commerce, in-house registry, `delivery: service-endpoint`
    - [ ] Dropping the public lane defers signature liability — self-load is admin-only; the admin stays the trust boundary
    - [ ] We do not charge makers to list (present tense, not "ever"); creators earn through contracts we sell direct, not a storefront cut
    - [ ] Cards: `charts/sprig-creator-program/TODO.md`
  - [ ] **Blocker — the `execute` event runs arbitrary JS in the top frame, and a listing policy does not fix it**. #security #critical
    - [ ] `POST /api/v1/functions/load/url` (`routers/functions.py:82`) installs a `main.py` from any GitHub URL today, no marketplace involved
    - [ ] A push that brings thousands of self-installers widens that surface
    - [ ] Pick one and record it for the endpoint: gate it or accept the risk in writing. The event half is closed: neutered 2026-11-02
    - [ ] Keeping Functions out of the community lane is correct and cheap but is not the control
  - [ ] **Blocker — no CSP exists, and enforcing a fresh one the week before a launch breaks the product**: tracked on the **CSP-configured gate** card under Repo Hygiene & Security, whose children carry these facts (merged 2026-11-02). #security #critical
  - [ ] **The app pane is the store's actual product, and it is not built** — four gaps. #bonsai
    - [ ] An installed app must open like an Artifact, run, and report progress — not "the assistant can call your API"; `Artifacts.svelte` already supplies the pane
    - [ ] The bridge validates by `event.origin`; a `srcdoc` frame without `allow-same-origin` has an opaque origin, so its postMessage arrives as `"null"` and is rejected at `Chat.svelte:416`
      - [ ] Validate `event.source === iframeElement.contentWindow` instead
    - [ ] Service workers, localStorage, IndexedDB, and Cache API need a real origin, so a genuine PWA cannot run in a `srcdoc` pane — in-container is the only rung where "PWA-type app" is literally true
    - [ ] Student progress needs a per-user per-sprig state API on the rootstock, not browser storage
  - [x] _2 done steps archived 2026-11-03 → docs/completed-todos.md._

### From Codebase (untracked)

- [ ] **Frontend Inline TODOs**: UX polish, component upgrades, bug investigation
  - [ ] Filter order handling in model config (`FiltersSelector.svelte:34`)
  - [ ] Voice input auto-stop logic in Knowledge Base (`AddTextContentModal.svelte:21`)
  - [ ] Shortcut support for generate-title button (`ChatItem.svelte:415`)
  - [x] User-facing error for Space participant issues (`Space.svelte:81`): a toast since 2026-11-02
  - [ ] Emoji picker search filtering (`EmojiPickerClean.svelte:47`)
  - [ ] Update RichTextInput Bubble/Floating to v3 (`RichTextInput.svelte:79`)
  - [ ] Note pages feature — multiple pages per note (`NoteEditor.svelte:80`)
  - [ ] Decide native vs custom file handling in notes (`NoteEditor/Chat.svelte:191`)
  - [ ] Investigate Kokoro worker issues (`kokoro.worker.ts:4`)

### Frontend — no-build strangler migration (approved 2026-07-25)

> Approved plan: move the AI-UI frontend off the SvelteKit build to server-rendered HTML + vanilla/htmx islands (htmx since slated for removal in favour of the in-house startr-swap, 2026-08-17), Svelte-as-biomes, strangler to zero. Three evidenced legs — delete duplicated code (~50%), cut the conversation load (172 req / 7.9 MB / ~19 s → near-instant), turn shared chats into a crawlable distribution surface.

> **HOW TO WORK ON THESE PAGES (as of 2026-07-31).** Never `make it_build` just to look at something.
>
> | you want to | run |
> | --- | --- |
> | **build anything** | **`make dev`** |
> | judge whether it ships | `make review` |
> | judge a page without rebuilding | `make review LIVE=1` |
> | judge Svelte changes | `make review REBUILD=1` |
>
> **Two commands, as of 2026-08-09.** `make dev` runs `uvicorn --reload` and `vite dev` side by side in one container, mounts `pages/`, seeds an admin and grafts the example ui-Sprig™ — everything is live and nothing needs a teardown. `review` boots the BAKED artifact, which is the pass that decides, because a review of your working tree is not a review of what you ship. `dev_run`, `review_live` and `review_rebuild` survive as aliases.
>
> Note `review LIVE=1` does NOT rebuild Svelte — it mounts `pages/` only, and the bundle stays frozen at whatever `it_build` last produced, with no warning.
>
> Under `review LIVE=1`: save a `.css`/`.js` under `pages/assets/` and the stylesheet **swaps in place** — no reload, so the page keeps its scroll and any open dialog; save a `.py` and the app **restarts itself in 2.8 s** and the tab reloads. Switching modes is 7 s, because the seeded volume is kept. `/pages/` is an index of every server-rendered page and carries a banner when the reloader is on.
>
> The gates deliberately have no live mode — `e2e`, `e2e_both` and `wizard_smoke` always boot the baked image, because a guard-rail run against a working tree tests something we do not ship. Full write-up: `docs/no-build-surface-convention.md` → "The dev loop".

- [ ] **Phase Q — clear the decks**: current-SPA drift fixes, cruft, and perf quick-wins — no migration needed. ([dossier](docs/board-dossiers.md))
  - [ ] **Drop the frontend's permission fallbacks**: the 13 `$user?.permissions?.x?.y ?? true` sites in `src/` are unreachable now that every enforced key ships in the payload. #frontend #tech-debt
    - [ ] A `?? true` can only mask future drift — it renders a control the API will refuse
    - [ ] Delete them; guard-rail asserts a denied permission hides its control
  - [ ] **`@cached(ttl=MODELS_CACHE_TTL)` never hits — the decorator is inert** (caching pass, 2026-07-26): the knob does nothing and every request stores an entry, so memory grows with request rate. #perf #tech-debt
    - Measured 2026-10-23: `generate_chat_completion` (`routers/openai.py:950`) calls it on every model call, so every answer probes providers live; fixed in Rootstock F1 (card "Congestion" in Bugs)
    - [ ] `routers/openai.py:550` + `routers/ollama.py:378` use bare `aiocache.cached` with no `key_builder`; the default key stringifies the Starlette `Request`, a new object each call, so it never repeats
    - [ ] Proven with `MODELS_CACHE_TTL=60`: five `/api/models` calls 0.74/0.73/0.78/1.70/0.74 s, zero hits
    - [ ] Add a `key_builder` on stable values (user id + provider-config revision) — or delete the decorators; removing a cache that never hits is behaviour-preserving.
  - [ ] **Redis/valkey + multi-worker — the actual concurrency lever** (scoped during the caching pass): `start.sh:233` runs `--workers ${UVICORN_WORKERS:-1}` — a SINGLE-process app today. #perf #architecture
    - [ ] `REDIS_URL`, `WEBSOCKET_MANAGER`, `WEBSOCKET_REDIS_URL`, and a redis-backed `PersistentConfig` exist in code; Dockerfile, compose, and CapRover set none
    - [ ] Raising `UVICORN_WORKERS` breaks websocket fan-out and duplicates every in-process cache per worker
    - [ ] Write the plan; decide the valkey sidecar: in-image vs CapRover one-click vs Sprig™.
    - [ ] Multi-worker test proving socket events cross workers.
  - [ ] Perf: put HTTP/2 in front — parallel boot fetches pay more once they stop queueing behind HTTP/1.1 connection limits. #perf
  - [ ] Perf: `/api/models` alone is ~770–995 ms of a ~820–1100 ms boot — latency, not payload (investigated 2026-07-26 with an EMPTY model list). #perf
    - [ ] The cost is the slowest provider probe in `get_all_base_models` (`utils/models.py:60-76`, already one `asyncio.gather`)
    - [ ] Each lever wants its own guard-rail and before/after
    - [ ] Backend: warm the base-models cache at startup; bound the per-provider probe timeout. (Defaulting it on is done.)
    - [ ] Frontend/islands: stop gating `loaded` on it — render the shell, fill the selector when it lands; the admin setup-wizard check (`$models.length === 0`) awaits the promise, not the boot chain.
    - [ ] Pagination is a third, separate lever — only after a payload measures large on a loaded instance (same open question for chat list, tools, prompts, knowledge).
  - [ ] Guard-rail Cypress spec for every area before it's touched
  - [ ] Modernize or prune the inherited upstream e2e specs: `registration/settings/chat/documents.cy.ts` now COMPILE (import depth `../support`→`../../support` fixed) but FAIL on stale open-webui UI. #e2e #tech-debt
    - [ ] They assume open signup (this fork hard-closes it after the first admin) and the old `Okay, Let's Go!` changelog dismiss (now the setup wizard's "Get Started"/Close via API)
    - [ ] Rewrite to the fork's flows or drop; they sit in a subdir, NOT in the default `make e2e` gate
  - [x] _18 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Phases 3–4 — medium surfaces, shell flip, then biomes**: Workshop FIRST, then users, evals, settings tabs, chat list → prune biomes (Functions, then chat core last, gated on the spike memo). That order sorts on 2–6% of the cost (measured 2026-08-02) — reorder it. ([dossier](docs/board-dossiers.md))
  - [ ] **SURVEYED: every migration candidate on one snapshot — the sorting key was wrong** (Alexander, 2026-08-02). #frontend #perf #critical
    - [ ] `cypress/e2e/upgrade/route-payload.cy.ts` 10/10 green on the restored snapshot (51 agents / 32 users / 17 knowledge bases / 8 prompts)
    - [ ] The floor: `/notes` with no data of its own costs 127 requests / 781 kB wire / 7,575 kB decoded
    - [ ] Route deltas above it: prompts +121 kB, functions +206, users +296, knowledge +455, evaluations +1,269, agents +1,714, chat +5,170 — for six of eight routes the list is 2–6% of what loading it costs
    - [ ] `/api/models` is 2,304 kB, fetched on every route, never cached: 741 of the 781 kB wire (95%) on a warm client
    - [ ] Server-rendered comparison: 12 requests / 234 kB wire / 472 kB decoded — one sixteenth of the EMPTY SvelteKit route
    - [ ] Method: decoded kB is the ranking column; wire kB is a returning-visitor figure (cold numbers in `workshop-payload.cy.ts`); `/home` not surveyed — Spaces has no list hook yet
  - [ ] **Reorder on lines deleted and open frequency — throughput no longer breaks ties.** #frontend
    - [ ] Component lines: users 3,126 · notes 2,910 · knowledge 1,671 · evaluations 1,359 · functions 1,249 · prompts 635 (ceilings — Agents landed at 53% of its count)
    - [ ] No telemetry exists, so the frequency column stays empty until Alexander fills it
    - [ ] `/admin/users` moves ahead of knowledge: largest component, the one surface that actually renders its base64 avatars, `users.cy.ts` already guards it
    - [ ] `/notes` is judged off this table: 2,910 lines of editor, not a list — the props-and-forms pattern may not apply
    - [ ] `/workshop/prompts` as warm-up: 635 lines, +121 kB, an afternoon
  - [ ] **THE FLOOR — parts 2 and 3: `/api/models` is the whole of what is left.** #frontend #perf #critical
    - [ ] The floor stands at 6,642 kB; `/api/models` is 2,304 kB of it and never caches — 741 kB over the wire on every navigation
    - [ ] Fixing the floor helps every route in the product, including the ones the strangler never reaches
    - [ ] Stop fetching `/api/models` on routes that never render it — it rides the `(app)` layout boot wave (`+layout.svelte:120`)
    - [ ] `/notes`, `/admin/users`, `/admin/functions`, `/admin/evaluations` each pay 2.3 MB for a model list they never render
    - [ ] Shrink the payload: `utils/models.py:175` sets `model["info"] = custom_model.model_dump()` per row, base64 avatars included — why it is 2,304 kB instead of tens of kB
  - [ ] **`routers/knowledge.py:42` writes to the database during a GET and queries once per row.** #backend
    - [ ] `get_knowledge` calls `Files.get_file_metadatas_by_ids` per knowledge base (the `Models.get_models()` N+1 shape) and prunes dead file ids via `update_knowledge_data_by_id`
    - [ ] So a concurrent read storm can write, and readers silently repair data
    - [ ] Fix AS the knowledge migration, on the "prune, don't port" rule
  - [ ] The no-build Prompts panel must not port the slash bug: it normalises on lookup
  - [ ] **Workshop is the next surface, elevated on production numbers** (Alexander, 2026-08-01). #frontend #perf #critical
    - [ ] Worst surface in the product; the only one missing the throughput budget (≤ ~2 MB transferred, first content < 2 s) on every axis
    - [ ] `/workshop/models` 144 requests / 20,520 kB / 6,181 kB transferred / 32 s
    - [ ] `/workshop/knowledge` ~140 requests / 18,203 kB / 5,257 kB / 19.07 s — a LIST OF MODELS slower than the 172 req / 7.9 MB / ~19 s conversation baseline
    - [ ] 5,567 lines across models/knowledge/prompts; the table predicts ~50–65%
    - [ ] First task is a before-measurement — the last two such assumptions (22 MB WASM, markdown libs) measured false
    - [ ] Candidate, read not measured: serial waterfall — route awaits `getModels` before `<Models />`, which then fetches `getWorkshopModels` + `getGroups` + `getBranding`
    - [ ] Candidate: static `marked`, `sortablejs`, `file-saver` in `Models.svelte`
    - [ ] Candidate: static `fuse.js`, `dayjs` + `relativeTime` in `Knowledge.svelte`
    - [ ] Candidate: base64 `model.meta.profile_image_url` per row
  - [ ] **The list payload repeats the same owner avatar once per agent** (filed 2026-08-01, measured 2026-08-02; `cypress/e2e/upgrade/workshop-payload.cy.ts` on the snapshot). #frontend #perf #critical
    - [ ] `GET /api/v1/models/` nests the owner's whole `UserResponse` per row: 475 kB of base64 avatars the page never renders (rows show "By {name}" as text)
    - [ ] 21 of 32 users carry avatars, 120 kB amplified ~4× by repetition
    - [ ] `/api/models` 2,304 kB + `/api/v1/models/` 1,503 kB = 3,807 kB — 41% of the page load, two endpoints carrying the same base64
    - [ ] SPA: 126 requests / 3,604 kB wire / 9,174 kB decoded / 5.4 s to first row; production's 20 MB does not fully reproduce (requests within 13%, bytes ~half)
    - [ ] Server-rendered: 11 requests / 234 kB / 152 ms cold, 7 kB / 44 ms repeat (0 data URIs vs 66; 6 cacheable avatar URLs)
    - [ ] In-app arrival still costs 919 kB wire (914 kB is `/api/v1/models/`) and 1,504 ms to first row
    - [ ] Timing stamped in-browser with `performance.now()` at the click, because `Date.now()` in a Cypress body stamps at queue time
    - [ ] Like-for-like (server page 1 is 24 rows vs the SPA's 51, so count both pages): 22 requests / ~477 kB — 7.6× less wire, 5.7× fewer requests
    - [ ] Also: `Models.get_models()` calls `Users.get_user_by_id()` in its loop — 49 queries for 48 rows
  - [ ] **A 166 kB favicon, a 166 kB splash and a 636 kB unsubsetted `Archivo-Variable.ttf` ride every cold page load** (found 2026-08-02 in the workshop top-25). #frontend #perf
    - [ ] Reopens the `/icons/` "not perf" call (the "already-gated" card in this section), which judged the file on disk
    - [ ] Just under 1 MB before anything renders, on the SPA and the server-rendered pages alike — PNG does not compress again on the wire, and a favicon is 16–48 px
    - [ ] Cheap and separable from the migration: resize the icon set to the sizes actually declared
    - [ ] Subset the font (the 2026-08-17 `sage-archivo.ttf` subsetting card under In Progress automated the build-time subset; re-measure what each page still loads)
  - [ ] **Avatars: one right size at the encoder plus a serve-time cache behind a cacheable URL — 30× measured, no new dependency beyond Pillow** (DECIDED 2026-08-01, Alexander). #frontend #perf
    - [ ] Decision: migration AND serve-time cache, not encoder-only — the migration's job is getting the blob out of the database row
    - [ ] Three real 250×250 avatars: 106.8 / 97.7 / 95.0 kB as PNG, 21 kB as JPEG, 5.9–7.2 kB at 128 px, 3.6–4.5 kB at 88 px — format alone 5×, format-plus-size 30×
    - [ ] Root cause: one canvas-resize block pasted three times (`ModelEditor.svelte:366`, `Settings/Account.svelte:134`, `ArenaModelModal.svelte:202`)
    - [ ] Only the agent copy omits the format argument, so it defaults to PNG
    - [ ] One shared encoder helper: WebP with JPEG fallback, dimensions matched to the slot
    - [ ] Migration moves originals to content-addressed storage on the data volume, leaving a reference in the row
    - [ ] Non-destructive (write, verify, then clear the row), idempotent, fails closed when the volume is not writable (`data_not_writable` issue_type)
    - [ ] Serve-time cache derives sizes beside the originals on first request; sizes come from a CLOSED set (44/128/256), never a free query parameter; cache on the volume, not in memory (multi-worker roadmap)
    - [ ] Exports must re-inline from storage and land WITH the migration — `Models.svelte:167` and `admin/Settings/Models.svelte:68` `JSON.stringify` models verbatim, so a local path silently breaks import portability
    - [ ] Hardening: format allowlist, byte ceiling, `Image.MAX_IMAGE_PIXELS`; Pillow verified absent from `requirements.txt` and the built image
    - [ ] Proof: `make upgrade_gate` boots a real snapshot
  - [ ] **Rename `/workshop/models` → `/workshop/agents`** (Alexander, 2026-08-01). #frontend #brand
    - [ ] The UI already says Agents (`Models.svelte` heading, page title, Import/Export Agents); only the URL, directory and component names say models
    - [ ] Consistent with the locked 2026-07-11 single tiered "Agents" surface decision
    - [ ] Do it AS the migration — renaming twice costs two redirect layers
    - [ ] The route, the nav label, the i18n keys, and a redirect from the old path for bookmarks
  - [ ] Count and pin the core biomes as a downward-only ratchet — chat core, rich-text editor, code editor, flow canvas, channels; the count only decreases #biomes #ratchet
  - [ ] **Mid-term: rebuild the chat core as a server-rendered fragment flow on startr-swap, not a ported island** (Alexander, 2026-07-27; "htmx" reworded 2026-11-02, since htmx leaves per the Remove htmx card). #frontend
    - [ ] The port is priced at 17,591 lines for a 15–30% cut
    - [ ] Fragment-first has the server own the conversation and send fragments, only the token stream stays vanilla — Phase S proved that half in ~260 lines, abort semantics included
    - [ ] A hypothesis with two Phase 0 datapoints; do NOT re-plan the phase order until one fragment surface is migrated and measured
    - [ ] The non-proxying browser driver Phase S made a condition
    - [ ] One migrated, measured fragment surface — the datum that settles it
  - [ ] Reimplement the flow canvas (`@xyflow/svelte`) framework-free
  - [ ] Slogan precision: "org-owned" not "user-owned"; keep yjs local-first for the editor #brand
  - [x] _7 done steps archived 2026-11-03 → docs/completed-todos.md._

## Backlog

_Items deferred to a later planning cycle. Move here from TODO when deprioritized._

- [ ] **Realistic fake details in the privacy filter, starting with email** #privacy (Alexander, 2026-11-12): an opt-in shape on domains we own; today `privacy/shapes.py` makes `p<8 hex>@example.invalid`, which reads as fake
  - [ ] [MANUALLY] Decide: register one or two domains for stand-ins, or keep a few on hand; each gets a null MX (RFC 7505), so mail sent to a stand-in bounces
  - [ ] [WE] Specs first: a realistic stand-in still reverses in streamed tool-call arguments, and never equals a real value in the map
  - [ ] [WE] A panel switch beside the detectors; `example.invalid` stays the default
  - Found in web Tinker's slice 0 (2026-11-12): phones already read real (`514-555-3668`, same area code), emails do not

- [ ] **Rotate the B2 key that 3.2.x printed into sage.startr.cloud's start log** #ops #security (Alexander, 2026-11-06): deferred to the backup ops work; Syncthing carries the backups meanwhile
  - Why it can wait: 3.3.0, live on both apps since 2026-11-06, no longer prints the rclone config or hands the environment to Sprig children; the 3.3.0 rotation run leaves `RCLONE_CONFIG_B2_ACCOUNT` and `RCLONE_CONFIG_B2_KEY` as they are. The release card called this the urgent half (the August cluster compromise)
  - [ ] [MANUALLY] Backblaze: a new application key for the backup bucket with the old key's capabilities; `sage-secret put ai-ui-sage-startr-cloud-b2-key --stdin` (the applicationKey), then the same with `--field account --replace` (the keyID)
  - [ ] [WE] Re-run `~/.local/share/ai-ui/rotation/rotate-3.3.0-secrets.sh`, dry run then `--go`: items already in the vault are reused, so only the two `RCLONE_CONFIG_B2_*` variables change, with one restart of sage.startr.cloud
  - [ ] [MANUALLY] Delete the old B2 application key in Backblaze

- [ ] **Sign in with Google and Apple for our services and each Sage box** #auth #ops (Alexander, 2026-11-06): one company address, `identity@sage.is`, owns the provider apps; plan at `~/.claude/plans/silverbullet/sign-in-providers.md`
  - [x] [WE] `identity@sage.is` made in Stalwart, password in the vault as `mail-identity@sage.is`; an outside probe landed and JMAP reads it (2026-11-06)
  - [ ] [MANUALLY] Share its INBOX with asomma and iplante (`stalwart.py share-inbox`, command in the plan)
  - [x] [WE] Google account on that address; project `sage-is-sign-in` in production; client "Realtor M door" behind M's Access (2026-11-06)
  - [ ] [MANUALLY] An Apple Account on that address; both logins into `Agents`
  - [ ] Our broker, Dex at `auth.sage.is` and `auth.sage.education`, so Google names us: both deployed 2026-11-07; open: M's door back on Google, education's 302 loop. OPS-Sage `runsheets/auth-broker.md`
  - [x] Decided 2026-11-06: Startr LLC enrolls with Apple on its D-U-N-S number; Sage.is, its operating name, is the app name
  - [ ] Decide: whose phone backs both accounts, one client per box or shared
  - [ ] AI-UI: an Apple provider beside the Google one (signed `.p8` client secret, form-post callback, relay addresses), specs first

- [ ] **The vault as the record for deployed keys: try.sage first, then a vault per cluster** #security (Alexander, 2026-11-04)
  - [x] Plan written up in `docs/try-sage-deployment.md`, "Planned: keys from the vault" (2026-11-04)
  - [ ] try.sage: its keys are pasted by hand into CapRover's env panel; `make deploy`, already under `sage-secret`, pushes the resolved `TRY_SAGE_*` values through CapRover's API, so a rotation is a vault edit plus a deploy
  - [ ] [MANUALLY] Rotate `TRY_SAGE_LLM_API_KEY` and `TRY_SAGE_TOOL_SERVER_API_KEY`, which 3.2.x handed to Sprig children and the 3.3.0 run left in place (2026-11-06): new keys at the provider and the tool server, `sage-secret put ai-ui-try-sage-is-llm-api-key --stdin` and `ai-ui-try-sage-is-tool-server-key`, then re-run the rotation script
  - [ ] Per cluster: one collection and one machine account each, its credentials on that cluster, not this Mac's Keychain; the `sage-box` files in `~/.sage-is/boxes/` already hold only `bw:` references
  - [ ] Names: `bw:ITEM` resolves by name across all an account sees, so an account that sees several clusters needs prefixed names (`realtor-m-*` does this today)

- [x] _Workshop apps tab: Tinker.Click apps run inside the box. Dropped 2026-11-12 (Alexander): web Tinker replaces it (card "Platform alignment"). Archived → docs/board-dossiers.md._

- [ ] **`telemetry-otel` Sprig: tracing for operators who set `ENABLE_OTEL`** #bonsai (2026-10-14): the 3.2.1 base keeps only `opentelemetry-api`; `ENABLE_OTEL=true` boots untraced with a warning
  - Parked 2026-11-03 (Alexander): until an operator needs tracing; no box sets `ENABLE_OTEL` today
  - The SDK and gRPC exporter already ride vector-chroma v3; this Sprig would add the HTTP exporter and the instrumentors
  - [ ] [WE] Pip overlay built like vector-chroma v3 (closure minus the rootstock): `opentelemetry-exporter-otlp-proto-http` + the `opentelemetry-instrumentation-*` set at the base's API version (1.45.1 / 0.66b1)
  - [ ] [WE] Decide who owns spans: FastAPI 0.143's native telemetry steps aside when the instrumentor's middleware is present (`_legacy_otel`)
  - [ ] [WE] Gate: graft, set `ENABLE_OTEL=true`, a span reaches a test OTLP collector

- [ ] **FastAPI's strict JSON Content-Type: turn it on?** #security (3.2.1 kept it off, Alexander 2026-10-14): `strict_content_type=False` in `main.py` parses a body sent with no Content-Type as JSON, as 3.2.0 did; decide after finding which API clients omit the header

- [ ] **LocalMind deep-exam: steal its ingestion/exports/copy, make it an AI-UI satellite** (plan: `docs/localmind-exam-plan.md`; frozen until Trellis/ISA pilot ships)
  - [ ] [WE] Phase 0–1: sample-pack baselines (ingest + export matrices), port proposals for PDF chunking, markdown-IR exporters, `{{Blank}}` copy model
  - [ ] [WE] Phase 2: one small PR per adopted piece behind AI-UI seams, with tests; kill-or-keep on `pandas`/`trafilatura` weight
  - [ ] [WE] Phase 3: satellite contract thinnest-first — STT via whisper sprig (deletes ~1G venv), embeddings/chat overflow, Docling for hard PDFs; read-only API scopes
  - [ ] [MANUALLY] Ship order decision (recommend STT first), then wire + test on the school server
  - [ ] [MANUALLY] Ask its author for AGPL-3.0 in writing (a `LICENSE` in the author's own commit); nothing is ported before that; the import commit is credited in a `NOTICE`
  - [ ] Onboarding rides on the shared collaboration repo (guide + skill pack, installed through the tap)
  - [x] _4 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **startr.style 1.x from core changes AI-UI's pages when the vendored copy is bumped** (2026-10-16; AI-UI pins 1.5.0 since `bb99576`, so a core publish no longer lands here at once) #startr-style #frontend
  - [ ] 206 Svelte files carry `--dark-bgc`/`--dark-c`/`--dark-bc`/`--hvr-dark-bgc`, which no rule reads in the kit or in AI-UI: dark styling from converted `dark:` classes never applies. Decide: kit tokens under `[data-theme="dark"]`, or a kit dark variant
  - [ ] `--c-hover` and `--bgc-hover` in pages/templates/agents.html:153,158,160 are no-ops today and work once 1.x ships; check the look is still wanted
  - [ ] `--button-hover:var(--primary)` from pages/shell.py:235 starts working: plain `<button>`s hover to the brand primary (`.btn:hover` outranks it)
  - [ ] `--br:1px solid …` as border-right (admin/Settings/Interface.svelte:431/437/444, admin/Settings/Images.svelte:552, workshop/Models/ModelEditor.svelte:583) keeps working in 1.x; move to the 2.0 name when it lands
  - [x] _4 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Finish offload Tier B + native-UI relocations** (2026-06-26): Tier A (cache purge + BuildCruft sweep) plus a manual Movies symlink took host disk from 12% to ~50% available. None of the remaining work blocks Bonsai™. ([dossier](docs/board-dossiers.md))
  - [ ] Tier B `home` from admin shell: `sudo offload --target-home /Users/somma move home --apply`. Reconcile the Music symlink first (points at `/Volumes/Somma 01 Dock Drive/Music`, offload expects `/MovedHome/somma/Music`) — same-volume `mv` + re-symlink, three commands
  - [ ] Tier B `app` (Signal, Obsidian, Steam, Keybase, VSCode, Cursor, Epic, Minecraft) — quit each before firing
  - [ ] Tier B `dev` (CoreSimulator 5.8 GiB)
  - [x] Docker Desktop's disk image already lives on the Dock Drive, and its volumes moved to Colima on 2026-10-08; Docker Desktop is uninstalled after 2026-10-16 (tap board)
  - [ ] Move iMovie, Music, and Photos libraries via native UI (per `offload relocations`)
  - [ ] Track [`Sage-is/homebrew-apps#1`](https://github.com/Sage-is/homebrew-apps/issues/1): `du -sk` → `stat -f %z` verification swap unblocks one-shot `offload move home --apply` on APFS-clone-heavy targets like `~/Movies`; until then, use the manual rsync + stat-verify + symlink dance from the 2.3.4 ship session

---

## Bugs

- [ ] **One model ID from two connections: the env-only one can serve it, unfiltered and unseen** #security #privacy (found 2026-11-12, web Tinker slice 0): connection `0` and `SAGE_LLM_API_URL` both list `deepseek/deepseek-v4.1-flash-1017`; the env one served it and made no stand-ins
  - Inferred, not traced: `app.state.MODELS` keys by ID, so one connection wins; the panel lists no `hidden:<id>` row (`pages/privacy_panel.py` `_connections`), so only `default_external` reaches it
  - [ ] [WE] Trace which connection wins a shared ID; a spec that fails while an unfiltered twin can win
  - [ ] Decide: show env-only connections on the panel (read-only on try.sage.is), or filter a shared ID when any of its connections is filtered
  - The dev volume `sage-ai-dev-data` has `default_external: true` since 2026-11-12

- [ ] **The dev container prints none of AI-UI's own INFO lines** #bug (found 2026-11-12): with `GLOBAL_LOG_LEVEL` unset, `env.py:64-70` picks INFO but skips `basicConfig`, so stdlib loggers stay at WARNING and `privacy: pseudonymized` never shows
  - Seen: only uvicorn's own INFO lines since start; every app line was ERROR
  - [ ] [WE] Apply the default level when the variable is unset, with a spec; prod keeps WARNING

- [ ] **Rootstock F0 leftovers: what the 2026-10-24 security fixes did not cover** #security (gathered 2026-11-02 from closed cards, now in `docs/completed-todos.md`)
  - [ ] [MANUALLY] Upstream fix, proposed, never edited from here: startr.style publishes an SRI hash beside every versioned file and keeps versioned paths immutable
  - [ ] [MANUALLY] try.sage.is: left on while only developers can reach it and no demos run (2026-10-23 to 2026-10-30); switch it off before the next demo
  - [x] _5 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Every restart turns document search off on a box with vector-chroma, until someone runs `--vector-on`** #bug #critical #sprigs (seen after deploys 2026-10-24, and 2026-10-27 after a plain restart: S04's nginx lock made CapRover redeploy sage.startr.cloud, `vector_db_ready: False`)
  - Cause: `vector` is a delivered overlay with no process, so neither the boot reconcile (`sprigs/supervisor.py` `_reconcile`, which re-points embedding, reranker, stt, tika, docling) nor the graft route (`routers/sprigs.py` `graft_sprig`) calls `vector_bootstrap.ensure_chromadb`; its step 2 would switch the client on from the overlay already on disk
  - [x] [MANUALLY] Alexander: pull it into 3.3.0 or keep it for F1: it ships in 3.3.0, with everything in the tree (2026-11-05); the fix is uncommitted in `routers/sprigs.py`, `sprigs/supervisor.py`, `sprigs/vector_bootstrap.py` and `sprigs/test_vector_reactivate.py`; `upgrade_gate` (2026-11-05) caught a graft that answered 500 when the import failed, now fixed
  - Until it ships: `scripts/kb-reindex.py BASE_URL --vector-on` after every deploy and every restart (release runbook, "After the deploy: document reading")
  - [ ] [WE] Found 2026-11-05: the prune route has no `vector` branch, so after a prune the client stays on until a restart; decide whether a prune turns search off
  - [x] _2 done steps archived 2026-11-03 → docs/completed-todos.md._
- [ ] **The SPA floor crept 539 kB unnoticed between 2026-08-02 and 3.2.2** #perf (found 2026-10-24 by `surface_budget` in `gauntlet_full`): `notes-empty` measures 7,179.9 kB decoded on the 3.2.2 image against the 6,800 kB ceiling set on 2026-08-02 at 6,641 kB; `/api/models` is 2,902 kB decoded on the 2026-07-12 snapshot
  - Held 2026-11-03 (Alexander): F1 starts once 3.3.0 ships
  - Found 2026-11-03: the whole creep is `/api/models`. It went 2,304 kB (08-02), 2,702 (3.1.0, measured 08-17), 2,902 (3.2.2), 2,910 (F0); everything else on the floor fell 60 kB, then rose 151 kB for the vendored stylesheet and fonts
  - Cause: the gate's container has open egress, and the snapshot's config lists OpenAI, Groq, OpenRouter and HF router with `model_ids: []`, so each run fetches four live catalogs. The floor grows with the calendar, not the code, and production keys leave on every run
  - Doubled: both merge sites in `routers/openai.py` (`:520-524`, `:586-589`) spread each provider object and nest it again as `"openai"`; nothing in `app/src` or the backend reads `.openai`. OpenRouter alone is 453 models, 810 kB today, up from about 584 kB on 08-02
  - Headroom on the last run (10-24): 7,339.4 kB against 7,350, so 10.6 kB; OpenRouter has added about 6 models since, so `release_smoke` for 3.3.0 will likely fail here with no code change
  - [x] [WE] Hermetic gate, code done 2026-11-05: a mock on the gate's network serves a frozen 100-model catalog per connection (`MOCK_MODEL_COUNT`), and `scripts/snapshots/point-providers-at-mock.py` points the copy's connections at it with no real key
  - [x] [WE] Ran 2026-11-05 in `gauntlet_full`: floor 5,780.6 kB decoded; the ceiling drops 7,350 -> 5,900 kB in `run-gate.sh`
  - [x] [WE] Drop the nested `"openai"` copy at both merge sites (2026-11-05), with `routers/test_openai_model_list.py` in `image_unit_tests`, green 2026-11-05
  - [ ] [WE] F1: the revision-keyed, ETag'd model list (plan, F1) brings `/api/models` down; re-measure and lower the ceiling with it
  - [x] _2 done steps archived 2026-11-03 → docs/completed-todos.md._
- [ ] **Production data reaches Backblaze in plaintext** #security #backup (Alexander, 2026-10-24): the deploy backups now move to Somma 02 encrypted; their siblings stay as they are until each gets a decision
  - [ ] [MANUALLY] Then drop the plaintext `SAGE_STARTR_CLOUD_ADMIN_KEY` from `.env`; the vault holds the same value
  - [ ] [MANUALLY] Sibling: Syncthing mirrors sage.startr.cloud's data folder (`webui.db`, uploads, vectors) to `Somma 01 Dock Drive/Sync/`, which Backblaze backs up as it is
  - [ ] [MANUALLY] Sibling: each node's nightly backup (volumes, database dumps, `captain-config`) rides the same sync to this Mac and Backblaze
  - [ ] [MANUALLY] Sibling: Colima's VM disks, dev volumes included, sit on the same drive
  - [ ] [MANUALLY] Check whether this Mac's Backblaze uses a private encryption key; with one, Backblaze holds only ciphertext for every sibling above
  - [x] _3 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **Congestion: one event loop carries every request, stream and socket, so streams stall and pages hang** #bug #perf #critical (Alexander, 2026-10-23; measured in the code the same day; plan section "Congestion and the Tinker gateway")
  - Held 2026-11-03 (Alexander): waits on the Rootstock card's F1
  - Every model call fetches provider model lists live: `routers/openai.py:950` calls the router's `get_all_models`, whose `@cached` (`:555`) never hits, and each call opens a new HTTP session (`:1042`)
  - Stream frames carry the whole answer so far, one per provider chunk, to every tab (`utils/middleware.py:1945-1951`, `socket/main.py:647-669`): about 5.6 MB per tab for a p90 answer, 43 MB for a p99
  - Uploads run extraction and embedding on the loop (`routers/retrieval.py:1536,1617`); the model list costs about 660 queries per page for role `user` (`main.py:1631`, `utils/access_control.py:145`)
  - Seen 2026-10-24: re-indexing sage.startr.cloud's knowledge bases held the loop so long that `/health` stopped answering and the health check replaced the container once; a 130,090-character file still cannot be indexed there
  - Decided 2026-10-24 (Alexander): indexing speed is a product fix, never per-host tuning or a GPU box: batched embedding calls (default 32, not 1) and uploads off the loop in F1; one embedding service per node through the gateway, vectors cached by model and chunk hash, index jobs with progress in F5
  - The watchdog's first catch (2026-10-24, a test box): the sign-in password check holds the loop about 270 ms (bcrypt, `utils/passwords.py:47` from `models/auths.py:141`); a class signing in together stalls everyone; a thread for it joins the F1 list
  - Each answer rewrites the chat blob at least three times, and every chat stores its messages twice; every request writes `user.last_active_at` (`utils/auth.py:277,303`); the database pool waits 30 s (`internal/db.py:43-46`)
  - [x] [WE] Rootstock F0: the loop-lag watchdog logs the file and line of each stall, never values (shipped 2026-10-24, `6222e39`); its first week orders the fixes
  - [ ] [WE] Rootstock F1: the ten fixes in the plan (batched embedding calls and the vector store's switch joined 2026-10-24), gated by `make stream_load` at 30 UI streams with uploads: loop lag p99 ≤100 ms, bytes ≤2× the text plus 40 kB, at most 3 blob writes per answer, 0 errors
  - [ ] [WE] Tinker load, hundreds to thousands of streams per box: the model gateway in its own process from Rootstock F2 (Rootstock card)

- [ ] **Branding colors don't reach the page — theme Sprig severs the cascade** (diagnosed live on :8099, 2026-08-17; approach settled with Alexander same day). Config holds `#b2b1fe`/`#9178cc`; the page feels green anyway. Fixes 1–3 shipped 2026-08-17; the rest is open (re-verified 2026-10-05). #bug #frontend
  - [ ] Three stacked sources on :8099: grafted `sprig-theme:workshop-bio` (`/themes/active.css`) sets `--primary/--secondary/--links` as GREEN LITERALS + a green-tinted `--color-gray-N` scale; the layout sets inline purple `--primary/--secondary` (wins those two); stock startr.style derives `--links: var(--primary)`.
    - The inline set moved from `+layout.svelte:565-570` to `applyBrandingColors` (`$lib/utils/branding.ts:25`), called at `+layout.svelte:552`.
  - [ ] Root cause: the Sprig's literal `--links` SEVERS the framework cascade, so inline `--primary` never reaches links; the tinted gray scale covers most surface regardless.
  - [ ] Upstream (first-party) fix: theme Sprigs must author `--links: var(--primary)`, not literals — keeps grafted themes brandable; fix `workshop-bio` + the authoring contract in the sprig spec.
    - Still open 2026-10-05: `scripts/themes/workshop-bio/theme.css:22` sets `--links: #2f7d4f`. The theme lives in this repo.
    - Checked 2026-11-05: `workshop-math` carries the same literal. The fix is a new signed `v2` theme artifact (`catalog_build TAG=v2`, `sprig_sign`, `sprig_publish`, a new sha pin): the Sprig lane, not an app release
  - [ ] Guard: e2e asserts a saved color reaches BOTH a SPA and a no-build page; the drift class is "one consumer honors config, the other silently doesn't".
  - [ ] Inline `<style>` stays CSP-compatible today (`'unsafe-inline'` kept per the CSP card); note in the policy's exception list when that ships.
  - [ ] Found on the way: the no-build shell never loads `/themes/active.css` — a grafted theme dresses the SPA and NOT the server-rendered panels. Decide whether the shell links it (theme parity) or stays deliberately unthemed; today's fix gates shell colors on `SPRIG_ACTIVE_THEME` so the two surfaces at least agree on who wins.
  - [x] _3 done steps archived 2026-11-03 → docs/completed-todos.md._

- [ ] **`make lint`'s frontend half is red and always was**: `bun run lint:frontend` (`eslint . --fix`) exits 1 with 9,609 errors (found 2026-08-17 the first time `lint` went otherwise green — the Python half never let it get this far). #bug #dx #lint
  - Re-measured 2026-09-25 with `eslint . -f json`: 9,622 errors, about 1,519 of them ours; `make lint` runs it with `--fix`, which rewrites files (its own card above the board's columns until 2026-11-02)
  - [x] Ignore third-party trees: `app/static/pyodide` (5,163, gitignored), `app/static/swagger-ui` (2,891), `pages/assets/vendor/` (46). Done 2026-11-02: `ignorePatterns` in `app/.eslintrc.cjs`
  - [ ] Ours: `app/src/lib` 1,385, `app/src/routes` 75, Cypress 55, `vite.config.ts` 4; top rules `no-unused-vars`, `no-unused-expressions`, `no-explicit-any`
  - [ ] Then make `lint:frontend` a gate (without `--fix` in CI) so it cannot regress; `make ship` does not run it today
  - [ ] The bulk is vendored code eslint should never read: `pages/assets/vendor/htmx.min.js` alone contributes thousands; `dev-reload.js` and `startr-swap.js` carry a handful of real `no-unused-vars`.
    - Corrected by the 2026-09-25 count: `pages/assets/vendor/` holds 46 errors; `app/static/pyodide` and `app/static/swagger-ui` hold the bulk
  - [ ] The vendored no-build assets under `backend/sage_is_ai/pages/assets/` postdate the eslint config — nothing ignores them.
  - [ ] Fix shape: eslint ignore for `pages/assets/vendor/` (done 2026-11-02), then read the residue honestly.
  - [ ] Note `--fix` in a LINT target mutates the tree on check — same class of surprise the format gate just retired.

- [ ] **Channel components carry zero `data-cy` hooks**: the Spaces specs pin on load-bearing raw ids (`#space-container`, `#messages-container`, `#send-message-button`) and the bare ProseMirror class; add hooks next time `app/src/lib/components/channel/` is touched. #dx

- [ ] **`response.background()` runs twice for the original streaming response**: `stream_body_handler` awaits it at its tail for every response it drains; `response_handler` awaits it again on the same original after the retry loops — awaiting a Starlette `BackgroundTask` twice runs the wrapped callable twice. #bug
  - Found 2026-08-08 during the chat-path weight census, while classifying it as dead code — it is not dead, it is a double-execution.
  - [ ] Continuation responses are spared — only `stream_body_handler` touches those.
  - [ ] Not verified: pipe functions that set their own background task.
  - Harmless today (checked 2026-11-05): the task is `cleanup_response`, which closes the aiohttp response and session and is safe twice; the direct-connection variant is too
  - [ ] When the chat path moves: move the second call into the `CancelledError` branch, never delete it (on cancel the first call never runs)
  - [x] _1 done step archived 2026-11-03 → docs/completed-todos.md._
- [ ] **Six JSON parse sites scrape from the first `{` to the last `}`; the prompt template teaches the model to break it**: the title template (`config.py:1629`) carries a literal example object at `:1640`, so a model that restates the format emits two objects — exactly the input the scrape fails on. #bug ([dossier](docs/board-dossiers.md))
  - Found 2026-08-08. Clean and fenced input parse; two objects in one reply do not.
  - [ ] These calls run on the task model, which operators set small, and small models restate the format most.
  - [ ] Worst site is RAG queries ([middleware.py:1055](app/backend/sage_is_ai/utils/middleware.py#L1055)): on failure it sets the entire model reply as the retrieval query, silently degrading RAG.
  - [ ] (1) Set `response_format` on the task calls — `utils/payload.py:346-353` already converts it to Ollama's `format`, and no task call sets it. A behaviour change: one at a time, fixture first (the freeze lifted 2026-08-08).
  - [ ] (2) One parser as the floor in a new `utils/llm_json.py` for providers that ignore it — strip fences, try the whole string, scan for balanced objects. New file, moves no citation; can land any time.
  - [ ] (3) Drop the example object from the template. A behaviour change: one at a time, fixture first (the freeze lifted 2026-08-08).
  - [ ] Trap: a shared helper is NOT the fix — in the restated-format case both objects are valid JSON and both carry the key, so no parser can tell them apart.
  - [ ] The six sites, consolidated 2026-08-08 into one `slice_json_object` helper, behaviour byte-identical (lines restated 2026-10-05):
    - [ ] [808](app/backend/sage_is_ai/utils/middleware.py#L808) tool calling
    - [ ] [968](app/backend/sage_is_ai/utils/middleware.py#L968) image prompt
    - [ ] [1055](app/backend/sage_is_ai/utils/middleware.py#L1055) RAG queries
    - [ ] [1494](app/backend/sage_is_ai/utils/middleware.py#L1494) follow-ups, through `run_json_task` (called at 1510)
    - [ ] [1554](app/backend/sage_is_ai/utils/middleware.py#L1554) title
    - [ ] [1494](app/backend/sage_is_ai/utils/middleware.py#L1494) tags, through `run_json_task` (called at 1583)
- [ ] **`features` on a chat request is accepted unvalidated** #bug: every unknown key passes, which is how the dead `web_search` branch was reachable from the API (that branch and its `NameError` were deleted 2026-11-05)
  - [ ] Validate `features` off the request body in `utils/middleware.py`; a behaviour change, one at a time, fixture first
- [ ] **`ENABLE_REALTIME_CHAT_SAVE=true` leaves reasoning stuck on "Thinking…" for the whole generation**: the flag changes what the browser receives, and the reasoning close rides the first content delta — the disclosure spins until the terminal `done: True` event. ([dossier](docs/board-dossiers.md)) #bug
  - [ ] Flag on: text deltas ship raw and the frontend appends `choices[0].delta.content` ([Chat.svelte:1241](app/src/lib/components/chat/Chat.svelte#L1241)).
  - [ ] Flag off: the frontend replaces serialized blocks ([Chat.svelte:1275](app/src/lib/components/chat/Chat.svelte#L1275)).
  - [ ] The content-delta close ([middleware.py:2003](app/backend/sage_is_ai/utils/middleware.py#L2003)) sends no serialized snapshot with the flag on ([middleware.py:2065](app/backend/sage_is_ai/utils/middleware.py#L2065)), so the last one the browser got says `done="false"`.
  - [ ] DB is correct both ways (`done="true" duration="1"`; oracle replay of `reasoning-field-then-content.sse`).
  - [x] Re-checked 2026-11-04 after the reasoning fix: still true. A flag-on replay of `reasoning-field-then-content.sse` keeps `done="false"` until the final event.
  - [ ] Flag on breaks two more paths (same replay): `reasoning-tag-inline.sse` shows raw `<think>…</think>` text until the end; after a field close ([middleware.py:1975](app/backend/sage_is_ai/utils/middleware.py#L1975)) the answer freezes at its first fragment, since later `reasoning_content` deltas ship raw.
  - [ ] Proposed fix: the flag decides only per-delta DB saves; the browser always gets serialized blocks. Pin it with flag-on oracle cases for the three streams (`realtime-save-on` covers only `plain-text.sse`).
  - Found 2026-08-04, chat-path census. The freeze lifted 2026-08-08; a fix goes one at a time, fixture first.
  - Same family as the reasoning-block bug below.
  - [ ] [MANUALLY] Check the flag on try.sage.is before deciding severity. Default `False` ([env.py:331](app/backend/sage_is_ai/env.py#L331)), absent from the docs' CapRover block; `cr-deploy apps try-sage-is` needs the captain password (token expired 2026-11-04).
- [ ] **A partial tag reaches the reader for one frame**: when a chunk boundary splits a reasoning tag, the loop emits the fragment raw before the next chunk completes it — cosmetic and brief, but visible. #bug
  - [ ] The `reasoning-tag-inline` oracle golden records a first event whose entire content is `<thin`.
  - Same family as the chunk-boundary whitespace defect in the reasoning-tag entry below; a tag-aware output buffer would kill both at once.
  - Found 2026-08-04 while reading the oracle goldens (chat-path chart). The freeze lifted 2026-08-08: one behaviour fix at a time, fixture first, and the fix re-records the golden deliberately. Still live 2026-11-05: event 4 also shows `…methods.</think`.

- [ ] **Unclosed reasoning block swallows the model's answer** (Alexander, 2026-08-03; demo-blocking): fixed in the working tree 2026-11-04 on both paths, mid-stream; waits on a live replay and Alexander's commit. #critical #bug ([dossier](docs/board-dossiers.md))
  - [ ] [MANUALLY] Live replay on `make dev_run`: a `deepseek-r1-distill` agent whose system prompt asks for `<thinking>` tags; the answer must show while it streams. Then `qwen3.5:9b` via Ollama: no bare `</think>` after the block (variant 3).
  - [ ] [MANUALLY] Commit: `middleware.py`, the two fixtures, the oracle and its 3 changed and 3 new goldens, the Makefile (`reasoning_tag_fixture` joins `gauntlet_full`; teeth move to `reasoning-field-no-end-tag`).
  - [ ] Known edge: a first text block with a bare `</think>` outside a code fence, and no opener, is read as a pre-filled thought and folded into the block.
  - [x] _9 done steps archived 2026-11-04 → docs/completed-todos.md._
- [ ] **Model special tokens reach the reader**: the assistant's rendered answer ended with `<｜end▁of▁sentence｜>`, DeepSeek's EOS token, printed as visible text — nothing in the backend strips model special tokens. #bug
  - Found 2026-08-03 in the same capture as the reasoning-tag bug.
  - [ ] A grep for stop-token or special-token handling across `sage_is_ai` returns nothing.
  - [ ] Every model family has its own set (`<|eot_id|>`, `<|im_end|>`, `<｜end▁of▁sentence｜>`, `<|end_of_text|>`), so the fix belongs at one boundary rather than per-provider.
  - [ ] Worth pairing with the reasoning-tag fix: both are "raw model protocol leaking into prose", both were visible in one screenshot, and both make a demo look unfinished.
  - [ ] [WE] 3.3.1 (Alexander, 2026-11-05): strip only at the end of the whole answer so far, never mid-answer, on the stream and non-stream paths; a fixture for a token split across chunks and one mentioned mid-answer

- [ ] **The changelog pager spec passes whether the button moves or not**: `wizard-changelog.cy.ts` was green against the broken transform version AND the working `margin-left` version — the gap is the environment, not the assertion. #bug #critical-gate
  - [ ] Spec under test: "moves to the other side once the notes run out".
  - [ ] The assertion has teeth against a zero shift: forcing 0 went RED — `expected 0 to be above 367.5`.
  - [ ] What it missed: a transform that applied under the driver but not in the operator's browser.
  - [ ] Decide: make the check discriminate in a real engine, or drop the claim and say the spec covers paging and the label only.
    - [ ] SikuliX is on the roadmap for exactly this class.

- [ ] **The diagnostics page still renders English for every reader**: every other no-build panel binds `translator(request)`, but `diagnostics_panel.py` calls `t(key, {})` at the default locale — a genuine loss for a Spanish operator rather than a no-op. #bug
  - [ ] Re-confirmed 2026-08-01 after the Jinja2 conversion — the templating pass moved its markup but did not thread a locale.
  - [ ] `_library_entries`, `_fix_steps` and `_row` still call `t(key, {})`.
  - [ ] Call sites (restated 2026-10-05): [73-75](app/backend/sage_is_ai/pages/diagnostics_panel.py#L73) in `_library_entries`, [113](app/backend/sage_is_ai/pages/diagnostics_panel.py#L113) and [117](app/backend/sage_is_ai/pages/diagnostics_panel.py#L117) in `_fix_steps`.
  - [ ] Call site: [155](app/backend/sage_is_ai/pages/diagnostics_panel.py#L155) in `_row`.
  - [ ] Keys are the nested `diagnostics.fix.*` ones whose values are real sentences.
  - [ ] Fix: thread a locale from `render_diagnostics(request, user)` (:204) through `_library_entries`, `_row` and `_fix_steps`. `_library_block` and `_ghost_block` went away in the Jinja2 conversion.
  - [ ] `_STATUS_LABEL` (:127) and `_SECTIONS` (:133) are hardcoded English too.
  - [ ] The mechanism is already there; only the plumbing is missing.
  - [ ] Corrected 2026-11-05: no locale has `diagnostics.*` keys, and `i18n.t()` returns the raw key on a miss, so binding a translator alone shows raw keys; add an en-US fallback in `i18n.t()` and the translations first

- [ ] **A Sprig that dies on boot leaves no evidence: child `stderr` is `DEVNULL`** #bug #sprigs (`sprigs/supervisor.py`, the spawn in `graft`)
  - [x] An evicted cultivar says so since 2026-11-05: "was pruned while booting: 'X' took over the embedding capability" (`_evict`, `SprigHandle.evicted_by`)
  - [ ] Capture child stderr to `DATA_DIR/sage-is/sprigs/<name>/child.log` (truncate per spawn, size cap; llama-server is chatty) and append its tail to the boot-failure message (`record_error` cuts at 600 characters)

- [ ] **AI Engine Wizard Embedding Download Has No Stall Watchdog**: when the embedding model fetch from HuggingFace stalls, the wizard sits in `embedding=downloading` indefinitely — a real user has no signal except an idle spinner. #bug
  - [ ] Stall causes: network drop, HF outage, slow link.
  - [ ] No timeout, no retry, no resumable state surfaced to the admin.
  - [ ] `wizard-smoke.sh` catches this externally via `INSTALL_TIMEOUT_SEC`.
  - [ ] Verified still unfixed 2026-08-03: no watchdog or `stalled` state in `routers/retrieval.py`.
  - Narrower than written (2026-10-05): `_download` tries `ensure_embedding` first (`retrieval.py:523`), and Sprig artifact pulls time out at 300 s (`sprigs/artifact.py:58`). A stall now needs the legacy fallback: `uv pip install` and the `get_ef` pull (`retrieval.py:584-623`), neither timed.
  - [ ] Surface HF download progress (bytes, last-byte timestamp) to `request.app.state.MODEL_DOWNLOAD_STATUS` so the status endpoint exposes liveness.
  - [ ] Watchdog in `_download` (`retrieval.py`):
    - [ ] if cache size hasn't grown in N minutes (configurable, default 5), mark status=`stalled`, capture the error.
    - [ ] allow retry via a re-POST to `/api/v1/retrieval/models/download`. Today `retrieval.py:455-456` answers "Download already in progress" while status reads `downloading`; the watchdog must move it off that value first.
  - [ ] Surface stalled state in the wizard UI with a retry button + "check your connection" hint.

*(Surfaced 2026-05-18 during the cross-arch smoke run when an internet drop wedged the embedding download. The wizard never noticed.)*

- [ ] **Chat Microphone Recording Does Not Populate Message Input**: Recording from the microphone icon in chat does not process speech into the text field used to send messages. Reported 2026-05-11 against a pre-2.3.3 build — reproduce on 3.0.0 first; STT plumbing has changed twice since (whisper Sprig dispatch, wizard cut-over). #critical #bug
  - [ ] Reproduce on 3.0.0; confirm whether capture, transcription, or input binding fails
  - Traced 2026-11-05: the server path, the response shape and the callbacks are wired. New find: in browser STT mode, cancel still inserts the transcript (`VoiceRecording.svelte:303-310, 407`, `onend` calls `onConfirm`)
  - [ ] Trace recorder output into the chat composer state; fix the handoff
  - [ ] Add regression coverage for microphone-to-input behavior in chat

---
