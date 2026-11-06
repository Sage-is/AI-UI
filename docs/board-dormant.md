# Dormant board cards

Open cards with no date in this quarter (newest before 2026-10-01, or none), moved out of TODO.md on 2026-11-03 so the board shows current work. Nothing here is done. To pick one up, move the card back to its section in TODO.md. Cards tagged #critical or #security, every open bug, and the in-house Sprig hosting card stayed on the board; two superseded ones came here with a note.

### In Progress

- [ ] **Spaces Enhancements**: agent context modes, auto-reply TTL, and multi-user — pulled forward 2026-07-30 as unlock #1 for the real-estate engagement. ([dossier](docs/board-dossiers.md))
  - [x] **Multi-user mechanics VERIFIED by the first Spaces e2e (2026-08-18)**: `spaces-multiuser.cy.ts` 5/5 — admin-created `role:user` member opens the shared space, posts via the socket round-trip, mentions by click, admin sees it.
    - Membership is `access_control.read/write.user_ids`, set at space create; management UI stays admin/facilitator-gated (the principal is the facilitator).
    - Found: the mention dropdown lists exactly `read.user_ids` — an unlisted admin is unmentionable (access bypass ≠ participant).
    - Live-agent variant `live/spaces-live-agent.cy.ts` is opt-in via `CYPRESS_BOT_URL`/`CYPRESS_BOT_KEY` (subdir = excluded from bare `make e2e`).
  - [ ] Agent context mode: `conversation` (last ~5 messages) and `full` (all recent) — `single` already ships
    - Decision record 2026-08-18: ship context modes next; bridge adapter at marketplace time; sidecar is packaging. `docs/decisions/2026-08-18-spaces-agent-integration.md`.
    - Live test rig: pullbots registered on :8099 via `scripts/seed-bot-agents.sh` (`bot9000.Sage-Agent`/`bot9001.Sage-Agent`, key in `.env` `PULLBOT_API_KEY`, never committed).
  - [x] **Auto-reply opened to the whole space (2026-08-18, Alexander's call)**: any member's un-mentioned post answers an armed agent question — was addressee-only; the VA-answers-for-the-principal workflow needs it. One-condition change at `spaces.py:621`; guards unchanged (@mention wins, 2-message window, one auto-reply per post, no agent-to-agent path). `awaiting_reply_from` still records the addressee for future UI/TTL.
  - [ ] Optional per-agent TTL for auto-reply expiration
    <!-- inline: spaces.py:391 -->
  - [x] **Tools from Spaces (2026-09-17)**: `generate_agent_response` sends the row's `meta.toolIds` through `process_chat_payload`; the CRM agent answers with its tool server while the cache is warm
  - [x] Cold boot: `generate_agent_response` fills `app.state.TOOL_SERVERS` when empty (2026-09-17); proof at the next restart, tracked on the Trellis board
  - [ ] **Silverbullet integration into Spaces** — wire the self-hosted Silverbullet PKM/wiki into Spaces. Planning conversation first (architecture, auth, data model), then code.
  - [ ] **Space theming for creator-led visual differentiation** (2026-06-15): creator-only "Theme" tab in Space settings — accent-color picker + optional logo upload, tinting nav chrome and thread accents
    - [ ] Identical-looking Spaces cause mis-posts; load-bearing for workshop facilitators and multi-org Rootstocks
    - [ ] No custom-CSS injection (XSS surface)
    - [x] Peset themes shipped as sprigs (bio = green, math = blue) so non-technical facilitators can theme without picking colors
    - [ ] Explore bundling and offering the presets only for spaces

### TODO / Real-estate segment engagement — first paid deployment (opened 2026-07-30)

- [ ] **Demo setup on try.sage.is**: Spaces access, the Space Agent, the trial model set
  - [ ] Turn on Spaces access for Realtor M.
  - [ ] Diagnose the unresponsive Space Agent via `/admin/diagnostics`. Actionable as of 2026-08-03 — the diagnostics page (2.3.3) and how-to-fix modals (2.3.4) are now live on try.sage.is.
  - [ ] **Decide the trial model set and who pays for the tokens.** Undecided as of 2026-07-30 and it gates the instance provisioning below. Note the hidden Groq connection on try.sage.is is uncapped per user, and three people will share this workspace.

- [ ] **Day-in-the-life walkthrough — staged and labelled as staged**: the proactive beats are outbound-on-a-schedule and **there is no job scheduler** — do not let "does it do that by itself?" get a soft answer.
  - The Telegram adapter (`bridges/adapters/telegram.py`, the most mature at 505 lines) carries the demo.
  - The only `scheduler` hits in the backend are the AUTOMATIC1111 diffusion sampler.
  - [ ] Trigger the beats (weather, stretches, reminders) by hand.
  - [ ] Say out loud that they are staged, and show the queue on the roadmap.

#### Discovery — before any tooling is designed

- [ ] **Discovery questions for Realtor M's brokerage**: the ladder, SOPs, systems, email, a real anchor
  - [ ] **Establish rung one of the responsibility ladder.** Nobody knows yet which task comes off his plate first, and the ladder is unbuildable without it. Candidates raised: inbox triage and drafting, listing/client paperwork, follow-up tracking.
  - [ ] **Assess whether documented SOPs exist**; if not, introduce TodoScope as the lightweight starting point. This is the input to everything above.
  - [ ] **Map the real system landscape:** a CRM, the regional MLS, Google Sheets, Airtable, and a great deal of phone/WhatsApp/memory. There is no single system of record, which means the first build is probably capture rather than integration. MLS access is typically licence-restricted — establish early whether we may touch it at all.
  - [ ] **Establish the brokerage's position on email.** Their shared admin and tech staff own it. Any mail-side integration needs their cooperation and may simply be refused — better to know before it is designed in.
  - [ ] **Replace the floating delivery milestone with a real anchor.** The "4-month" figure was our peer's own arbitrary soon-ish and cannot be met or missed as written.

- [ ] **Settle the WhatsApp question**: currently mis-framed as "explore" — the bridge already shipped in 2.0.0, so there is nothing to evaluate.
  - Shipped: `bridges/adapters/whatsapp.py`, 291 lines, webhook-driven, HMAC-SHA256 verified, full runbook in `docs/bridges.md`.
  - [ ] Decide (a) whether Spaces already covers the internal case and makes the bridge unnecessary.
  - [ ] Decide (b) whether it is client-facing.
    - [ ] If client-facing on his business number: WAHA is unofficial and carries ban risk on the number his livelihood runs through — that risk conversation happens **before** we provision.
  - [ ] If we do proceed: provision a WAHA sidecar container, a phone number, and a public HTTPS webhook.
    - try.sage.is is a single-app CapRover deploy with no sidecar beside it, so this is infra provisioning, not a config toggle.

#### Dedicated instance — after the demo

- [ ] Migration path for anything he creates on try.sage.is between the demo and the cutover.

### TODO / Test suite throughput

- [ ] **Run the e2e suite concurrently** (Alexander, 2026-08-09): `make e2e` is **4m51s for 46 specs / 233 tests** serially against one container, the gate between every change and confidence — its wall-clock is a tax on every iteration. #dx #tooling
  - [ ] As many specs in parallel as the harness allows.
  - Cypress supports parallel spec execution; the blocker is shared state rather than the runner.
  - `scripts/e2e/run-cypress.sh` boots ONE rootstock on one volume, and signup hard-closes after the first admin — two specs racing to seed the same instance is a data race, not a speed-up.
  - [ ] Shape that works: probably N containers on N volumes with the spec list partitioned — also what lets `e2e_both` stop costing double.
  - [ ] Measure the serial baseline per spec first — partitioning by duration matters more than by count.
    - `setup-dialog` 21s, `wizard-welcome` 33s and `setup-navigation` 25s are a third of the run between them.

### TODO / Repo Hygiene & Security

- [ ] **Repo-wide hidden-artifact allowlist rollout**: Deny dotfiles and dotfolders everywhere in the repo by default; explicitly include only approved shared hidden artifacts so local state cannot drift into git by accident.
  - _Implemented: `.gitignore` allowlist, contributor approval rule in `CONVENTION.instructions.md`, `!.*.example` template allowlist, included/excluded verification. Archived 2026-08-15._
  - [ ] Review currently tracked hidden artifacts and remove any that should be excluded going forward

- [ ] **Coordinated langchain major bump**: bump the langchain/langchain-community/langchain-core trio (rag-loaders Sprig™ side) past 0.3.x to drop the `CVE-2026-34070` suppression.
  - [ ] `.trivyignore` suppresses `CVE-2026-34070`: path traversal in `langchain_core`'s legacy `load_prompt()`, unreachable in this codebase — see `.trivyignore` comment.
  - [ ] The fix (`langchain-core==1.2.22`) needs `langchain-core<1.0.0` dropped, which both pinned sprig-side packages require (`langchain==0.3.30`, `langchain-community==0.3.27`, `app/backend/requirements.txt:51-56`).
  - [ ] Plan and test the coordinated bump, then remove the `.trivyignore` entry.

### TODO / OAuth UX & Identity Linking

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

### TODO / Release Wrap-Up

- [ ] **Tri-repo Jidoka (自働化) + Poka-Yoke (ポカヨケ) for the publish flow**: Bootstrap shipped in 2.3.1; the render layer and commit-hook checks are still open. ([dossier](docs/board-dossiers.md))
  - [x] **Source of truth** — `distribution.env` hardlinked across all three repos (CLI_VERSION, SERVER_TAG, IMAGE, VOLUME, DATA_MOUNT, WAITLIST_URL). `make distribution_sync`/`distribution_verify` in each repo's Makefile; `release_finish`/`hotfix_finish` gated on verify.
  - [x] **Bootstrap order** — homebrew-apps (canonical volume + `--tag` on `ai-ui start`/`try`/`update`), AI-UI (Makefile reads `distribution.env` for VOLUME_DATA + IMAGE_TAG defaults), Sage.Education-docs (Makefile reads `distribution.env`, `distribution_sync`/`verify` targets) — all wired.
  - [x] **Cross-repo workflow doctrine** — homebrew-apps README states `git flow feature start <name>` policy. AI-UI and docs README updates land with the docs-repo install pages.
  - [ ] **Poka-yoke** — pre-commit hook in each repo refuses commits whose declared image/volume/version conflict with `distribution.env`; installed via `make install_dev`. Wrong values can't reach the index.
    - [x] _AI-UI hardlink chain self-healing (`make install_hooks`: pre-commit `distribution_verify`, post-checkout/merge/rewrite `distribution_heal`), landed 2.3.3. Archived → docs/completed-todos.md._
    - [x] **OBSOLETE (2026-08-13)** — no chain to heal. Sibling needs a `distribution_verify` equivalent, not a healer. Reduced to: give homebrew-apps and Sage.Education-docs the same 4-line `cmp` check.
  - [x] _Hardlink retired 2026-08-13 #poka-yoke: ~155 lines of healer/arbitration replaced by 11 — `distribution_sync` copies out, `distribution_verify` asserts byte-equality; no owner declared, divergence reported and reconciled by hand; all three repos now 1 link, sha `69754e40`. Archived → docs/completed-todos.md._
  - [x] _Three silent failures in the replacement caught 2026-08-14 #poka-yoke: `_pin_server_tag` printed success with no match (now asserts result via `grep -qx`), `distribution_verify` passed on zero comparisons (now prints the count), `distribution_sync` skipped absent peers silently (now names each peer). Four lines, proved both directions. Archived → docs/completed-todos.md._
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

- [ ] **Update banner: redirect admins to auto-update config**: replace `UpdateInfoToast.svelte` copy with deployment-shape-aware guidance — messaging only, no backend changes.
  - [x] Guidance: auto-deploying installs (CapRover, Portainer, K8s) pick up new tags automatically; brew/manual installs run `ai-ui update --tag X.Y.Z` (shown inline)
  - [x] CapRover's existing auto-pull is the structural poka-yoke
  - [x] Edit `app/src/lib/components/layout/UpdateInfoToast.svelte`: new copy + inline `<code>` for the command + two links (`ea342c2`)
  - [x] Update `app/src/lib/i18n/locales/en-US/translation.json` with new strings; other locales fall back to English until translated
  - [ ] Create `WEB-Sage.Education-docs/docs/admin/auto-updates.md` (CapRover config + brew alt + Portainer/K8s/other one-paragraph each + Need help? → `support@sage.is`)
  - [ ] Verify: banner renders with new copy when current < latest for an admin; release-notes link points at the specific tag; docs page renders in Docusaurus dev server

- [ ] **`make ship` publishes no GitHub release page**: add a `gh release create --verify-tag --latest` step with the CHANGELOG section as notes (v3.0.0 to v3.2.0 were published by hand 2026-09-29)

### TODO / Pitch & Documentation

- [ ] **Pitch — Fix Privacy Absolutes**: Audit `docs/elevator-pitch.md` for unconditional privacy claims
  - [x] Replace "nothing phones home" → "nothing leaves your building unless you send it" (`813e0c3`)
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

### TODO / Sprig B1 — finish extraction (audit backlog, sequenced next)

- [ ] **Accelerator-aware Sprigs™ — drop the CPU-only assumption** (captured 2026-07-27): the whole chain currently hardcodes CPU; when GPU support lands, sprigs need alternative variants per accelerator (cuda/rocm/metal) selected the same way arch is today. #bonsai
  - [ ] `scripts/gates/embedding-parity/build-artifacts.sh` installs torch from the `whl/cpu` index on purpose — the CUDA wheels are ~2GB of unused weight for a CPU gate
  - [ ] The GGUF cultivars ship CPU builds; `HOST_ARCH` compatibility is a two-value question (`arm64`/`amd64`) with no accelerator dimension
  - [ ] Widen `compatible` in `/catalog` from arch-match to arch+accelerator-match
  - [ ] `build-artifacts.sh` takes a torch-flavour argument instead of a pinned CPU index URL
  - [ ] Plan for the parity gate: its thresholds assume device-stable numerics — `cosine_min >= 0.999` (f16) may not survive a CPU reference vs GPU inference comparison
    - [ ] Either generate the reference per-accelerator or make the tolerance device-aware
    - [ ] Do NOT loosen the threshold to paper over a device gap; that is the check that caught the Hangul tokenizer divergence

- [ ] **Delete the chromadb pip fallback** (end-state of the bootstrap): blocked on prod-registry cutover + one release of soak. `vector_bootstrap.py` already prefers the sprig; the pip path goes cold automatically once prod has a registry. #bonsai

### TODO / Sprig B2 — non-technical clarity (audit backlog; data model before UI)

- [ ] **Catalog schema enrichment**: the CATALOG carries only machine fields, so the admin UI can only show raw keys like `minilm-onnx-inhoused` — prerequisite for a legible UI; the UI can only be as clear as this data. #bonsai
  - [ ] Add `display_name` + `description` (plain "what this does") to each entry
  - [ ] Add `size_mb`, `license`, and `tier` (`recommended`|`advanced`|`held`)
  - [ ] Add `restart_required` (bool, replacing the prose `post_graft_note` inference)
  - [ ] Add a slot/`replaces` marker for the six mutually-exclusive embedding cultivars

- [ ] **Stand up `bonsai.sage.is` spec hub** (2026-06-28; scaffold SHIPPED locally 2026-07-08): implementers spend hours here; polish compounds. ([dossier](docs/board-dossiers.md)) #bonsai
  - _Shipped locally 2026-07-08: 11ty scaffold, build-time spec fetch, `/sprig-spec/v1/` + `/rootstock-spec/v1/` render, catalog-hub home. Archived 2026-08-15._
  - [ ] [MANUALLY] `git init` + push `BONSAI/sprig-spec` and `BONSAI/rootstock-spec` BEFORE the hub — no `.git` anywhere in `BONSAI/`, CI clones the spec repos
    - [ ] The `app-` capability prefix reserved in `sprig-spec/v1.md` (2026-08-15) exists only as one uncommitted copy on this disk
  - [ ] [MANUALLY] Create `sage-is/bonsai-docs`, push `~/Documents/Projects/GitHub/BONSAI/bonsai-docs/`, Cloudflare Pages project (build `bun run build`, output `dist`) + CNAME `bonsai.sage.is`
    - [ ] 11ty renders single-page views of the canonical specs pulled from GitHub at build time
  - [ ] After the hub is live: flip the sage.is/bonsai + sage.is/sprigs spec links from github.com to `bonsai.sage.is/*/v1/`
  - [ ] Point the `$id` URLs in `sprig-spec/v1.md` and `rootstock-spec/v1.md` at the canonical `bonsai.sage.is` URL once the site is live

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

### TODO / v2.x — Near Term

- [ ] **Auth & Onboarding**: Email notifications and LDAP consolidation
  - [ ] Outgoing email notifications (reuse bridge SMTP config)
  - [ ] Consolidate LDAP config into Auth/Integrations tab

- [ ] **Frontend Toolchain Upgrade**: Svelte 5, Vite 6, SvelteKit latest
  - [ ] Svelte 4 → 5
  - [ ] Vite 5 → 6
  - [ ] SvelteKit 2.5 → latest

- [ ] **Podman Compatibility**: Verify builds and document setup
  - [ ] Test and fix Podman build issues (VM memory, rootless networking)
  - [ ] Document Podman-specific setup (VM memory bump, `host.containers.internal`)
  - [ ] Revisit Makefile `CONTAINER_RUNTIME` auto-detection once Podman is a verified alternative

- [ ] **2.4 ML Bundle (signed per-arch × per-accel)**: replace the 2.3.1 transitional ML wizard path (runtime `uv pip install` + `sitecustomize.py`) with signed tarball bundles published on GitHub Releases.
  - [ ] Wizard pulls via `curl | sha256sum -c | tar -xz`
  - [ ] `distribution.env` carries `ML_BUNDLE_TAG` + per-variant SHA256s
  - [ ] Bring CUDA back as a first-class matrix cell
  - [ ] `requirements-ml.lock` from 2.3.1 is the build input — no thrown-away work

- [ ] **Knowledge Base Improvements**: AI ingestion and admin cleanup
  - [x] AI-parsed ingestion mode: shipped in 2.0.0 (CHANGELOG "PDF Ingestion Modes")
  - [ ] Admin Documents page cleanup
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

### TODO / v3.0 — Future

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
    <!-- inline: ollama.py:1798 -->
  - [ ] Configurable upload timeouts based on file size (replace hardcoded 240s)
    <!-- inline: audio.py:662,743,850 ollama.py:1749,1851,1875 -->
  - [ ] Console/log viewer tab in admin (WebSocket log streaming)

- [ ] **Platform Features**: Workspaces, analytics, search, mobile, a11y
  - [ ] Sage.is hosted email notification service (for deployments without SMTP)
  - [ ] Workspace switcher (project-scoped model configs, shared vs private)
  - [ ] Built-in task tracking (convert chat responses to tasks, due dates, progress)
  - [ ] Personal analytics dashboard (usage patterns, model preferences)
  - [ ] Semantic search across all chats and documents
  - [ ] Mobile-first optimizations (swipe gestures, PWA enhancements)
  - [ ] Accessibility: screen reader, high contrast, keyboard navigation

### TODO / From Codebase (untracked)

- [ ] **Backend Inline TODOs**: Load balancing, type updates, deprecation removal
  - [ ] Intelligent load balancing for multiple Ollama backends (`ollama.py:1`)
  - [ ] Update Ollama type support when upstream adds new types (`ollama.py:1428`)
  - [ ] Handle tool name collisions by prepending toolkit name (`utils/tools.py:109`)
  - [ ] Replace legacy system message insertion with `add_or_update_system_message` (`middleware.py:1396`)
  - [ ] Add retries to audio processing requests (`audio.py:1221`)
  - [ ] Remove deprecated `WEBUI_JWT_SECRET_KEY` fallback at next major version (`env.py:393`)

- [ ] **Audio/TTS UX polish** (surfaced live in dev mode 2026-07-26; the last two ride with the Settings/Admin migration pass):
  - _Shipped: first-playback loading toast (`ResponseMessage.svelte`); Settings double-load memoized (`Settings/Audio.svelte`). Archived 2026-08-15._
  - [ ] Opening Settings → Audio RELOADS Kokoro even after playback already loaded it — the Settings main-thread loader and the playback Web Worker (`kokoro.worker.ts`) are separate contexts; share one loader/model so the model loads once per session
  - [ ] Kokoro voice selector is janky (a type-in input + a list that only opens after you clear the field) → replace with a clean, DRY `<select>`/combobox

### TODO / Frontend — no-build strangler migration (approved 2026-07-25)

- [ ] **Phase Q0 — board hygiene**: TODO.md on TodoScope convention, this plan's tracked TODOs filed, board kept current every phase. #critical
  - Superseded 2026-11-03: the weekly board register pass keeps the board current, and the no-build strangler now runs inside the Rootstock card
  - [x] Verify TODO.md structure + `.todoscope-exclude.csv` (both already on-convention)
  - [x] File the migration epic + tracked TODOs into TODO.md
  - [ ] Keep the board mirroring reality as each phase's steps land and ship
    - [x] Reconciled again 2026-07-29 after the branding surface: entry filed with BOTH line-count readings rather than the flattering one.
    - [x] Reconciled 2026-07-29 after Phases 0–2 landed: 14 stale "uncommitted" markers cleared (every one of them is in `HEAD`; the tree is clean), the error-persistence and toast work filed, Phase 2 split from 3–4 with diagnostics closed and theme/wizard named, and the locale blocker filed rather than left living only in a docstring. Worth noting WHY the drift happened, since it will recur: entries were written at the moment work finished, when it was genuinely uncommitted, and nothing brings the board back after the user commits. The board cannot know — only a pass like this one closes it.

- [ ] **Version `/themes/active.css`** (deferred 2026-07-26, unblocked 2026-08-01): every full page load spends a render-blocking round-trip on 23 bytes of `/* no theme grafted */`. ([dossier](docs/board-dossiers.md)) #perf #bonsai
  - [ ] Unblocked: panels moved to Jinja2; `shell.py` needs no templating, and `shell.asset_url()` already version-stamps by release
  - [ ] Measured on the shipped image: `cache-control: no-cache`, no ETag, no Last-Modified, `If-None-Match` returns 200 not 304, via the static `<link>` at `app.html:21`
  - [ ] Inject `?v=<active theme name + css mtime>` into the shell's `<link>` at serve time
  - [ ] Serve the CSS `immutable, max-age=31536000` — a graft changes the token, so pickup is instant with zero revalidation (SvelteKit's `_app/immutable` trick)
  - [ ] Trap: do NOT key invalidation to deploys — `SPRIG_ACTIVE_THEME` flips at RUNTIME (`routers/sprigs.py:151,305`), so deploy-keyed caching hides a fresh graft until restart
    - [ ] Rejected: short TTL (grafted theme one load late); ETag-only (saves the 23-byte body, not the round-trip)

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

### TODO / Founder Bio & Provenance

- [ ] **Etsy / islands provenance — firm up the sources**: make the "employee #4 / built the Etsy Mini / called them islands" bio citable. #brand #provenance
  - [ ] Public today: #4 (Fred Wilson/USV 2006, via zh.wikipedia); the Etsy Mini is a documented island-shaped widget
  - [ ] Detail in the `reference_etsy_islands_provenance` memory + the plan's provenance appendix
  - [ ] Retrieve the archived Fred Wilson / USV 2006 post from archive.org (the usv.com URL now 404s) — locks the #4 primary source
  - [ ] (Alexander) Confirm true hire order — recollection is possibly earlier than #4 (Stinchcomb joined later; came on ~after Forman, ~with Nuzzolillo)
  - [ ] Find receipts for Etsy Mini authorship (publicly credited to Etsy collectively)
  - [ ] Find evidence of internal "islands" vocabulary predating the 2019 public coinage

### Backlog

- [ ] **A process for agents whose model is gone** (Alexander, 2026-08-17): when an agent's base model stops resolving — model deleted, connection removed, hosted key dead, capability Sprig pruned — the agent goes silently mute; today nobody is told and nothing suggests a fix. #ux #reliability
  - [ ] Detect: on agent use (and/or a periodic sweep), check the base model still resolves to a live entry; classify the loss (missing model vs dead connection vs pruned capability).
  - [ ] Suggest, don't auto-fix: surface it to the agent's OWNER ("this agent can't reach its model — pick a new one") and to an ADMIN (which agents broke, what removed the model), with the plausible remaps offered.
  - [ ] The live precedent: the unresponsive Space Agent on try.sage.is (`charts/friday-demo/TODO.md`) — this failure class is what that diagnosis keeps finding by hand.
  - [ ] Fits `/admin/diagnostics`: an `agents_orphaned` check beside the capability probes, with a how-to-fix modal naming the affected agents.
  - [ ] Decide the nudge channel: in-app banner on the agent, the admin panel, and/or the existing webhook/offline-notify path.

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
  - Sourcemaps are already off in production builds (`37997c4`, `vite.config.ts:113`)
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
  - [ ] Depends on the first-time-OAuth UX TODO ([above](#oauth-ux--identity-linking)) landing first.

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
  - [x] `make install_dev` — auto-install dev tools via Homebrew
  - [x] `make scan_container` — trivy image scanning (post-build)
  - [x] `make lint` — eslint + prettier + black rollup (`ruff` replaced black in `2daa3ac`)
  - [ ] Gate release finish on passing DB tests and scans
  - [ ] Support the same gated release flow locally or on CI
  - [x] Staging: try.sage.is is the canary; `make deploy` stops there if it does not come up (2026-09-27)
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

### Bugs

- [ ] **`surface_budget` floor over ceiling since at least 3.1.0**: `notes-empty` decodes 6,978 kB against the 6,800 kB ceiling — and the 2026-08-10 `3.1.0-amd64` image measures 6,978.6, so the regression PREDATES the 2026-08-17 cleanup sitting (A/B run, same snapshot, 0.5 kB apart). #bug #critical
  - Superseded 2026-11-03 by the card "The SPA floor crept 539 kB unnoticed between 2026-08-02 and 3.2.2": the ceiling was raised on purpose, with the reason in `run-gate.sh`, on 2026-10-24
  - [ ] The gate's own comment records 6,642 kB on 2026-08-02 after the font/icon work — ~336 kB grew back somewhere in 2026-08-02→08-10 and nobody ran `gauntlet_full` across the line.
  - [ ] Heaviest single item: `/api/models?` at 2,702 kB decoded — snapshot-driven, worth checking against the 08-02 figure first; the rest is `_app/immutable` chunks (top four: 764+606+543+411 kB).
  - [ ] The ledger (`app/cypress/perf-routes.json`) is untracked and overwritten per run, so there was no baseline to catch the drift — consider committing a dated copy per release.
  - [ ] Do NOT raise the ceiling to go green; the gate says so itself. Find the 336 kB or earn the raise deliberately.

### Notes from the emptied subsection "Founder Bio & Provenance"

---
