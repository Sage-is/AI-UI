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

-[x] **Happy Summary**
  -[x]v2.0.0 shipped the Sage rename, Spaces UX, setup wizard, chat sharing, knowledge-base improvements, and messaging bridges for WhatsApp, Telegram, Signal, and Email.
  -[x]v2.1.0 added OAuth (Google + GitHub), email magic-link login, and Developer Mode onboarding.
  -[x]v2.2.0 added persona magic-links, embedded tutorials, and the persona switcher — workshops boot from one URL.
  -[x]v2.3.0 added the ChromaDB embedding engine, the try.sage welcome page, larger mermaid mind-maps, and Strawberry's diagram grammar.
  -[x]v2.3.1 (shipped 2026-05-19) laid the Jidoka spine — `distribution.env` hardlinked across AI-UI, homebrew-apps, and Sage.Education-docs — plus the ML wizard transitional fix (uv + CPU-only torch + sitecustomize.py), the FastAPI env-gate dependency-order fix, the SPA `/api/*` JSON 404, and CVE bumps for langchain + python-multipart. Released via `release_and_push_GHCR`; `ghcr.io/sage-is/ai-ui:2.3.1` published and `SERVER_TAG=2.3.1` pinned.
  -[x] Release engineering is in much better shape: security scanning, pre-commit hooks, DB upgrade smoke tests, dependency cleanup, and a much leaner Docker path are all in place.
  -[x] The docs now keep active references separate from historical audits, plans, and retrospectives so this roadmap can stay focused on unfinished work.

---

## In Progress

_Items currently in progress. Move items here and or use tag source with `# FIXME:` when work begins._

- [ ] **DEFER until 2026-06-10: deploy 2.3.2 to try.sage.is**: `v2.3.2` tagged 2026-06-03; image `ghcr.io/sage-is/ai-ui:2.3.2` published with OCI labels. **try.sage.is is in active-use freeze through 2026-06-10** (Bialic actively using it — no production deploys to that target during the window). `sage.startr.cloud` is NOT under the freeze and can be redeployed at any time. After 2026-06-10: CapRover Method-6 image-pull at captain.try.sage.is → `try-sage-is` app → `ghcr.io/sage-is/ai-ui:2.3.2`. Verify `/assets/loader.js` returns 200 (currently 404) and Permissions-Policy is the lean allowlist. #critical

- [x] **Ship 2.3.1 — Jidoka spine + three Poka-Yoke children**: Shipped 2026-05-19. Tag `v2.3.1` pushed, `ghcr.io/sage-is/ai-ui:2.3.1` published, `SERVER_TAG=2.3.1` pinned across the hardlink chain. Detail in `CHANGELOG.md`; plan at `~/.claude/plans/given-our-newest-trends-modular-sloth.md`. #critical

- [x] **try.sage Manual Regression Sign-off** (2026-04-27): Phase A backend + Phase B frontend shipped. All 12 smoke checks passed (container boot, persona magic-links, banner, switcher, tutorial, admin tab, hidden connection, model filter, env-gate disable). Reference left for future regression-pass authors.

- [ ] **try.sage Production Decisions**: (Alexander Somma + Izzy Plante) — Surfaced by Docker exploration. Block CapRover one-click rollout.
  - [x] Decide where `TRY_SAGE_LLM_API_KEY` lives in production: plain env, Docker secret mount, or external vault. Recommend Docker secret for try.sage.is itself, plain env for self-hosted workshops.
    - [x] note:As we use cap rover and the system injects env vars we're leaning this way
  - [ ] Add the dummy-tools server question to the same review: keep, remove, or replace with real preview capability (web search, sandboxed runner).



---

## TODO

### Repo Hygiene & Security

- [ ] **Repo-wide hidden-artifact allowlist rollout**: Deny dotfiles and dotfolders everywhere in the repo by default; explicitly include only approved shared hidden artifacts so local state cannot drift into git by accident.
  - [x] Implement the repo-wide hidden-artifact allowlist in `.gitignore`
  - [x] Document the contributor approval rule for new hidden artifacts in `CONVENTION.instructions.md`
  - [x] Use `!.*.example` as the generic allowlist for sanitized hidden example templates
  - [x] Verify included vs excluded hidden artifacts (`.obsidian/`, `.semgrep/`, `.env.example`, `.claude/`, `.env`, `app/.eslintrc.cjs`, `app/backend/.gitignore`)
  - [ ] Review currently tracked hidden artifacts and remove any that should be excluded going forward

### OAuth UX & Identity Linking

- [ ] **OAuth identity linking v1 — let users attach Google/GitHub/Microsoft to existing accounts whose email doesn't match the provider's email**: Today the only graceful path is `OAUTH_MERGE_ACCOUNTS_BY_EMAIL`, which silently links any OAuth identity with a matching email to any existing user — fine for self-hosted single-admin installs, useless when the user's local AI-UI email differs from their Google/GitHub email, and an account-takeover footgun if email control is ever weaker than account control. Build two self-service flows (Pattern A + Pattern B), lift the one-provider-per-user schema limit, and harden the admin controls with Poka-Yoke devices so misconfiguration becomes impossible. Decisions confirmed in plan thread 2026-05-28.
  - [ ] **Schema lift to multi-provider stacking**: Replace single `oauth_sub TEXT UNIQUE` on the User model with per-provider columns: `google_sub`, `github_sub`, `microsoft_sub` (and `apple_sub` when Apple lands). Each `UNIQUE`. Generic `oidc` keeps the existing `oauth_sub` column as catch-all. Rewrite every callsite reading `user.oauth_sub` to dispatch by provider — `Users.get_user_by_oauth_sub(provider, sub)` becomes the new shape. Migration ships before any UX work.
  - [ ] **Pattern A — Settings-driven link/unlink**: Account Settings → "Connected providers" section showing each linked provider with an unlink button, plus "Connect Google / GitHub / Microsoft" buttons for unlinked providers. Clicking initiates OAuth round-trip with a session-bound `state` token; on callback the system attaches the new `<provider>_sub` to the already-signed-in user record. Security proved by being signed in.
  - [ ] **Pattern B — OAuth-first claim flow with magic-link verify**: When a user clicks "Sign in with Google" and no oauth_sub or email match exists, instead of 403 or auto-creating a pending user, redirect to `/auth/claim?provider=google&sub=...&temp=<token>`. Page asks "Do you have an existing account?" → user enters AI-UI email → backend sends a magic link to that email → click attaches the OAuth identity to the existing account. Branch the no-existing-account case to a separate "Create new account" flow gated on `ENABLE_OAUTH_SIGNUP` + allowlist policy.
  - [ ] **Per-provider link mode** (replaces the global `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` toggle): Each provider config block gets `<provider>_link_mode` with three values: `silent_merge_by_email` (current behavior — email match auto-attaches sub), `verify_via_magic_link` (email match triggers a magic-link to confirm ownership before attaching — same pipeline as Pattern B), `disabled` (no auto-linking; users must initiate from Account Settings via Pattern A). Default on fresh install: `verify_via_magic_link` if SMTP is configured, else `silent_merge_by_email` with a save-time warning. Migration from existing `OAUTH_MERGE_ACCOUNTS_BY_EMAIL=True` initializes all providers to `silent_merge_by_email` (preserves behavior); `=False` initializes to `disabled`. Global toggle stays as fallback for one major version, then dropped. Threat-model split: self-host single-user + workshop installs want silent merge (admin has pre-vouched), small/regulated orgs want verify (Google account compromise ≠ inbox compromise).
  - [ ] **Replace raw 403 with a real status page**: Backend redirects `handle_callback` failures to `/auth/status?reason=<signup_disabled|allowlist_blocked|domain_blocked|role_pending|email_taken>&email=<masked>` rather than throwing `HTTPException(403, ACCESS_PROHIBITED)` at [utils/oauth.py:508-511](app/backend/sage_is_ai/utils/oauth.py#L508). Frontend route renders branded copy + "request approval" CTA (mailto or webhook). API surface keeps the 403 for programmatic clients. Copy direction:
    - `signup_disabled`: "Your email `<masked-email>` doesn't have an account at <site name>. Ask your admin for access." + "Request access" button (mailto or webhook trigger).
    - `role_pending` (auto-created from OAuth signup but awaiting approval — the default behavior since `DEFAULT_USER_ROLE=pending`): "Thanks! Your account is being reviewed. We'll email you when approved." + the existing pending-account UX. The pending-by-default behavior IS the poka-yoke — don't bypass it.
    - `domain_blocked` / `allowlist_blocked`: "Your email isn't on this site's allowed list. Talk to your admin if you think this is a mistake."
  - [ ] **Per-provider allowed-domains policy** (replaces global `OAUTH_ALLOWED_DOMAINS`): Each provider config block gets its own `<provider>_allowed_domains` list. Google can be `@openco.ca` only while GitHub stays open; Microsoft can be `@school.edu, @school.k12.org`. Per-provider config blocks already exist in [config.py:316-700](app/backend/sage_is_ai/config.py#L316) — extend with the domain field.
  - [ ] **Per-user OAuth allowlist**: User record gets `oauth_eligible BOOLEAN DEFAULT True` plus per-provider override (`google_allowed`, etc.). Admin can lock down workshops to the invited cohort: even if a user's email matches the domain allowlist, they're rejected unless they're on the user allowlist. Sane default is "eligible," restrictive mode is one toggle.
  - [ ] **Save-time Poka-Yoke on admin OAuth config**:
    - [ ] Refuse to save `ENABLE_OAUTH_SIGNUP=True` with empty/wildcard allowed-domains; require explicit "I understand this is open registration" confirmation toggle.
    - [ ] Treat empty allowed-domains list as "no one" (fail-closed), not "everyone" (fail-open).
    - [ ] Block enabling Pattern B claim flow if SMTP isn't configured — the magic link would never arrive. Inline error: "Configure email first (Settings → Email)."
    - [ ] Inline preview after each field change: "With current settings, the following can sign up: Google @openco.ca only; GitHub open to allowlisted users only."
  - [ ] **"Simulate sign-in" admin diagnostic** — highest-leverage Poka-Yoke: Admin pastes an email + picks a provider, system shows what would happen end-to-end without making any DB changes. Output: "Would link to existing user X" / "Would create new pending user" / "Would 403 — not in domain allowlist" / "Would 403 — user not on per-user allowlist." Catches misconfiguration before a real user hits it.
  - [ ] **i18n** all new user-facing copy (status pages, claim flow, settings labels).
  - [ ] **Audit log** entry on every link/unlink event with `(timestamp, user_id, provider, sub, action, actor)` — admin or user.
  - [ ] **Migration safety**: existing users with `oauth_sub = "google@..."` get their column-typed value populated by the migration; old field stays nullable for one release for rollback safety, removed in N+1.

### Release Wrap-Up

- [ ] **`make caprover_app_create APP=<name>` wrapper**: One Makefile call to register a new CapRover app via the HTTP API (`/api/v2/user/apps/appDefinitions/register`), POST the env-var block, set the persistent volume path, and connect a custom domain. Driver: avoid the dashboard click-through we did for `try-sage-is` on `captain.production.openco.ca` 2026-05-01.

- [ ] **Port `sharded-zooming-parrot` Poka-Yoke release plan to this Makefile**: Add `release_preflight` (Docker memory, working tree clean, gh auth, develop synced) before any irreversible step in `release_and_push_GHCR`; make `it_build_multi_arch_push_GHCR` safe to re-run after a partial failure. Driver: 2.3.0 release_finish completed but buildx OOMed mid-push, leaving the tag on origin without a matching GHCR image. Plan at `~/.claude/plans/sharded-zooming-parrot.md`.
  - [ ] **`wizard_smoke` cold-cache false-fail (2.3.2, 2026-05-29)**: The 15-min `INSTALL_TIMEOUT_SEC` wasn't enough for ~5 GB of wheels + ~2 GB embedding model on residential bandwidth — smoke false-failed even though uv was actively downloading and `models/status` showed `error: null`. Adding a `SKIP_SMOKE=1` bypass is NOT poka-yoke — it normalizes operator override of the safety gate. Real poka-yoke directions to evaluate: (a) bake uv wheel cache + embedding model into the smoke image at build time so install becomes unpack-only (image grows ~5-7 GB but smoke becomes deterministic and runs in minutes); (b) move smoke to the staging CapRover app once it exists (datacenter bandwidth removes the residential-bandwidth dimension entirely; ties into the staging-smoke design discussed for 2.3.3); (c) make smoke resumable across container restarts so a partial install survives and the next run starts from where it stopped. Any of these makes the failure mode disappear at the root. Until one ships, a cold-cache false-fail blocks the release — that's the gate doing its job.
  - [ ] **Target naming clarity**: `release_finish` only finishes git-flow (merge + tag + push) — it does NOT publish the image. `release_and_push_GHCR` is the canonical ship target but its name doesn't read that way, and its hidden `release_smoke` prereq is a footgun. Consider a `make ship` alias and a rename of `release_finish` → `release_gitflow_finish`.
  - [ ] **`make help` is hardcoded echos**: `##` inline target docs (already present on `wizard_smoke`, `cross_smoke`, `_pin_server_tag`, etc.) are invisible to operators because `help:` doesn't scan for them. Refactor `help:` to grep `## <target> — <description>` lines and render them automatically. One-time change, ongoing payoff.

- [ ] **Tri-repo Jidoka (自働化) + Poka-Yoke (ポカヨケ) for the publish flow**: Bootstrap shipped in 2.3.1; render layer + commit-hook checks still pending. Plan at `~/.claude/plans/given-our-newest-trends-modular-sloth.md`.
  - [x] **Source of truth** — `distribution.env` hardlinked across all three repos (CLI_VERSION, SERVER_TAG, IMAGE, VOLUME, DATA_MOUNT, WAITLIST_URL). `make distribution_sync`/`distribution_verify` in each repo's Makefile; `release_finish`/`hotfix_finish` gated on verify.
  - [x] **Bootstrap order** — homebrew-apps (canonical volume + `--tag` on `ai-ui start`/`try`/`update`), AI-UI (Makefile reads `distribution.env` for VOLUME_DATA + IMAGE_TAG defaults), Sage.Education-docs (Makefile reads `distribution.env`, `distribution_sync`/`verify` targets) — all wired.
  - [x] **Cross-repo workflow doctrine** — homebrew-apps README states `git flow feature start <name>` policy. AI-UI and docs README updates land with the docs-repo install pages.
  - [ ] **Poka-yoke** — pre-commit hook in each repo refuses commits whose declared image/volume/version conflict with `distribution.env`. Same hook installed via `make install_dev`. Wrong values can't reach the index.
    - [x] **AI-UI: hardlink chain self-healing** — `make install_hooks` wires four pre-commit-framework hook stages: `pre-commit` runs `distribution_verify` (refuse if chain broken with operator-named fix), `post-checkout`/`post-merge`/`post-rewrite` run `distribution_heal` (silent re-link when content matches, warn-and-skip on divergence). Replaces the manual `make distribution_sync` step after any git operation that rewrites the file. Landed in 2.3.3.
    - [ ] **Symmetric hooks in homebrew-apps + Sage.Education-docs** — same `install_hooks` + `distribution_heal` pattern in both sibling repos so a chain break introduced from a sibling editor also self-heals. Slots into the Jidoka render layer item below.
  - [ ] **Jidoka render layer** — `make sync-from-distribution` in each repo regenerates templated docs/formula/Makefile fragments from `distribution.env`; `release_finish` calls it on the two siblings before tagging. If any sibling's working tree turns dirty after the regen, the release halts with the diff printed (machine stops itself; operator confirms or fixes).
  - [ ] **Docs render** — Docusaurus install commands and version strings pulled from `distribution.env` via remote-content plugin or build-time include. Brew formula caveats and AI-UI README install section regenerated from the same templates.

- [ ] **`ai-ui` brew formula self-manages a launchd service**: The `homebrew-apps` formula should ship a complete LaunchAgent plist so `brew services start ai-ui` (or `ai-ui start`) brings the container up at user login, restarts on crash, and survives shell exit — no operator-side launchd surgery, no hand-patching `~/Library/LaunchAgents/*.plist`. Validated the pattern on a deployment 2026-05-19 against the stock `cloudflared` brew formula, which ships a plist with no subcommand in `ProgramArguments`; cloudflared then prints help and exits 1, KeepAlive retries forever, brew shows `error 1`, and the only fix is hand-patching the plist (which `brew upgrade` later silently overwrites). Our formula must not repeat that wart. Same Poka-Yoke direction as `make upgrade` + the brew CLI's `ai-ui update --tag X.Y.Z`.
  - [ ] LaunchAgent plist template baked into `ai-ui.rb` / `ai-ui@1.rb`'s `service do` block with full `ProgramArguments` (binary + `start` subcommand + the flags that actually launch the container), `KeepAlive { SuccessfulExit=false }`, `RunAtLoad=true`, `StandardOutPath`/`StandardErrorPath` → `/opt/homebrew/var/log/ai-ui.{log,err.log}`.
  - [ ] `--system` flag (or a sibling `ai-ui-headless` formula) installs a LaunchDaemon under `/Library/LaunchDaemons/` for unattended-reboot uptime — for boxes where nobody logs in after power-cycle. Document the tradeoff vs. auto-login + LaunchAgent.
  - [ ] `ai-ui start` / `ai-ui stop` / `ai-ui update` integrate with `launchctl` (or `brew services`) so the lifecycle is one command on each side and idempotent across re-runs.
  - [ ] Idempotent install/upgrade: `brew upgrade ai-ui` must not duplicate the plist, silently evict a running service, or leave an orphan plist after `brew uninstall`. `brew services list` should always reflect reality.
  - [ ] Pre-flight in `ai-ui start`: refuse to launch when another container is already bound to the configured port or container name; prompt the operator to `ai-ui stop` first rather than silently double-binding.
  - [ ] Smoke: an `ai-ui` formula test (`test do` block) that installs the agent, asserts the service starts, hits `/health`, then deregisters cleanly.

- [ ] **Update banner: redirect admins to auto-update config**: Replace `UpdateInfoToast.svelte` copy with deployment-shape-aware guidance — auto-deploying installs (CapRover, Portainer, K8s) pick up new tags automatically; brew/manual installs run `ai-ui update --tag X.Y.Z` (shown inline). New docs page `WEB-Sage.Education-docs/docs/admin/auto-updates.md` covers config per deployment shape + `support@sage.is` contact. No backend changes — CapRover's existing auto-pull is the structural poka-yoke; this is messaging only. Plan: `~/.claude/plans/given-our-newest-trends-modular-sloth.md`.
  - [ ] Edit `app/src/lib/components/layout/UpdateInfoToast.svelte`: new copy + inline `<code>` for the command + two links
  - [ ] Update `app/src/lib/i18n/locales/en-US/translation.json` with new strings; other locales fall back to English until translated
  - [ ] Create `WEB-Sage.Education-docs/docs/admin/auto-updates.md` (CapRover config + brew alt + Portainer/K8s/other one-paragraph each + Need help? → `support@sage.is`)
  - [ ] Verify: banner renders with new copy when current < latest for an admin; release-notes link points at the specific tag; docs page renders in Docusaurus dev server

- [x] **TODO.md cleanup pass** (2026-05-25): Post-2.3.1 reconcile — collapsed the shipped 2.3.1 entry to a single [x], promoted the 2.4 ML bundle follow-up to its own item, added v2.3.1 to Happy Summary, trimmed the completed try.sage regression entry. KANBAN.canvas will regenerate automatically from this file.

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

### Bonsai™ Spec Site & Documentation Architecture

_Decisions locked 2026-06-28 by panel-review with Rich Harris, Maggie Appleton, Rauno Freiberg, and Daniel Stenberg. Outcome: `bonsai.sage.is/sprig-spec/v1/` as the canonical spec hub, `sage.is/bonsai/` as the curious-visitor explainer, `spec.sage.is` reserved for future non-Bonsai specs._

_Implementation precedes docs (2026-06-30 panel-push; Decision #19 in the Bonsai™ roadmap): the First Graft card below ships before the spec-site/explainer cards in this section._

- [ ] **First Graft: make one wizard toggle pull a Sprig** (2026-06-30): Walking-skeleton slice through 8.C→8.G for ONE capability — wire the existing "Graft Sprigs™ for me" wizard path to graft sprig-embedding-mock, run it on a loopback port, point RAG_EMBEDDING_ENGINE=openai dispatch at it, return one real embedding. Defer 8.A.2 spec-promotion, the other five 8.B repos, sigstore, prune/topgraft/revive, state.json, migration banner, image slimming until graft #2. #bonsai #critical

- [ ] **Stand up `bonsai.sage.is` spec hub** (2026-06-28): New repo `Sage-is/bonsai-docs` at `~/Documents/Projects/GitHub/BONSAI/docs/`. 11ty + Cloudflare Pages. CNAME `bonsai.sage.is`. Renders single-page views of the canonical spec content pulled from GitHub at build time. This is the polish target — implementers spend hours here, polish compounds. #bonsai
  - [ ] Scaffold the 11ty project (matches sage.is build pattern: bun + `@11ty/eleventy`, Cloudflare Pages deploy via `wrangler.toml`)
  - [ ] Vendor the sage.is book theme — copy `_includes/`, `assets/css/`, and the `books/` templates from `~/Documents/Projects/GitHub/WEB-Sage.is/src/`
  - [ ] Build-time spec fetch: `git clone --depth 1 --branch v1.0.0 sage-is/sprig-spec` and the rootstock-spec sibling into the 11ty data dir
  - [ ] Render `bonsai.sage.is/sprig-spec/v1/` and `bonsai.sage.is/rootstock-spec/v1/` as single-page renders of `v1.md`
  - [ ] Catalog-hub home at `bonsai.sage.is/` reusing the `books.njk` card-grid pattern — one card per spec, version, license, read/clone CTAs
  - [ ] Cloudflare Pages deploy + CNAME `bonsai.sage.is` → `bonsai-docs.pages.dev`
  - [ ] Configure `$id` URLs in `sprig-spec/v1.md` and `rootstock-spec/v1.md` to reference the canonical `bonsai.sage.is` URL once the site is live

- [ ] **Author `sage.is/bonsai/` explainer** (2026-06-28): Curious-visitor doorway on the main marketing site at `~/Documents/Projects/GitHub/WEB-Sage.is/src/bonsai/`. Sub-path on the existing 11ty build, NOT a separate subdomain. Catches the long-tail SEO that should never hit normative spec text. Polish bar: good content + correct typography + clear illustrations. Does NOT need interaction polish; the spec hub carries that. #bonsai
  - [ ] Write "What is Bonsai™?" explainer page with the architectural metaphor in plain prose
  - [ ] Write "What is a Sprig™?" with one or two illustrations (per Maggie's layered-design argument)
  - [ ] Write the AGPL-and-proprietary-Sprigs FAQ — covers Decision #13 (arms-length boundary doctrine) in newcomer-friendly language
  - [ ] Add hand-off CTA: "Ready to write a Sprig™?" → link to `bonsai.sage.is/sprig-spec/v1/`
  - [ ] Add hand-off CTA: "Want to build a conformant Rootstock™?" → link to `bonsai.sage.is/rootstock-spec/v1/`
  - [ ] Long-tail SEO meta: title/description/og: tags tuned for "what is bonsai sage", "how do I write a sprig", "sage AGPL plugin"

- [ ] **Reserve `spec.sage.is` DNS** (2026-06-28): Set up the subdomain now without a site behind it. Reason: if Sage.is ever publishes a non-Bonsai spec, that's the canonical URL home. Avoids painting into a corner where every Sage.is spec inherits the Bonsai metaphor in its URL. Per Daniel Stenberg's guardrail in the panel review. #bonsai #dns
  - [ ] Add `spec.sage.is` CNAME record (parked, no content)
  - [ ] Document in `docs/` why it's reserved so it doesn't get repurposed casually

- [ ] **Confirm Bonsai™ metaphor horizon before `bonsai.sage.is` ships** (2026-06-28): Open strategic question from Rich Harris's line of inquiry. The chosen canonical URL is doubly committed — to Sage.is staying AND to Bonsai™ surviving as the architectural name for 10+ years. If the architecture rebrands later, every JSON Schema `$id`, every conformance citation, every blog reference takes a 301. Decide before ship. #bonsai #strategic-decision
  - [ ] Founders' decision: is Bonsai™ the long-horizon name?
  - [ ] If yes — `bonsai.sage.is` ships as canonical
  - [ ] If unsure — switch canonical URL to `spec.sage.is/sprig-v1/` (metaphor-durable; survives an architecture rename)
  - [ ] Document the decision and the reasoning in a brief `docs/` note so future-us doesn't relitigate

- [ ] **Define spec-hub polish punch-list** (2026-06-28): Translate Rauno Freiberg's "polish target" principle into a concrete pre-launch checklist for `bonsai.sage.is`. The list IS the bar — ship only when each is true. Explicitly excluded: the `sage.is/bonsai/` explainer does NOT need to hit this bar; content quality is its bar instead. #bonsai #polish
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

- [ ] **Spaces Enhancements**: Agent context modes and auto-reply TTL
  - [ ] Agent context mode: `conversation` (last ~5 messages) and `full` (all recent) — `single` already ships
  - [ ] Optional per-agent TTL for auto-reply expiration
    <!-- inline: spaces.py:384 -->
  - [ ] **Silverbullet integration into Spaces** — wire the self-hosted Silverbullet PKM/wiki tool into Spaces so a Space can carry a structured note-graph alongside chats and files. Planning conversation first (architecture, auth, data model) before any code.
  - [ ] **Space theming for creator-led visual differentiation** (2026-06-15) — let Space creators set a visual theme so users do not confuse one Space for another. Minimum viable: a "Theme" tab in Space settings (creator-only) with an accent-color picker + optional logo upload that tints navigation chrome and message-thread accents. The pain: switching between e.g. "Math Tutoring Space" and "Math Department Admin Space" looks identical today, leading to mis-posts. Especially load-bearing for workshop facilitators (each workshop gets its own visual identity so students always know which one they are in) and multi-org operators on shared Rootstocks. Avoid full custom-CSS injection (XSS surface); for workshop/trial deployments, ship pre-built theme presets (bio = green, math = blue, etc.) so non-technical facilitators can theme without picking colors.


- [ ] **Frontend Toolchain Upgrade**: Svelte 5, Vite 6, SvelteKit latest
  - [ ] Svelte 4 → 5
  - [ ] Vite 5 → 6
  - [ ] SvelteKit 2.5 → latest

- [ ] **Podman Compatibility**: Verify builds and document setup
  - [ ] Test and fix Podman build issues (VM memory, rootless networking)
  - [ ] Document Podman-specific setup (VM memory bump, `host.containers.internal`)
  - [ ] Revisit Makefile `CONTAINER_RUNTIME` auto-detection once Podman is a verified alternative

- [ ] **2.4 ML Bundle (signed per-arch × per-accel)**: Replace the 2.3.1 transitional ML wizard path (runtime `uv pip install` + `sitecustomize.py`) with signed tarball bundles published on GitHub Releases. Wizard pulls via `curl | sha256sum -c | tar -xz`; `distribution.env` carries `ML_BUNDLE_TAG` + per-variant SHA256s. Bring CUDA back as a first-class matrix cell. `requirements-ml.lock` from 2.3.1 is the build input — no thrown-away work. Plan: `~/.claude/plans/given-our-newest-trends-modular-sloth.md`.

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
  - [ ] Replace legacy system message insertion with `add_or_update_system_message` (`middleware.py:997`)
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

---

## Backlog

_Items deferred to a later planning cycle. Move here from TODO when deprioritized._

- [ ] **Apple Sign-In with lazy-JWT client_secret rotation**: Add Apple as a fourth OAuth provider alongside Google/Microsoft/GitHub. The 6-month Apple `client_secret` JWT expiry is the operator footgun — design it out by regenerating the JWT on every `handle_login`/`handle_callback` call instead of scheduling rotation. ES256 signing with the `.p8` EC key is sub-millisecond, so the cost is invisible inside an already-interactive HTTP flow; no APScheduler / cron / persisted JWT state. Apple Developer Program membership ($99/year) is the only hard prerequisite — without it, this stays blocked.
  - [ ] Spike: confirm authlib's `StarletteOAuth2App.client_secret` is mutable per-request (1-2h). If authlib caches it into a pre-built request object, switch to a `compliance_fix` hook that injects the Authorization header just-in-time.
  - [ ] Backend: `apple_oauth.py` with JWT generator + P8 parser + config validator that signs a throwaway JWT at save-time so a bad key is caught before it can break sign-in.
  - [ ] Wire into `OAuthManager.handle_login`/`handle_callback`: regenerate JWT, swap into `client.client_secret`, then call authlib as normal.
  - [ ] Handle Apple's `response_mode=form_post` callback (Apple POSTs back; other providers GET) and first-time-only name/email capture (returning users get only `sub`).
  - [ ] Admin UI: Team ID + Key ID + P8 textarea (masked) in `OAuthSettings.svelte`, with the save-time signing validation surfaced as an inline error.
  - [ ] Frontend: Apple button + icon in the login provider selector.
  - [ ] Test loop: cloudflared / ngrok tunnel (Apple requires HTTPS, no localhost) + Apple Developer sandbox app.

- [ ] **Admin-driven OAuth user pre-link / org-wide provisioning**: Today the only ways to admit an OAuth user are `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` (implicit email-match against any existing account) or `ENABLE_OAUTH_SIGNUP` (open auto-create — every first-time login gets a `role=pending` user the admin then has to promote). Neither matches the "I want to invite Alice to my workshop and have her sign in with Google" workflow. Two layers, smallest first:
  - [ ] **Admin invites by email**: Admin → Users → "Invite" creates a user record with a chosen role (e.g. `user`) and a flag like `oauth_only=True` + `linked_provider=null`. When that email signs in via any OAuth provider for the first time, the callback links the `oauth_sub` to that pre-created record (same code path as merge-by-email, but gated on the invite flag rather than the global merge toggle). Closes the "raw 403 because admin didn't know they needed to do something" path.
  - [ ] **Org-level bulk linking**: Admin uploads a CSV (or pulls from Google Workspace / Microsoft Entra via SCIM) with `email,role,group` rows. All those users are pre-provisioned. Same callback linking path. Useful for workshop cohorts and school deployments.
  - [ ] **Invite expiry + revocation**: pre-created invites without a linked oauth_sub after N days surface in admin UI for cleanup.
  - [ ] **Audit log entry** on link event so admins can see "Alice's Google account (sub: google@...) was linked to her invited record on 2026-06-01".
  - [ ] Depends on the first-time-OAuth UX TODO ([above](#oauth-ux)) landing first so the user-facing experience around "your invite has been received" is coherent.

- [ ] **History purge for excluded hidden artifacts**: After the root hidden-artifact allowlist lands and the team reviews scope, run BFG Repo-Cleaner or `git filter-repo`, rotate any exposed secrets, and coordinate clone remediation for anyone with an existing copy of the repo.
  - [ ] Confirm which previously committed hidden artifacts must be purged from history
  - [ ] Prepare the team runbook for rewrite, force-push, and clone remediation
  - [ ] Rotate any credentials exposed by now-excluded hidden artifacts

- [ ] **try.sage Tutorial Video Production**: (Alexander Somma + Izzy Plante) — Content work, not code.
  - [ ] Pick individual videos from the [working playlist](https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u) for each of the 6 default tutorial steps.
  - [ ] Populate `TRY_SAGE_TUTORIAL_STEPS_JSON` per workshop deployment with the chosen URLs and step descriptions.
  - [ ] Publish the Bialik Sage tutorial content package: three short videos plus a follow-up email with system prompts.
  - [ ] Keep system-prompt disclosure only in the dedicated system-prompt video. Swap that one video per team session without a codebase release.

- [ ] **Buff Out the Default First-Run Landing Page** — try.sage already has a polished welcome page (persona picker, banner, branded imagery, tutorial overlay). The default first-run landing for a fresh self-hosted install is much thinner. Port the relevant pieces — minus the trial-only bits — so a fresh install feels like a finished product, not an empty room.
  - [ ] Audit what `try.sage` welcome ships today (`TrySage*` components in `app/src/lib/components/`): copy, imagery, tutorial-step cards, layout, animations.
  - [ ] Identify which pieces are *trial-only* (banner countdown, persona switcher, magic-link QR) vs. *generally useful for any first-run* (welcome card, "what to try first" buttons, tutorial overlay, branded slideshow continuity).
  - [ ] Design the default landing — what does a new admin see *immediately* after completing the setup wizard? Empty home with the chat composer is too thin. Suggested shape: a one-card welcome with "Start a chat", "Set up Ollama", "Create a Space", "Invite users" CTAs that link into the actual flows.
  - [ ] Add a default tutorial overlay (same component as `TrySageTutorial`, different content). Steps focus on the *self-hosted* admin journey: where chats go, where data lives, how to add a model, how to invite users.
  - [ ] Localize copy via i18n.
  - [ ] Vitest spec covering the auto-show + dismiss + replay flow (parallel to the try.sage tutorial spec).
  - [ ] Make the "Replay welcome" admin escape hatch available outside trial mode — sibling to the existing Trial Mode tab.

- [ ] **Provider logos for remote models**: Agents and remote models show no brand icon today — only a name, and sometimes only an icon with no provider mark. Ship recognizable logos for hosted providers (Claude/Anthropic, ChatGPT/OpenAI, Gemini/Google, etc.) so users can tell at a glance which service a model calls. Builds on **PK-1** (Local/External badge) above — PK-1 adds `is_external` + `provider_label` to the model API; this is the visual layer that turns `provider_label` into a logo. Bundle local engines (Ollama, etc.) into the same icon set so the treatment is consistent across local and remote.
  - [ ] Map `provider_label` → logo asset; ship a known-provider icon set (Anthropic, OpenAI, Google, Mistral, Meta, Ollama) plus a neutral fallback for unknown providers.
  - [ ] Render the logo in the model selector, response bubbles, and Space agent messages — same surfaces PK-1 badges the Local/External state.
  - [ ] Icon-only display option for agents that have no avatar set, so a remote-backed agent still carries a brand mark.
  - [ ] Use license-clean marks (official brand assets where the brand permits, or simple-icons / public-domain equivalents); document the source per logo to avoid trademark/licensing risk. Cross-check with the slideshow image-licensing discipline already applied in Codebase Cleanup.

- [ ] **Learning Visibility Dashboard**: Mentioned in `the-arsonists-smoke-detector.md`. We need to build this as we are publishing the article soon to the sage.education resource page.


- [ ] **Alex bio update** (Alexander Somma): Add Alex's background to the sage.is/about and sage.education pages — currently only Izzy's story appears. Should include Etsy backend, teaching career, and CTO role.

- [ ] **Docker Image Slimming (Pinned / Paused)**: (Alexander Somma)
  - [x] Hit the ~2.5GB target (down from 9.7GB)
  - [ ] Hit the ~1.5GB base-image target after trimming heavy transitive deps

- [ ] **Dockerfile: stop running pip as root**: Every `make it_build` prints `WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager` from the runtime stage. Fix by switching pip installs into a venv (`python -m venv /opt/venv` then `pip install …` against that venv) or by adding a non-root build user before the pip step. Bundled with the broader "non-root container" hardening if/when that lands; standalone fix is small.

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
  - [x] Env vars for reset enablement and interval — `ENABLE_TRY_SAGE`, `TRY_SAGE_RESET_INTERVAL_HOURS`
  - [x] Lifespan task fires the reset selectively (chats + files only; KBs and accounts persist)
  - [x] Banner countdown + pre-reset warning state (blue → amber when `hours_until_reset < 1`)
  - [x] Admin extend/reset endpoints with audit log lines
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

- [ ] **Audio Regression Testing Suite**: Deterministic voice-input coverage across recorder, transcription, and chat-input handoff
  - [ ] Define the audio test pyramid: unit logic, component behavior, browser E2E, and limited real-device smoke coverage
  - [ ] Build a golden audio corpus for regression runs: clean speech, silence, noisy input, clipped speech, accented speech, and low-volume samples
  - [ ] Add deterministic browser audio tests that feed known audio files as fake microphone input instead of relying on a live human mic in CI
  - [ ] Auto-grant microphone permissions in browser test runs and verify recording state transitions, processing UI, and transcript insertion into chat input
  - [ ] Cover failure paths explicitly: permission denied, empty transcript, transcription failure, canceled recording, and timeout handling
  - [ ] Add transcript assertions using normalized text matching where exact punctuation is not stable
  - [ ] Decide which audio paths run full end-to-end against the real backend transcription flow versus mocked/stubbed transcription responses
  - [ ] Evaluate Playwright specifically for browser-level media permission control, fake microphone input, cross-browser smoke tests, and trace debugging
  - [ ] Keep a small manual or staged real-microphone smoke suite for supported devices instead of making live microphone capture a required CI gate
  - [ ] Document how to run audio regression tests locally, in CI, and on staging with the required browser flags, fixtures, and expected assertions

- [ ] **Backend Rewrite Research**: Evaluate framework options and build contract tests
  - [ ] Review `docs/backend-rewrite-research.md` with team
  - [ ] Phase -1: Generate contract test suite from OpenAPI spec (private submodule)
  - [ ] Phase 0 spike: chosen framework + streaming Ollama proxy
  - [ ] Team decision: Go + PocketBase, Rust + Loco, or Python + Django?

- [ ] **Open WebUI Fork Maintainer Outreach**: Reach out to the BSD-3 / MIT fork cohort identified in `docs/outreach/open-webui-forks.md`. Six maintainers were shortlisted as potential allies after evaluating 32 forks. No fork has stood up its own community channel — every README still points at the upstream Open WebUI Discord — so there is a clear opening for Sage.is AI to consolidate the cohort.
  - [ ] Review the shortlist with the team and prioritize who to contact first
  - [ ] Draft a generic outreach template plus per-fork customization for the top three
  - [ ] Contact `blascerecer/open-webui` (101 stars, BSD-3, MCP bridge) — direct technical overlap with Sage.is AI's MCP work
  - [ ] Contact Public AI Movement (`forpublicai`) at hello@publicai.network — strongest mission match, "AI as public infrastructure"
  - [ ] Contact AMD-affiliated `aigdat/raux` via the GAIA team on LinkedIn — Tier-1 silicon vendor signal
  - [ ] Contact `AI3clauseBSD/claused-webai` (francoisp / headgasket) — most ideologically aligned, building a federation of "former-open" projects
  - [ ] Contact `BochaAI/open-webui-Bocha` at info@bochaai.com — vendor MCP integration angle, geographic diversity
  - [ ] Contact `hasanraiyan/open-webui` (Raiyan Hasan) — indie BSD-3 maintainer with public email
  - [ ] Decide whether to stand up a Matrix room or Discord for the BSD-3 Open WebUI cohort
  - [ ] Refresh the CSV (`docs/outreach/open-webui-forks.csv`) every ~6 months as forks evolve and as the license conversation matures

- [ ] **Finish offload Tier B + native-UI relocations** (2026-06-26): host disk freed from 12% to ~50% available after Tier A (cache purge + BuildCruft sweep) and Movies symlinked manually. Remaining work, none of it blocks Bonsai™:
  - [ ] Tier B `home` from admin shell — `sudo offload --target-home /Users/somma move home --apply`. Music symlink needs reconciling first (currently points at `/Volumes/Somma 01 Dock Drive/Music`, offload expects `/MovedHome/somma/Music`). Same-volume `mv` + re-symlink solves it in three commands.
  - [ ] Tier B `app` (Signal, Obsidian, Steam, Keybase, VSCode, Cursor, Epic, Minecraft) — quit each before firing
  - [ ] Tier B `dev` (CoreSimulator 5.8 GiB)
  - [ ] Docker Desktop disk image relocation via native UI (~14 GiB, biggest single win remaining)
  - [ ] iMovie Library + Music Library + Photos Library native-UI moves (per `offload relocations`)
  - [ ] Track upstream fix on [`Sage-is/homebrew-apps#1`](https://github.com/Sage-is/homebrew-apps/issues/1) — `du -sk` → `stat -f %z` verification swap that unblocks one-shot `offload move home --apply` for APFS-clone-heavy targets like `~/Movies`. Until then, the manual rsync+stat-verify+symlink dance from the 2.3.4 ship session is the workaround.

---

## Bugs

- [ ] **Knowledge file upload fails with misleading `'NoneType' object is not iterable`**: Hit on sage.startr.cloud 2026-06-05 running 2.3.2; try.sage.is on 2.3.2 does NOT exhibit this. The user-visible error is `400: 'NoneType' object is not iterable`. Root cause is downstream of the actual failure: `generate_openai_batch_embeddings` at [retrieval/utils.py:803-805](app/backend/sage_is_ai/retrieval/utils.py#L803-L805) (and the ollama/azure_openai siblings) catches every exception, logs it via `log.exception`, and returns `None`. The caller `generate_multiple` at [retrieval/utils.py:462](app/backend/sage_is_ai/retrieval/utils.py#L462) calls `embeddings.extend(func(...))` — `None` is not iterable, so the user sees the TypeError instead of the real cause (DNS failure, 401, model not loaded, endpoint not listening, etc.). The real error is in the container logs as the `log.exception` block immediately preceding the TypeError traceback. The try.sage.is vs sage.startr.cloud divergence is most likely (a) different `RAG_EMBEDDING_ENGINE` value (try.sage may be on `chroma` or local sentence-transformer, bypassing this path entirely), or (b) stale URL/key in the sage.startr.cloud DB from the inherited 2-month-old volume. #critical #bug
  - [ ] **Fix the silent-failure footgun**: replace `return None` in all three `generate_*_batch_embeddings` functions with `raise EndpointUnreachable(url, underlying)` so callers see the real cause. This IS Phase 2 of the 2.3.3 hardening plan, applied one layer deeper than originally scoped. See `~/.claude/plans/due-to-the-many-silly-ladybug.md`.
  - [ ] **Map `EndpointUnreachable` → `503` with `{detail, url, fix}`** in a FastAPI exception handler so the UI gets a structured fix-pointer instead of a misleading TypeError.
  - [ ] **Boot probe the embedding URL** so `/admin/diagnostics` lights up red BEFORE the next upload, not at first failure.
  - [ ] **Diagnose sage.startr.cloud specifically**: read the container log for the `log.exception` block preceding a TypeError. Determine which engine is configured (openai? chroma? bare?) and what URL it points at. Compare to try.sage.is's working config.
  - [ ] **Refresh the bug's surface footprint**: the same `Exception → None` swallow exists in `generate_ollama_batch_embeddings`, `generate_azure_openai_batch_embeddings`, and likely the reranker — audit them as a class, fix them together.

*(Surfaced 2026-06-05 by Alexander; sage.startr.cloud only; try.sage.is unaffected on identical 2.3.2 image.)*

- [ ] **AI Engine Wizard Embedding Download Has No Stall Watchdog**: When the embedding model fetch from HuggingFace stalls (network drop, HF outage, slow link), the wizard sits in `embedding=downloading` indefinitely. No timeout, no retry, no resumable state surfaced to the admin. `wizard-smoke.sh` catches this externally via `INSTALL_TIMEOUT_SEC`, but a real user has no signal except an idle spinner. #bug
  - [ ] Surface HF download progress (bytes, last-byte timestamp) to `request.app.state.MODEL_DOWNLOAD_STATUS` so the status endpoint exposes liveness.
  - [ ] Watchdog in `_download` (`retrieval.py`): if cache size hasn't grown in N minutes (configurable, default 5), mark status=`stalled`, capture the error, allow retry via a re-POST to `/api/v1/retrieval/models/download`.
  - [ ] Surface stalled state in the wizard UI with a retry button + "check your connection" hint.

*(Surfaced 2026-05-18 during the cross-arch smoke run when an internet drop wedged the embedding download. The wizard never noticed.)*

- [ ] **Chat Microphone Recording Does Not Populate Message Input**: Recording from the microphone icon in chat does not process speech into the text field used to send messages #critical #bug
  - [ ] Reproduce the issue in the chat interface and confirm whether capture, transcription, or input binding is failing
  - [ ] Trace the microphone/transcription flow from recorder output into the chat composer state
  - [ ] Fix the handoff so completed recordings populate the message input field
  - [ ] Add regression coverage for microphone-to-input behavior in chat

*(Surfaced by user report in chat, 2026-05-11.)*

- [ ] **Code Fence in chat renders near invisible**: when inputting text in chat and using codefence the typed or pasted text in the codefence is white on light grey.
  - [ ] to reproduce start new chat, use backticks and click space key to open codefence ux. Type words.
  - [ ] Depending on text entered various colors visible. Take note of low contrast combinations.
  - [ ] Locate cause of color issue and fix


---

## Done

> Completed items are moved to `docs/completed-todos.md` periodically.
> Check off items with `- [x]` and leave them in place until the next cleanup.

- [x] **try.sage Runtime `/llm-status` Endpoint Not Env-Gated**: With `ENABLE_TRY_SAGE=false`, `GET /api/v1/sage/runtime/llm-status` returns `403 {"detail":"Not authenticated"}` instead of 404. The route handler is registered unconditionally; auth is the only barrier. Sibling endpoints (`status`, `personas`, `limits`) correctly 404 when the env flag is off. #critical #bug
  - [x] Locate the `llm-status` route handler in the trial runtime router
  - [x] Confirm whether it sits outside the trial router or whether the router-level `enable_try_sage` check is missing for this handler specifically — root cause was **dependency order**: `_require_try_sage_enabled()` was called inline AFTER `Depends(get_admin_user)` had already evaluated, so auth's 401/403 fired before the env-gate's 404. Same defect class affected `/extend` and `/reset`.
  - [x] Add the same gating that protects `status` / `personas` / `limits` so the route returns 404 when the env flag is false — fix at `app/backend/sage_is_ai/routers/sage_runtime.py:267-272`: lifted gate into `_gate: None = Depends(_require_try_sage_enabled)` parameter listed BEFORE `Depends(get_admin_user)`. Applied to `/llm-status`, `/extend`, `/reset`. Docstring of `_require_try_sage_enabled` now documents the ordering contract.
  - [x] Re-run the trial smoke for-loop; confirm `404 /llm-status` — verified against fresh `sage-is/ai-ui:bug-verify` image; all seven trial endpoints (`status`, `personas`, `limits`, `llm-status`, `extend`, `clear`, `reset`) return 404.

*(Surfaced 2026-05-10 during the regression sweep — caught by the `for ep in status personas limits llm-status extend clear` curl loop.)*

- [x] **Unregistered `/api/*` Paths Return SPA HTML Instead of 404**: With `ENABLE_TRY_SAGE=false`, `GET /api/v1/sage/runtime/extend` and `GET /api/v1/sage/runtime/clear` return `200 text/html` (5463 bytes, identical etag) — the SvelteKit static catch-all serves `index.html` for unregistered backend paths. Breaks any curl-based smoke test that expects 404 for absent routes and masks future router-registration bugs. #bug
  - [x] Locate where the SPA static catch-all is mounted in the FastAPI app — `SPAStaticFiles.get_response` in `app/backend/sage_is_ai/main.py`.
  - [x] Add a guard so `/api/*` paths that don't match a registered router return JSON 404, not the SPA index — fix at `app/backend/sage_is_ai/main.py:498-510`: in `SPAStaticFiles.get_response`, paths equal to `api` or starting with `api/` now return `JSONResponse(status_code=404, content={"detail": "Not Found"})` instead of falling through to `index.html`.
  - [x] Verify with a curl against any made-up `/api/v1/nonexistent` path — should return 404 with `application/json` — verified: `GET /api/v1/literally_made_up_path` returns `404 Not Found` with 22-byte JSON body. Non-api SPA paths still return `200 text/html` (frontend routing intact).
  - [x] Re-run the trial smoke for-loop; `extend` and `clear` should report `404 /<endpoint>` — verified, plus `/reset` also 404 (which would have been a third leak without this fix).

*(Surfaced 2026-05-10 during the same sweep.)*

- [x] **Homebrew Tap Release**: Finish and verify the brew install path #critical
  - [x] Test: `brew tap sage-is/apps && brew install ai-ui`
  - [x] Fix homebrew-apps Makefile `release_finish`
  - [x] git flow state got stuck on v0.1.2 release; manual merge required to complete
  - [x] celebrate!!! :D

- [x] **try.sage Runtime and Admin Controls**: (Alexander Somma + Izzy Plante) — Shipped Phase A 2026-04-27.
  - [x] Gate try.sage.is ai behind env vars
  - [x] Seed default try.sage agents: Sage Strawberry, Sage Startr.Style, AstroPi AI tutor (with KBs)
  - [x] Register `https://markdown-search.production.openco.ca` in `TOOL_SERVER_CONNECTIONS`
  - [x] Add a dummy-tools server with placeholder endpoints (revisit later — see Production Decisions)
  - [x] Trial helper endpoints: status, personas, limits, llm-status, extend, reset
  - [x] Auto-reset every 24h via env-configurable settings; selective wipe preserves persona accounts and KBs
  - [x] Admin-only extend (capped at one extension per window) and force-reset
  - [x] RBAC via existing `get_admin_user` dependency on protected endpoints
  - [x] Hidden OpenAI-compatible LLM connection (memory-only, never persisted, never echoed in any response)
  - [x] Model allowlist via `TRY_SAGE_LLM_MODELS`
  - [x] Document env vars, reset semantics, admin controls in `docs/try-sage-deployment.md`
  - [x] Makefile targets `try_sage_start` / `try_sage_stop`

- [x] **try.sage.is Experience and Insights**: (Alexander Somma + Izzy Plante) — Shipped Phase B 2026-04-27.
  - [x] Persistent top-of-screen try.sage banner with live HH:MM:SS countdown
  - [x] Admin extend/reset CTAs in the banner row (live next to the countdown they affect)
  - [x] Non-admin info line directing to docs and admin
  - [x] User-bar persona switcher: admin + facilitator + 3 trial users (configurable up to 5 trial users)
  - [x] Tutorial overlay with config-driven steps (`TRY_SAGE_TUTORIAL_STEPS_JSON`); 6-step default with placeholder cards when unset
  - [x] Setup wizard suppression in trial mode + admin escape hatch in Admin → Settings → Trial Mode
  - [x] Per-step `dismissible` flag honored; localStorage seen-flag persists across sessions
  - [x] Provider-agnostic analytics shim (Matomo + GA + Plausible) wired via `$config.analytics`
  - [x] Pure-Svelte zero-dep QR encoder for persona magic-link sharing in workshops
  - [x] Document the UX + analytics event map in `docs/try-sage-deployment.md`

- [x] **try.sage Tutorial Step Cards Render Empty**: When the tutorial does open (via Admin → Trial Mode → Replay tutorial), the step cards are missing content — title, "Video coming soon" placeholder, and `description` paragraph all missing or partially missing. #bug
  - [x] Reproduce: with `TRY_SAGE_TUTORIAL_STEPS_JSON` unset, open the tutorial via the admin replay button — confirm cards render without expected content
  - [x] Inspect the default-step rendering branch in `app/src/lib/components/setup/TrySageTutorial.svelte` — specifically the placeholder card layout that fires when `step.video_url` is empty/missing
  - [x] Confirm whether the `DEFAULT_STEPS` constant is reachable, the iteration is correct, and i18n wrapping isn't producing empty strings
  - [x] Fix the missing-cards rendering so at minimum each step shows: title, "Video coming soon" placeholder, and the step's `description` paragraph

*(Surfaced 2026-04-29 in the same regression session.)*

- [x] **Trial Banner Overlapped by Left Sidebar**: Once a persona signed in, the left sidebar (admin / chat list) overlapped the trial banner. Banner was a full-width strip pushed into the layout flow; sidebar's z-index let it cut into the banner's edges. #bug
  - [x] Float the banner above the app shell rather than reflowing it inline. Outer wrapper `position:fixed; top:0.5rem; left:0; right:0; z:40; pointer-events:none`. Inner pill `max-w:60ch; margin:0 auto; pointer-events:auto; rounded; subtle shadow`. Doesn't push navbar/content down on first paint and z-index keeps it above the sidebar.
  - [x] Edited `app/src/lib/components/TrySageBanner.svelte` outer wrapper only — inner content (countdown row, persona-jump row, `<details>` block) untouched.
  - [x] Banner now slides 280px right when the desktop sidebar opens so it stays centered over the chat content, not the full viewport. Driven off the existing `showSidebar` store with a 200ms ease transition. Mobile is unaffected (sidebar overlays there).

*(Surfaced + fixed 2026-04-29 during regression testing.)*

- [x] **Replace David / Sistine Chapel Art in Login Slideshow**: The login/onboarding/welcome slideshow ships a Michelangelo's David and a Sistine Chapel ceiling image — both are recognisable Renaissance pieces that don't fit the Sage.is brand and may carry licensing risk depending on the source photo. Swap for original or CC/public-domain imagery. #bug
  - [x] Find the offending images under `app/static/` (likely `static/assets/images/` or wherever `SlideShow.svelte` reads from) and confirm the exact filenames + license source
  - [x] Pick replacements: original Sage.is photography, or CC0 / public-domain alternatives that match the warm-workshop tone (libraries, classrooms, observatories, etc.)
  - [x] Replace files in-tree, keep filenames stable so `SlideShow.svelte` keeps working without code change. Run the build and visually confirm new images render in the welcome slideshow + try.sage welcome page.
  - [x] Cross-link with the existing **Codebase Cleanup → "Replace login slideshow images with original or CC/public-domain photos"** task — collapse if both are doing the same work.

*(Surfaced 2026-04-29 reviewing the trial welcome page imagery.)*

- [x] **try.sage Tutorial Does Not Auto-Open on First Persona Sign-In**: The TrySageTutorial modal is supposed to auto-open the first time a persona signs in (gated on `$config?.features?.enable_try_sage` + signed-in `$user` + missing `localStorage.try_sage_tutorial_seen_v1`). Manually triggering "Replay tutorial" from Admin → Trial Mode opens it correctly, so the modal itself works — only the auto-trigger fails. #bug
  - [x] Reproduce: clear `localStorage.try_sage_tutorial_seen_v1`, sign in via a persona magic link, confirm modal does NOT appear
  - [x] Inspect the `onMount`/reactive trigger condition in `app/src/lib/components/setup/TrySageTutorial.svelte` — likely the `$user` check fires before the user store hydrates after magic-link verify, OR the SvelteKit hard-navigation from `/auth#magic_token=...` lands before the layout has subscribed to `tutorialReopen`
  - [x] Fix so the auto-show fires on first persona sign-in, not just from the admin "Replay tutorial" button
  - [x] Add a Vitest spec that mounts the component with mocked `$config`, `$user`, and a clean `localStorage`, and asserts the modal opens

*(Surfaced 2026-04-29 during manual regression of the persona sign-in flow.)*

- [x] TodoScope Alignment
  - [x] Restructure TODO.md to TodoScope conventions
  - [x] Fix duplicate rows in `.todoscope-exclude.csv`
  - [x] Run TodoScope scanner and verify kanban board matches expectations
