> Status 2026-10-03: this plan was written 2026-09-26 from three read-only sweeps. Step 1 (retire six enacted docs, fix inbound links) ran on 2026-10-03 and is done; its result is recorded at the end of this file. The repo was on `develop`, not `release/3.2.0`, when it ran. Step 2 is decided except item 3 (2026-10-04). Steps 3 to 5 are open and belong to the tests, UX and docs path with Alexander (its "First week" card on the Trellis board).

# AI-UI docs drift pass

## Context

Three read-only sweeps checked 72 docs against the code on `release/3.2.0`. Drift was found in 22 of the 26 top-level docs, the decisions index, the board cross-references and the Bonsai drafts. Alexander set the rule for this pass:

- Retire any draft or plan that was enacted and is older than 2–3 weeks. Git history keeps it; the file system does not need to.
- Cut stale content that no upcoming TODO card needs.
- Fix facts in the docs that stay.
- Where a doc is borderline, stop and decide it together, interactively.

Constraints: no git writes (Alexander commits). `docs/decisions/` and `charts/` are synced outside git, so deleting there is unrecoverable; edit only, never delete. Don't hard-wrap prose. Use the Hemingway register. Send prose rewrites over ~2000 chars through `/delegate-edit` and review the diff.

## Step 1 — Retire enacted or dead docs [WE]

Delete the file, then fix every inbound link in the same sitting.

| Doc | Why retire | Inbound links to fix |
|---|---|---|
| `docs/api-refactoring-plan.md` | Enacted: 24/24 API files migrated (`docs/completed-todos.md:142`); `createApiHelper` in `app/src/lib/apis/base.ts:51` | `docs/README.md:29` |
| `docs/knowledge-ingestion-modes-plan.md` | Enacted: AI-parsed mode shipped (`CHANGELOG.md:526`); no open card for "external" mode | `docs/README.md:33`, `docs/archive/README.md:40` |
| `docs/try-sage-docker-exploration.md` | Enacted: the `try_sage_*` targets exist; the doc now misstates them | `Makefile:1734` comment (check hardlink count first, per global rule) |
| `docs/bonsai/sprig-spec-v1-draft.md` | Enacted June draft; canonical v1.0.0 is in `BONSAI/sprig-spec/v1.md` | `README.md:101`, `docs/bonsai/sprig-creator-program.md` |
| `docs/bonsai/rootstock-spec-v1-draft.md` | Same; canonical is `BONSAI/rootstock-spec/v1.md` | same sweep |

Also retire `docs/env-scripts.md`. `manage_env.sh` never existed. Fold its one true fact into `docs/development-workflow.md` in one line: `make setup_env` wraps `tools/setup_project_env.sh`. Fix `docs/README.md:32`.

## Step 2 — Interactive checkpoints [MANUALLY + WE]

Stop and decide each one with Alexander before editing.

> Decided 2026-10-04 (Alexander): item 1, community-hub.md rewritten as the winter plan (the hub is coming this winter); item 2, product-stack.md redrawn from the code, and it names the hub as coming this winter; item 4, README.md:101 points at sage.is/bonsai/ (step 1). Both docs went through a map, write and fact-check workflow, with the last seven findings applied by hand. Item 3 (backend-rewrite-research.md) stays open. Steps 3 to 5 now belong to the tests, UX and docs path with Alexander.

1. **`docs/community-hub.md`**: most of it was never built. Open cards need `COMMUNITY_HUB_URL` (`TODO.md:191`) and an allowlist reconcile (`TODO.md:195`). Choose between cutting it to the parts those cards need and retiring it. It is linked from `README.md:75,87` and `docs/bonsai/sprig-creator-program.md:115`.
2. **`docs/product-stack.md`**: the 2025-11 diagram is wrong on the ORM, storage, web search and ML stack. No card needs it. Choose between retiring it and redrawing a short current version. It is linked from `README.md:73` and `docs/README.md:20`.
3. **`docs/backend-rewrite-research.md`**: keep it; `TODO.md:1099-1102` holds the team review. Fix the two garbles from the uncommitted edit: the `## Why ` heading at :9, and ":27 As I when I completed this research is no Go or Rust…" (proposed: "When I finished this research, no Go or Rust equivalent…existed"). Refresh the counts: 65.4k LOC, 49 deps, 30 routers, and the file line counts. Drop the dead pgvector/psycopg2/Postgres-search claims and footnotes 2–4. Confirm the wording with Alexander, since the edit is his own work in progress.
4. **`README.md:101` Sprig Spec link**: the BONSAI repos are not pushed yet (`TODO.md:473`), so there is no public URL. Choose from: link `https://bonsai.sage.is` ahead of launch, link the sage.is explainer, or drop the link text until the push lands.

## Step 3 — Fix facts in living docs [WE]

Fix each item in place; the evidence is in the sweep tables.

- **`docs/troubleshooting.md`**: image `ghcr.io/sage-is/ai-ui`, volume `sage-ai-data`, port 8080. `AIOHTTP_CLIENT_TIMEOUT` unset means no timeout. The Ollama URL is in the Connections panel.
- **`docs/API-examples.md`**: the messages endpoint is `/{id}/messages/{message_id}`. Replace `/rag/api/v1/process/doc` with `/api/v1/retrieval/process/file`. Fix the single-quote `$SAGE_EMAIL` bug.
- **`docs/CONTRIBUTING.md`**: repo `Sage-is/AI-UI`, Discord `discord.gg/3BtwHkXS`, `app/src/lib/i18n/locales`. Replace "powered by Ollama" with any OpenAI-compatible provider plus Ollama.
- **`docs/SECURITY.md`**: repo link and product name. Semgrep runs through `make scan_sast`, not on every commit.
- **`docs/development-workflow.md`**: cut the `src/admin/config.yml` / CMS residue (:188-201) and the Django test residue (:433-443). Replace the README section list. Replace "This Week" with the real board sections. `make help_all` lists the gate targets. Add `distribution-chain-verify` to the hook list.
- **`docs/release-runbook.md:22`**: `_pin_server_tag` writes in place with `perl -i`.
- **`docs/try-sage-deployment.md`**: `configured` equals `bool(connections)` (:180). Add `make sprig_publish` to recovery (:283-289). Tool servers register conditionally (:5,136). Three analytics providers, not four. Fix the banner title, the persona labels and the `/openai` mount.
- **`docs/deploy-sage-startr-cloud.md`**: delete the shipped "Still remaining" list (:74-80). The catalogue has 19 packages, not 16.
- **`docs/apache.md`**: port 8080; drop the upstream branding at :214-216. It has uncommitted edits, so keep them.
- **`docs/orientation.md`**: five surfaces, stated once. `/welcome` has been replaced and `/home` hollowed. The wire route is `/pages/admin/sprigs/wire/{name}`.
- **`docs/no-build-surface-convention.md`**: the figures now come from `route-payload.cy.ts`. Update the surface and panel counts (19 panels, 21 templates).
- **`docs/bridges.md`**: Signal has shipped. The path is `sage_is_ai/bridges/`, and the tree should include `outgoing.py`. Channel is now Space, via `forward_space_message_to_bridges`.
- **`docs/file-handling-field-rules.md:80`**: drop `scanner/kanban.py` and `make sync_todos`. Point at the real KANBAN.canvas generator, found by grepping the Makefile at edit time.
- **`docs/sprigs/capabilities.md:12`**: thirteen divergences, not eleven.
- **`docs/CONVENTION.instructions.md` vs the root copy**: merge into the root file (a superset holding the Hidden Artifact, FastAPI ordering and Styling sections). Replace the docs copy with a one-line pointer, or hardlink it if Alexander prefers.

## Step 4 — Decisions index and line-number rot [WE]

- **Rebuild the `docs/decisions/README.md` index from disk.** Drop the 22 dead targets. Add the 24 unlisted records. Name `Rs_list.md`, `Ss_list.md` and `Rs_list original.md` as non-records. Fix `.gitignore:29` to `:44`. This is a mechanical rebuild, so delegate it.
- **Replace every `TODO.md:NNN` / `TODO.md#LNNN` citation with the card title.** This follows `docs/board-register-method.md:38`. Sites: the decision records (widget-mount, home-page, python-quality-gates, chat-path-tighten, import-seam), `charts/*` (chat-path-restructure, sprig-creator-program, friday-demo, rad-servers runbook), and the code comments `app/backend/sage_is_ai/utils/middleware.py:1258`, `pages/home_panel.py:14` and `scripts/smoke/chat-response-oracle.py:378`.
- **`central-intelligence-widget-mount.md`**: add a "superseded by `2026-08-08-hollowing-a-svelte-route.md`" line. Remove the dead `sage-integration-scope.md` reference in resident-agent. Fix the `Chat.svelte` path in home-starter. Replace the literal `…` links in raw-tool-call-form and chat-path-tighten.
- **`docs/completed-todos.md:346-347, 552, 556`**: fix the root-relative decision links. Drop the dead `server-tag-3.0.0-bump` link.

## Step 5 — Board drift [WE, confirm restores with Alexander]

- **`TODO.md:38`**: `default_external` is already ON (`config.py:987`); tick the card.
- **`TODO.md:581`**: AI-parsed ingestion has shipped (`CHANGELOG.md:526`); tick it.
- **`TODO.md:1016`, `docs/board-dossiers.md:318`**: the anchor is `#oauth-ux--identity-linking`.
- **`docs/board-dossiers.md:449`**: the card "Demo tenant reset — one task, not three" was deleted without archiving (commit `25589ee`). Ask whether to restore it to TODO.md or stub it in completed-todos.
- **Dossiers for completed cards** (:71, :503, :509, :515): mark them done or move them.
- The board already passes the 350-char register rule (max 349), so no register pass is needed.

## Verification [WE]

- **Links:** a Python link check over `docs/**/*.md`, `README.md` and `CHANGELOG.md` must report zero broken relative links. Exception: `board-dossiers.md`'s frozen root-relative history links, which stay out of scope and should be noted as known.
- **Makefile:** `grep -n` each Makefile target named in the edited docs against the Makefile and `make help_all`.
- **Sprig capabilities:** `make sprig_capabilities_check`, or the generator `--check`, still reports a match.
- **Kanban:** regenerate KANBAN.canvas per `docs/file-handling-field-rules.md` and confirm the board gates pass after the TODO.md edits.
- **Makefile hardlinks:** `stat -f "%l"` confirms the link count is unchanged after the Makefile comment edit.
- **Hand-off [MANUALLY]:** Alexander reviews `git status` / `git diff` and commits.

## Step 1 result (2026-10-03)

Run as a 14-agent workflow: three retire agents with disjoint file ownership, then three verify, refute and fix rounds. Uncommitted; Alexander commits.

- Gone: `docs/api-refactoring-plan.md`, `docs/knowledge-ingestion-modes-plan.md`, `docs/try-sage-docker-exploration.md`, `docs/env-scripts.md`, `docs/bonsai/sprig-spec-v1-draft.md`, `docs/bonsai/rootstock-spec-v1-draft.md` (git shows `D`; history keeps them).
- Links fixed: `README.md:101` now points at <https://sage.is/bonsai/>; `docs/README.md` lost three index lines and gained one for this plan; `docs/archive/README.md:40` names only `backend-rewrite-research.md`; the `Makefile` try.sage comment names only `docs/try-sage-deployment.md` (link count 1 before and after); `docs/development-workflow.md:325` carries the one true fact from env-scripts.md (`make setup_env` wraps `tools/setup_project_env.sh`); `charts/sprig-security/TODO.md:31` names the canonical `BONSAI/sprig-spec/v1.md` instead of the draft.
- Gate trim: `scripts/gates/docs-targets.allow` lost three rows (`try_sage_smoke`, `try_sage_stop`, `try_sage_build_n_start`) that only the retired exploration doc proposed; `scripts/gates/docs-targets.sh` comment reworded. The gate passes.
- Left as history, on purpose: `docs/completed-todos.md:416` and the gate comment still name the exploration doc as incident provenance.
- Verify: 140 relative links scanned, 30 broken, all pre-existing and all in step 2 to 4 territory (`SECURITY.md`, `backend-rewrite-research.md` pgvector, `completed-todos.md` root-relative links, `decisions/README.md` dead index, three decision records). The final `ok=false` came only from this plan file naming the six retired paths; both refuters upheld every factual claim.
