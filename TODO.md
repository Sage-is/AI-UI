# Roadmap

This file tracks active work only.

> Historical snapshots and completed bulk moved to `docs/completed-todos.md` and `docs/archive/` on 2026-04-09.
>
> **Convention** — Sections below map to kanban columns. Inline source-code
> tags use the same vocabulary so items stay cross-referenced between this
> file and the codebase. `KANBAN.canvas` auto-generates from this file and
> inline tags — do not hand-edit it.
>
> | Column      | Markdown section  | Inline tag  |
> |-------------|-------------------|-------------|
> | Backlog     | `## Backlog`      |             |
> | TODO        | `## TODO`         | `# TODO:`   |
> | In Progress | `## In Progress`  | `# FIXME:`  |
> | Bugs        | `## Bugs`         | `# BUG:`    |
> | Done        | `- [x]` items / `## Done` | —   |
>
> `# DEPRECATED:` tags should be tracked as TODO items for removal at the
> stated version.

---

## In Progress

_Items currently in progress. Move items here and or use tag source with `# FIXME:` when work begins._

- [ ] **DRY the fresh-boot test admin — one canonical credential, no drift** (Alexander, 2026-08-17: "Always avoid drift"): every harness that boots an EMPTY instance uses `admin@example.com`/`password`, defined once. #dx
  - [ ] Canonical source: `scripts/lib/test-admin.env` (`TEST_ADMIN_EMAIL`, `TEST_ADMIN_PASSWORD`, `TEST_ADMIN_NAME`).
  - [ ] Consumers: `scripts/smoke/sprig-lifecycle.sh` (drifted to `s8@sage.is`, 3 sites), `scripts/manual-check.sh` (re-point its defaults), `scripts/e2e/run-cypress.sh` (export as `CYPRESS_ADMIN_*`), `app/cypress/support/e2e.ts` (env first, canonical value as documented fallback).
  - [ ] The snapshot-backed gates KEEP their distinct `upgrade-gate@sage.is` on purpose — an injected row in a copy of production data must not collide with a real account and must self-attribute. Do not "DRY" them into the shared identity; say so in the env file.

- [ ] **Remove htmx; every consumer moves to startr-swap** (earmarked 2026-08-17): three admin panels still ride the 50.9 KB vendored `htmx.min.js` while the 11.9 KB in-house library carries every page-to-page swap — one engine, not two. #frontend #dx
  - [x] **Fragment question SETTLED by reading the source (2026-08-17, Alexander's call, verified)**: startr-swap already consumes fragments — `DOMParser.parseFromString(text, 'text/html')` wraps any fragment in a document, and `selectorFor` finds the region by `#id` in it. The panels' htmx `outerHTML` responses (wrapper included) are already the right shape. Today's `data-swap-off` exists only because the panels were never DECLARED as regions — `closest` resolved to the outer region, whose selector isn't in the fragment.
    - [ ] Mechanics that ARE the migration: mark each panel wrapper `data-swap` (ids stay); htmx buttons become real links or one-button forms (startr-swap claims only `a[href]` and `form`); `hx-vals` JSON becomes hidden inputs.
    - [ ] Semantic shift to check per panel: htmx `outerHTML` replaces the wrapper element, startr-swap replaces its CHILDREN — server-set attributes on the wrapper itself won't land.
    - [ ] No fragment fixture exists (`fixtures/swap/` holds full documents only) — add one so the behavior is pinned before the panels lean on it.
  - [ ] Consumers to migrate, each with its e2e spec green after:
    - [ ] Sprigs (`sprigs.html`, `sprigs_panel.py`): Refresh `hx-get`, per-card `hx-post` wire + verb actions, all targeting `#sprigs-panel`/`outerHTML`.
    - [ ] Diagnostics (`diagnostics.html`, `diagnostics_panel.py`): per-row Re-probe `hx-post` carrying `hx-vals` JSON — needs a plain-form equivalent (hidden inputs) — plus Re-probe-all `hx-get`, `#diagnostics-panel`.
    - [ ] Branding (`branding.html`, `branding_panel.py`): save form `hx-post`, `#branding-panel`; its `data-swap-off` becomes a live swap.
  - [ ] Delete the scaffolding: `vendor/htmx.min.js` plus its section in `vendor/README.md`; the three injection sites `router.py:373`, `:433`, `:1194`.
  - [ ] Re-word the prose that names htmx: `shell.py:191`, `sprigs_panel.py` and `branding_panel.py` docstrings, `router.py` comments `:497` and `:800`, `pages.css:274`, `color-pair.js` header — note its document-delegation pattern survives the engine change.
  - [ ] Cross-link: deleting the vendor file kills the bulk of the 9,609-error eslint card under Bugs — re-measure and update that card in the same sitting.
  - [ ] Guard rails: `startr_swap_check` still green; the panels' Cypress specs plus `make e2e` green; no third swap idiom — plain HTML first, per doctrine.

- [x] _Unused-import/local cleanup DONE (2026-08-17): 247 F401 + 36 F841 cleared, both rules enforced in `[tool.ruff.lint]` — the conservative set now runs whole; 214 auto-fixed, the rest read (2 availability probes kept: 1 `noqa` naming the sprig hot-graft rebind, 1 deleted); frozen migration trees (`migrations/versions/`, `internal/migrations/`) per-file-ignored, not edited; middleware's one line deletion (`negative_prompt`, dead since fork) re-pointed all 9 fences and 52 citations −1 in the same change. Archived → docs/completed-todos.md._ #gates

- [x] _Formatting consolidated on `ruff format` (2026-08-17): 87 files reformatted, oracle 12/12 byte-identical, `changelog_panel.py` AST-proven identical against a complexipy +8 artifact (baseline raised with note, not earned); `black --check` deleted from `lint`, `ruff_format_check` wired in; black survives ONLY as the runtime dep behind the `routers/utils.py` format endpoint. Found on the way: `lint`'s frontend half was already red — see Bugs. Archived → docs/completed-todos.md._ #gates

- [x] _`sage-archivo.ttf` subsetting automated (2026-08-17): committed 153 KB binary deleted; the watch Dockerfile now subsets `Archivo-Variable.ttf` at build time (`python3 -m fontTools.subset`, basic-Latin + em-dash, 92 KB, wght/wdth axes verified) via a named `fonts` build context; `WATCH_IMG` bumped `15.18.0-r2` so cached images rebuild themselves. Archived → docs/completed-todos.md._
---

## TODO

- [ ] **Converge the two deployed instances**: `try-sage-is` vs `sage-startr-cloud` #critical
  Both run `ghcr.io/sage-is/ai-ui:3.1.0` on the same host (openco2), yet their runtime
  state differs materially. Surfaced 2026-08-15 during an infrastructure backup audit.
  - [ ] `try-sage-is` carries **5.4 GB** of sprig-installed `ml_packages` (190 packages);
        `sage-startr-cloud` carries none. Establish which is intended.
  - [ ] Storage shapes differ: `try-sage-is` uses a docker volume, `sage-startr-cloud`
        a bind mount into `/root/Sync`. Pick one.
  - [x] If both need the same wheels, evaluate a shared read-only wheelhouse volume —
        feasible since both run on the same node, and pays the 5.4 GB once not twice.
  - [ ] Mark `ml_packages` and `cache` as regenerable so infrastructure backups can
        exclude them (they are ~36% of one node's nightly backup today)

### Real-estate segment engagement — first paid deployment (opened 2026-07-30)

_The first paid real-estate deployment of AI-UI, and deliberately the beachhead for a real-estate vertical rather than a one-off. Client identities, commercial terms, dates, and the external commitment live in [.clients.md](.clients.md) — untracked by design (`.gitignore:3` denies dotfiles), so that link is dead in a fresh clone and is meant to be. **Codenames only in this file:** **Realtor R** (the customer), **School B** (the prior demo tenant whose data is still on try.sage.is), **Reviewer T** (internal reviewer). Never write a real client name into a tracked file._

**How success is measured here** — the customer's own definition, and worth adopting as the segment's: (1) their assistant and VA stop having to ask the principal things, (2) hours back in the principal's week. They explicitly rejected "deals closed" (market forces dominate; attribution is fiction) and "nothing falls through the cracks" (humans stay in the loop and humans drop things). We measure what the software determines and nothing more. Any dashboard or report we build should hold that line.

**Shape of the delivery** — configs lead, code follows: ship value as Agents, prompts, knowledge bases, and Spaces configuration first; add features only where configuration genuinely cannot reach; then package the whole arrangement as **autoconfig Sprigs** so the next agent in the segment is a graft rather than a rebuild. That last step is what makes this a beachhead instead of a consulting job.

**Chart** — the **Monday 2026-08-10, 13:00** kickoff and product tour is charted separately at [charts/friday-demo/TODO.md](charts/friday-demo/TODO.md): ten decision cards, four on the frontier, decision records under `docs/decisions/`. That chart decides which no-build work rides the pre-demo deploy; it does not reorder the migration.

#### Week one — demo on try.sage.is

- [ ] **Reviewer T's bottom-of-page cutoff**: the `--pos:fixed` 100vh flex-centered layer hid content behind mobile browser chrome and off both scroll ends — reproduced on 3.0.0, fixed 2026-08-03 by migrating the surface. ([dossier](docs/board-dossiers.md))
  - Fix: server-rendered no-build page (`pages/try_sage_panel.py` + `try-sage.html`, 4.6 KB first response) — normal flow, `100dvh`, safe-area inset, overflow-safe `margin:auto` centering.
  - `TrySageWelcome.svelte` deleted; anonymous `/` answers server-side only when `ENABLE_TRY_SAGE` is on, other deploys untouched.
  - Guard-rail `try-sage-welcome.cy.ts` asserts phone-viewport scroll + flag-off inertness; `ENABLE_TRY_SAGE` passthrough added to the e2e + manual-check harnesses.
- [ ] Turn on Spaces access for Realtor R.
- [ ] Diagnose the unresponsive Space Agent via `/admin/diagnostics`. Actionable as of 2026-08-03 — the diagnostics page (2.3.3) and how-to-fix modals (2.3.4) are now live on try.sage.is.
- [ ] **Decide the trial model set and who pays for the tokens.** Undecided as of 2026-07-30 and it gates the instance provisioning below. Note the hidden Groq connection on try.sage.is is uncapped per user, and three people will share this workspace.
- [ ] **Day-in-the-life walkthrough — staged and labelled as staged**: the proactive beats are outbound-on-a-schedule and **there is no job scheduler** — do not let "does it do that by itself?" get a soft answer.
  - The Telegram adapter (`bridges/adapters/telegram.py`, the most mature at 505 lines) carries the demo.
  - The only `scheduler` hits in the backend are the AUTOMATIC1111 diffusion sampler.
  - [ ] Trigger the beats (weather, stretches, reminders) by hand.
  - [ ] Say out loud that they are staged, and show the queue on the roadmap.

#### Discovery — before any tooling is designed

- [ ] **Establish rung one of the responsibility ladder.** Nobody knows yet which task comes off his plate first, and the ladder is unbuildable without it. Candidates raised: inbox triage and drafting, listing/client paperwork, follow-up tracking.
- [ ] **Assess whether documented SOPs exist**; if not, introduce TodoScope as the lightweight starting point. This is the input to everything above.
- [ ] **Map the real system landscape:** a CRM, the regional MLS, Google Sheets, Airtable, and a great deal of phone/WhatsApp/memory. There is no single system of record, which means the first build is probably capture rather than integration. MLS access is typically licence-restricted — establish early whether we may touch it at all.
- [ ] **Settle the WhatsApp question**: currently mis-framed as "explore" — the bridge already shipped in 2.0.0, so there is nothing to evaluate.
  - Shipped: `bridges/adapters/whatsapp.py`, 291 lines, webhook-driven, HMAC-SHA256 verified, full runbook in `docs/bridges.md`.
  - [ ] Decide (a) whether Spaces already covers the internal case and makes the bridge unnecessary.
  - [ ] Decide (b) whether it is client-facing.
    - [ ] If client-facing on his business number: WAHA is unofficial and carries ban risk on the number his livelihood runs through — that risk conversation happens **before** we provision.
  - [ ] If we do proceed: provision a WAHA sidecar container, a phone number, and a public HTTPS webhook.
    - try.sage.is is a single-app CapRover deploy with no sidecar beside it, so this is infra provisioning, not a config toggle.
- [ ] **Establish the brokerage's position on email.** Their shared admin and tech staff own it. Any mail-side integration needs their cooperation and may simply be refused — better to know before it is designed in.
- [ ] **Replace the floating delivery milestone with a real anchor.** The "4-month" figure was the customer's own arbitrary soon-ish and cannot be met or missed as written.

#### Dedicated instance — after the demo

- [ ] **Provision Realtor R his own instance rather than leaving a paying customer on the shared demo box.** Decided 2026-07-30. Solves three problems at once: recurring tenant cleanup, uncapped shared spend, and his working data sitting beside strangers'.
- [ ] Migration path for anything he creates on try.sage.is between the demo and the cutover.
- [ ] **The social push escalates this from tidy-up to pre-launch blocker**: before the announcement, migrate Realtor R off the shared box, or cap spend, or both — not covered by any marketplace item. #critical
  - The push drives open-source self-installers at try.sage.is — the same shared box holding a paying customer's working data.
  - All three problems above get worse at once: tenant cleanup, uncapped shared spend, and his data sitting beside strangers'.
  - Spend budgets are item 2 in the `#### Platform unlocks` sequence, which the marketplace quarter slice already depends on.

#### Platform unlocks pulled forward by this engagement

All four were backlog items before 2026-07-30 and are now customer-blocking. **Sequence them; do not run them in parallel.**

- The no-build strangler migration is mid-Phase 2 with the wizard (the hardest surface) still ahead; stalling it half-migrated is the worst available outcome.
- The external November commitment is signage and materials only, so it imposes **no ship-by date** and must not be used to justify parallelising these.

- [ ] **1. Spaces multi-user** — three people (principal, assistant, VA) share one workspace from day one, and the customer's primary success metric is unreachable without it. Highest value, do first. Extends `### v2.x — Near Term` → _Spaces Enhancements_.
- [ ] **2. Spend budgets per user AND per API key** — required before a customer instance goes live with hosted models and three sharers. See the backlog item; the try.sage uncapped-Groq note there is now a live commercial exposure, not a hypothetical.
- [ ] **3. Sprig catalog de-hardcoding (marketplace M1)** — prerequisite for shipping the tooling as autoconfig Sprigs, and therefore for the segment story rather than just this customer. The blocker is the hardcoded Python `CATALOG` in `supervisor.py`.
- [ ] **4. Job queue** — last on purpose. The demo is staged-and-labelled and November needs no software, so nothing forces real proactive nudges until the configs and features have landed. Promote it when a staged beat has to become a real one.

### Test suite throughput

- [ ] **Run the e2e suite concurrently** (Alexander, 2026-08-09): `make e2e` is **4m51s for 46 specs / 233 tests** serially against one container, the gate between every change and confidence — its wall-clock is a tax on every iteration. #dx #tooling
  - [ ] As many specs in parallel as the harness allows.
  - Cypress supports parallel spec execution; the blocker is shared state rather than the runner.
  - `scripts/e2e/run-cypress.sh` boots ONE rootstock on one volume, and signup hard-closes after the first admin — two specs racing to seed the same instance is a data race, not a speed-up.
  - [ ] Shape that works: probably N containers on N volumes with the spec list partitioned — also what lets `e2e_both` stop costing double.
  - [ ] Measure the serial baseline per spec first — partitioning by duration matters more than by count.
    - `setup-dialog` 21s, `wizard-welcome` 33s and `setup-navigation` 25s are a third of the run between them.

- [x] _Favicon gate rot fixed (2026-08-09): `sprig-lifecycle.sh:224` asserted a favicon deleted deliberately on 2026-08-02, so `sprig_smoke` sat at 65/66 and the pre-push `gauntlet` refused every push while checking nothing true; now asserts the three icons `app.html` actually links — 68 passed, 0 failed. The lesson: a gate naming a file is a gate that outlives the file. #dx #tech-debt. Archived → docs/completed-todos.md._

- [ ] **Derive the icon check from the markup**: the favicon-gate fix swapped one hardcoded filename for three, which rots the same way — just later. #dx
  - [ ] Read every `/static/icons/X` out of `app/src` and `site.webmanifest` and assert each is served. Same shape as `scripts/gates/docs-targets.sh`.
  - [ ] Adding an icon enrols it, deleting one retires it, nothing to remember.
  - [ ] Cover the two PWA manifest icons (192×192, 512×512) — never checked by any gate; a missing one breaks install silently.

### Repo Hygiene & Security

- [ ] **Community-share leak + dead wiring**: fix the leak and the dead wiring the flag currently hides before `ENABLE_COMMUNITY_SHARING` goes back on for the sharing site (~2 weeks out) (Switch 1 of the 2026-08-15 poka-yoke resolution). #security #critical ([dossier](docs/board-dossiers.md))
  - [ ] Every model Share click sent the full model record — `params.system` included — as a query string to a public request bin, live since the initial commit with the flag defaulted on.
  - [ ] Scope: try.sage.is (3.0.0) and every deployed instance.
  - [x] Done today: flag default flipped to `False` (`config.py:1471`); the two share buttons that ignored it gated (`FunctionMenu.svelte`, `Feedbacks.svelte`) — a mask, not a fix; flag-on re-arms everything below.
  - [ ] Full evidence in `charts/sprig-creator-program/TODO.md`.
  - [ ] [MANUALLY] Treat as an incident first: check whether the bin captured traffic and rotate anything a shared system prompt disclosed — before any code fix.
    - [ ] `Models.svelte:105` points at `https://webhook.site/93a1d2e8-5b27-44c4-8493-0f915cad92c5`.
    - [ ] The size guard at `:108` tests `knowledge_base`, a field a model object does not have, so `isLarge` is always false and the URL-query branch always runs.
  - [ ] [WE] Replace the webhook.site URL; fix or delete the dead `knowledge_base` guard.
  - [ ] [WE] Add `COMMUNITY_HUB_URL` as a `PersistentConfig`; replace the ~9 hardcoded `https://sage.is` literals.
    - [ ] Literals: `Prompts.svelte`, `Models.svelte`, `Functions.svelte`, `ShareChatModal.svelte`, `Feedbacks.svelte`, `prompts_panel.py`, `agents_panel.py`.
  - [ ] [WE] Build or drop the missing destination pages (`/prompts/create`, `/models/create`, `/functions/create`, `/chats/upload`, `/leaderboard`) — four of five soft-404, so Share toasts success and does nothing.
  - [ ] [WE] Reconcile the handshake word: doc says the hub posts `ready`, every listener waits for `loaded`.
  - [ ] [WE] Reconcile the postMessage allowlist: community.sage.is in none of the three; localhost port disagrees 5173 vs 9999.
  - [ ] [WE] Do not ship `function` or `tool` share types at launch.
    - [ ] A shared Function is unsandboxed RCE (`exec` server-side, `new Function` browser-side).
    - [ ] A shared tool with `auth_type: "session"` exfiltrates each caller's JWT to the publisher.
  - [ ] [WE] Add a `source`/`origin` field to shared items so a bad one can be enumerated and revoked — no incident response without it.
- [ ] **Repo-wide hidden-artifact allowlist rollout**: Deny dotfiles and dotfolders everywhere in the repo by default; explicitly include only approved shared hidden artifacts so local state cannot drift into git by accident.
  - _Implemented: `.gitignore` allowlist, contributor approval rule in `CONVENTION.instructions.md`, `!.*.example` template allowlist, included/excluded verification. Archived 2026-08-15._
  - [ ] Review currently tracked hidden artifacts and remove any that should be excluded going forward

- [ ] **CSP-configured gate**: assert a CSP is set — an unset header and a deliberate omission look identical to the process (charted 2026-08-15 in the poka-yoke pass). #security #critical ([dossier](docs/board-dossiers.md))
  - [ ] `CONTENT_SECURITY_POLICY` is unset in `.env.example`, the `Dockerfile`, `docker-compose.yaml`, and `distribution.env`.
  - [ ] `SecurityHeadersMiddleware` (`main.py:1473`, `utils/security_headers.py::set_security_headers()`) builds headers purely from env vars.
  - [ ] `routers/diagnostics.py:610` already grades the absence "degraded" — the system knows and cannot stop anything.
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
- [ ] **Neuter the `execute` event branch, do NOT delete it**: `Chat.svelte:382-395` runs server-supplied code through `new Function(...)` in the top frame, unsandboxed (Note 1 of the 2026-08-15 poka-yoke resolution). #security #critical ([dossier](docs/board-dossiers.md))
  - [ ] Deletion refuted by adversarial verification: it looks dead — nothing in the repo emits `"execute"` — but that was the wrong test; it is public extension-API vocabulary reached through two unfiltered forwarders.
  - [ ] Forwarder 1: `middleware.py:1782-1784` forwards any event a configured upstream model, Pipe, or stream Filter puts in the SSE body.
  - [ ] Forwarder 2: `routers/chats.py:522-552` (`EventForm{type,data}`, `get_verified_user` only) forwards any event from a REST client or API key — and `ENABLE_API_KEY_ENDPOINT_RESTRICTIONS` defaults False.
  - [ ] The CSP child above closes the same hole browser-side — belt-and-braces, do both, ship whichever lands first.
  - [ ] Keep the arm, refuse to call `new Function`, always invoke `cb` so callers get a response.
  - [ ] Trap: deleting the branch breaks `__event_emitter__` callers silently and hangs `__event_call__` callers for 60s — the fallthrough `else` never invokes `cb`.
- [ ] **HTMLToken raw-text invariant — document and gate it, do NOT "fix" the asymmetry** (Note 2 of the 2026-08-15 poka-yoke resolution): branching on `html` silently breaks five features, not three. #security #bonsai ([dossier](docs/board-dossiers.md))
  - [ ] `HTMLToken.svelte:17` computes `html = DOMPurify.sanitize(token.text)`, but the iframe / `<file>` / `<status>` / `<source_id>` branches (lines 55, 72, 87, 105, 123) test raw `token.text` on purpose.
  - [ ] DOMPurify's stock profile removes `<iframe>` with its contents (`ALLOWED_TAGS` omits it, `DEFAULT_FORBID_CONTENTS` includes it) and erases the four custom tags (no hyphen, so the custom-element regex rejects them).
  - [ ] The invariant: every raw-text branch either pins its origin or renders with bare `sandbox` (the generic branch, whose `src` is unvalidated).
    - [ ] YouTube hardcodes `youtube.com/embed/` + an 11-char id regex; file uses a same-origin admin-gated endpoint.
  - [ ] One comment at line 17 stating why `html` is only for `<video>`/`<audio>`.
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
- [ ] **Coordinated langchain major bump**: bump the langchain/langchain-community/langchain-core trio (rag-loaders Sprig™ side) past 0.3.x to drop the `CVE-2026-34070` suppression.
  - [ ] `.trivyignore` suppresses `CVE-2026-34070`: path traversal in `langchain_core`'s legacy `load_prompt()`, unreachable in this codebase — see `.trivyignore` comment.
  - [ ] The fix (`langchain-core==1.2.22`) needs `langchain-core<1.0.0` dropped, which both pinned sprig-side packages require (`langchain==0.3.30`, `langchain-community==0.3.27`, `app/backend/requirements.txt:51-56`).
  - [ ] Plan and test the coordinated bump, then remove the `.trivyignore` entry.



### OAuth UX & Identity Linking

- [ ] **OAuth identity linking v1**: let users attach Google/GitHub/Microsoft to existing accounts whose email doesn't match the provider's email; decisions confirmed in plan thread 2026-05-28 ([dossier](docs/board-dossiers.md)).
  - [ ] The only graceful path today is `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` — silent email-match linking, useless when the local email differs from the provider's.
    - [ ] Also an account-takeover footgun if email control is weaker than account control.
  - [ ] Scope: build Patterns A + B, lift the one-provider-per-user schema limit, harden the admin controls with Poka-Yoke devices.
  - [ ] **Schema lift to multi-provider stacking**: migration ships before any UX work.
    - [ ] Replace single `oauth_sub TEXT UNIQUE` with per-provider `UNIQUE` columns `google_sub`, `github_sub`, `microsoft_sub` (+ `apple_sub` when Apple lands).
    - [ ] Generic `oidc` keeps `oauth_sub` as catch-all.
    - [ ] Rewrite every `user.oauth_sub` callsite to `Users.get_user_by_oauth_sub(provider, sub)`.
  - [ ] **Pattern A — Settings-driven link/unlink**: Account Settings → "Connected providers" lists each linked provider with an unlink button, plus Connect buttons for the rest.
    - [ ] OAuth round-trip carries a session-bound `state` token; callback attaches `<provider>_sub` to the already-signed-in user.
  - [ ] **Pattern B — OAuth-first claim flow with magic-link verify**: no oauth_sub or email match → redirect to `/auth/claim?provider=google&sub=...&temp=<token>` instead of 403 or auto-create.
    - [ ] User enters their AI-UI email; the magic link attaches the identity.
    - [ ] No-existing-account branch goes to a separate create flow gated on `ENABLE_OAUTH_SIGNUP` + allowlist policy.
  - [ ] **Per-provider link mode** (replaces global `OAUTH_MERGE_ACCOUNTS_BY_EMAIL`): each provider gets `<provider>_link_mode`.
    - [ ] Modes: `silent_merge_by_email` (current behavior), `verify_via_magic_link` (Pattern B pipeline), `disabled` (Pattern A only).
    - [ ] Fresh-install default: `verify_via_magic_link` if SMTP is configured, else `silent_merge_by_email` with a save-time warning.
    - [ ] Migration: `OAUTH_MERGE_ACCOUNTS_BY_EMAIL=True` → all providers `silent_merge_by_email`; `=False` → `disabled`.
    - [ ] Global toggle stays as fallback one major version, then drops.
  - [ ] **Replace raw 403 with a real status page**: redirect `handle_callback` failures to `/auth/status?reason=<signup_disabled|allowlist_blocked|domain_blocked|role_pending|email_taken>&email=<masked>`.
    - [ ] Replaces `HTTPException(403, ACCESS_PROHIBITED)` at [utils/oauth.py:508-511](app/backend/sage_is_ai/utils/oauth.py#L508); API surface keeps the 403 for programmatic clients.
    - [ ] Frontend route renders branded copy + "request approval" CTA (mailto or webhook).
    - Copy: `signup_disabled` → "no account at <site name>" + "Request access" button.
    - Copy: `role_pending` → "being reviewed" + existing pending UX; OAuth signup auto-creates awaiting approval — `DEFAULT_USER_ROLE=pending` IS the poka-yoke, don't bypass it.
    - Copy: `domain_blocked`/`allowlist_blocked` → "not on the allowed list, talk to your admin".
  - [ ] **Per-provider allowed-domains policy** (replaces global `OAUTH_ALLOWED_DOMAINS`): each provider block gets `<provider>_allowed_domains`.
    - [ ] Example: Google `@openco.ca` only while GitHub stays open, Microsoft `@school.edu, @school.k12.org`.
    - [ ] Provider blocks already exist at [config.py:316-700](app/backend/sage_is_ai/config.py#L316); extend with the domain field.
  - [ ] **Per-user OAuth allowlist**: `oauth_eligible BOOLEAN DEFAULT True` on the user record plus per-provider overrides (`google_allowed`, etc.).
    - [ ] Lets a workshop lock to the invited cohort even when the domain allowlist matches.
    - [ ] Default is eligible; restrictive mode is one toggle.
  - [ ] **Save-time Poka-Yoke on admin OAuth config**:
    - [ ] Refuse to save `ENABLE_OAUTH_SIGNUP=True` with empty/wildcard allowed-domains without an explicit "I understand this is open registration" confirmation toggle.
    - [ ] Treat an empty allowed-domains list as "no one" (fail-closed), not "everyone" (fail-open).
    - [ ] Block enabling Pattern B when SMTP isn't configured — the magic link would never arrive. Inline error: "Configure email first (Settings → Email)."
    - [ ] Inline preview after each field change: "With current settings, the following can sign up: Google @openco.ca only; GitHub open to allowlisted users only."
  - [ ] **"Simulate sign-in" admin diagnostic** — highest-leverage Poka-Yoke: admin pastes an email + picks a provider; system shows the end-to-end outcome with no DB changes.
    - [ ] Outcomes: "Would link to existing user X" / "Would create new pending user" / "Would 403 — not in domain allowlist" / "Would 403 — user not on per-user allowlist".
    - [ ] Catches misconfiguration before a real user hits it.
  - [ ] **i18n** all new user-facing copy (status pages, claim flow, settings labels).
  - [ ] **Audit log** entry on every link/unlink event: `(timestamp, user_id, provider, sub, action, actor)` — admin or user.
  - [ ] **Migration safety**: migration populates the typed columns from existing `oauth_sub = "google@..."`.
    - [ ] Old field stays nullable one release for rollback, removed in N+1.

### Release Wrap-Up

- [ ] **`make caprover_app_create APP=<name>` wrapper**: one Makefile call to register a new CapRover app via the HTTP API — avoid the dashboard click-through we did for `try-sage-is` on `captain.example.com` 2026-05-01.
  - [ ] Register via `/api/v2/user/apps/appDefinitions/register`.
  - [ ] POST the env-var block.
  - [ ] Set the persistent volume path.
  - [ ] Connect a custom domain.

- [ ] **Port `sharded-zooming-parrot` Poka-Yoke release plan to this Makefile**: make `_it_build_multi_arch_push_GHCR` safe to re-run after a partial failure; build the tag from a throwaway worktree. Plan: `~/.claude/plans/sharded-zooming-parrot.md`. ([dossier](docs/board-dossiers.md))
  - [x] _Post-push GHCR manifest verify SHIPPED 2026-07-19 — fixture 3/3, `verify_ghcr_manifest` + `manifest_verify_fixture` gate the SERVER_TAG pin. Sub-essay archived 2026-08-15 → `docs/completed-todos.md`._
  - [ ] **The release builds whichever branch you are standing on, not the tag (2026-08-11)**: fix — build the tag from a throwaway `git worktree`. #critical
    - [ ] A worktree build is reproducible from the tag, immune to local edits and branch position.
    - [ ] `finish_flow` ends on `git checkout develop`; `release_and_push_GHCR` builds on the next line — `org.opencontainers.image.revision` stamps develop's HEAD while `v$(VERSION)` names master's merge commit.
    - [ ] 3.1.0 trees differed by 7 files, 2845 deletions, so the tag does not reproduce the image; publishing 3.1.0 honestly needed a hand-typed `git checkout master`.
  - [ ] **The 2.3.0 driver recurred verbatim in 3.1.0 (2026-08-10)**: second occurrence of a known, carded failure mode. #critical
    - [ ] 2.3.0: buildx OOMed mid-push — tag on origin with no GHCR image.
    - [ ] 3.1.0: `release_finish` pushed tag `v3.1.0`, then the build failed — tag published, no matching GHCR image, the exact state this card was opened for.
    - [ ] Recovery was hand-driven: `it_build_multi_arch_push_GHCR`, then `verify_ghcr_manifest`, then `_pin_server_tag`.
  - [x] _Multi-arch `bun install` contention FIXED 3.1.0 (2026-08-10) — `sharing=locked` BuildKit cache mount on bun's cache in `Dockerfile`; 940 tarballs, 21s solo vs 181s contended, second arch reads warm cache in 31s; `ensure_builder --use` fixed, cache wipe now opt-in via `CLEAN_BUILD=1`; reads as a network flake and is not one. Archived → docs/completed-todos.md._
  - [ ] **`wizard_smoke` cold-cache false-fail (2.3.2, 2026-05-29)**: 15-min `INSTALL_TIMEOUT_SEC` too short for ~5 GB wheels + ~2 GB embedding model — evaluate, any removes the failure at the root:
    - [ ] Smoke false-failed on residential bandwidth while uv downloaded and `models/status` showed `error: null`.
    - [ ] `SKIP_SMOKE=1` is NOT poka-yoke; until a root fix ships, a cold-cache false-fail blocks the release — the gate doing its job.
    - [ ] Bake uv wheel cache + embedding model into the smoke image at build time (image grows ~5-7 GB; smoke turns deterministic, runs in minutes).
    - [ ] Move smoke to the staging CapRover app once it exists (datacenter bandwidth; ties into the 2.3.3 staging-smoke design).
    - [ ] Make smoke resumable across container restarts.
  - [x] _One release door SHIPPED (2026-08-12) — `make ship` is the only public publish path, hotfixes included; internals `_`-prefixed with no `##`; deleted `scripts/release.sh`, `release:` + 5 dead targets; GHCR pair collapsed into `_release_and_push_GHCR`; `docs_gate` caught all 4 stale doc references. Archived → docs/completed-todos.md._
  - [x] _`release_preflight` SHIPPED (2026-08-12) — 4 outside-world checks before `release_smoke`: `gh auth status`, docker reachable ≥8 GiB (`RELEASE_MIN_DOCKER_GIB`), `v$(RELEASE_VERSION)` not on origin, `## [X.Y.Z]` in CHANGELOG.md; origin-tag check alone catches both 2.3.0 and 3.1.0. Archived → docs/completed-todos.md._
  - [x] _Lightweight tags unpublishable (2026-08-12) — `scripts/hooks/no-lightweight-tags.sh` on pre-push via `gauntlet_fast`, teeth 4/4, judges only unpushed tags; `v3.1.0` re-cut annotated (`git tag -f -a` + force push, no delete); `v2.0.0` stays lightweight. Archived → docs/completed-todos.md._
  - [x] _`make help` scans `##` SHIPPED (2026-08-12) — awk scan of `## ` comments, 29 documented targets annotated up to 71; `make help_all` keeps the full 137-name dump; `_`-prefixed targets cannot appear. Archived → docs/completed-todos.md._
  - [ ] **Both ratchets are unrunnable on a fresh clone (2026-08-12)** `#critical`: `cognitive_complexity` and `chat_path_structure` hard-fail "no baseline" on every clone and CI runner, and `make lint` fails with them.
    - [ ] `.gitignore:31` excludes `/scripts/gates/*/baseline.json` and none was ever committed.
    - [x] Bootstrap circularity FIXED (2026-08-17): `--tighten` now seeds all six ceilings from scratch and warns that fences are authored by hand, never generated. Proven live — the chat-path baseline was lost locally and rebuilt through this path (ceilings via `--tighten`, nine fences re-authored from the 2026-08-05 census, gate + relocate + teeth all green).
    - [ ] Baselines stay out of git (Alexander, 2026-08-12); `chat_path_structure_teeth` stays in `gauntlet_fast`.
    - [ ] Remaining: either track the baselines or drop the ratchets from every rollup — a fresh clone still starts fence-less, and ceilings seeded from a regressed tree bless the regression.
  - [x] _`gauntlet_fast` + one hook mechanism (2026-08-12) — pre-push runs `scan_tree` + `gauntlet_fast`, green in 8.3s; deleted `.githooks/`, which `.gitignore:3` kept out of git so `Makefile:633`'s recommended hooksPath silently disabled all 5 pre-commit stages on a fresh clone; 4 `_teeth` gates now run for the first time. Archived → docs/completed-todos.md._
  - [x] _`gauntlet_full` runs from clean (2026-08-12) — declared `it_build` on the 12 targets consuming `$(IMAGE_NAME):$(IMAGE_TAG)` instead of reordering, so position carries no meaning; phony, so one build (dry run: build line 14, first consumer 28); `scan_container` joins `gauntlet_full`, NOT `scan`. Archived → docs/completed-todos.md._
  - [x] _`parity_gate` removed from `gauntlet_full` (2026-08-12) — exits 0 when its multi-gigabyte GGUF artifacts are absent, so it reported success forever and the Korean-probe canary watched nothing; run it on a llama.cpp tag bump; `GATE_STRICT=1` draft dropped. Archived → docs/completed-todos.md._
  - [x] _Version copies cut 5→3 (2026-08-12) — README heading now a shields badge reading origin's tags (zero writers); `bump_release_version`'s README rewrite removed in the SAME change (a match-less `re.sub` writer silently no-ops); unreachable `$(or $(SERVER_TAG),latest)` arm deleted; SERVER_TAG = PUBLISHED, IMAGE_TAG = BUILT — never compare them. Archived → docs/completed-todos.md._
  - [x] _Pre-push hooks inert on tag pushes fixed (2026-08-12) — pre-commit skips every hook on a no-new-commit ref range (seen on the `v3.1.0` repair: 8 hooks Skipped, `tags_annotated` among them); `always_run: true` on `scan-tree` + `gauntlet-fast`, proved in sandbox on an empty range. Archived → docs/completed-todos.md._
  - [x] _`distribution_verify` could not fire, could not pass (2026-08-12) — two mutually-hiding defects: `files:` gate never triggered on a no-content hardlink break, `expected_links` 2 failed sibling-less clones; fixed both, `always_run: true`, into `gauntlet_fast`. Superseded 2026-08-13: hardlink and link counting gone. Archived → docs/completed-todos.md._
  - [ ] **Dependency-CVE scanning belongs on CI loop, not commit hook** (deferred 2026-08-12): keep the hook as lockfile early warning; stop counting it as CVE coverage.
    - [ ] `audit-deps` gates on `files: (bun\.lock|requirements\.txt)$`, so a CVE against an untouched dependency never triggers it — the normal case.
    - [ ] `always_run` is the wrong device (trivy every commit, staleness untouched).
    - [ ] Schedule `make scan_deps` + `scan_container` on a CI runner (see Gitea-vs-Woodpecker).
  - [x] _`docs_gate` reads doc trees outside the repo (2026-08-12) — roots are DATA in `scripts/gates/docs-targets.roots` (gitignored, tracked `.example`; `~` and `%REPO_SLUG%` expand at run time), absent roots announced not silent; now in `gauntlet_fast` with `docs_gate_teeth`, self-test 6/6 — caught its own vacuous pass first run. Archived → docs/completed-todos.md._
  - [x] _`distribution_verify`/`distribution_heal` unified on one `DIST_LINK_PRELUDE` (2026-08-12) — two opposite-direction link-count derivations and two open-coded BSD/GNU `stat` fallbacks collapsed; heal fixture still 7/7. Archived → docs/completed-todos.md._
- [ ] **Tri-repo Jidoka (自働化) + Poka-Yoke (ポカヨケ) for the publish flow**: Bootstrap shipped in 2.3.1; the render layer and commit-hook checks are still open. Plan at `~/.claude/plans/given-our-newest-trends-modular-sloth.md`. ([dossier](docs/board-dossiers.md))
  - [x] **Source of truth** — `distribution.env` hardlinked across all three repos (CLI_VERSION, SERVER_TAG, IMAGE, VOLUME, DATA_MOUNT, WAITLIST_URL). `make distribution_sync`/`distribution_verify` in each repo's Makefile; `release_finish`/`hotfix_finish` gated on verify.
  - [x] **Bootstrap order** — homebrew-apps (canonical volume + `--tag` on `ai-ui start`/`try`/`update`), AI-UI (Makefile reads `distribution.env` for VOLUME_DATA + IMAGE_TAG defaults), Sage.Education-docs (Makefile reads `distribution.env`, `distribution_sync`/`verify` targets) — all wired.
  - [x] **Cross-repo workflow doctrine** — homebrew-apps README states `git flow feature start <name>` policy. AI-UI and docs README updates land with the docs-repo install pages.
  - [ ] **Poka-yoke** — pre-commit hook in each repo refuses commits whose declared image/volume/version conflict with `distribution.env`; installed via `make install_dev`. Wrong values can't reach the index.
    - [x] _AI-UI hardlink chain self-healing (`make install_hooks`: pre-commit `distribution_verify`, post-checkout/merge/rewrite `distribution_heal`), landed 2.3.3. Archived → docs/completed-todos.md._
    - [x] **OBSOLETE (2026-08-13)** — no chain to heal. Sibling needs a `distribution_verify` equivalent, not a healer. Reduced to: give homebrew-apps and Sage.Education-docs the same 4-line `cmp` check.
  - [x] _Hardlink retired 2026-08-13 `#poka-yoke`: ~155 lines of healer/arbitration replaced by 11 — `distribution_sync` copies out, `distribution_verify` asserts byte-equality; no owner declared, divergence reported and reconciled by hand; all three repos now 1 link, sha `69754e40`. Archived → docs/completed-todos.md._
  - [x] _Three silent failures in the replacement caught 2026-08-14 `#poka-yoke`: `_pin_server_tag` printed success with no match (now asserts result via `grep -qx`), `distribution_verify` passed on zero comparisons (now prints the count), `distribution_sync` skipped absent peers silently (now names each peer). Four lines, proved both directions. Archived → docs/completed-todos.md._
  - [ ] **Jidoka render layer** — `make sync-from-distribution` in each repo regenerates templated docs/formula/Makefile fragments from `distribution.env`; `release_finish` runs it on the two siblings before tagging and halts with the diff printed if any sibling's working tree turns dirty.
  - [ ] **Docs render** — Docusaurus install commands and version strings pulled from `distribution.env` (remote-content plugin or build-time include); brew formula caveats and the AI-UI README install section regenerated from the same templates.
- [ ] **`ai-ui` brew formula self-manages a launchd service**: the `homebrew-apps` formula ships a complete LaunchAgent plist so `brew services start ai-ui` (or `ai-ui start`) brings the container up at login, restarts on crash, and survives shell exit. ([dossier](docs/board-dossiers.md))
  - [ ] No hand-patching `~/Library/LaunchAgents/*.plist` — stock `cloudflared` proved the trap 2026-05-19.
    - [ ] Its plist omits the subcommand from `ProgramArguments`, so it exits 1, KeepAlive retries forever, brew shows `error 1`.
    - [ ] `brew upgrade` silently overwrites the hand-patched fix.
  - [ ] Bake the plist template into `ai-ui.rb` / `ai-ui@1.rb`'s `service do` block
    - [ ] Full `ProgramArguments`: binary + `start` subcommand + the container-launch flags
    - [ ] `KeepAlive { SuccessfulExit=false }`, `RunAtLoad=true`
    - [ ] `StandardOutPath`/`StandardErrorPath` → `/opt/homebrew/var/log/ai-ui.{log,err.log}`
  - [ ] `--system` flag (or a sibling `ai-ui-headless` formula) installs a LaunchDaemon under `/Library/LaunchDaemons/` for unattended-reboot uptime; document the tradeoff vs auto-login + LaunchAgent
  - [ ] `ai-ui start`/`stop`/`update` integrate with `launchctl` (or `brew services`): one command per side, idempotent across re-runs
  - [ ] Idempotent install/upgrade: `brew upgrade ai-ui` must not duplicate the plist, evict a running service, or leave an orphan plist after `brew uninstall`; `brew services list` always reflects reality
  - [ ] Pre-flight in `ai-ui start`: refuse to launch when another container holds the configured port or container name; prompt the operator to `ai-ui stop` first
  - [ ] Smoke: formula `test do` block installs the agent, asserts the service starts, hits `/health`, deregisters cleanly
- [ ] **Update banner: redirect admins to auto-update config**: replace `UpdateInfoToast.svelte` copy with deployment-shape-aware guidance — messaging only, no backend changes. Plan: `~/.claude/plans/given-our-newest-trends-modular-sloth.md`.
  - [ ] Guidance: auto-deploying installs (CapRover, Portainer, K8s) pick up new tags automatically; brew/manual installs run `ai-ui update --tag X.Y.Z` (shown inline)
  - [ ] CapRover's existing auto-pull is the structural poka-yoke
  - [ ] Edit `app/src/lib/components/layout/UpdateInfoToast.svelte`: new copy + inline `<code>` for the command + two links
  - [ ] Update `app/src/lib/i18n/locales/en-US/translation.json` with new strings; other locales fall back to English until translated
  - [ ] Create `WEB-Sage.Education-docs/docs/admin/auto-updates.md` (CapRover config + brew alt + Portainer/K8s/other one-paragraph each + Need help? → `support@sage.is`)
  - [ ] Verify: banner renders with new copy when current < latest for an admin; release-notes link points at the specific tag; docs page renders in Docusaurus dev server

### Privacy & Poka-Yoke #critical

- [ ] **Review & implement Poka-Yoke privacy plan**: Three structural mistake-proofing changes surfaced by panel review
  - [ ] **PK-1 — Local/External model indicator**: Add `is_external` + `provider_label` to model API response; show Local/External badge in model selector, response bubbles, and space agent messages
  - [ ] **PK-2 — Admin chat access default OFF**: Change `ENABLE_ADMIN_CHAT_ACCESS` default to `False` in `config.py:1378`; add audit log line in `routers/chats.py:86`; add visible banner when admin views a user's chats
  - [ ] **PK-3 — Workshop external model warning**: Show inline warning when an agent is created with an external-provider base model
  - [ ] Update CHANGELOG.md: document breaking change (admin chat access now opt-in)
  - [ ] Full plan at: `~/agent-planning/plans/poka-yoke-buzzing-sedgewick.md`

### Pitch & Documentation

- [ ] **Pitch — Fix Privacy Absolutes**: Audit `docs/elevator-pitch.md` for unconditional privacy claims
  - [ ] Replace "nothing phones home" → "nothing leaves your building unless you send it"
  - [ ] Replace "we don't store data" → "Sage stores nothing; schools may store by default; ephemeral mode is available"
  - [ ] Add educator-visibility default sentence: "Sage ships with educator visibility on by default. Students can toggle privacy at any time."
  - [ ] Revise model-transparency claim: "when a user is permitted to inspect an agent, they always see which model it calls"
  - [ ] Audit remaining absolute claims for similar conditionals

- [ ] **Pitch — Pick Primary Audience**: Decide family pitch vs. org pitch as the launch face
  - [ ] Choose one audience for the current pitch (family: local/budget-first, or org: sovereignty/compliance)
  - [ ] Revise opening hook for that audience only
  - [ ] Confirm cake metaphor stays in the family version only
  - [ ] Stub a second pitch outline for the other audience

- [ ] **Publish Threat Model**: One public document establishing what Sage defends and what it does not
  - [ ] Document what Sage-the-company stores (nothing) vs. what schools may store (by default)
  - [ ] Document residual risks for users of the anonymizing proxy
  - [ ] Document warrant/subpoena response sequence for school deployments
  - [ ] Written commitment: no automated behavioral flagging (hate speech, self-harm, etc.) without explicit school opt-in
  - [ ] Publish to `docs/` and link from README and elevator-pitch

### Sprig B1 — finish extraction (audit backlog, sequenced next)

- [ ] **Accelerator-aware Sprigs™ — drop the CPU-only assumption** (captured 2026-07-27): the whole chain currently hardcodes CPU; when GPU support lands, sprigs need alternative variants per accelerator (cuda/rocm/metal) selected the same way arch is today. #bonsai
  - [ ] `scripts/gates/embedding-parity/build-artifacts.sh` installs torch from the `whl/cpu` index on purpose — the CUDA wheels are ~2GB of unused weight for a CPU gate
  - [ ] The GGUF cultivars ship CPU builds; `HOST_ARCH` compatibility is a two-value question (`arm64`/`amd64`) with no accelerator dimension
  - [ ] Widen `compatible` in `/catalog` from arch-match to arch+accelerator-match
  - [ ] `build-artifacts.sh` takes a torch-flavour argument instead of a pinned CPU index URL
  - [ ] Plan for the parity gate: its thresholds assume device-stable numerics — `cosine_min >= 0.999` (f16) may not survive a CPU reference vs GPU inference comparison
    - [ ] Either generate the reference per-accelerator or make the tolerance device-aware
    - [ ] Do NOT loosen the threshold to paper over a device gap; that is the check that caught the Hangul tokenizer divergence
- [ ] **Delete the chromadb pip fallback** (end-state of the bootstrap): blocked on prod-registry cutover + one release of soak. `vector_bootstrap.py` already prefers the sprig; the pip path goes cold automatically once prod has a registry. #bonsai

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

- [ ] **Catalog schema enrichment**: the CATALOG carries only machine fields, so the admin UI can only show raw keys like `minilm-onnx-inhoused` — prerequisite for a legible UI; the UI can only be as clear as this data. #bonsai
  - [ ] Add `display_name` + `description` (plain "what this does") to each entry
  - [ ] Add `size_mb`, `license`, and `tier` (`recommended`|`advanced`|`held`)
  - [ ] Add `restart_required` (bool, replacing the prose `post_graft_note` inference)
  - [ ] Add a slot/`replaces` marker for the six mutually-exclusive embedding cultivars
- [ ] **`/catalog` hygiene**: `GET /catalog` dumps `repo`/`tag`/`insecure`/`binary_sha256` to the browser (`routers/sprigs.py`). Return only presentation fields (security + noise). #bonsai
- [ ] **Sprigs admin UI redesign** (`app/src/lib/components/admin/Sprigs.svelte`): group cards by capability. #bonsai
  - [ ] Collapse the six embedding cultivars into one "Embedding" choice with a cultivar picker
  - [ ] Disclose consequences BEFORE Graft/Prune: size, restart-required, "replaces X" / "this breaks document search"
  - [ ] Hide `pid`/`base_url`
  - [ ] Explain the Sprig/Graft/Prune/Wilted metaphor inline (tooltip or docs link)
  - [ ] Add first-run guidance instead of a wall of 14 cards

- [ ] **Stand up `bonsai.sage.is` spec hub** (2026-06-28; scaffold SHIPPED locally 2026-07-08): implementers spend hours here; polish compounds. ([dossier](docs/board-dossiers.md)) #bonsai
  - _Shipped locally 2026-07-08: 11ty scaffold, build-time spec fetch, `/sprig-spec/v1/` + `/rootstock-spec/v1/` render, catalog-hub home. Archived 2026-08-15._
  - [ ] [MANUALLY] `git init` + push `BONSAI/sprig-spec` and `BONSAI/rootstock-spec` BEFORE the hub — no `.git` anywhere in `BONSAI/`, CI clones the spec repos
    - [ ] The `app-` capability prefix reserved in `sprig-spec/v1.md` (2026-08-15) exists only as one uncommitted copy on this disk
  - [ ] [MANUALLY] Create `sage-is/bonsai-docs`, push `~/Documents/Projects/GitHub/BONSAI/bonsai-docs/`, Cloudflare Pages project (build `bun run build`, output `dist`) + CNAME `bonsai.sage.is`
    - [ ] 11ty renders single-page views of the canonical specs pulled from GitHub at build time
  - [ ] After the hub is live: flip the sage.is/bonsai + sage.is/sprigs spec links from github.com to `bonsai.sage.is/*/v1/`
  - [ ] Point the `$id` URLs in `sprig-spec/v1.md` and `rootstock-spec/v1.md` at the canonical `bonsai.sage.is` URL once the site is live
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
    - [ ] Design: `~/.claude/plans/the-arch-guard-trusts-effervescent-moonbeam.md` (Track B) + memory `project_sprig_marketplace.md`
  - [ ] **Quarter slice, scoped 2026-08-15 against a social push**: the push needs the store to exist. #bonsai #marketplace
    - [ ] M1 stays at position 3 in the `#### Platform unlocks` sequence, so the push date depends on Spaces multi-user and spend budgets — book no announcement against a date those two control
    - [ ] Ships: M1 catalog-as-data, M1b admin self-load (`POST …/sprigs/load`, `sprigs.d/*.json` on the volume), `/catalog` redaction
    - [ ] Ships: schema enrichment (`display_name`, `description`, `size_mb`, `license`, `tier`, `publisher`, `homepage` — once, with M1)
    - [ ] Ships: browse/search UI over the 20 shipped sprigs
    - [ ] Should: remote signed `catalog.json` on a Sage.is URL, artifacts staying on GHCR
    - [ ] Does not ship: public submission lane, storefront index, M5 commerce, in-house registry, `delivery: service-endpoint`
    - [ ] Dropping the public lane defers signature liability — self-load is admin-only; the admin stays the trust boundary
    - [ ] We do not charge makers to list (present tense, not "ever"); creators earn through contracts we sell direct, not a storefront cut
    - [ ] Cards: `charts/sprig-creator-program/TODO.md`; analysis: `~/.claude/plans/business-planning-time-how-stateful-crystal.md`
  - [ ] **Blocker — the `execute` event runs arbitrary JS in the top frame, and a listing policy does not fix it**. #security #critical
    - [ ] `Chat.svelte:387` passes the `__event_emitter__` `execute` type to `new Function(...)` unsandboxed
    - [ ] `POST /api/v1/functions/load/url` (`routers/functions.py:82`) installs a `main.py` from any GitHub URL today, no marketplace involved
    - [ ] A push that brings thousands of self-installers widens that surface
    - [ ] Pick one and record it: gate the endpoint, sandbox the event, or accept the risk in writing
    - [ ] Keeping Functions out of the community lane is correct and cheap but is not the control
  - [ ] **Blocker — no CSP exists, and enforcing a fresh one the week before a launch breaks the product**. #security #critical
    - [ ] `SecurityHeadersMiddleware` is wired at `main.py:1473` but `CONTENT_SECURITY_POLICY` is unset in `.env.example`, the Dockerfile, compose, and `distribution.env`
    - [ ] `routers/diagnostics.py:610` already grades it degraded
    - [ ] Exceptions to cover: `https://startr.style/style.css` in both frontends (`app/src/app.html:31`, `pages/shell.py:206`), Artifacts srcdoc frames, Pyodide, the WASM sprigs, every inline style
    - [ ] Ship `Content-Security-Policy-Report-Only` first, collect violations from a real session, then enforce
  - [ ] **The app pane is the store's actual product, and it is not built** — four gaps. #bonsai
    - [ ] An installed app must open like an Artifact, run, and report progress — not "the assistant can call your API"; `Artifacts.svelte` already supplies the pane
    - [ ] Not this quarter, but reserve the `app-` prefix now, per the `agent-` precedent in `_notices/2026-07-11-reply-to-scion.md`
    - [ ] The bridge validates by `event.origin`; a `srcdoc` frame without `allow-same-origin` has an opaque origin, so its postMessage arrives as `"null"` and is rejected at `Chat.svelte:417`
      - [ ] Validate `event.source === iframeElement.contentWindow` instead
    - [ ] Service workers, localStorage, IndexedDB, and Cache API need a real origin, so a genuine PWA cannot run in a `srcdoc` pane — in-container is the only rung where "PWA-type app" is literally true
    - [ ] Student progress needs a per-user per-sprig state API on the rootstock, not browser storage
    - [ ] The spec reserves `ui-` and `agent-` but not `app-` — reserve it now
- [ ] **Incoming: `startr-team` agent framework as a `service-endpoint` Sprig** (midterm; awareness notice from Scion 2026-07-11, no action requested): grafts onto AI-UI as a REMOTE Sprig, never a source dependency. ([dossier](docs/board-dossiers.md)) #bonsai #agents
  - [ ] Sage-is = science+platform, Startr = tooling+product — the arms-length Graft Union™ settles licensing
  - [x] Done at the cheap moment: `agent-` capability prefix RESERVED in sprig-spec v1.md with a planned `sage-is/v1/agent` dispatch shape; CHANGELOG [Unreleased] entry added
  - [ ] Define the contract when the Sprig lands — run lifecycle, streamed events, cancellation, schema at `sprig-spec/schemas/sage-is/v1/agent.json`
    - [ ] Bidirectional from day one (locked 2026-07-11): a rootstock callback surface so agents work with the operator's data instead of shipping copies
  - [ ] Wire explicit rootstock dispatch — the "no per-capability dispatch code" guarantee covers only OpenAI-compatible shapes
  - [ ] Implement `delivery: service-endpoint` (currently unimplemented); both deliveries locked — hosted `service-endpoint` and on-hardware `oci-artifact`, keeping zero-egress intact
  - [ ] Keep one tiered "Agents" surface, no renames — the locked decisions define the EXTENDED tier (simple agents already ship as workspace Agents and Space agents)
    - [ ] The model-transparency claim extends to the remote tier
    - [ ] Job queue + spend budgets are PREREQUISITES: runs live on the queue, budgets gate spend
  - [ ] Ignore Scion's stale pointer paths: specs live in the BONSAI sibling repos, the graft API is `routers/sprigs.py`, pins live in the supervisor CATALOG
- [ ] **Bonsai/sprigs pages as markdown + text-graph→SVG diagrams** (captured 2026-07-08): both pages are hand-written njk today — re-author as markdown so content edits stop requiring template surgery. #bonsai #site
  - [ ] Diagrams from text markup rendered to SVG at build time — mermaid is the baseline candidate, or a custom "simple text graph" markup (TBD, mermaid-style)
  - [ ] Renderer emits house-styled SVG: startr.style tokens, correct fonts, label collision avoidance
    - [ ] The Graft Union™ label landing on a connector line is exactly the class of bug a renderer should prevent
  - [ ] Candidate consumers beyond these two pages: the bonsai.sage.is spec hub and future architecture docs

- [ ] **Reserve `spec.sage.is` DNS** (2026-06-28): Set up the subdomain now without a site behind it. Reason: if Sage.is ever publishes a non-Bonsai spec, that's the canonical URL home. Avoids painting into a corner where every Sage.is spec inherits the Bonsai metaphor in its URL. Per Daniel Stenberg's guardrail in the panel review. #bonsai #dns
  - [ ] Add `spec.sage.is` CNAME record (parked, no content)
  - [ ] Document in `docs/` why it's reserved so it doesn't get repurposed casually

- [ ] **Define spec-hub polish punch-list** (2026-06-28): translate Rauno Freiberg's "polish target" principle into a concrete pre-launch checklist for `bonsai.sage.is` — the list IS the bar, ship only when each is true. #bonsai #polish
  - [ ] Excluded: the `sage.is/bonsai/` explainer does NOT need to hit this bar; content quality is its bar instead
  - [ ] Scroll-spy nav: current section highlighted, smooth scroll on anchor click, sticky table of contents on long pages
  - [ ] Code-block copy buttons with success state ("Copied" pill, then fade back)
  - [ ] Instant search across all specs (Pagefind or equivalent — fully client-side, no JS backend)
  - [ ] Focus-ring spec — consistent, visible, WCAG-AA accessible across light/dark
  - [ ] Typography scale + line-length cap (60-80ch); generous vertical rhythm
  - [ ] Dark-mode handling: `prefers-color-scheme` default + explicit toggle, persisted
  - [ ] Hover states on every interactive element (links, buttons, code-block actions)
  - [ ] Animated reveal of nav items on scroll into view (subtle, sub-300ms)
  - [ ] Cursor-following micro-details on the catalog home — 4ms attention, not pageant moves

### v2.x — Near Term

- [ ] **Auth & Onboarding**: Email notifications and LDAP consolidation
  - [ ] Outgoing email notifications (reuse bridge SMTP config)
  - [ ] Consolidate LDAP config into Auth/Integrations tab

- [ ] **Spaces Enhancements**: agent context modes, auto-reply TTL, and multi-user — pulled forward 2026-07-30 as unlock #1 for the real-estate engagement. ([dossier](docs/board-dossiers.md))
  - [ ] **Multi-user**: a principal + assistant + VA share one workspace on day one; the customer's success metric ("they stop asking him things") is unreachable without it
  - [ ] Agent context mode: `conversation` (last ~5 messages) and `full` (all recent) — `single` already ships
  - [ ] Optional per-agent TTL for auto-reply expiration
    <!-- inline: spaces.py:384 -->
  - [ ] **Silverbullet integration into Spaces** — wire the self-hosted Silverbullet PKM/wiki into Spaces. Planning conversation first (architecture, auth, data model), then code.
  - [ ] **Space theming for creator-led visual differentiation** (2026-06-15): creator-only "Theme" tab in Space settings — accent-color picker + optional logo upload, tinting nav chrome and thread accents
    - [ ] Identical-looking Spaces cause mis-posts; load-bearing for workshop facilitators and multi-org Rootstocks
    - [ ] No custom-CSS injection (XSS surface)
    - [ ] Ship preset themes (bio = green, math = blue) so non-technical facilitators can theme without picking colors
- [ ] **Frontend Toolchain Upgrade**: Svelte 5, Vite 6, SvelteKit latest
  - [ ] Svelte 4 → 5
  - [ ] Vite 5 → 6
  - [ ] SvelteKit 2.5 → latest

- [ ] **Podman Compatibility**: Verify builds and document setup
  - [ ] Test and fix Podman build issues (VM memory, rootless networking)
  - [ ] Document Podman-specific setup (VM memory bump, `host.containers.internal`)
  - [ ] Revisit Makefile `CONTAINER_RUNTIME` auto-detection once Podman is a verified alternative

- [ ] **2.4 ML Bundle (signed per-arch × per-accel)**: replace the 2.3.1 transitional ML wizard path (runtime `uv pip install` + `sitecustomize.py`) with signed tarball bundles published on GitHub Releases. Plan: `~/.claude/plans/given-our-newest-trends-modular-sloth.md`.
  - [ ] Wizard pulls via `curl | sha256sum -c | tar -xz`
  - [ ] `distribution.env` carries `ML_BUNDLE_TAG` + per-variant SHA256s
  - [ ] Bring CUDA back as a first-class matrix cell
  - [ ] `requirements-ml.lock` from 2.3.1 is the build input — no thrown-away work

- [ ] **Knowledge Base Improvements**: AI ingestion and admin cleanup
  - [ ] AI-parsed ingestion mode + admin Documents page cleanup
  - [ ] Fold engine-specific config under `<details>/<summary>` in the admin page

- [ ] **Codebase Cleanup**: Channel→Space rename, semantic HTML, branding
  - [ ] Channel → Space DB migration (Alembic rename of tables, columns, enum values)
  - [ ] Rename `components/channel/` directory → `components/space/`
  - [ ] Replace wrapper `<div>` elements with semantic custom elements
  - [ ] Swagger UI: custom styling, branding, auth handling
  - [ ] CapRover one-click template
  - [ ] Scrub remaining upstream open-webui references in comments and defaults
  - [ ] Add migration idempotency guards on all `create_table` / `add_column` calls
  - [ ] Replace login slideshow images with original or CC/public-domain photos

### v3.0 — Future

- [ ] **Developer Mode**: Single image, dev CLI, HMR
  - [ ] `ai-ui dev` CLI command: clones repo, mounts source, enables DEV_MODE
  - [ ] DeveloperStep wizard: informational in prod, celebration with wizard illustration in dev mode
  - [ ] Node.js + npm installed to data volume on first dev start
  - [ ] Same image, same container — `DEV_MODE=true` switches to vite HMR + uvicorn reload

- [ ] **Upload & Download UX**: Progress streaming, time estimates, admin viewer
  - [ ] Download progress streaming to frontend (WebSocket/SSE from backend)
  - [ ] Admin panel tab for AI Engine download status and progress
  - [ ] `HF_TOKEN` support for faster authenticated HuggingFace downloads
  - [ ] Download time estimates based on measured connection speed
  - [ ] Upload progress bars with percentage and speed meters
    <!-- inline: ollama.py:1748 -->
  - [ ] Configurable upload timeouts based on file size (replace hardcoded 240s)
    <!-- inline: audio.py:598,652,759 ollama.py:1699,1799,1823 -->
  - [ ] Console/log viewer tab in admin (WebSocket log streaming)

- [ ] **Platform Features**: Workspaces, analytics, search, mobile, a11y
  - [ ] Sage.is hosted email notification service (for deployments without SMTP)
  - [ ] Workspace switcher (project-scoped model configs, shared vs private)
  - [ ] Built-in task tracking (convert chat responses to tasks, due dates, progress)
  - [ ] Personal analytics dashboard (usage patterns, model preferences)
  - [ ] Semantic search across all chats and documents
  - [ ] Mobile-first optimizations (swipe gestures, PWA enhancements)
  - [ ] Accessibility: screen reader, high contrast, keyboard navigation

### From Codebase (untracked)

- [ ] **Backend Inline TODOs**: Load balancing, type updates, deprecation removal
  - [ ] Intelligent load balancing for multiple Ollama backends (`ollama.py:1`)
  - [ ] Update Ollama type support when upstream adds new types (`ollama.py:1378`)
  - [ ] Handle tool name collisions by prepending toolkit name (`utils/tools.py:109`)
  - [ ] Replace legacy system message insertion with `add_or_update_system_message` (`middleware.py:1037`)
  - [ ] Add retries to audio processing requests (`audio.py:1120`)
  - [ ] Remove deprecated `WEBUI_JWT_SECRET_KEY` fallback at next major version (`env.py:393`)

- [ ] **Frontend Inline TODOs**: UX polish, component upgrades, bug investigation
  - [ ] Filter order handling in model config (`FiltersSelector.svelte:34`)
  - [ ] Voice input auto-stop logic in Knowledge Base (`AddTextContentModal.svelte:21`)
  - [ ] Shortcut support for generate-title button (`ChatItem.svelte:415`)
  - [ ] User-facing error for Space participant issues (`Space.svelte:81`)
  - [ ] Emoji picker search filtering (`EmojiPickerClean.svelte:47`)
  - [ ] Update RichTextInput Bubble/Floating to v3 (`RichTextInput.svelte:79`)
  - [ ] Note pages feature — multiple pages per note (`NoteEditor.svelte:80`)
  - [ ] Decide native vs custom file handling in notes (`NoteEditor/Chat.svelte:191`)
  - [ ] Investigate Kokoro worker issues (`kokoro.worker.ts:4`)

- [ ] **Audio/TTS UX polish** (surfaced live in dev mode 2026-07-26; the last two ride with the Settings/Admin migration pass):
  - _Shipped: first-playback loading toast (`ResponseMessage.svelte`); Settings double-load memoized (`Settings/Audio.svelte`). Archived 2026-08-15._
  - [ ] Opening Settings → Audio RELOADS Kokoro even after playback already loaded it — the Settings main-thread loader and the playback Web Worker (`kokoro.worker.ts`) are separate contexts; share one loader/model so the model loads once per session
  - [ ] Kokoro voice selector is janky (a type-in input + a list that only opens after you clear the field) → replace with a clean, DRY `<select>`/combobox

### Frontend — no-build strangler migration (approved 2026-07-25)

> Approved plan: move the AI-UI frontend off the SvelteKit build to
> server-rendered HTML + vanilla/htmx islands, Svelte-as-biomes, strangler to
> zero. Three evidenced legs — delete duplicated code (~50%), cut the
> conversation load (172 req / 7.9 MB / ~19 s → near-instant), turn shared chats
> into a crawlable distribution surface. Full plan:
> `~/.claude/plans/we-got-to-gtm-stateful-teapot.md`.

> **HOW TO WORK ON THESE PAGES (as of 2026-07-31).** Never `make it_build` just
> to look at something.
>
> | you want to | run |
> | --- | --- |
> | **build anything** | **`make dev`** |
> | judge whether it ships | `make review` |
> | judge a page without rebuilding | `make review LIVE=1` |
> | judge Svelte changes | `make review REBUILD=1` |
>
> **Two commands, as of 2026-08-09.** `make dev` runs `uvicorn --reload` and
> `vite dev` side by side in one container, mounts `pages/`, seeds an admin and
> grafts the example ui-Sprig™ — everything is live and nothing needs a
> teardown. `review` boots the BAKED artifact, which is the pass that decides,
> because a review of your working tree is not a review of what you ship.
> `dev_run`, `review_live` and `review_rebuild` survive as aliases.
>
> Note `review LIVE=1` does NOT rebuild Svelte — it mounts `pages/` only, and
> the bundle stays frozen at whatever `it_build` last produced, with no warning.
>
> Under `review LIVE=1`: save a `.css`/`.js` under `pages/assets/` and the
> stylesheet **swaps in place** — no reload, so the page keeps its scroll and any
> open dialog; save a `.py` and the app **restarts itself in 2.8 s** and the tab
> reloads. Switching modes is 7 s, because the seeded volume is kept. `/pages/`
> is an index of every server-rendered page and carries a banner when the
> reloader is on.
>
> The gates deliberately have no live mode — `e2e`, `e2e_both` and `wizard_smoke`
> always boot the baked image, because a guard-rail run against a working tree
> tests something we do not ship. Full write-up:
> `docs/no-build-surface-convention.md` → "The dev loop".

- [ ] **Phase Q0 — board hygiene**: TODO.md on TodoScope convention, this plan's tracked TODOs filed, board kept current every phase. #critical
  - [x] Verify TODO.md structure + `.todoscope-exclude.csv` (both already on-convention)
  - [x] File the migration epic + tracked TODOs into TODO.md
  - [ ] Keep the board mirroring reality as each phase's steps land and ship
    - [x] Reconciled again 2026-07-29 after the branding surface: entry filed with BOTH line-count readings rather than the flattering one.
    - [x] Reconciled 2026-07-29 after Phases 0–2 landed: 14 stale "uncommitted" markers cleared (every one of them is in `HEAD`; the tree is clean), the error-persistence and toast work filed, Phase 2 split from 3–4 with diagnostics closed and theme/wizard named, and the locale blocker filed rather than left living only in a docstring. Worth noting WHY the drift happened, since it will recur: entries were written at the moment work finished, when it was genuinely uncommitted, and nothing brings the board back after the user commits. The board cannot know — only a pass like this one closes it.

- [ ] **Phase Q — clear the decks**: current-SPA drift fixes, cruft, and perf quick-wins — no migration needed. ([dossier](docs/board-dossiers.md))
  - [x] Enforce the 8-char password server-side (`auths.py`) — measure-twice e2e verified (200→bug, 400→fixed); committed
  - [x] Fix `UserUpdateForm` / `SpaceForm` TS↔Pydantic drift — committed
  - [x] Delete the dead `SUPPORTED_FILE_EXTENSIONS` copy in `constants.ts` (backend 50-entry list is live) — committed
  - [x] _Permission-tree defaults reconciled (2026-07-27): 4 value disagreements + 1 missing key; enforcement read absent `features.web_search` as denied, so no non-admin ever got the web-search button; added `USER_PERMISSIONS_FEATURES_WEB_SEARCH` (default `True`), Pydantic defaults now derive from the table, `get_permissions()` backfills; `permissions-drift.cy.ts` RED→GREEN, e2e 13/15, `KEEP=1 make upgrade_gate` 20/21 vs a real v1.1.1 snapshot. #security #critical. Archived → docs/completed-todos.md._
  - [ ] **Drop the frontend's permission fallbacks**: the 13 `$user?.permissions?.x?.y ?? true` sites in `src/` are unreachable now that every enforced key ships in the payload. #frontend #tech-debt
    - [ ] A `?? true` can only mask future drift — it renders a control the API will refuse
    - [ ] Delete them; guard-rail asserts a denied permission hides its control
  - [x] _`| grep -q` under `set -o pipefail` resolved (2026-07-28) — never a product bug: grep's first hit SIGPIPEs the writer, 141 reads as failure, or as "no match" at `upgrade-gate.sh:55`, which reported clean on the exact failure it guards; pipe-free primitives in `scripts/lib/gate.sh`, 12 sites converted, `pipefail_lint` + `pipefail_fixture` shipped; `gauntlet_full` exit 0, `upgrade_gate` 21/21. #critical. Archived → docs/completed-todos.md._
  - [x] _Cruft sweep (deps): removed unused `chart.js` + `@mediapipe/tasks-vision` and the dead DOMPurify import in `MarkdownInlineTokens.svelte`; bun.lock `Removed: 2`; `it_build` + guard-rails green; fuller depcheck of the other 100+ deps is a separate pass. Archived → docs/completed-todos.md._
  - [x] _Hyperscript attribute forms (`_`, `script`, `data-script`) stripped by one DOMPurify `uponSanitizeAttribute` hook (`utils/sanitize.ts`, root `+layout.svelte`) covering all 14 `@html` sites; `content-security-sanitizer.cy.ts` measure-twice RED→GREEN. Archived → docs/completed-todos.md._
  - [x] Perf: `Cache-Control: immutable` on `_app/immutable/*` — measure-twice e2e verified (empty header→immutable); committed
  - [x] _ML libs off the conversation chunk: the 22 MB WASM was already lazy (audit inferred wrong); deleted dead `@huggingface/transformers` import, kokoro-js dynamic in `chat/Settings/Audio.svelte`; nodes/2 2.70→0.65 MB, app load 5.39→4.12 MB (−24%), 13.4→10.6 MB decoded. Archived → docs/completed-todos.md._
  - [x] _`/icons/` waste resolved as already-gated: image ships 0 `.xcf` (`.dockerignore`) and 1.3 MB icons total; the audit read a stale host build; the 6 identical 170 KB placeholder PNGs → branding-art task, not perf. Archived → docs/completed-todos.md._
  - [x] _Markdown-render lazy-load shipped as architecture hardening, measured perf-neutral: katex/mermaid/codemirror were ALREADY lazy (identical 13.41→10.27 MB delta in both builds); real wins = dead `import katex` deleted, `hljs` dynamic in `copyToClipboard`, memoized `{#await import()}` loaders (`Markdown/lazy.ts`); `markdown-render-lazy.cy.ts` green before and after. #perf #frontend. Archived → docs/completed-todos.md._
  - [x] _Boot waterfall batched into one `Promise.all` wave after settings: three round-trips removed (~19 ms loopback, ~180 ms at 60 ms RTT); `boot-waterfall.cy.ts` RED→GREEN and pins settings-resolves-before-`/api/models`. #perf #frontend. Archived → docs/completed-todos.md._
  - [x] _Caching pass (2026-07-26): flipped the `ENABLE_BASE_MODELS_CACHE` default with invalidation wired from both provider-config endpoints (~740 ms → ~4.5 ms, ~160×; `models-cache.cy.ts` asserts both halves); `/static` + `/assets` get `public, max-age=604800`; combined: boot data-fetch 821.5→102.5 ms (8×), `/api/models` 768→17 ms; e2e 12/14 (two known leaks); PersistentConfig — an admin's saved choice survives upgrade. #perf. Archived → docs/completed-todos.md._
  - [ ] **`@cached(ttl=MODELS_CACHE_TTL)` never hits — the decorator is inert** (caching pass, 2026-07-26): the knob does nothing and every request stores an entry, so memory grows with request rate. #perf #tech-debt
    - [ ] `routers/openai.py:550` + `routers/ollama.py:378` use bare `aiocache.cached` with no `key_builder`; the default key stringifies the Starlette `Request`, a new object each call, so it never repeats
    - [ ] Proven with `MODELS_CACHE_TTL=60`: five `/api/models` calls 0.74/0.73/0.78/1.70/0.74 s, zero hits
    - [ ] Add a `key_builder` on stable values (user id + provider-config revision) — or delete the decorators; removing a cache that never hits is behaviour-preserving.
    - [ ] Audit the other bare-`cached` sites: `utils/chat.py`, `utils/models.py` (the `utils/middleware.py` copy was dead, removed 2026-08-06).
  - [ ] **Redis/valkey + multi-worker — the actual concurrency lever** (scoped during the caching pass): `start.sh:233` runs `--workers ${UVICORN_WORKERS:-1}` — a SINGLE-process app today. #perf #architecture
    - [ ] `REDIS_URL`, `WEBSOCKET_MANAGER`, `WEBSOCKET_REDIS_URL`, and a redis-backed `PersistentConfig` exist in code; Dockerfile, compose, and CapRover set none
    - [ ] Raising `UVICORN_WORKERS` breaks websocket fan-out and duplicates every in-process cache per worker
    - [ ] Write the plan; decide the valkey sidecar: in-image vs CapRover one-click vs Sprig™.
    - [ ] Multi-worker test proving socket events cross workers.
  - [ ] Perf: put HTTP/2 in front — parallel boot fetches pay more once they stop queueing behind HTTP/1.1 connection limits. #perf
  - [ ] Perf: `/api/models` alone is ~770–995 ms of a ~820–1100 ms boot — latency, not payload (investigated 2026-07-26 with an EMPTY model list). #perf
    - [ ] The cost is the slowest provider probe in `get_all_base_models` (`utils/models.py:60-76`, already one `asyncio.gather`)
    - [ ] `ENABLE_BASE_MODELS_CACHE` defaults `False` (`config.py:994-997`), so every call re-probes every provider
    - [ ] Each lever wants its own guard-rail and before/after
    - [ ] Backend: default the base-models cache on and/or warm it at startup; bound the per-provider probe timeout.
    - [ ] Frontend/islands: stop gating `loaded` on it — render the shell, fill the selector when it lands; the admin setup-wizard check (`$models.length === 0`) awaits the promise, not the boot chain.
    - [ ] Pagination is a third, separate lever — only after a payload measures large on a loaded instance (same open question for chat list, tools, prompts, knowledge).
  - [x] _e2e Poka-Yoke pass (2026-07-27): `make e2e` GREEN 15/15 specs, 30/30 tests; `support/e2e.ts` snapshots the admin-mutable config surface per spec and restores only what changed (leaks logged BY NAME); `stt-not-configured` sets `stt.ENGINE=''` itself; sprigs-panel assertion reads `post_graft_note` from `/catalog`, pinned `retries: 0`. #e2e. Archived → docs/completed-todos.md._
  - [x] _e2e harness could silently run on the previous run's data (2026-07-29): `|| true` on `docker volume rm` hid a held volume — third instance of a gate whose failure is indistinguishable from success; fix waits for container removal, retries, hard-exits naming the holder; proved able to fire: `FATAL: volume 'sage-e2e-data' survived removal`. #e2e #critical. Archived → docs/completed-todos.md._
  - [x] _Colour-picker e2e automated after all (Alexander, 2026-07-29): a synthetic `input` event exercises the picker→hex contract — green on both implementations, proved able to fail; SikuliX stays on the roadmap for streaming/scroll surfaces (Phases 3–4), near-worthless for form surfaces. #e2e #frontend. Archived → docs/completed-todos.md._
  - [ ] Guard-rail Cypress spec for every area before it's touched
  - [ ] Modernize or prune the inherited upstream e2e specs: `registration/settings/chat/documents.cy.ts` now COMPILE (import depth `../support`→`../../support` fixed) but FAIL on stale open-webui UI. #e2e #tech-debt
    - [ ] They assume open signup (this fork hard-closes it after the first admin) and the old `Okay, Let's Go!` changelog dismiss (now the setup wizard's "Get Started"/Close via API)
    - [ ] Rewrite to the fork's flows or drop; they sit in a subdir, NOT in the default `make e2e` gate
- _Phase S — streaming spike: GO SHIPPED 2026-07-27 (Cypress cannot see streaming, so any streaming guard-rail needs a non-proxying driver; every streamed surface gets a human pass before it is called done; the shared-runtime probe HOLDS, 16/16, so Phase 4 is unblocked on runtime grounds). Full entries archived 2026-08-15 → `docs/completed-todos.md`._

- [ ] **Version `/themes/active.css`** (deferred 2026-07-26, unblocked 2026-08-01): every full page load spends a render-blocking round-trip on 23 bytes of `/* no theme grafted */`. ([dossier](docs/board-dossiers.md)) #perf #bonsai
  - [ ] Unblocked: panels moved to Jinja2; `shell.py` needs no templating, and `shell.asset_url()` already version-stamps by release
  - [ ] Measured on the shipped image: `cache-control: no-cache`, no ETag, no Last-Modified, `If-None-Match` returns 200 not 304, via the static `<link>` at `app.html:21`
  - [ ] Inject `?v=<active theme name + css mtime>` into the shell's `<link>` at serve time
  - [ ] Serve the CSS `immutable, max-age=31536000` — a graft changes the token, so pickup is instant with zero revalidation (SvelteKit's `_app/immutable` trick)
  - [ ] Trap: do NOT key invalidation to deploys — `SPRIG_ACTIVE_THEME` flips at RUNTIME (`routers/sprigs.py:151,305`), so deploy-keyed caching hides a fresh graft until restart
    - [ ] Rejected: short TTL (grafted theme one load late); ETag-only (saves the 23-byte body, not the round-trip)
- [x] _Phase 0 — seam + Sprigs pilot SHIPPED (2026-07-27): `/pages` + `/pages/_assets` registered BEFORE the SPA catch-all; the pilot panel measured Svelte 231 vs island 233 vs FRAGMENT 157 lines (−32%), so fragments are the shrinking path and the island was deleted; the template-engine question was answered by the twelve-panel Jinja2 conversion (2026-08-01). Full measurements archived → docs/completed-todos.md._

- _Phase 1 — ui-Sprig contract + cookie bridge SHIPPED 2026-07-27 (`ui_sprig_gate` 22/22; the scripting grant is held by NAME; "no framework sprigs" enforced three ways). Full entry archived 2026-08-15 → `docs/completed-todos.md`. Open spec work extracted below._

- [ ] **ui-Sprig spec follow-through — write the shipped decisions into the spec repo** (extracted 2026-08-15 from the archived Phase S and Phase 1 entries, per the board un-mix) ([dossier](docs/board-dossiers.md)) #sprigs #ui
  - [ ] **ui-Sprig NAMED SLOTS — decided 2026-08-01, not built** (Alexander, on the workshop-welcome fragment: "I'm not so sure we should have [it] everywhere") #sprigs #ui
    - [ ] The spec (`sprig-spec/v1.md:137`) promises mounts, slots, or a manifest; the implementation ships ONE unnamed global slot (`shell.py:117`)
    - [ ] A grafted fragment renders on all fourteen server-rendered pages — fifteen since `/pages/home` (2026-08-09)
    - [ ] Chosen design: the rootstock declares the slot set, the Sprig's manifest names one, the validator refuses unknown names — fail-closed, same shape as the 22 refusals `make ui_sprig_gate` proves
    - [ ] AMENDED 2026-08-09 (Alexander): the address is PAGE plus POSITION (`home:top`, `home:aside`, `diagnostics:footer`) — settle that shape before the manifest field is written
    - [ ] Sequencing: `SPRIG_ACTIVE_UI` is a single pointer, one ui-Sprig live at a time — multi-Sprig first, then slots
    - [ ] Divergence belongs in `IMPLEMENTATION.md`; test case is `workshop-welcome`
    - [ ] `shell.py` declares the slot set; `render_page` emits only the named slot
    - [ ] `sprigs/ui_dispatch.py` validates the name
    - [ ] `scripts/build-sprig-ui.sh` refuses at build too (deliberately stricter than runtime)
    - [ ] `ui_sprig_gate` grows a 23rd refusal
    - [ ] Spec repo: manifest field + version bump; write the risk in — the slot set is a published contract, version it, never rename in place
  - [ ] Write "no framework sprigs" into the ui-Sprig spec repo — fragments + host runtime only #sprigs #ui
    - [ ] Carry the THREE mechanisms (grant, inline-and-same-origin, size ceiling)
    - [ ] Carry the honest note that no static check decides "is this a framework"
  - [ ] Write the runtime-probe costs into the spec — they are the MECHANISM behind "no framework sprigs" (probe evidence in `docs/completed-todos.md`) #sprigs #ui
    - [ ] "Externalise the runtime" is not one specifier: `svelte/internal` external with `svelte` bundled builds clean, throws at mount
    - [ ] Publishing the runtime defeats tree-shaking (27.3 → 95.4 kB unminified)
- [x] _HOLLOWING shipped as the second migration mode, `/home` first (2026-08-08, Alexander): the route keeps its address and chrome, gives up its content, hosts the server-rendered page via `pageHost.ts` (`SetupDialog.svelte` is the precedent). It costs bytes and must never be cited as a payload win — it buys reach and one implementation. Delete the hollow only when the chat core goes server-rendered. [Record](docs/decisions/2026-08-08-hollowing-a-svelte-route.md). #frontend. Archived → docs/completed-todos.md._

- [x] **The parity gate has three states now, not two** (2026-08-08). `surfaces.ts` was binary — registered means compared, removed means gone. Hollowing adds **hollowed**: one implementation, two addresses, **exempt**. Comparing a hollowed route is the mirror that file already warns about, "a gate whose failure is indistinguishable from success". **The exemption is triggered by hollowing or deletion — a structural fact — never by "parity achieved", which is a judgement**: parity reached once does not mean parity holds, and the gate exists to catch what an author did not think to test _later_, when the no-build page is edited and a control quietly goes. `home-hollow.cy.ts` replaces the comparison and judges the host instead — the fetch happened, server-rendered markup arrived (`page-heading`, the only marker that can prove it, since nothing under `/pages/` can 404), the marketplace slot came with it, exactly one shell arrived, and a failure says so rather than showing an empty box. The `home` entry was registered and retired the same day. #frontend #dx

- [x] _Wired Sprigs™ SHIPPED (2026-08-09), with the rule that now governs every future setting: a WIRE is what the operator decides once, a SETTING is what a person decides — if two people would answer differently it cannot be a wire. `sprigs/wiring.py`, `SPRIG_WIRES`, sixth lifecycle state `enabled`, `/pages/settings/calendar` the first per-user no-build page; verified with two accounts. Records: [wiring](docs/decisions/2026-08-09-wired-sprigs-and-two-layers.md), [starter + calendar](docs/decisions/2026-08-09-home-starter-and-calendar.md). #sprigs #backend. Archived → docs/completed-todos.md._

- [ ] **Sidebar toggles for Home and Calendar, and a landing-page preference** (Alexander, 2026-08-09): two features, one shared settings surface — neither gets tacked onto a page build. ([dossier](docs/board-dossiers.md)) #frontend #ux
  - [ ] Not blocked on the top nav: the dashboard surfaces now share a `DashboardShell` with one `LINKS` list and Calendar joined it (losing its "Soon" badge and `preventDefault` dead link) — the sidebar is this card
  - [ ] Per-surface show-in-sidebar toggles, mirroring Spaces. `Sidebar.svelte` hardcodes `/home`, `/notes`, `/workshop` — a change of shape, not a fourth `<a>`
  - [ ] Per-user landing-page preference (chat vs home vs a chosen Space vs part of Notes): needs persistence + a settings screen; changes what `/` means for a signed-in reader
  - [ ] Do not hardcode the option list — Notes may be replaced by Silverbullet; read the choices from what the instance has
- [ ] **Human UX review of the no-build surfaces**: judge before any of them takes over a route (Alexander, 2026-07-28: "it's close but the UX feels a little off"). ([dossier](docs/board-dossiers.md)) #frontend #ux
  - [ ] `/admin/sprigs` vs `/pages/admin/sprigs` and `/admin/diagnostics` vs `/pages/admin/diagnostics` are both live — same data, same deployment — so judging is the cheapest it will ever be
  - [ ] A green suite is the WEAKEST evidence here: a 13/13-green autoscroll broke on a real trackpad, and the "Show me how to fix this" button passed every assertion while doing nothing
  - [ ] `scripts/manual-check.sh` boots a seeded instance with both live (`--graft-ui` for the marketplace slot)
  - [ ] Judge, not assume:
    - [ ] top-fixed CSS toasts vs toast library
    - [ ] `<details>` remedy vs modal
    - [ ] absolute vs live-relative timestamp
    - [ ] whole-panel swap vs patch
    - [ ] branding preview shows SAVED values, not as-you-type
  - [ ] Branding colour pair now tested both directions — human check narrows to: swatch opens the OS dialog; picking a colour feels immediate
  - [ ] Run it with someone who has not been building it
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
  - [x] _Floor part 1 of 3 done 2026-08-02: fonts and icons −934 kB decoded on every SvelteKit route (spread 0.0 kB; floor 7,576.0 → 6,642.5 kB, agents-legacy −1,056, server-rendered pages 0.0). Archivo 652 → 187 kB, Vazirmatn 241 → 111 kB plus a `unicode-range` so it loads only when Persian text is present; icon masters 512 → 256 px at 45,710 bytes. First-visit win only — `/api/models` still never caches. Archived → docs/completed-todos.md._
  - [x] _Two-sided `unicode-range` guard shipped (`cypress/e2e/font-unicode-range.cy.ts`): structural for too-wide (served stylesheet scopes the face to Arabic), behavioural for too-narrow (Persian text must pull the font), both proved able to fail; trap — the minifier rewrites `U+0600-06FF` as `U+6??`. Archived → docs/completed-todos.md._
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
  - [ ] **A prompt stored without a leading slash can never be fetched, edited or deleted — and every UI-imported prompt is stored that way** (found 2026-08-02 by the Prompts guard-rail). #backend #critical
    - [ ] Reproduced against a throwaway container; production snapshot unaffected — all 8 rows carry the slash
    - [ ] `Prompts.insert_new_prompt` stores `command` verbatim while three readers look up `f"/{command}"` (`routers/prompts.py:99`, `:126`, `:161`)
    - [ ] `Prompts.svelte`'s import handler strips the leading slash, so imported prompts are permanently undeletable and the UI shows no error
    - [ ] Normalise at the write points — `insert_new_prompt` and `update_prompt_by_command` — not the three readers
    - [ ] One-line repair for existing rows lacking the slash
    - [ ] The no-build panel must NOT port this: it normalises on lookup
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
  - [x] _Parity gate earned its keep 2026-08-02: the Agents empty state dropped the `agents-list` container — invisible to every behavioural spec (`workshop-agents.cy.ts` seeds three agents first), visible to the gate that reads hooks. Fixed by one always-present container, `{% else %}` deleted; parity 8/8, Agents 9/9. Archived → docs/completed-todos.md._
  - [x] _Startr Swap shipped 2026-08-09: links and forms swap in place via `pages/assets/startr-swap.js` (11,932 B raw / 5,343 gz vs htmx 50,917 / 16,367); `/settings/calendar` hollowed; suite 46 specs / 234 tests / 190 passing / 0 failing / 4m10s; `make startr_swap_check` runs in `gauntlet_full`; record `docs/decisions/2026-08-09-startr-swap-link-swapping.md`. OPEN: startr.style's licence conflict (LICENSE AGPL-3.0 / LICENSE.txt MIT / package.json ISC) blocks publishing, and nobody has reviewed any of it. Archived → docs/completed-todos.md._
  - [ ] **A 166 kB favicon, a 166 kB splash and a 636 kB unsubsetted `Archivo-Variable.ttf` ride every cold page load** (found 2026-08-02 in the workshop top-25). #frontend #perf
    - [ ] Reopens the line-395 `/icons/` "not perf" call, which judged the file on disk
    - [ ] Just under 1 MB before anything renders, on the SPA and the server-rendered pages alike — PNG does not compress again on the wire, and a favicon is 16–48 px
    - [ ] Cheap and separable from the migration: resize the icon set to the sizes actually declared
    - [ ] Subset the font (line 105 already proposes automating the Cypress fixture copy)
  - [ ] ~~**Agent avatars are uncompressed PNG data URIs inline in the list payload**~~ — REFUTED 2026-08-01 by the snapshot. #frontend #perf
    - [ ] Only 16 of 324 `model` rows carry a data URI and all agent `meta` totals 868 kB — the third inference (after the 22 MB WASM and the markdown libs) that read perfectly and measured false
    - [ ] Keep the cheap format fix as its own item: `toDataURL('image/webp', 0.8)` at slot-matched dimensions instead of default PNG at 250×250 (`ModelEditor.svelte:366`)
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
  - [ ] **Mid-term: rebuild the chat core as an htmx flow, not a ported island** (Alexander, 2026-07-27). #frontend
    - [ ] The port is priced at 17,591 lines for a 15–30% cut
    - [ ] htmx-first has the server own the conversation and send fragments, only the token stream stays vanilla — Phase S proved that half in ~260 lines, abort semantics included
    - [ ] A hypothesis with two Phase 0 datapoints; do NOT re-plan the phase order until one fragment surface is migrated and measured
    - [ ] Phase 1 cookie bridge — fragments need the token off localStorage
    - [ ] The non-proxying browser driver Phase S made a condition
    - [ ] One migrated, measured fragment surface — the datum that settles it
  - [ ] Reimplement the flow canvas (`@xyflow/svelte`) framework-free
  - [ ] Slogan precision: "org-owned" not "user-owned"; keep yjs local-first for the editor #brand

### Founder Bio & Provenance

- [ ] **Etsy / islands provenance — firm up the sources**: make the "employee #4 / built the Etsy Mini / called them islands" bio citable. #brand #provenance
  - [ ] Public today: #4 (Fred Wilson/USV 2006, via zh.wikipedia); the Etsy Mini is a documented island-shaped widget
  - [ ] Detail in the `reference_etsy_islands_provenance` memory + the plan's provenance appendix
  - [ ] Retrieve the archived Fred Wilson / USV 2006 post from archive.org (the usv.com URL now 404s) — locks the #4 primary source
  - [ ] (Alexander) Confirm true hire order — recollection is possibly earlier than #4 (Stinchcomb joined later; came on ~after Forman, ~with Nuzzolillo)
  - [ ] Find receipts for Etsy Mini authorship (publicly credited to Etsy collectively)
  - [ ] Find evidence of internal "islands" vocabulary predating the 2019 public coinage

---

## Backlog

_Items deferred to a later planning cycle. Move here from TODO when deprioritized._


- [ ] **Optimize the board register pass** (Alexander, 2026-08-15): make the weekly pass cheap — or unnecessary at the source. #dx
  - [ ] A `scripts/gates/` check (the `docs-targets.sh` / `--self-test` shape) refusing commits that add open TODO.md lines >350 ch — stops regrowth where it starts.
  - [ ] Extract the pass tooling (scout, rewrite contract, token verifier, splice) from `docs/board-register-method.md` into `scripts/` so any repo runs it in one command.
  - [ ] Decide whether TodoScope itself should flag over-length cards (upstream: `~/bin/TodoScope` `kanban.py`).
  - [ ] Decide automation: a scheduled weekly agent per repo, or the manual `/todo-scope` cadence.

- [ ] **Share cards beyond try.sage — and the branding problem they run into** (Alexander, 2026-08-03): any default card outside try.sage must be the operator's, not ours ([dossier](docs/board-dossiers.md)). #frontend #brand
  - [ ] Only `pages/templates/try-sage.html` carries a social card (gated on `WEBUI_URL`, Sage.is-branded 1200×630 JPEG)
  - [ ] The SPA shell `app/src/app.html` stays unbranded by decision (`try-sage-welcome.cy.ts` asserts it)
  - [ ] Decide first which surfaces are shareable at all — a pasted `/admin/diagnostics` or `/workshop/agents` link resolves to a login, so a card there advertises the instance's existence
  - [ ] Weigh (a): operator-supplied `og_image_url` in the branding panel beside the existing seven, zero generation
  - [ ] Weigh (b): request-time generation from `title`, `subtitle`, `logo_url`, `primary_color`/`accent_color` — the composition `tools/og-card/card.html` does by hand
  - [ ] Weigh (c): neutral unbranded default, overridden by (a)
  - [ ] Prerequisite: tags stay absent, never half-emitted, when unconfigured — the try.sage guard-rail invariant
- [ ] **Version and vendor startr.style — the reasons keep accumulating** (Alexander, 2026-08-01): vendoring a pinned copy answers all four reasons at once and deletes the egress line from `shell.py` ([dossier](docs/board-dossiers.md)). #frontend #perf #startr-style
  - [ ] Do it after the no-build migration settles, so it pins against a stable surface
  - [ ] (1) Unversioned URL — SPOF by construction; a `startr.style/style.css` 5xx renders every consumer naked
  - [ ] (2) No SRI
  - [ ] (3) An air-gapped Rootstock gets unstyled chrome permanently — zero-egress is a case we sell — and the load is the one off-machine reach on an ordinary page load, telling startr.style someone opened an admin page
  - [ ] (4) The agents row menu overlays via `--pos:absolute`; with the framework blocked it falls into flow and shoves its neighbours — the bug positioning fixed, reappearing offline
  - [ ] Reason (4) is new in kind — BEHAVIOUR now depends on the CDN, not just appearance
- [ ] **startr.style grid breakpoint gap**: neither grid system spans the full breakpoint ladder (found 2026-08-01; Alexander: backlog it, do not patch the framework yet). ([dossier](docs/board-dossiers.md)) #startr-style #docs
  - [ ] `.grid` takes column counts — `--col-xs` (440px), `--col-sm` (640), `--col-md` (768), `--col-lg` (1024) — with no `--col` base and no `--col-xl`
  - [ ] The prop system's `--gtc` has base/`-sm`/`-md`/`-lg`/`-xl` but no `-xs`, so a layout wanting both a 440px tier and a 1280px tier must mix the two systems
  - [ ] Upstream fix: a handful of lines in `src/static/style.css`; one fix serves every consumer — real gap, not a blocker (the agents list went flex-wrap at zero cost)
  - [ ] Document the 440px `-xs` tier in the `/startr-style` skill prop tables — they list only `-sm`/`-md`/`-lg`/`-xl`/`-pt`
- [ ] **One-click GUI installer + code signing** (captured 2026-07-17): a double-click installer for Sage.is AI-UI (+ its Rootstock™/Sprig™ runtime) for people who won't touch a terminal — not just the `ai-ui` brew CLI. #onboarding
  - [ ] Load-bearing prerequisite: **software signing**, or the flow dies at the OS "unidentified developer / can't be opened" warning (exactly the audience that bails)
    - [ ] macOS: Apple Developer ID + **notarization** (+ stapling) of the `.app`/`.dmg`/`.pkg`
    - [ ] Windows: **Authenticode** (ideally EV) to clear SmartScreen
  - [ ] Relates to the `ai-ui` brew formula + Developer-Mode onboarding; prior art to mine is Osmantic ODS (item below)

- [ ] **Review Osmantic ODS for onboarding ideas** (captured 2026-07-17): [github.com/Osmantic/ODS](https://github.com/Osmantic/ODS) — "Osmantic Deployment System"; adjacent competitor; onboarding is their strength. #onboarding
  - [ ] NOT just a wizard: a full local-AI-server orchestrator bundling **Open WebUI** (same lineage as us) + llama-server + LiteLLM + n8n + Whisper + Kokoro + Qdrant + SearXNG + ComfyUI as Docker containers
  - [ ] Mine:
    - [ ] Single-command zero-prereq installers (bash + PowerShell) with GPU auto-detect → model selection
    - [ ] A **bootstrap "first chat in <2 min"** mode (vs. our wizard's up-front model downloads)
    - [ ] A management dashboard
    - [ ] **Plug-and-play service folders** that rhyme with Sprigs™
  - [ ] Our edge stays the slim Rootstock™ + zero-egress Sprig™ runtime + marketplace
  - [ ] Feeds the one-click-installer item above

- [ ] **Configurable sprigs + sidecar-sprig variant** (captured 2026-07-18): sprigs carry SETTINGS (per-entry schema — e.g. a service `url`) plus a **sidecar sprig** kind that points at an operator-run external service instead of shipping an artifact. #bonsai
  - [ ] Concrete driver: the Docling *standard* sprig is ~5GB (docling-serve hard-pulls `docling-jobkit[ray,rq,vlm]` → ray/codeflare/kubernetes)
  - [ ] A sidecar variant (operator runs docling-serve, the sprig just sets `DOCLING_SERVER_URL` from a settings field) is the pragmatic path
  - [ ] Offer BOTH standard (in-container, zero-egress) + sidecar for tika/docling
  - [ ] This is the spec's currently-unimplemented `delivery: service-endpoint` shape
  - [ ] Work:
    - [ ] (a) per-sprig settings schema + Admin UI field + persistence + dispatch read
    - [ ] (b) service-endpoint/sidecar delivery that skips the pull and points capability config at the URL (sidecar "graft" = "save URL")
    - [ ] (c) standard + sidecar catalog entries

- [ ] **Tighten the Vite build**: it eats ~half the image build — full image build measured 3m37s with the Vite frontend stage taking roughly half (captured 2026-07-15 during the 3.0.0 release). #perf
  - [ ] The cost doubles in `release_smoke` (native + amd64 builds) and the amd64 side pays QEMU tax on top
  - [ ] Levers, roughly in order of payoff:
    - [ ] (1) the frontend build output is arch-neutral JS/CSS/wasm — build it ONCE and COPY the same `build/` into both arch images instead of re-running Vite under emulation
    - [ ] (2) buildx cache mounts for `node_modules` + `.svelte-kit` + Vite's cache dir so unchanged frontends skip the work
    - [ ] (3) Dockerfile layer ordering so backend-only changes never bust the frontend layer
  - [ ] Sourcemaps are already off in production builds (6c393d9)
  - [ ] **NOTE:** vite specific solutions may exist or svelte upgrades

- [ ] **Job queue for long-running processes** (idea captured 2026-07-06): no unified queue, no retry, no concurrency caps, no visible progress. ([dossier](docs/board-dossiers.md))
  - [ ] Knowledge-base population/reindex, image generation, model downloads, bulk transcription, and big uploads all run as synchronous requests or fire-and-forget threads
  - [ ] Ad-hoc status today: `MODEL_DOWNLOAD_STATUS` dict, per-request `ThreadPoolExecutor` in audio.py
  - [ ] Sequenced as unlock #4 (last) for the real-estate engagement 2026-07-30 — the November commitment needs no software; promote when a staged beat must become a real one
  - [ ] Settle first: DB-backed in-process queue (single-container fit, Bonsai™-friendly) vs redis-backed (already a dep) — lean DB-backed until multi-worker is real
  - [ ] Build: job table (id/type/owner/state/progress/error) + bounded worker pool + one status endpoint (poll or SSE)
  - [ ] Surface running jobs in admin diagnostics and the requesting user's UI
  - [ ] Fold in prior art: the download-watchdog TODO (stalled-download detection) and the upload/download UX memories (progress bars, time estimates)
- [ ] **Spend/usage budgets per user AND per API key** (idea captured 2026-07-06): a shared API key spends indistinguishably from its owner with no caps. ([dossier](docs/board-dossiers.md))
  - [ ] Load-bearing for workshops: cost containment on shared instances
  - [ ] Cap the try.sage trial's hidden Groq connection — uncapped per user
  - [ ] Sequenced as unlock #2 for the real-estate engagement 2026-07-30: a paying customer's instance goes live with hosted models and three people sharing it
  - [ ] Two ledgers, per-user and per-key (the key is the accounting unit when shared)
    - [ ] Request counts + token usage + upstream cost estimates per model/connection
  - [ ] Enforcement
    - [ ] Soft cap: warn banner/email
    - [ ] Hard cap: 429 with a clear "budget exhausted" body
    - [ ] Admin-settable defaults + per-user overrides
    - [ ] Monthly reset or rolling window
  - [ ] Admin UI: usage table sortable by user/key/model
  - [ ] User UI: own usage + remaining budget + per-key breakdown, so a leaked or greedy shared key is visible and revocable
  - [ ] Later: Space-level budget as the natural third ledger (Spaces multi-tenancy)
- [ ] **`e2e_watch`: replace noVNC with WebRTC**: swap the VNC hop for a WebRTC stream — lower latency, no websockify middleman, plays nicer through tunnels. #tests
  - [ ] `make e2e_watch` serves the interactive Cypress GUI via Xvfb → x11vnc → noVNC (`scripts/e2e/watch/`)
  - [ ] Same wrapper-image shape; only the transport layers in `scripts/e2e/watch/Dockerfile` + `entrypoint.sh` change
  - [ ] Decided 2026-07-02 with the P0/P1 Cypress revival
- [ ] **`sprig-test-cypress` self-test graft prototype gate**: one-shot `transport: none` dev-family Sprig™ that runs the e2e suites against its own rootstock loopback. #tests #bonsai
  - [ ] Reports into Admin → Diagnostics ("Self-test: N/N ✅")
  - [ ] Prototype gate first: Electron/Chromium headless closure on the Wolfi base (X11/GTK libs, ~500MB–1GB artifact, per-arch)
  - [ ] Kills the Cypress-binary CDN pull (north star)
  - [ ] Greenlight pending after 8.I.4/8.I.5

- [ ] **Apple Sign-In with lazy-JWT client_secret rotation**: add Apple as the fourth OAuth provider; regenerating the client_secret JWT on every login designs out the 6-month Apple JWT expiry footgun. ([dossier](docs/board-dossiers.md))
  - [ ] ES256 with the `.p8` key is sub-millisecond — no scheduler or persisted JWT state
  - [ ] Hard prerequisite: Apple Developer Program ($99/year)
  - [ ] Spike (1-2h): confirm authlib `StarletteOAuth2App.client_secret` is mutable per-request; if cached, inject the Authorization header just-in-time via a `compliance_fix` hook.
  - [ ] Backend `apple_oauth.py`: JWT generator + P8 parser + config validator that signs a throwaway JWT at save-time, so a bad key fails before sign-in.
  - [ ] Wire into `OAuthManager.handle_login`/`handle_callback`: regenerate JWT, swap into `client.client_secret`, call authlib as normal.
  - [ ] Handle Apple's `response_mode=form_post` callback (POST, not GET)
  - [ ] Capture first-time-only name/email (returning users get only `sub`)
  - [ ] Admin UI in `OAuthSettings.svelte`: Team ID + Key ID + masked P8 textarea; surface the save-time signing failure as an inline error.
  - [ ] Frontend: Apple button + icon in the login provider selector.
  - [ ] Test loop: cloudflared/ngrok tunnel (Apple requires HTTPS, no localhost) + Apple Developer sandbox app.
- [ ] **Admin-driven OAuth user pre-link / org-wide provisioning**: OAuth admission today is `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` (implicit email-match) or `ENABLE_OAUTH_SIGNUP` (auto-create at `role=pending`); neither covers "invite Alice, she signs in with Google". Two layers, smallest first. ([dossier](docs/board-dossiers.md))
  - [ ] Admin invites by email: Admin → Users → "Invite" creates a user with a chosen role plus `oauth_only=True`, `linked_provider=null`; first OAuth login links `oauth_sub` to that record — the merge-by-email code path gated on the invite flag, not the global toggle. Closes the raw-403 path.
  - [ ] Org-level bulk linking: CSV upload or Google Workspace / Microsoft Entra SCIM pull of `email,role,group` rows; same callback linking path. For workshop cohorts and school deployments.
  - [ ] Invite expiry + revocation: invites with no linked `oauth_sub` after N days surface in the admin UI for cleanup.
  - [ ] Audit log entry per link event, e.g. "Alice's Google sub linked to her invited record on 2026-06-01".
  - [ ] Depends on the first-time-OAuth UX TODO ([above](#oauth-ux)) landing first.
- [ ] **History purge for excluded hidden artifacts**: After the root hidden-artifact allowlist lands and the team reviews scope, run BFG Repo-Cleaner or `git filter-repo`, rotate any exposed secrets, and coordinate clone remediation for anyone with an existing copy of the repo.
  - [ ] Confirm which previously committed hidden artifacts must be purged from history
  - [ ] Prepare the team runbook for rewrite, force-push, and clone remediation
  - [ ] Rotate any credentials exposed by now-excluded hidden artifacts

- [ ] **try.sage Tutorial Video Production**: (Alexander Somma + Izzy Plante) — Content work, not code.
  - [ ] Pick individual videos from the [working playlist](https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u) for each of the 6 default tutorial steps.
  - [ ] Populate `TRY_SAGE_TUTORIAL_STEPS_JSON` per workshop deployment with the chosen URLs and step descriptions.
  - [ ] Publish the Custom Sage tutorial content package: three short videos plus a follow-up email with system prompts.
  - [ ] Keep system-prompt disclosure only in the dedicated system-prompt video. Swap that one video per team session without a codebase release.

- [ ] **Buff Out the Default First-Run Landing Page**: try.sage ships a polished welcome (persona picker, banner, branded imagery, tutorial overlay); a fresh self-hosted install lands on a much thinner page. Port the pieces, minus the trial-only bits. ([dossier](docs/board-dossiers.md))
  - [ ] Audit today's try.sage welcome (`TrySage*` in `app/src/lib/components/`): copy, imagery, tutorial-step cards, layout, animations.
  - [ ] Split trial-only (banner countdown, persona switcher, magic-link QR) from any-first-run (welcome card, "what to try first" buttons, tutorial overlay, branded slideshow continuity).
  - [ ] Design the post-wizard landing: one-card welcome with "Start a chat", "Set up Ollama", "Create a Space", "Invite users" CTAs that link into the real flows.
  - [ ] Default tutorial overlay (same component as `TrySageTutorial`, new content): where chats go, where data lives, how to add a model, how to invite users.
  - [ ] Localize copy via i18n.
  - [ ] Vitest spec: auto-show + dismiss + replay, parallel to the try.sage tutorial spec.
  - [ ] "Replay welcome" admin escape hatch outside trial mode — sibling to the existing Trial Mode tab.
- [ ] **Provider logos for remote models**: agents and remote models show no brand icon (a name at most) — ship provider logos as the visual layer on PK-1's `is_external` + `provider_label`. ([dossier](docs/board-dossiers.md))
  - [ ] Local engines (Ollama, etc.) in the same icon set for consistency
  - [ ] Map `provider_label` → logo asset: known-provider set (Anthropic, OpenAI, Google, Mistral, Meta, Ollama) plus a neutral fallback for unknowns.
  - [ ] Render in the model selector, response bubbles, and Space agent messages — the same surfaces PK-1 badges Local/External.
  - [ ] Icon-only display option for agents with no avatar, so a remote-backed agent still carries a brand mark.
  - [ ] License-clean marks only: official brand assets where permitted, or simple-icons / public-domain
    - [ ] Document the source per logo
    - [ ] Cross-check the slideshow image-licensing discipline from Codebase Cleanup
- [ ] **Learning Visibility Dashboard**: Mentioned in `the-arsonists-smoke-detector.md`. We need to build this as we are publishing the article soon to the sage.education resource page.

- [ ] **Alex bio update** (Alexander Somma): Add Alex's background to the sage.is/about and sage.education pages — currently only Izzy's story appears. Should include Etsy backend, teaching career, and CTO role.

- [ ] **Docker Image Slimming (Pinned / Paused)**: (Alexander Somma)
  - _Shipped: hit the ~2.5 GB target (down from 9.7 GB). Archived 2026-08-15._
  - [ ] Hit the ~1.5GB base-image target after trimming heavy transitive deps

- [ ] **Dockerfile: stop running pip as root**: every `make it_build` prints the root-user pip WARNING from the runtime stage — standalone fix is small.
  - [ ] The warning: `WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager`
  - [ ] Fix: switch pip installs into a venv (`python -m venv /opt/venv` then `pip install …` against that venv)
  - [ ] Or add a non-root build user before the pip step
  - [ ] Bundled with the broader "non-root container" hardening if/when that lands

- [ ] **CI/CD Pipeline**: Gated releases, scanning, and regression tests
  - [ ] `make install_dev` — auto-install dev tools via Homebrew
  - [ ] `make scan_container` — trivy image scanning (post-build)
  - [ ] `make lint` — eslint + prettier + black rollup
  - [ ] Gate release finish on passing DB tests and scans
  - [ ] Support the same gated release flow locally or on CI
  - [ ] Staging CapRover instance for pre-prod testing
    <!-- inline: Makefile:572 -->
  - [ ] Selenium-driven browser regression tests
  - [ ] OWASP ZAP DAST via `make scan_dast`

- [ ] **Build System Evaluation**: Consider alternatives to Make
  - [ ] Evaluate migrating Makefile to a cleaner build tool (Rake, Invoke, or Just)

- [ ] **Auto Reset Mode (Trial Environments)**: Mostly delivered by try.sage. Two gaps remain — see subitems. Reference: `docs/try-sage-deployment.md`.
  - _Shipped: reset env vars, selective lifespan wipe (chats + files, KBs/accounts persist), banner countdown + warning state, admin extend/reset endpoints with audit lines. Archived 2026-08-15._
  - [ ] **Post-reset confirmation messaging** — when the auto-reset fires, signed-in users currently see no signal. Add a one-shot toast or banner state: "Trial reset complete — chats and uploads cleared." Drive it from a `try_sage.last_reset_at` timestamp the frontend compares against `localStorage.try_sage_last_seen_reset`.
  - [ ] **Tests for reset timing and message visibility** — pytest spec for `periodic_try_sage_reset` (mock the clock, assert selective wipe runs at the right tick); Vitest spec for `TrySageBanner` countdown formatting and color-shift threshold.

- [ ] **Full Regression Testing Suite**: End-to-end coverage for core user flows, integrations, and release confidence
  - [ ] Standardize Svelte unit/integration tests on Vitest, matching current Svelte guidance
  - [ ] Add jsdom plus `@testing-library/svelte` for component regression coverage where DOM interaction matters
  - [ ] Cover high-risk Svelte components first: chat composer, microphone/transcription flow, auth forms, settings, and uploads
  - [ ] Expand the existing Cypress E2E suite to cover the core happy-path and failure-path user journeys
  - [ ] Define a deterministic test-data strategy for local and CI runs: seeded state where needed, stubs where faster and safer
  - [ ] Evaluate Playwright for cross-browser smoke coverage and trace-based CI debugging before deciding on dual-stack vs migration
  - [ ] Gate releases on a tiered regression pipeline: fast Vitest checks first, browser regressions after, smoke coverage on release builds
  - [ ] Document how to run each regression layer locally and in deployment pipelines

- [ ] **Audio Regression Testing Suite**: Deterministic voice-input coverage across recorder, transcription, and chat-input handoff. ([dossier](docs/board-dossiers.md))
  - [ ] Define the audio test pyramid: unit logic, component behavior, browser E2E, limited real-device smoke
  - [ ] Build a golden audio corpus: clean speech, silence, noisy, clipped, accented, low-volume samples
  - [ ] Feed known audio files as fake microphone input in browser tests; no live human mic in CI
  - [ ] Auto-grant mic permissions; verify recording state transitions, processing UI, transcript insertion into chat input
  - [ ] Cover failure paths: permission denied, empty transcript, transcription failure, canceled recording, timeout
  - [ ] Assert transcripts via normalized text matching where exact punctuation is unstable
  - [ ] Decide which paths run real backend transcription vs mocked/stubbed responses
  - [ ] Evaluate Playwright: media permission control, fake mic input, cross-browser smoke, trace debugging
  - [ ] Keep a small manual/staged real-microphone smoke suite; never a required CI gate
  - [ ] Document local, CI, and staging runs: browser flags, fixtures, expected assertions
- [ ] **Backend Rewrite Research**: Evaluate framework options and build contract tests
  - [ ] Review `docs/backend-rewrite-research.md` with team
  - [ ] Phase -1: Generate contract test suite from OpenAPI spec (private submodule)
  - [ ] Phase 0 spike: chosen framework + streaming Ollama proxy
  - [ ] Team decision: Go + PocketBase, Rust + Loco, or Python + Django?

- [ ] **Open WebUI Fork Maintainer Outreach**: Contact the six BSD-3/MIT fork maintainers shortlisted from 32 forks in `docs/outreach/open-webui-forks.md`. No fork runs its own community channel — every README points at the upstream Open WebUI Discord — so Sage.is AI can consolidate the cohort. ([dossier](docs/board-dossiers.md))
  - [ ] Review the shortlist with the team; prioritize first contacts
  - [ ] Draft a generic outreach template plus per-fork customization for the top three
  - [ ] Contact `blascerecer/open-webui` (101 stars, BSD-3, MCP bridge) — direct overlap with Sage.is AI's MCP work
  - [ ] Contact Public AI Movement (`forpublicai`), hello@publicai.network — strongest mission match, "AI as public infrastructure"
  - [ ] Contact AMD-affiliated `aigdat/raux` via the GAIA team on LinkedIn — Tier-1 silicon vendor signal
  - [ ] Contact `AI3clauseBSD/claused-webai` (francoisp / headgasket) — most ideologically aligned, building a federation of "former-open" projects
  - [ ] Contact `BochaAI/open-webui-Bocha`, info@bochaai.com — vendor MCP integration angle, geographic diversity
  - [ ] Contact `hasanraiyan/open-webui` (Raiyan Hasan) — indie BSD-3 maintainer with public email
  - [ ] Decide: Matrix room or Discord for the BSD-3 cohort
  - [ ] Refresh `docs/outreach/open-webui-forks.csv` every ~6 months
- [ ] **Finish offload Tier B + native-UI relocations** (2026-06-26): Tier A (cache purge + BuildCruft sweep) plus a manual Movies symlink took host disk from 12% to ~50% available. None of the remaining work blocks Bonsai™. ([dossier](docs/board-dossiers.md))
  - [ ] Tier B `home` from admin shell: `sudo offload --target-home /Users/somma move home --apply`. Reconcile the Music symlink first (points at `/Volumes/Somma 01 Dock Drive/Music`, offload expects `/MovedHome/somma/Music`) — same-volume `mv` + re-symlink, three commands
  - [ ] Tier B `app` (Signal, Obsidian, Steam, Keybase, VSCode, Cursor, Epic, Minecraft) — quit each before firing
  - [ ] Tier B `dev` (CoreSimulator 5.8 GiB)
  - [ ] Relocate the Docker Desktop disk image via native UI (~14 GiB, biggest single win remaining)
  - [ ] Move iMovie, Music, and Photos libraries via native UI (per `offload relocations`)
  - [ ] Track [`Sage-is/homebrew-apps#1`](https://github.com/Sage-is/homebrew-apps/issues/1): `du -sk` → `stat -f %z` verification swap unblocks one-shot `offload move home --apply` on APFS-clone-heavy targets like `~/Movies`; until then, use the manual rsync + stat-verify + symlink dance from the 2.3.4 ship session

---

## Bugs

- [ ] **`surface_budget` floor over ceiling since at least 3.1.0**: `notes-empty` decodes 6,978 kB against the 6,800 kB ceiling — and the 2026-08-10 `3.1.0-amd64` image measures 6,978.6, so the regression PREDATES the 2026-08-17 cleanup sitting (A/B run, same snapshot, 0.5 kB apart). #bug #critical
  - [ ] The gate's own comment records 6,642 kB on 2026-08-02 after the font/icon work — ~336 kB grew back somewhere in 2026-08-02→08-10 and nobody ran `gauntlet_full` across the line.
  - [ ] Heaviest single item: `/api/models?` at 2,702 kB decoded — snapshot-driven, worth checking against the 08-02 figure first; the rest is `_app/immutable` chunks (top four: 764+606+543+411 kB).
  - [ ] The ledger (`app/cypress/perf-routes.json`) is untracked and overwritten per run, so there was no baseline to catch the drift — consider committing a dated copy per release.
  - [ ] Do NOT raise the ceiling to go green; the gate says so itself. Find the 336 kB or earn the raise deliberately.

- [ ] **Branding colors don't reach the page — theme Sprig severs the cascade, no-build shell plumbs nothing** (diagnosed live on :8099, 2026-08-17; approach settled with Alexander same day). Config holds `#b2b1fe`/`#9178cc`; the page feels green anyway. #bug #frontend
  - [ ] Three stacked sources on :8099: grafted `sprig-theme:workshop-bio` (`/themes/active.css`) sets `--primary/--secondary/--links` as GREEN LITERALS + a green-tinted `--color-gray-N` scale; `+layout.svelte:565-570` sets inline purple `--primary/--secondary` (wins those two); stock startr.style derives `--links: var(--primary)`.
  - [ ] Root cause: the Sprig's literal `--links` SEVERS the framework cascade, so inline `--primary` never reaches links; the tinted gray scale covers most surface regardless.
  - [ ] Fix 1 — restore severed props, never duplicate recipes: injection sets `--primary`, `--secondary`, plus `--links: var(--primary)` and `--button-hover: var(--primary)`; the framework's own color-mix recipes re-resolve. No app-side color math.
  - [ ] Fix 2 — no-build shell parity: `pages/shell.py` emits the same `:root{}` block from `app.state.config.BRANDING`; today it plumbs nothing and every panel (the branding panel included) wears framework defaults.
  - [ ] Fix 3 — honest conflict UX, not silent precedence: the branding panel AND `Theme.svelte` show a plain-words warning when a theme Sprig is active, with a one-click prune. ELI5 wording.
  - [ ] Upstream (first-party) fix: theme Sprigs must author `--links: var(--primary)`, not literals — keeps grafted themes brandable; fix `workshop-bio` + the authoring contract in the sprig spec.
  - [ ] Guard: e2e asserts a saved color reaches BOTH a SPA and a no-build page; the drift class is "one consumer honors config, the other silently doesn't".
  - [ ] Inline `<style>` stays CSP-compatible today (`'unsafe-inline'` kept per the CSP card); note in the policy's exception list when that ships.
  - [ ] Found on the way: the no-build shell never loads `/themes/active.css` — a grafted theme dresses the SPA and NOT the server-rendered panels. Decide whether the shell links it (theme parity) or stays deliberately unthemed; today's fix gates shell colors on `SPRIG_ACTIVE_THEME` so the two surfaces at least agree on who wins.

- [ ] **`make lint`'s frontend half is red and always was**: `bun run lint:frontend` (`eslint . --fix`) exits 1 with 9,609 errors (found 2026-08-17 the first time `lint` went otherwise green — the Python half never let it get this far). #bug #dx
  - [ ] The bulk is vendored code eslint should never read: `pages/assets/vendor/htmx.min.js` alone contributes thousands; `dev-reload.js` and `startr-swap.js` carry a handful of real `no-unused-vars`.
  - [ ] The vendored no-build assets under `backend/sage_is_ai/pages/assets/` postdate the eslint config — nothing ignores them.
  - [ ] Fix shape: eslint ignore for `pages/assets/vendor/`, then read the residue honestly.
  - [ ] Note `--fix` in a LINT target mutates the tree on check — same class of surprise the format gate just retired.

- [ ] **Admin models panel tears down on every mutation**: `init()` in [Settings/Models.svelte](app/src/lib/components/admin/Settings/Models.svelte) opens with `models = null` and the whole panel sits inside `{#if models !== null}` — the control just clicked unmounts and a spinner replaces it (found 2026-08-07 by `models-refresh.cy.ts`). #bug
  - [ ] `init()` is called by upsert, toggle, delete and the model editor as well as by mount — correct on first load, wrong for a mutation.
  - [ ] Symptom: the user's cursor is left hovering nothing; a populated list flashes to a spinner and back.
  - [ ] The e2e could not observe a disabled button because the button was not on the page while it was disabled.
  - [ ] Refresh path already fixed (`init` gained a `blank = true` parameter; `refreshModelsHandler` passes `false`) — the other four call sites still blank.
  - [ ] Fix the rest: a one-word change each, but each wants a look at what the surrounding handler does after the await.

- [ ] **`getModels` has no token parameter, yet 33 call sites pass one**: `connections` gets a string, the merge no-ops — direct-connection models are silently never merged; where `base` lands truthy, `/api/models/base` returns 200 with the wrong list (found 2026-08-07). #bug ([dossier](docs/board-dossiers.md))
  - [ ] Signature at [apis/index.ts:52](app/src/lib/apis/index.ts#L52) is `(connections, base, refresh)`; callers spell `getModels(localStorage.token, <directConnections>)`.
  - [ ] The merge at [index.ts:90](app/src/lib/apis/index.ts#L90) iterates `undefined` and no-ops.
  - [ ] Worst path: truthy `base` sends the request to `/api/models/base` ([main.py:1698](app/backend/sage_is_ai/main.py#L1698)) — 200 with the wrong list instead of 404ing where someone would notice.
  - [ ] Fix the 32 remaining call sites. The admin models page is already corrected — `(token, null, true)` → `(null, false, true)`, provably identical since its merge block was a no-op.
  - [ ] Mechanical fix, but it touches the model list on every surface: own commit + full `make e2e_both`.
- [ ] **Four names defined twice in the same module; the first of each is unreachable by name**: each site carries a `# noqa: F811` today — gate green, shadowing greppable, not correct (found 2026-08-06 by the newly adopted ruff gate, `F811`). #bug #gates
  - [ ] `get_all_feedbacks` at [evaluations.py:97](app/backend/sage_is_ai/routers/evaluations.py#L97) shadows the one at :75.
  - [ ] `get_file_content_by_id` at [files.py:550](app/backend/sage_is_ai/routers/files.py#L550) shadows :431.
  - [ ] `get_functions` at [functions.py:50](app/backend/sage_is_ai/routers/functions.py#L50) shadows :40.
  - [ ] All three are FastAPI handlers, so both routes still serve — the decorator registers by path, and only the Python name collides.
  - [ ] The fourth is different and worth reading first: `ENABLE_LDAP` is imported at [auths.py:44](app/backend/sage_is_ai/routers/auths.py#L44) and rebound at :317 — a config import shadowed by a local.
  - [ ] Decide per site: rename the second, or delete the first if it is genuinely dead.

- [ ] **`bump_release_version` leaves `SERVER_TAG` on the previous release**: the bump target updates only `app/package.json` and `README.md`, so `distribution.env` reads `SERVER_TAG=3.0.0` while 3.0.1 is being cut (found 2026-08-06 while readying 3.0.1). #release
  - [ ] `SERVER_TAG` is the canonical server-image version read by the brew CLI, the Makefile fallback and the docs.
  - [ ] The tag still resolves correctly during a release because `GIT_TAG` outranks it in the precedence chain (`Makefile:74`) — the staleness is invisible until something reads the file directly.
  - [ ] The file has three hardlinks — source of truth `homebrew-apps/distribution.env`, mirrored into this repo and `WEB-Sage.Education-docs` — so it must be edited in place.
    - [ ] macOS `sed -i` replaces the inode and breaks the chain.
  - [ ] Either teach `bump_release_version` to rewrite it inode-safely, or add it to the release runbook as an explicit manual step.
- [ ] **A literal `◁think▷` in streamed content freezes client-visible streaming for the rest of the stream**: `tag_content_handler` keeps a zero-capture-group pattern, so `match.group(1)` raises `IndexError` on every later delta before the emit (found 2026-08-08 by the duplication sweep's dead-code lens, adversarially confirmed). #bug
  - [ ] Mechanism: for a start tag not shaped `<...>`, `start_tag_pattern = re.escape(start_tag)` — zero capture groups — so when `◁think▷` appears in content, `re.search` matches and `match.group(1)` raises `IndexError`.
  - [ ] The per-delta try swallows it, but the append already happened — EVERY later delta re-matches and re-raises BEFORE the emit and before the realtime save.
  - [ ] The reader sees a frozen message until the final done event delivers everything at once, with `◁think▷` rendered as text.
  - [ ] Kimi-family models emit exactly this tag.
  - [ ] The tuple is cannot-succeed code that also breaks live streaming — worse than dead.
  - [ ] No net covers it; extending `reasoning-tag-fixture.py` with a `◁think▷` case is part of the fix.
  - [ ] Behaviour frozen until the structure work lands.

- [ ] **The two-message title path persists one message and emits another**: the `elif len(messages) == 2` arm persists `messages[0].get("content", user_message)` — the FIRST — but emits `message.get("content", user_message)` — the LAST — so the stored chat title and the one the reader watches arrive can differ (found 2026-08-08 by the sweep). #bug
  - [ ] Found while proving the title envelope cannot join the follow-ups/tags task runner.
  - [ ] A code comment now marks the emit site.
  - [ ] Frozen; fix belongs to [Unfreeze the ledger].

- [ ] **`response.background()` runs twice for the original streaming response**: `stream_body_handler` awaits it at its tail for every response it drains; `response_handler` awaits it again on the same original after the retry loops — awaiting a Starlette `BackgroundTask` twice runs the wrapped callable twice. #bug
  - [ ] Found 2026-08-08 during the chat-path weight census, while classifying it as dead code — it is not dead, it is a double-execution.
  - [ ] Continuation responses are spared — only `stream_body_handler` touches those.
  - [ ] Harmless if the background is an idempotent cleanup; not verified.
  - [ ] Deleting the second call is a behaviour change, so it is frozen with the rest.
- [ ] **Six JSON parse sites scrape from the first `{` to the last `}`; the prompt template teaches the model to break it**: `config.py:1584` ends the title template with a literal example object, so a model that restates the format emits two objects — exactly the input the scrape fails on. #bug ([dossier](docs/board-dossiers.md))
  - [ ] Found 2026-08-08. Clean and fenced input parse; two objects in one reply do not.
  - [ ] These calls run on the task model, which operators set small, and small models restate the format most.
  - [ ] Worst site is RAG queries ([middleware.py:1041](app/backend/sage_is_ai/utils/middleware.py#L1041)): on failure it sets the entire model reply as the retrieval query, silently degrading RAG.
  - [ ] (1) Set `response_format` on the task calls — `utils/payload.py:350-361` already converts it to Ollama's `format`, and no task call sets it. Behaviour: sequence after the structure work.
  - [ ] (2) One parser as the floor in a new `utils/llm_json.py` for providers that ignore it — strip fences, try the whole string, scan for balanced objects. New file, moves no citation; can land any time.
  - [ ] (3) Drop the example object from the template. Behaviour: sequence after the structure work.
  - [ ] Trap: a shared helper is NOT the fix — in the restated-format case both objects are valid JSON and both carry the key, so no parser can tell them apart.
  - [ ] The six sites, consolidated 2026-08-08 into one `slice_json_object` helper, behaviour byte-identical:
    - [ ] [797](app/backend/sage_is_ai/utils/middleware.py#L797) tool calling
    - [ ] [955](app/backend/sage_is_ai/utils/middleware.py#L954) image prompt
    - [ ] [1042](app/backend/sage_is_ai/utils/middleware.py#L1041) RAG queries
    - [ ] [1498](app/backend/sage_is_ai/utils/middleware.py#L1499) follow-ups
    - [ ] [1543](app/backend/sage_is_ai/utils/middleware.py#L1543) title
    - [ ] [1572](app/backend/sage_is_ai/utils/middleware.py#L1572) tags
- [ ] **Mid-stream model switch never reaches retries**: `stream_body_handler` assigns `model_id` at [middleware.py:1786](app/backend/sage_is_ai/utils/middleware.py#L1786) without `nonlocal` — the retries still read the originally requested model while the DB records the selected one. #bug
  - [ ] Only `content`/`content_blocks` are declared `nonlocal` (at 1749–1750), so the assignment is function-local.
  - [ ] The retries: tool-call at 2068, code-interpreter at 2163.
  - [ ] Found 2026-08-04 during the chat-path seam census; fix deferred — behaviour frozen until the structure work lands (`charts/chat-path-restructure`).
  - [ ] Line numbers restated 2026-08-06 after the three tightening passes.

- [ ] **`features.web_search` is a live `NameError`, not a feature**: [middleware.py:1247](app/backend/sage_is_ai/utils/middleware.py#L1247) calls `chat_web_search_handler`, which does not exist — `POST /api/chat/completions` with `{"features": {"web_search": true}}` returns a 500. #bug ([dossier](docs/board-dossiers.md))
  - [ ] Found 2026-08-04. The definition arrived commented out in `bbb4f10` and `hasattr` confirms False.
  - [ ] Unreachable from the UI: `Chat.svelte:1716` gates on `$config?.features?.enable_web_search`, which the backend never emits.
  - [ ] Reachable from the API: `features` is popped off the request body unvalidated.
  - [ ] Delete the branch — do NOT wire it up. Decision confirmed 2026-08-06: search moved to OpenAPI tool servers (`TOOL_SERVER_CONNECTIONS` + `utils/try_sage_tool_servers.py`).
    - [ ] `ENABLE_WEB_SEARCH` exists nowhere in the backend.
    - [ ] `retrieval/web/` is down to `utils.py`, imported once for `get_web_loader` in `routers/retrieval.py:89`.
  - [ ] Validate `features` off the request body — every unknown key is silently accepted, which is what makes the branch reachable at all.
  - [ ] Both fixes are behaviour: sequence after the structure work.
- [ ] **`ENABLE_REALTIME_CHAT_SAVE=true` leaves reasoning stuck on "Thinking…" for the whole generation**: the flag changes what the browser receives, and the reasoning close rides the first content delta — the disclosure spins until the terminal `done: True` event. ([dossier](docs/board-dossiers.md)) #bug
  - [ ] Flag on: text deltas ship raw and the frontend appends `choices[0].delta.content` ([Chat.svelte:1240](app/src/lib/components/chat/Chat.svelte#L1240)).
  - [ ] Flag off: the frontend replaces serialized blocks ([Chat.svelte:1276](app/src/lib/components/chat/Chat.svelte#L1276)).
  - [ ] The close rides the first content delta ([middleware.py:1844](app/backend/sage_is_ai/utils/middleware.py#L1844)), so the last serialized snapshot says `done="false"`.
  - [ ] DB is correct both ways (`done="true" duration="1"`; oracle replay of `reasoning-field-then-content.sse`).
  - [ ] Found 2026-08-04, chat-path census; behaviour frozen, logged not fixed.
  - [ ] Same family as the reasoning-block bug below.
  - [ ] Check whether the flag is set on try.sage.is before deciding severity — if it is, users see this now.
- [ ] **The direct-connections admin toggle is advisory, not enforcing**: no request path checks `ENABLE_DIRECT_CONNECTIONS` — an admin who disables direct connections for data governance has not closed the path; any client posting `model_item: {"direct": true}` walks through. ([dossier](docs/board-dossiers.md)) #bug #security
  - [ ] `ENABLE_DIRECT_CONNECTIONS` is read only by `/api/config` ([main.py:1978](app/backend/sage_is_ai/main.py#L1978)) and the admin get/set pair in `routers/configs.py`.
  - [ ] The chat route branches on `model_item.get("direct", False)` off the request body ([main.py:1752](app/backend/sage_is_ai/main.py#L1752)) and that branch skips `check_model_access`.
  - [ ] `utils/chat.py` gates only on `request.state.direct`.
  - [ ] Found 2026-08-04, chat-path census; behaviour frozen.
  - [ ] Enforce the flag on the request path — needs sign-off, closing it narrows product surface.
  - [ ] Not an SSRF: `generate_direct_chat_completion` relays `request:chat:completion` to the BROWSER, which makes the call — triage as an open admin toggle, not server-side model access.
- [ ] **`data: [DONE]` does not terminate the stream loop**: `stream_body_handler` has no case for the sentinel — it fails `json.loads` and is skipped by the `except` at [middleware.py:1926](app/backend/sage_is_ai/utils/middleware.py#L1926); a provider that appends anything after the sentinel gets it rendered. #bug
  - [ ] Content arriving AFTER `[DONE]` is still parsed, appended to the blocks, emitted to the reader and persisted.
  - [ ] Harmless with well-behaved providers, which stop sending.
  - [ ] Pinned in the `done-sentinel-and-noise` oracle golden, which ends with `"Answer survives the noise. trailing after DONE"`.
  - [ ] Found 2026-08-04 while reading the oracle goldens (chat-path chart); logged not fixed — behaviour frozen.

- [ ] **A partial tag reaches the reader for one frame**: when a chunk boundary splits a reasoning tag, the loop emits the fragment raw before the next chunk completes it — cosmetic and brief, but visible. #bug
  - [ ] The `reasoning-tag-inline` oracle golden records a first event whose entire content is `<thin`.
  - [ ] Same family as the chunk-boundary whitespace defect in the reasoning-tag entry below; a tag-aware output buffer would kill both at once.
  - [ ] Found 2026-08-04 while reading the oracle goldens (chat-path chart); logged not fixed — behaviour frozen, and the fix must re-record the golden deliberately.

- [ ] **Pruning the Tika or Docling Sprig™ leaves `CONTENT_EXTRACTION_ENGINE` aimed at a released port**: `supervisor.prune()` reverses no dispatch and the router reset skips tika/docling — worst case a pruned tika permanently re-creates the "unreachable" alarm a previous fix killed. ([dossier](docs/board-dossiers.md)) #bug #sprigs
  - [ ] `supervisor.prune()` ([supervisor.py:1322](app/backend/sage_is_ai/sprigs/supervisor.py#L1322)) reverses no dispatch.
  - [ ] The router reset ([sprigs.py:275-300](app/backend/sage_is_ai/routers/sprigs.py#L275)) covers five `was_active_*` capabilities (embedding, reranker, stt, theme, ui) — tika and docling are absent.
  - [ ] `tika_dispatch.py:29` / `docling_dispatch.py:26` set the engine on graft; nothing unsets it (only other writers: `config.py:2117`, `main.py:1047`, `routers/retrieval.py:873`).
  - [ ] [boot.py:95-99](app/backend/sage_is_ai/diagnostics/boot.py#L95) probes `TIKA_SERVER_URL` whenever the engine is set; neither carries the `sprig-local` sentinel, so the `main.py` restart backstops miss it too.
  - [ ] Found 2026-08-05 (AIML responder charting); reported mechanically in the Gaps section of `docs/sprigs/capabilities.md`, gated by `make sprig_capabilities_check`.
  - [ ] Quick fix: two more `was_active_*` resets beside the five in `sprigs.py`.
  - [ ] Better: a `point_*_off(app, handle)` companion per dispatch module plus one registry read by the graft, boot-reconcile and prune fan-outs — today three hand-maintained copies of one table.
- [ ] ~~**`models-cache.cy.ts` gates a timing quantity, and it now fails on `HEAD`**~~ (2026-08-04, superseded by the entry above — kept for the record of how the wrong answer looked right) ([dossier](docs/board-dossiers.md)) #tests #bug
  - Both assertions compare a round-trip against `CACHED_MAX_MS` 250 ms, measured 810/871 ms on `HEAD` and 912/968 ms with an unrelated change reverted.
  - The machine, not the code, is the variable — the exact flaky-gate failure the `surface_budget` bytes-only doctrine predicts.
  - Suspected cause of the unreproduced 3-failure run earlier on 2026-08-04.
- [ ] **Unclosed reasoning block swallows the model's answer** (Alexander, 2026-08-03; demo-blocking): no close path has an end-of-stream finalizer — worst case the whole answer stays sealed inside the collapsed reasoning block, or private reasoning renders as text. Three variants. #critical #bug ([dossier](docs/board-dossiers.md))
  - [ ] `tag_content_handler` ([middleware.py:380](app/backend/sage_is_ai/utils/middleware.py#L380)) closes only on its opening pair's exact end tag, with no end-of-stream finalizer.
  - [ ] The field-path close is guarded on `if value:` ([middleware.py:1850](app/backend/sage_is_ai/utils/middleware.py#L1850)).
  - [ ] Variant 1, tag drift: any open/close mismatch leaves the block open forever.
    - [ ] `scripts/smoke/reasoning-tag-fixture.py` fails 16 cases across 5 defects (`<thinking>` closed `</think>`, the reverse, `</THINKING>`, `</ thinking>`, never-closes).
    - [ ] A sixth cosmetic case (space eaten at chunk=7, not chunk=1 or 999) explains the reported "not always".
  - [ ] Variant 2, field path — the priority, reproduced from Alexander's capture: the literal `</thinking>` plus the whole answer stay sealed, `done="false"`.
    - [ ] DeepSeek R1 templates pre-fill the opener into the PROMPT; a provider that streams everything through `reasoning` and sends no `content` delta never fires the `if value:` close.
    - [ ] Confirmed 3 ways 2026-08-04 on live code: chat `171f30b9`, 08:34 UTC, production snapshot on `:8102`; a `deepseek-r1-distill-llama-70b` call with 736 reasoning chars and 0 content; a control that closed.
    - [ ] Trigger: a UI-built agent whose system prompt asks for `<thinking>` tags on a native-reasoning provider.
  - [ ] Variant 3 (2026-08-06, `qwen3.5:9b` via Ollama, chat `aafdddab`): a bare `</think>` with no opener arrives in the CONTENT stream and renders as text.
    - [ ] The field path opens AND closes correctly (`done="true"`) first; the field path opens it, the tag path orphans the close.
    - [ ] Not a regression: pre- and post-tightening replays were byte-identical.
  - [ ] Fix (1): end-of-stream finalizer — close any reasoning block still open when the stream ends and surface its content.
  - [ ] Fix (2): treat an unpaired closing tag as an implicit opening at position zero (tag-path variant).
    - [ ] Does NOT cover variant 3 — there, DROP an orphan close tag when a reasoning block already closed in the same message.
  - [ ] Fix (3): widen the close match to any end tag in the list, case-insensitive, `</\s*tag\s*>`.
  - [ ] Remove the `<<thinking>(.*?)>` start-tag strip WITH a fixture case — it eats literal `<<thinking>…>` spans, silently deleting reasoning content.
    - [ ] NOT dead (proven 2026-08-08 after a session deleted and restored it).
  - [ ] Extend the fixture to the field path before trusting it; today it mirrors the TAG path only.
  - [ ] READ FIRST: golden `fixtures/chat-response/reasoning-field-closed-then-orphan.sse` (oracle replays 12 streams) FREEZES the variant-3 leak as it is; read it before changing the tag logic.
    - [ ] Its job is to go RED when fix (2) lands — an implicit open there would mint a second block and swallow the answer.
    - [ ] Line numbers restated 2026-08-04 (stale by ~93 before the −160 dead-handler deletion); re-derive from the quoted source text, not the number.
- [ ] **Model special tokens reach the reader**: the assistant's rendered answer ended with `<｜end▁of▁sentence｜>`, DeepSeek's EOS token, printed as visible text — nothing in the backend strips model special tokens. #bug
  - [ ] Found 2026-08-03 in the same capture as the reasoning-tag bug.
  - [ ] A grep for stop-token or special-token handling across `sage_is_ai` returns nothing.
  - [ ] Every model family has its own set (`<|eot_id|>`, `<|im_end|>`, `<｜end▁of▁sentence｜>`, `<|end_of_text|>`), so the fix belongs at one boundary rather than per-provider.
  - [ ] Worth pairing with the reasoning-tag fix: both are "raw model protocol leaking into prose", both were visible in one screenshot, and both make a demo look unfinished.

- [ ] **The changelog pager spec passes whether the button moves or not** `#critical-gate`: `wizard-changelog.cy.ts` was green against the broken transform version AND the working `margin-left` version — the gap is the environment, not the assertion. #bug
  - [ ] Spec under test: "moves to the other side once the notes run out".
  - [ ] The assertion has teeth against a zero shift: forcing 0 went RED — `expected 0 to be above 367.5`.
  - [ ] What it missed: a transform that applied under the driver but not in the operator's browser.
  - [ ] Decide: make the check discriminate in a real engine, or drop the claim and say the spec covers paging and the label only.
    - [ ] SikuliX is on the roadmap for exactly this class.

- [ ] **The diagnostics page still renders English for every reader**: every other no-build panel binds `translator(request)`, but `diagnostics_panel.py` calls `t(key, {})` at the default locale — a genuine loss for a Spanish operator rather than a no-op. #bug
  - [ ] Re-confirmed 2026-08-01 after the Jinja2 conversion — the templating pass moved its markup but did not thread a locale.
  - [ ] `_library_entries`, `_fix_steps` and `_row` still call `t(key, {})`.
  - [ ] Call sites: [line 81](app/backend/sage_is_ai/pages/diagnostics_panel.py#L81), [88](app/backend/sage_is_ai/pages/diagnostics_panel.py#L88).
  - [ ] Call sites: [89](app/backend/sage_is_ai/pages/diagnostics_panel.py#L89), [144](app/backend/sage_is_ai/pages/diagnostics_panel.py#L144).
  - [ ] Keys are the nested `diagnostics.fix.*` ones whose values are real sentences.
  - [ ] Fix: thread a locale through `_library_block` → `_fix_steps` → `_row` → `_ghost_block`, four signatures deep — why it was not done alongside the wizard panels.
  - [ ] The mechanism is already there; only the plumbing is missing.

- [ ] **`SensitiveInput` hardcodes `id="password-input"`, so a page with two of them mislabels every field but the first**: [SensitiveInput.svelte:27](app/src/lib/components/common/SensitiveInput.svelte#L27) sets a literal `id` — every screen reader announces "Client Secret" for all five fields on `OAuthSettings.svelte`. #bug #a11y
  - [ ] Line 23 pairs it with `<label class="sr-only" for="password-input">`.
  - [ ] `OAuthSettings.svelte` mounts five of them — Google secret, GitHub secret, Microsoft secret, magic-link SMTP password, LDAP password.
  - [ ] Duplicate IDs are invalid HTML; `for` resolves to the first match, so clicking any label focuses the Google field.
  - [ ] Fix: default `id` to a generated value and let callers override — the same shape `Switch.svelte` already uses (`export let id = ''`).
  - [ ] Found while hooking the panel for the no-build migration, not introduced by it.

- [ ] **An evicted Sprig™ is reported as "exited on boot", which is not what happened**: grafting a second cultivar of a capability prunes the first ([supervisor.py:1271-1278](app/backend/sage_is_ai/sprigs/supervisor.py#L1271-L1278)) — the victim is SIGTERMed mid-boot. #bug
  - [ ] It surfaces as `sprig 'minilm-onnx-inhoused' exited on boot (rc=-15)` — `rc=-15` IS SIGTERM, and the supervisor sent it.
  - [ ] Hit 2026-07-30 grafting from the wizard mid-download; the wizard now refuses that path, which does not fix the message.
  - [ ] Two fixes together:
    - [ ] (1) say what happened — "pruned while booting: 'multilingual-e5-large' took over the embedding capability".
    - [ ] (2) capture child `stderr` — it is `DEVNULL` ([supervisor.py:1299](app/backend/sage_is_ai/sprigs/supervisor.py#L1299)), so a cultivar that dies for any other reason leaves no evidence.
- [ ] **Retest knowledge upload on sage.startr.cloud (on 3.0.0 since 2026-07-16)**: the misleading TypeError can no longer occur, but the underlying endpoint fault it masked (engine config or a stale URL/key in the inherited volume) was never diagnosed. Upload once; if it fails, `/admin/diagnostics` now names the real cause. #bug

- [ ] **AI Engine Wizard Embedding Download Has No Stall Watchdog**: when the embedding model fetch from HuggingFace stalls, the wizard sits in `embedding=downloading` indefinitely — a real user has no signal except an idle spinner. #bug
  - [ ] Stall causes: network drop, HF outage, slow link.
  - [ ] No timeout, no retry, no resumable state surfaced to the admin.
  - [ ] `wizard-smoke.sh` catches this externally via `INSTALL_TIMEOUT_SEC`.
  - [ ] Verified still unfixed 2026-08-03: no watchdog or `stalled` state in `routers/retrieval.py`.
  - [ ] Surface HF download progress (bytes, last-byte timestamp) to `request.app.state.MODEL_DOWNLOAD_STATUS` so the status endpoint exposes liveness.
  - [ ] Watchdog in `_download` (`retrieval.py`):
    - [ ] if cache size hasn't grown in N minutes (configurable, default 5), mark status=`stalled`, capture the error.
    - [ ] allow retry via a re-POST to `/api/v1/retrieval/models/download`.
  - [ ] Surface stalled state in the wizard UI with a retry button + "check your connection" hint.

*(Surfaced 2026-05-18 during the cross-arch smoke run when an internet drop wedged the embedding download. The wizard never noticed.)*

- [ ] **Wizard `whisper` status stuck at `pending` after a whisper Sprig™ graft (cosmetic — STT works)**: grafting `whisper-base-ggml` serves STT, but `GET /api/v1/retrieval/models/status` keeps `models.whisper != "ready"` — static analysis says it SHOULD read ready. #bug
  - [ ] STT works through the sprig: `/api/v1/audio/transcriptions` → 200.
  - [ ] `point_stt_at` ([sprigs/stt_dispatch.py:40](app/backend/sage_is_ai/sprigs/stt_dispatch.py#L40)) flips it and IS called by the graft route ([routers/sprigs.py:113](app/backend/sage_is_ai/routers/sprigs.py#L113)).
  - [ ] Single worker; dict seeded ([main.py:1119](app/backend/sage_is_ai/main.py#L1119)); endpoint returns it raw ([retrieval.py:439](app/backend/sage_is_ai/routers/retrieval.py#L439)).
  - [ ] Needs LIVE inspection:
    - [ ] `KEEP=1 make sprig_smoke`
    - [ ] `curl …/models/status` right after the whisper graft
    - [ ] temp log in `point_stt_at`
  - [ ] Surfaced 2026-07-22 by `sprig_smoke`.

- [ ] **Chat Microphone Recording Does Not Populate Message Input**: Recording from the microphone icon in chat does not process speech into the text field used to send messages. Reported 2026-05-11 against a pre-2.3.3 build — reproduce on 3.0.0 first; STT plumbing has changed twice since (whisper Sprig dispatch, wizard cut-over). #critical #bug
  - [ ] Reproduce on 3.0.0; confirm whether capture, transcription, or input binding fails
  - [ ] Trace recorder output into the chat composer state; fix the handoff
  - [ ] Add regression coverage for microphone-to-input behavior in chat

- [ ] **Code fence in chat renders near invisible**: typed or pasted text inside a code fence shows white on light grey. Reported pre-3.0.0 — reproduce first (new chat, backticks + space to open the fence, type; note the low-contrast combinations), then locate the color source and fix. #bug

---
