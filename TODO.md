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

- [x] **Deploy 2.3.2 to try.sage.is**: `v2.3.2` deployed at some point after the 2026-06-10 freeze lifted — confirmed live 2026-07-03 (`GET try.sage.is/api/config` → `version: 2.3.2`; `/assets/loader.js` → `200`, was 404 at the time this item was written). Never checked off. #critical

- [ ] **try.sage.is is two releases behind (2.3.2 live, 2.3.4 is current)** (surfaced 2026-07-03 reconciling this list against production): `distribution.env`'s `SERVER_TAG=2.3.4`; CHANGELOG shows 2.3.3 (Admin Diagnostics page + `EndpointHealth` registry) and 2.3.4 (how-to-fix modals + command library) shipped after the 2.3.2 deploy and never made it to try.sage.is. No freeze is currently on record for try.sage.is beyond the 2026-06-10 window — worth a quick check with Alexander/Izzy that nothing new has superseded it before redeploying. CapRover Method-6 image-pull at captain.try.sage.is → `try-sage-is` app → `ghcr.io/sage-is/ai-ui:2.3.4`. #critical

- [x] **Ship 2.3.1 — Jidoka spine + three Poka-Yoke children**: Shipped 2026-05-19. Tag `v2.3.1` pushed, `ghcr.io/sage-is/ai-ui:2.3.1` published, `SERVER_TAG=2.3.1` pinned across the hardlink chain. Detail in `CHANGELOG.md`; plan at `~/.claude/plans/given-our-newest-trends-modular-sloth.md`. #critical

- [x] **try.sage Manual Regression Sign-off** (2026-04-27): Phase A backend + Phase B frontend shipped. All 12 smoke checks passed (container boot, persona magic-links, banner, switcher, tutorial, admin tab, hidden connection, model filter, env-gate disable). Reference left for future regression-pass authors.


---

## TODO

### Repo Hygiene & Security

- [ ] **Repo-wide hidden-artifact allowlist rollout**: Deny dotfiles and dotfolders everywhere in the repo by default; explicitly include only approved shared hidden artifacts so local state cannot drift into git by accident.
  - [x] Implement the repo-wide hidden-artifact allowlist in `.gitignore`
  - [x] Document the contributor approval rule for new hidden artifacts in `CONVENTION.instructions.md`
  - [x] Use `!.*.example` as the generic allowlist for sanitized hidden example templates
  - [x] Verify included vs excluded hidden artifacts (`.obsidian/`, `.semgrep/`, `.env.example`, `.claude/`, `.env`, `app/.eslintrc.cjs`, `app/backend/.gitignore`)
  - [ ] Review currently tracked hidden artifacts and remove any that should be excluded going forward

- [ ] **Coordinated langchain major bump to drop CVE-2026-34070 suppression**: `.trivyignore` suppresses `CVE-2026-34070` (path traversal in `langchain_core`'s legacy `load_prompt()`, unreachable in this codebase — see `.trivyignore` comment) because the fix (`langchain-core==1.2.22`) needs `langchain-core<1.0.0` dropped, which both pinned sprig-side packages (`langchain==0.3.30`, `langchain-community==0.3.27`, `app/backend/requirements.txt:51-56`) require. Plan and test a coordinated bump of the whole langchain/langchain-community/langchain-core trio (rag-loaders Sprig™ side) past 0.3.x, then remove the `.trivyignore` entry.

- [ ] **Automate `sage-archivo.ttf` subsetting instead of committing a hand-subsetted binary**: `scripts/e2e/watch/sage-archivo.ttf` is a manually-subsetted (basic-Latin + em-dash) copy of `app/static/assets/fonts/Archivo-Variable.ttf`, shrunk from 637 KB to 153 KB to clear the `check-added-large-files` 500 KB cap. It'll silently drift out of sync (or grow back over the cap) if the noVNC branding text changes and nobody remembers to re-subset by hand. Move the `pyftsubset` step into `scripts/e2e/watch/Dockerfile` itself (`COPY` the full font, subset at build time) so there's no binary duplicate to maintain in git.

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

- [ ] **`make caprover_app_create APP=<name>` wrapper**: One Makefile call to register a new CapRover app via the HTTP API (`/api/v2/user/apps/appDefinitions/register`), POST the env-var block, set the persistent volume path, and connect a custom domain. Driver: avoid the dashboard click-through we did for `try-sage-is` on `captain.example.com` 2026-05-01.

- [ ] **Port `sharded-zooming-parrot` Poka-Yoke release plan to this Makefile**: Add `release_preflight` (Docker memory, working tree clean, gh auth, develop synced) before any irreversible step in `release_and_push_GHCR`; make `it_build_multi_arch_push_GHCR` safe to re-run after a partial failure. Driver: 2.3.0 release_finish completed but buildx OOMed mid-push, leaving the tag on origin without a matching GHCR image. Plan at `~/.claude/plans/sharded-zooming-parrot.md`.
  - [x] **Post-push manifest verify SHIPPED** (2026-07-19; fixture 3/3, live pass on `:latest`, live 404 fails loudly; uncommitted, user commits): after the multi-arch push, `release_and_push_GHCR` + `hotfix_and_push_GHCR` now assert the pushed GHCR image is PRESENT (not a 404) and a real amd64+arm64 index, BEFORE the SERVER_TAG pin — so a missing/single-arch image fails at the operator's terminal, not later at CapRover (the 3.0.0 → CapRover "manifest unknown" class, and the sibling `--platform`-typo single-arch class). New `scripts/verify-image-manifest.sh` uses `docker buildx imagetools inspect --raw` (registry-agnostic — survives the in-house-registry swap, no ghcr token dance), drops buildx's `unknown/unknown` provenance rows, refuses bare tags. Fixture `scripts/smoke/manifest-verify-fixture.sh` proves the logic against public images (good multi-arch → pass; amd64-leaf, digest discovered at runtime → fail; absent tag → fail). Targets `verify_ghcr_manifest` + `manifest_verify_fixture` (help-annotated, in `.PHONY`). Still OPEN in this parent item: `release_preflight` (docker mem, clean tree, gh auth, develop synced) and re-run-safety of `it_build_multi_arch_push_GHCR` after a partial failure. #critical
  - [ ] **`wizard_smoke` cold-cache false-fail (2.3.2, 2026-05-29)**: The 15-min `INSTALL_TIMEOUT_SEC` wasn't enough for ~5 GB of wheels + ~2 GB embedding model on residential bandwidth — smoke false-failed even though uv was actively downloading and `models/status` showed `error: null`. Adding a `SKIP_SMOKE=1` bypass is NOT poka-yoke — it normalizes operator override of the safety gate. Real poka-yoke directions to evaluate: (a) bake uv wheel cache + embedding model into the smoke image at build time so install becomes unpack-only (image grows ~5-7 GB but smoke becomes deterministic and runs in minutes); (b) move smoke to the staging CapRover app once it exists (datacenter bandwidth removes the residential-bandwidth dimension entirely; ties into the staging-smoke design discussed for 2.3.3); (c) make smoke resumable across container restarts so a partial install survives and the next run starts from where it stopped. Any of these makes the failure mode disappear at the root. Until one ships, a cold-cache false-fail blocks the release — that's the gate doing its job.
  - [ ] **Target naming clarity**: `release_finish` only finishes git-flow (merge + tag + push) — it does NOT publish the image. `release_and_push_GHCR` is the canonical ship target but its name doesn't read that way, and its hidden `release_smoke` prereq is a footgun. Consider a `make ship` alias and a rename of `release_finish` → `release_gitflow_finish`.
  - [ ] **`make help` is hardcoded echos**: `##` inline target docs (already present on `wizard_smoke`, `cross_smoke`, `_pin_server_tag`, and now `verify_ghcr_manifest`/`manifest_verify_fixture`) are invisible to operators because `help:` doesn't scan for them. Refactor `help:` to grep `## <target> — <description>` lines and render them automatically. One-time change, ongoing payoff.

- [x] **Shared build/gate libraries — DRY pass** (2026-07-22; uncommitted-in-part, user commits): extracted two shared libs to kill copy-pasted boilerplate. `scripts/lib/gate.sh` — PASS/FAIL + `ok`/`no`/`require`/`gate_summary`; adopted by `verify-image-manifest.sh` + `manifest-verify-fixture.sh` + the 4 heavy smoke gates (lifecycle/upgrade/durability/signing), all re-certified green via `gauntlet_full` (66/66, 12/12, 10/10). `scripts/lib/sprig-build.sh` — `sprig_build_defaults` (the 8 OCI/registry constants), `sprig_arch_normalize`, portable `sha256`, `sprig_ensure_registry`, `sprig_push` (optional `SIG_LAYER` superset), `sprig_timing_start|end`. **9 `build-sprig-*` recipes** now source it (tika, docling, backup-rclone, rag-loaders, export-document, media-ffmpeg, dev-svelte, vector-chroma, whisper) — ~270 lines of duplication gone; every recipe gained the ⏱ footer. Certified by REAL rebuild across 3 shapes: **tika** (jlink server, both arches — sha256 **byte-identical** to the CATALOG pins), **backup-rclone** (static-download deliver + SIGN), **rag-loaders** (pip). Hazards caught during rollout: set-e safety (helpers `return 0` past benign falses — arm64 arch, registry poll); `TAG=v2` preserved for dev-svelte/vector-chroma; whisper's out-of-block `ORAS_IMG`/`sha256` de-duplicated.
  - [ ] **4 outlier recipes stay OFF the lib** (by design — none has the standard arch/push blocks; forcing them = over-fit): `build-sprig-theme.sh` (arch-neutral 846-byte token artifacts), `build-sprig-minilm.sh` (arch-neutral ONNX weights, custom push — **also carries the macOS `bsdtar` lacks-`--sort=name` reproducibility bug: switch its pack to GNU-tar-in-docker when next touched**), `build-sprig-reranker.sh` (GGUF, two push paths), `repack-sprig-arch.sh` (re-tags an existing artifact — different tool). Optional light reuse: they COULD call `sprig_build_defaults` + `sprig_ensure_registry` for constants/registry only.
  - [ ] **`wizard-smoke.sh` keeps its own helper style** (`require`/`fail` with container-log dump, `KEEP_ON_FAIL`) — could adopt `gate.sh` for consistency, but its fail-shape differs; low priority.
  - [ ] **`parity_gate` now SKIPs (not FAILs) when its 8.I.3 artifacts are absent** (shipped 2026-07-22) so `gauntlet_full` no longer halts on a not-yet-built future gate. To actually EXERCISE parity, build the artifacts: `scripts/build-llama-static.sh` (+ the 8.I.3 gguf/harness prep), then `make parity_gate`.

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

- [x] **First Graft: make one wizard toggle pull a Sprig** (2026-06-30, exceeded by 2026-07-03): Shipped as the walking skeleton (mock-embedding on a loopback port, `RAG_EMBEDDING_ENGINE=openai` dispatch) and grew well past it in the four days since. Catalog now carries **14 entries across 9 capabilities** (`app/backend/sage_is_ai/sprigs/supervisor.py`, AST-counted): six `embedding` cultivars (mock-embedding, all-MiniLM-onnx, minilm-onnx-inhoused, multilingual-e5-large, bge-large-en-v1.5, e5-large-gguf), plus one each for `dev`, `vector`, `rag`, `export`, `code`, `browser-ml`, `media`, `backup`. `GET /catalog`, `POST /graft`, and `POST /prune` are all live (`routers/sprigs.py`); docstring drift that claimed prune/top-graft/multi-catalog were deferred is fixed. `revive` = re-graft (no separate op); `topgraft` runs inside graft(). **12 of the 14 deliver via sha256-verified `oci-artifact`** from a local registry (matching the 12 registry repos, no HuggingFace/pip pull at graft time); the 2 that don't are `mock-embedding` (mock server) and `all-MiniLM-onnx` (live HF pull). The in-housing north star (no end user pulls from HuggingFace or pip once Sprigs work) is real for those 12, not aspirational. `scripts/smoke/sprig-lifecycle.sh` is wired into `gauntlet` and passes 41/41 (verified 2026-07-03: bare-rootstock absences, clean pre-graft 503s, GGUF-on-bare-rootstock, vector-chroma, rag-loaders restart-free, live onnx→gguf top-graft, export-document, code-pyodide/browser-ml, media-ffmpeg/backup-rclone/dev-svelte, final image 604MB). `make sprig_registry` (new 2026-07-03) makes the local OCI registry an idempotent one-command dependency of `sprig_smoke` instead of an undocumented "must already be running" assumption. #bonsai #critical

- [x] **Sprig subsystem audit + Poka-Yoke pass** (2026-07-03/04): 5-dimension adversarial audit (44 verified findings). Answered the operator's three questions — clean? / all chunks sprigged? / clear for non-technical people? Shipped this pass: **(quick wins)** the admin UI now surfaces the backend's actual graft/prune error detail instead of a generic toast (`Sprigs.svelte`); pinned the redundant runtime `chromadb==0.6.3` install (`retrieval.py`, was unpinned → base-breaking 1.5.x); rewrote the drifted "DEFERRED" docstrings across `supervisor.py`/`routers/sprigs.py`/`mock_embedding_server.py`/`embedding_server.py`; fixed the grafted counter to include `delivered`; added the 21 missing Sprig i18n keys to `en-US`; corrected the "12 → 14 entries" miscount. **(durability — the lead ask)** grafts now survive a Rootstock™ restart: the supervisor persists a volume-resident `state.json` and reconciles on boot — re-extracting deliver overlays from a volume-cached sha256-verified tar (`artifact.py`, offline; also fixes the "tag bump won't re-pull" footgun via a `.delivered-tag` marker) and re-spawning embedding cultivars, with a single-owner flock guard for multi-worker and an import-time fail-clean guard in `main.py` (a dead-loopback embedding config no longer reports "ready"). Config-pointing extracted to a shared `sprigs/embedding_dispatch.py` (router + reconcile, no drift). **(test coverage, 2026-07-04)** `sprig_smoke` grew to **44 checks** — new section 6c grafts `minilm-onnx-inhoused`, the only user of artifact.py's `chroma-onnx` seed path (previously zero coverage on that path), asserts a 384-dim vector from the seeded offline cache, and checks `state.json` on the volume. New **`make sprig_durability`** gate (`scripts/smoke/sprig-durability.sh`, wired into `gauntlet_full`): full `docker rm -f` recreation with the registry STOPPED → boot reconcile restores the ffmpeg overlay + re-spawns the embedding child from the volume, offline. Cypress `sprigs-panel.cy.ts` grew to **7 tests**: new failed-graft test asserts the backend's fix-pointer ("Graft vector-chroma first") reaches the toast, and a counter regression test asserts `delivered` sprigs count as grafted. The two big cultivars the default gates skip got their own **opt-in `make e2e_heavy`** gate (`cypress/e2e/heavy/sprig-cultivars.cy.ts`, in NO gauntlet — run on demand): verified 3/3 green 2026-07-04 — vector-chroma delivery, **bge-large-en-v1.5 grafting restart-free straight after the overlay delivery** (enabled by a new `importlib.invalidate_caches()` poka-yoke in the supervisor's dep pre-check — the parent's stale import cache used to force a restart between vector-chroma and any onnx graft), and **all-MiniLM-onnx doing its real ~80MB HF/chroma-S3 pull** then top-grafting over bge with the 1024→384 "must be reindexed" width warning asserted in the UI (a Poka-Yoke path nothing else tested). Fixing the heavy runner also surfaced+fixed that `SPEC=` spec selection was silently broken for ALL subdir suites (Cypress 15 intersects `--spec` with the top-level-only `specPattern` — `cypress/e2e/upstream/` was unreachable too); `run-cypress.sh` now overrides `specPattern` instead. Default gates stay zero-egress. #bonsai

### Sprig B1 — finish extraction (audit backlog, sequenced next)

- [x] **Extraction pass shipped** (2026-07-05/06, all gates green: smoke **57/57**, durability 12/12, e2e 12/12, e2e_heavy 3/3): Catalog is now **15 entries / 11 capabilities, zero-egress at graft time**. **(reranker)** New `bge-reranker-v2-m3-gguf` — the design pivoted from ONNX cross-encoder to GGUF once scouting confirmed the in-house static llama-server (b9859) supports `--rerank` and its `/v1/rerank` speaks the exact Jina/Cohere contract the existing `ExternalReranker` (`engine=external`) already parses: one binary + one Q8_0 model (~360MB), zero client changes, `sprigs/reranker_dispatch.py` points `RAG_EXTERNAL_RERANKER_URL` at the loopback. Packaging `scripts/build-sprig-reranker.sh` sanity-gates semantic ordering before push. **(stt)** New `whisper-base-ggml` — static whisper.cpp **v1.9.1** `whisper-server` (v1.7.4 lacks `/health`; static musl needs `-DGGML_OPENMP=OFF`) + ggml-base-q8_0, serving `/v1/audio/transcriptions` for the untouched `STT_ENGINE=openai` client path (`sprigs/stt_dispatch.py`); grafting makes the wizard's HF whisper download skippable. **(cleanup)** `all-MiniLM-onnx` RETIRED (last live-pull entry; heavy cypress swapped to `minilm-onnx-inhoused`, same 1024→384 width-warning coverage, gate now zero-egress and 5× faster); `sprigs/vector_bootstrap.py` unifies the two divergent chromadb pip sites into ONE sprig-first bootstrap (volume tar → registry → pinned-pip fallback; try.sage flips to sprig-first automatically at prod cutover); top-graft/reconcile/prune/restart-backstops generalized to all three server capabilities (`server_args` catalog field). Ops lessons burned in: host disk hit 100% mid-build (Docker VM corruption — recovered, zero artifact loss), macOS bsdtar lacks `--sort=name` (packs now run GNU tar in docker), `e2e` needs `app/node_modules` (containerized `bun install --frozen-lockfile` restores it after cleanup sweeps). **(upgrade path, 2026-07-06 follow-up)** "Pull the new image and boot" still upgrades everything: pins/tags ship WITH the image, and boot reconcile brings the volume into agreement — deliver overlays re-extract (offline on same tag, re-pull on bump), weight cultivars now honor tag bumps too (`.delivered-tag` marker extended to model-dir/chroma-onnx seeds; the sentinel-only check silently served STALE weights across version bumps), retired catalog entries are skipped WITH a logged re-graft pointer, and a failed upgrade pull leaves the current version serving (wipe only after verified pull). Live-proven by tag-bump simulation; smoke re-verified 57/57. Prod caveat: tag bumps need the registry reachable → don't bump artifact tags in prod images until the registry cutover ships. #bonsai
- [ ] **Delete the chromadb pip fallback** (end-state of the bootstrap): blocked on prod-registry cutover + one release of soak. `vector_bootstrap.py` already prefers the sprig; the pip path goes cold automatically once prod has a registry. #bonsai
- [x] **Poka-Yoke pass + sage.startr.cloud upgrade rehearsal SHIPPED** (2026-07-12; all standard gates green on the final image — smoke 66/66, signing 10/10, durability 12/12, e2e green, upgrade_gate 16/16; uncommitted, user commits): a 32-agent adversarial audit (refute-first verify, several findings reproduced live) returned **25 confirmed findings**; every code-level one fixed. **Security/correctness (backend):** theme validator now decodes CSS escapes before scanning so `url(\68ttp…)` / `\@import` can't smuggle an external beacon past the self-containment check (unit-proven in-image); `SPRIG_REQUIRE_SIGNED` with no pubkey is a LOUD boot error instead of silently bricking every signature-required graft on reconcile; arch-refused (and registry-unreachable) reconcile entries no longer erode from `state.json` — a new `_deferred` set keeps them in desired-state until an explicit prune or a compatible host (prune clears them); `MODEL_DOWNLOAD_STATUS["chromadb"]` starts honest ("pending", not a literal "ready" lie on a slim boot); `_check_boot_config` names a malformed `SPRIG_REGISTRY`, an unknown host arch, and the require-signed-without-key case at boot. **Operator-facing (UI):** `/catalog` exposes `host_arch` + per-entry `compatible`; the admin Sprigs panel greys out incompatible cards with "Not available on this server (amd64)" + tooltip, so no click 503s (i18n keys added). **Supply chain:** `publish-sprigs.sh` now derives the repo list from the supervisor CATALOG (not whatever's in the local registry — the gap that let the 2 theme artifacts ship unpublished) and verifies ANONYMOUS ghcr pullability via the token endpoint, not just gh-api visibility. **Privacy:** `tools/db_snapshots/` fully gitignored — real user data (176MB webui.db, 3.9GB vectors) was one `git add` from committing. **New gate `make upgrade_gate`** (`scripts/smoke/upgrade-gate.sh` + `scripts/snapshots/inject-test-admin.py` + `cypress/e2e/upgrade/legacy-data.cy.ts`, reusable via `TARGET_URL` against any snapshot/staging clone): boots THIS image on a COPY of the prod snapshot (read-only source, throwaway admin injected into the copy), proving DB migration, user/chat/knowledge survival, legacy openai-embedding config untouched, RAG degrading cleanly (asserts HTTP code, not just body shape), chromadb reading the prod store with collection PARITY, themes on legacy data, and the amd64 capability gap (loud + asserted, section 6). Gate-quality fixes: `jq length`-counts-error-keys, unconditional "restarted healthy", and the fresh-volume amd64 rehearsal were all self-defeating and are fixed. `run-cypress.sh` gained `TARGET_URL` mode so the upgrade Cypress half can actually run against an existing container. Findings the audit surfaced but that are ARCH/DEPLOY decisions, not code bugs → the two items below. #bonsai #critical
- [x] **Prod-registry cutover SHIPPED** (2026-07-12, poka-yoke pass): registry is env-driven — `SPRIG_REGISTRY` (default `ghcr.io/sage-is`, SECURE) + `SPRIG_REGISTRY_INSECURE` (auto-on only for loopback/local hosts) in `sprigs/supervisor.py`; all 16 catalog `repo`/`insecure` fields resolve from those constants; boot reachability probe (`_check_registry_reachable`) turns an unreachable registry into ONE loud boot log instead of a per-graft 503; boot-config validation catches a malformed `SPRIG_REGISTRY` (scheme prefix, uppercase path). 5 smoke/e2e boot sites + Makefile run targets pass the dev registry through; `SPRIG_REGISTRY` env pass-through added to `COMMON_RUN_ARGS`. **NEAR-TERM per Alexander:** self-host the prod registry in-cluster with GHCR as mirror, or proxy GHCR for now — `SPRIG_REGISTRY` makes that a zero-code swap. #bonsai
- [x] **amd64 Sprig artifacts (8.J) — DEPLOY BLOCKER RESOLVED** (2026-07-15, shipped in 3.0.0): all **17 catalog entries graft on both arm64 and amd64** — nothing arm64-only remains (static recheck 17/17 in the real image). amd64 artifacts: python-wheel closures (vector-chroma `v2-amd64`, rag-loaders/export-document `v1-amd64`) built per-arch under QEMU; ONNX embedding weights flipped arch-neutral (minilm/e5-large/bge — empty `amd64` override, same tag+sha, they ride the vector-chroma onnxruntime); static servers (whisper `v1-amd64`, and the two GGUF via `repack-sprig-arch.sh` after `scripts/build-llama-static.sh`); static downloads (media-ffmpeg/backup-rclone `v1-amd64`); dev-svelte `v2-amd64`. **The llama.cpp b9859 yak is solved:** `LLAMA_BUILD_UI=OFF` + `LLAMA_USE_PREBUILT_UI=OFF` builds the server headless (empty embedded-UI lib), dodging the missing-`loading.html` HF-bundle failure — `LLAMA_BUILD_UI=OFF` alone is NOT enough (the prebuilt fetch still runs). Both GGUF amd64 artifacts BOOT-TESTED under QEMU: e5-gguf serves 1024-dim embeddings, reranker orders correctly via `/v1/rerank`. Multi-arch schema (`arches: {arch: {tag, binary_sha256}}`) + graft-time overlay unchanged. `upgrade_gate` section 6 flipped from must-REFUSE to must-GRAFT. Full status in `docs/deploy-sage-startr-cloud.md`. #bonsai #critical #deploy-blocker
- [x] **Sprigs published to GHCR** (2026-07-07): all **14 sprig artifacts** (16 tags — incl. the catalog-pinned `vector-chroma:v2` + `dev-svelte:v2`) copied registry-to-registry from `local-registry:5000` to `ghcr.io/sage-is/sprig-*` via dockerized oras (`oras cp`, gh-token login). Off-machine durability for the whole catalog: the anonymous-Docker-volume single-point-of-failure is now mitigated even before the 11 missing build recipes land. Visibility: **all 14 flipped to PUBLIC** (2026-07-07, per-package web UI — GitHub has NO API for container-package visibility; two flips silently didn't take on the first pass and needed an API-verified retry). Anonymous pulls verified with a credential-less oras client. Any self-hoster can now pull the whole catalog; sha256 pins in the CATALOG remain the integrity guarantee. Registry-host cutover (env-driven, `insecure` gating) remains the separate #critical item below — until it lands, deployed images still pull from `local-registry:5000` only. #bonsai
- [x] **Publish pipeline + public sprig catalog page** (2026-07-07): **(a) `make sprig_publish`** (`scripts/publish-sprigs.sh`) — pushes every local tag to `ghcr.io/sage-is` idempotently, then GATES on visibility: fails with per-package fix URLs when anything is non-public (GitHub has no visibility API; the gate makes silently-internal packages impossible — three of the 14 manual flips silently failed on the first pass, which is exactly the failure mode this closes). Run it after any `build-sprig-*.sh`. One-time org check [MANUALLY]: allow public package creation at github.com/organizations/sage-is/settings/packages. **(b) `sage.is/sprigs/`** — canonical public catalog page in WEB-Sage.is (`src/sprigs.njk` + `src/_data/sprigs.yaml`, books.njk card-grid pattern, startr.style mobile-first): 14 sprigs in 4 plain-language groups with size/license/tag, `oras pull` commands, GHCR links, and a "how grafting works" section. The YAML's title/description fields deliberately prefigure the B2 catalog-schema enrichment — when that lands, generate this file from the supervisor CATALOG instead of hand-maintaining. Build verified (11ty renders `dist/sprigs/`); deploy = commit+push WEB-Sage.is [MANUALLY]. #bonsai

- [x] **Sprig™ artifact signing shipped (minisign, offline)** (2026-07-08/09; gate `make sprig_signing` **10/10 first run**; uncommitted, user commits): artifacts now carry a minisign signature as a second OCI layer (`application/vnd.sage-is.sprig.minisig`), verified **offline in the Rootstock before extraction**. Verifier `sprigs/minisign.py` is pure in-base (stdlib blake2b + the `cryptography` Ed25519 already shipped — zero new deps), validated against real minisign 0.11 output including content-tamper, trusted-comment-tamper, and wrong-key refusals; wired into `artifact.py` under the same verify-before-cache discipline as the sha256 pin (which remains the allowlist — the signature adds publisher provenance for mirrors and the future marketplace, via the per-entry `pubkey` hook). Policy: a present signature is ALWAYS verified fail-closed; required per-entry (`signed: True`) or globally (`SPRIG_REQUIRE_SIGNED=1`); a cache that predates the requirement re-pulls instead of failing. Sigstore keyless was rejected for v1: Fulcio/Rekor round-trips break air-gapped verify (boot reconcile re-verifies cached artifacts with NO network); anyone can still audit with the stock CLI (`minisign -Vm <tar> -P <pubkey>` — trusted comment binds `repo:tag sha256=…`). Tooling: `make sprig_sign` (`scripts/sign-sprigs.sh`, dockerized oras+minisign, re-signs every local tag in place — tar bytes unchanged so pins hold), SIGN_KEY hooks in all three `build-sprig-*.sh`, `FORCE=1 make sprig_publish` for the changed manifests, committed DEV fixture key (`scripts/dev-keys/`, worthless by design) powering the gate, and `sprig_signing` wired into `gauntlet_full`. **Remaining:** [MANUALLY] generate the production keypair (recipe in `scripts/dev-keys/README.md`, passphrase to the password manager) → `SIGN_KEY=~/sage-keys/sprig.key make sprig_sign` → `FORCE=1 make sprig_publish`; then [WE] pin the `.pub` line as `_DEFAULT_PUBKEY` in `artifact.py` and flip catalog entries to `signed: True`. IMPLEMENTATION.md divergence #1 updated in both spec repos (the divergence is now WHICH scheme, not whether to sign). #bonsai #critical
- [ ] **Bring sprig hosting in-house — replace GitHub's package store as primary** (idea captured 2026-07-06; escalated to NEAR-TERM 2026-07-08: community pushback on GitHub-only hosting, per Alexander — the specs and sage.is/sprigs page now word GHCR as "current publish target, not the permanent home"): GHCR is the current publish target (first artifacts pushed there), but the dependency cuts against the sovereignty story — GitHub rate-limits anonymous pulls, can change package policy, and a Microsoft-hosted registry is an odd anchor for a zero-egress/self-sovereign architecture. Candidates to weigh: **self-hosted `registry:2` or Zot on openco.ca CapRover** (Zot is OCI-artifact-native — built for exactly the oras/sprig.yaml use case — and both fit the existing infra + Caddy TLS pattern); **Forgejo/Gitea packages** (self-hosted, gives a UI + auth story for free); **Cloudflare R2 behind a registry** (cheap egress for big artifacts, matches the existing Cloudflare Pages footprint); Docker Hub (rejected-by-default: pull limits worse than GHCR). Decision criteria: anonymous-pull bandwidth for ~600MB artifacts, uptime someone else pages for vs. sovereignty, and whether the registry host being env-driven (prod-cutover item above) makes this a zero-code swap later — it should, which lowers the stakes: publish to GHCR now, migrate freely later. #bonsai
- [ ] **Sprig artifact packaging — reproducible recipe gap down to ~4 of 17 repos** (surfaced 2026-07-03; most closed 2026-07-13/15): in-repo build scripts now exist for `sprig-embedding-minilm-onnx`, `sprig-reranker-bge-gguf`, `sprig-stt-whisper-base` (the original three), PLUS `sprig-vector-chroma`, `sprig-rag-loaders`, `sprig-export-document`, `sprig-media-ffmpeg`, `sprig-backup-rclone`, `sprig-dev-svelte` (`build-sprig-*.sh`), and the shared `scripts/build-llama-static.sh` (the static llama-server prereq the GGUF sprigs stage). **Still recipe-less (~4):** `sprig-browser-ml`, `sprig-code-pyodide` (extract wasm/js from the frontend build stage — arch-neutral), and the ONNX-export embeddings `sprig-embedding-e5-large-onnx`, `sprig-embedding-bge-onnx` (HF→ONNX export; weights arch-neutral). `sprig-embedding-e5-gguf` has no standalone recipe but is regenerable from `build-llama-static.sh` + the convert/quantize step (rescued at `~/sprig-rescue/convert.sh`). **(b) named registry volume** `sprig-registry-data` SHIPPED 2026-07-12. Remaining: write the ~4 missing recipes so every `binary_sha256` is regenerable/auditable end-to-end. #bonsai #critical

### Sprig B2 — non-technical clarity (audit backlog; data model before UI)

- [ ] **Catalog schema enrichment (prerequisite for a legible UI)**: the CATALOG carries only machine fields, so the admin UI can only show raw keys like `minilm-onnx-inhoused`. Add to each entry: `display_name`, `description` (plain "what this does"), `size_mb`, `restart_required` (bool, replacing the prose `post_graft_note` inference), `tier` (`recommended`|`advanced`|`held`), `license`, and a slot/`replaces` marker for the six mutually-exclusive embedding cultivars. The UI can only be as clear as this data. #bonsai
- [ ] **`/catalog` hygiene**: `GET /catalog` dumps `repo`/`tag`/`insecure`/`binary_sha256` to the browser (`routers/sprigs.py`). Return only presentation fields (security + noise). #bonsai
- [ ] **Sprigs admin UI redesign** (`app/src/lib/components/admin/Sprigs.svelte`): group cards by capability; collapse the six embedding cultivars into one "Embedding" choice with a cultivar picker; disclose consequences BEFORE Graft/Prune (size, restart-required, "replaces X" / "this breaks document search"); hide `pid`/`base_url`; explain the Sprig/Graft/Prune/Wilted metaphor inline (tooltip or docs link); add first-run guidance instead of a wall of 14 cards. #bonsai

- [ ] **Stand up `bonsai.sage.is` spec hub** (2026-06-28; scaffold SHIPPED locally 2026-07-08): New repo `Sage-is/bonsai-docs` at `~/Documents/Projects/GitHub/BONSAI/bonsai-docs/`. 11ty + Cloudflare Pages. CNAME `bonsai.sage.is`. Renders single-page views of the canonical spec content pulled from GitHub at build time. This is the polish target — implementers spend hours here, polish compounds. Remaining: [MANUALLY] create the GitHub repo + push, Cloudflare Pages project + CNAME, then the polish punch-list below. #bonsai
  - [x] Scaffold the 11ty project (2026-07-08: bun + `@11ty/eleventy` 3.x, `wrangler.toml`, builds green — 3 pages in 0.09s)
  - [x] ~~Vendor the sage.is book theme~~ (descoped 2026-07-08: lean own layout + startr.style CDN, matching the sprigs/bonsai pages instead of the heavier book machinery; revisit only if the polish punch-list demands it)
  - [x] Build-time spec fetch (2026-07-08: `tools/fetch-specs.sh` — local sibling checkouts first for offline dev, `git clone --depth 1 --branch $SPEC_REF` fallback for CI; pin `SPEC_REF=v1.0.0` once the specs tag)
  - [x] Render `/sprig-spec/v1/` and `/rootstock-spec/v1/` (2026-07-08: paginated template, GitHub-style anchor slugs so in-page links match the repos, draft-status banner linking each repo's IMPLEMENTATION.md)
  - [x] Catalog-hub home with one card per spec, version, license, read/GitHub CTAs (2026-07-08)
  - [ ] [MANUALLY] Create `sage-is/bonsai-docs`, push `~/Documents/Projects/GitHub/BONSAI/bonsai-docs/`, Cloudflare Pages project (build `bun run build`, output `dist`) + CNAME `bonsai.sage.is`
  - [ ] After hub is live: flip the sage.is/bonsai + sage.is/sprigs spec links from github.com to `bonsai.sage.is/*/v1/`
  - [ ] Configure `$id` URLs in `sprig-spec/v1.md` and `rootstock-spec/v1.md` to reference the canonical `bonsai.sage.is` URL once the site is live

- [x] **Author `sage.is/bonsai/` explainer** (2026-06-28; AUTHORED 2026-07-08, deploy = commit+push WEB-Sage.is [MANUALLY]): Curious-visitor doorway at `WEB-Sage.is/src/bonsai.njk` (single file mirroring the shipped sprigs.njk pattern rather than the originally-sketched `src/bonsai/` dir). What-is-Bonsai in plain prose, What-is-a-Sprig with an inline-SVG graft diagram (rootstock + three fingerprint-checked sprigs + Graft Union label), the AGPL-and-proprietary-Sprigs FAQ (4 Q&As in newcomer language: your-Sprig-your-license, selling proprietary Sprigs, operator obligations, where the derivative-work line is), hand-off CTAs to both specs (GitHub repos until the hub is live — flip to `bonsai.sage.is/*/v1/` after, tracked in the hub item above), SEO title/description tuned. Sprigs page closing paragraph cross-links /bonsai/ + both spec repos. Build verified (dist/bonsai/ renders, cross-links present both directions). 2026-07-08 follow-ups: Graft Union™ SVG label moved off the connector lines (junction dot added), marketplace line added to the sell-a-Sprig FAQ answer. #bonsai

- [ ] **Sprig™ marketplace — simple selling of Sprigs** (captured 2026-07-08, now a PUBLIC commitment: the sage.is/bonsai FAQ says "A Sprig marketplace is on our roadmap to make selling one simple"): support paid and proprietary Sprigs with listing/selling as simple as Etsy made it for makers — Alexander (CTO) was a founding engineer there (employee #5), and that pedigree is named on the page. Interacts with: the in-house registry cutover (paid artifacts need authenticated pulls), catalog schema enrichment (license/tier/price surface), and the spec's `delivery: service-endpoint` shape (hosted paid Sprigs need no artifact download at all). Methodology inspiration (both named by Alexander 2026-07-08): **Etsy** for maker-simple selling, and **Shopify's playbook for getting devs involved** — a partner/developer program, first-class SDKs and docs (the MIT `sage-is-sprig-sdk-py` sketched in the Sprig Spec is the seed), revenue share that favors the builder, and the marketplace itself as the distribution channel that makes writing a Sprig worth a developer's weekend. Scope TBD: payments, publisher identity/verification, revenue split, and how a purchased Sprig lands in an operator's catalog. #bonsai #marketplace
  - [ ] **Architecture approved 2026-07-19 (roadmap-only, no code yet)** — full design in `~/.claude/plans/the-arch-guard-trusts-effervescent-moonbeam.md` (Track B) + memory `project_sprig_marketplace.md`. **Spine = catalog-as-data:** the one hard blocker is that `SprigSupervisor.CATALOG` is a hardcoded Python dict (`supervisor.py` ~222-625) — extract the `_sprig()` entry schema to a validated model and merge entries from three sources at runtime, ALL feeding the _unchanged_ graft pipeline (allowlist → arch guard → pull → sha256 → minisign → extract → spawn). The marketplace is a new _source_ of catalog entries, not a new trust model. **Three lanes = a trust ladder, not a trust hole:** (S1) first-party curated signed index (Sage.is key, the storefront); (S2) curated community, publisher-signed via the existing per-entry `pubkey`; (S3) admin self-load — any OCI ref + optional sha/pubkey added at runtime, persisted to the volume, graftable with NO image rebuild. S3 is the fully-open escape hatch AND the fast sprig-dev inner loop (collapses edit-supervisor.py→rebuild→smoke into point-at-local-registry→load→graft→iterate) AND the community on-ramp; `SPRIG_REQUIRE_SIGNED=1` ratchets an instance to signed-only. **Phases:** M1 catalog-as-data + admin self-load (keystone; recommended first slice — ships S3 + dev loop before any storefront; also redact `repo/tag/binary_sha256/insecure` from the browser catalog, the redaction TODO); M2 remote curated storefront + in-house registry cutover (Zot); M3 discovery/browse UX; M4 community submission lane; M5 commerce — paid/proprietary sprigs + **checkout** (Stripe-style; issues a signed entitlement enforced two ways: gated authenticated pull for `oci-artifact`, or bearer-token to a publisher-hosted `service-endpoint`); schema adds tier/price/publisher_id/purchase_url. Open decisions: storefront/registry name, M1 index shape, self-load sha-pin default + unsigned UI marking, Zot vs GHCR-proxy, entitlement binding (per-instance vs per-account). #bonsai #marketplace

- [ ] **Incoming: `startr-team` agent framework as a `service-endpoint` Sprig** (midterm; awareness notice from Scion 2026-07-11, no action requested): the Startr-brand agent framework grafts onto AI-UI as a REMOTE Sprig (managed HTTPS endpoint), never as a source dependency — brand boundary is Sage-is = science+platform, Startr = tooling+product, and the arms-length Graft Union™ settles licensing per the spec's own License-compatibility section. **Done now (the cheap moment, specs still draft/unpushed):** `agent-` capability prefix RESERVED in sprig-spec v1.md with a planned `sage-is/v1/agent` extension dispatch shape; CHANGELOG [Unreleased] entry added. **Midterm work on our side when the Sprig actually lands (comes with its own scoped task):** (a) define the `sage-is/v1/agent` contract — run lifecycle, streamed events, cancellation; schema at `sprig-spec/schemas/sage-is/v1/agent.json`; (b) explicit rootstock dispatch wiring for the extension shape (the "no per-capability dispatch code" guarantee covers only OpenAI-compatible shapes); (c) `delivery: service-endpoint` support is a prerequisite — currently unimplemented (IMPLEMENTATION.md divergence rows). Note: Scion's pointer paths were inferred and stale (specs live in the BONSAI sibling repos, not docs/bonsai/; graft API is `routers/sprigs.py`, not retrieval.py; pins live in the supervisor.py CATALOG, not distribution.env). **DECISIONS locked 2026-07-11 (Alexander, four-question round; these are the EXTENDED tier — the simple agents already exist as workspace Agents/model presets + Space agents in `spaces.py` `data.agents`):** (1) **bidirectional from day one** — the `sage-is/v1/agent` contract includes a rootstock callback surface (agent invokes rootstock tools/knowledge/models, authenticated per run) so agents work with the operator's data instead of shipping copies; (2) **both deliveries by design** — `service-endpoint` for hosted, `oci-artifact` for on-hardware runs, keeping zero-egress intact for private deployments; (3) **one tiered "Agents" surface** — no renames; extended agents appear alongside simple ones with a tier badge, and the model-transparency claim must extend to the remote tier; (4) **job queue + spend budgets are PREREQUISITES** — sequence both backlog items into the midterm agent work (runs live on the queue, budgets gate spend before a runaway team burns a key). Spec reservation + CHANGELOG amended same day to carry (1) and (2). #bonsai #agents

- [x] **Theme Sprigs™ SHIPPED — mechanism (1) of the UI-extension ladder** (Alexander's "make it so" 2026-07-11; smoke **66/66 first run**, was 57; uncommitted, user commits): a Sprig can now theme the running interface with design tokens only. **Catalog is 17 entries / 12 capabilities** (+`theme-workshop-bio` green, +`theme-workshop-math` blue — the workshop presets the Spaces-theming backlog wanted, 846-byte artifacts, the first Sprigs with FULL in-repo source: `scripts/themes/` + `scripts/build-sprig-theme.sh` with a build-time self-containment gate). Mechanics: capability `theme`, `server: deliver` + `seed: model-dir` composes unchanged (volume-resident, restart/upgrade durable via existing machinery); graft-time validation fail-closed in `sprigs/theme_dispatch.py` (strips comments, then refuses `@import`/external `url()`/script-shaped content — CSS can't execute but CAN beacon, so external refs break zero-egress — plus a 512KB cap); activation = one PersistentConfig pointer (`SPRIG_ACTIVE_THEME`, `ui.sprig_active_theme`); unauthenticated `GET /themes/active.css` in main.py serves the active sheet (styles the login page too; empty sheet when none); `app.html` loads it on every page; last-grafted-wins, prune of the active theme resets (`theme_reset` flag + admin toast + i18n key). The token hook: the interface's Tailwind gray scale reads `var(--color-gray-N)` with the variables never declared, so a `:root` block wins without `!important` (oled-dark's four inline gray overrides still beat stylesheets by design). Spec: the `theme-` reservation graduated to a **defined v1 contract** (Theme Sprigs™ section in sprig-spec v1.md, written FROM the shipped implementation — 4 Sprig MUSTs + 4 rootstock MUSTs), CHANGELOG updated, both IMPLEMENTATION.md files record the match, hub renders `#theme-sprigs`. **Remaining on the ladder:** (2) declarative extensions (manifest of menu items/actions/iframe panels — the marketplace default, Slack/Shopify-shaped) and (3) signed slot-mounted web components (hold until prod signing + publisher identity mature); `ui-` prefix stays reserved. [MANUALLY] after the prod signing pass: FORCE-publish the two theme artifacts to GHCR, flip visibility, add their cards to sage.is `sprigs.yaml`. #bonsai #ui #marketplace

- [ ] **Author the bonsai/sprigs pages as markdown + a text-graph→SVG diagram pipeline** (captured 2026-07-08): both pages are hand-written njk today; re-author them as markdown so content edits stop requiring template surgery. Diagrams from text markup rendered to SVG at build time — mermaid is the baseline candidate, or a custom "simple text graph" markup (TBD, mermaid-style) whose renderer emits house-styled SVG (startr.style tokens, correct fonts, label collision avoidance — the Graft Union™ label landing on a connector line is exactly the class of bug a renderer should prevent). Candidate consumers beyond these two pages: the bonsai.sage.is spec hub and future architecture docs. #bonsai #site

- [ ] **Reserve `spec.sage.is` DNS** (2026-06-28): Set up the subdomain now without a site behind it. Reason: if Sage.is ever publishes a non-Bonsai spec, that's the canonical URL home. Avoids painting into a corner where every Sage.is spec inherits the Bonsai metaphor in its URL. Per Daniel Stenberg's guardrail in the panel review. #bonsai #dns
  - [ ] Add `spec.sage.is` CNAME record (parked, no content)
  - [ ] Document in `docs/` why it's reserved so it doesn't get repurposed casually

- [x] **Confirm Bonsai™ metaphor horizon before `bonsai.sage.is` ships** (2026-06-28; DECIDED 2026-07-08): Rich Harris's strategic question answered by Alexander — **Bonsai™ is sticking as the 10-year name**, so `bonsai.sage.is` ships as the canonical spec URL and the hub scaffold proceeds against it. The `spec.sage.is` reservation above stays as the escape hatch per Daniel Stenberg's guardrail (parked DNS, no content). #bonsai #strategic-decision
  - [x] Founders' decision: is Bonsai™ the long-horizon name? — YES (Alexander, 2026-07-08)
  - [x] `bonsai.sage.is` ships as canonical (hub scaffold built the same day)
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

- [ ] **Audio/TTS UX polish** (surfaced live in dev mode 2026-07-26; the last two ride with the Settings/Admin migration pass):
  - [x] First-playback Kokoro load was silent for seconds → now a dismissible "Loading the Kokoro voice model (first use)…" toast (`ResponseMessage.svelte`)
  - [x] Kokoro double-load in Settings (doubling progress %) → memoized load promise so `getVoices()` + the reactive share one download (`Settings/Audio.svelte`)
  - [ ] Opening Settings → Audio RELOADS Kokoro even after playback already loaded it — the Settings main-thread loader and the playback Web Worker (`kokoro.worker.ts`) are separate contexts; share one loader/model so the model loads once per session
  - [ ] Kokoro voice selector is janky (a type-in input + a list that only opens after you clear the field) → replace with a clean, DRY `<select>`/combobox

### Frontend — no-build strangler migration (approved 2026-07-25)

> Approved plan: move the AI-UI frontend off the SvelteKit build to
> server-rendered HTML + vanilla/htmx islands, Svelte-as-biomes, strangler to
> zero. Three evidenced legs — delete duplicated code (~50%), cut the
> conversation load (172 req / 7.9 MB / ~19 s → near-instant), turn shared chats
> into a crawlable distribution surface. Full plan:
> `~/.claude/plans/we-got-to-gtm-stateful-teapot.md`.

- [ ] **Phase Q0 — board hygiene**: TODO.md on TodoScope convention, this plan's tracked TODOs filed, board kept current every phase. #critical
  - [x] Verify TODO.md structure + `.todoscope-exclude.csv` (both already on-convention)
  - [x] File the migration epic + tracked TODOs into TODO.md
  - [ ] Keep the board mirroring reality as each phase's steps land and ship

- [ ] **Phase Q — clear the decks**: current-SPA drift fixes, cruft, and perf quick-wins (no migration needed).
  - [x] Enforce the 8-char password server-side (`auths.py`) — measure-twice e2e verified (200→bug, 400→fixed); committed
  - [x] Fix `UserUpdateForm` / `SpaceForm` TS↔Pydantic drift — committed
  - [x] Delete the dead `SUPPORTED_FILE_EXTENSIONS` copy in `constants.ts` (backend 50-entry list is live) — committed
  - [ ] Reconcile the drifted permission-tree defaults
  - [ ] Cruft sweep: dead exports, unused deps (`chart.js`, `@mediapipe`), stale flags
  - [ ] Strip hyperscript attribute forms (`_`, `script`, `data-script`) in the user-content sanitizer; verify DOMPurify config
  - [x] Perf: `Cache-Control: immutable` on `_app/immutable/*` — measure-twice e2e verified (empty header→immutable); committed
  - [x] Perf: eager ML libs off the conversation chunk (nodes/2) — MEASURED: the 22 MB WASM was already lazy (feature-gated, NOT on the load path; the audit inferred wrong). Real win: deleted dead `@huggingface/transformers` import + made kokoro-js dynamic in `chat/Settings/Audio.svelte`. Fresh-build verified: nodes/2 2.70→0.65 MB, app load 5.39→4.12 MB transfer (−24%), 13.4→10.6 MB decoded; auth+cache guard-rails green. Ready to commit.
  - [x] Perf: `/icons/` waste — RESOLVED as already-gated. Image ships 0 `.xcf` (`.dockerignore **/*.xcf`) and 1.3 MB icons total; the audit read the stale host build. The 6 identical 170 KB PNGs are placeholder art meant to diverge (favicon/logo/splash + dark variants) → branding-art task, not perf.
  - [x] Perf/arch: lazy-load markdown-render libs (katex/mermaid/highlight/codemirror) — SHIPPED as architecture hardening, MEASURED as perf-neutral. Four changes landed: (A) deleted the DEAD `import katex` in `utils/marked/katex-extension.ts` (tokenizer never used it; real render is `KatexRenderer.svelte`, untouched → tex still renders); (B) `hljs` now dynamic-imported inside `copyToClipboard` (copy-only, off every page's utils chunk); (C+D) `CodeBlock` + `KatexRenderer` load via memoized `{#await import()}` loaders (`Markdown/lazy.ts`) only when a code/math token renders — streaming-safe (one promise identity, no re-pending flash). MEASURE-TWICE FINDING: the hoped-for "plain convo sheds ~10 MB" is NOT real — mermaid/codemirror/katex were ALREADY lazy (Vite component chunking); a plain convo never pulled them, before or after (measured: release-3.0.0 vs develop, identical 13.41→10.27 delta = the nodes/2 win alone; no separate mermaid/codemirror chunk fetched in EITHER build). So this change's value is real but not bytes: dead-code removal, hljs deferral, and EXPLICIT/structural laziness aligned with the plan's islands principle (robust vs a future refactor making them eager). Guard-rail `markdown-render-lazy.cy.ts` GREEN before AND after (seeds a chat, asserts `.katex` + `.copy-code-button` + `pre.mermaid` render; plain-text control asserts none) — proves the refactor broke no rendering. #perf #frontend
  - [ ] Perf: batch the serial boot waterfall into `Promise.all`; put HTTP/2 in front
  - [ ] Guard-rail Cypress spec for every area before it's touched
  - [ ] Modernize (or prune) the inherited upstream e2e specs — `registration/settings/chat/documents.cy.ts` now COMPILE (import depth `../support`→`../../support` fixed) but FAIL on stale open-webui UI: they assume OPEN signup (this fork hard-closes it after the first admin, so the "Sign up" toggle is hidden) and the old changelog dismiss `Okay, Let's Go!` (now the setup wizard's "Get Started"/Close, handled via API). Rewrite to the fork's actual flows or drop tests of removed behavior. Note: they're in a subdir so NOT in the default `make e2e` gate. #e2e #tech-debt

- [ ] **Phase S — streaming spike** (go/no-go on strangler-to-zero): vanilla fetch-stream island in an htmx shell over HTTP/2 (autoscroll, stop, streamed markdown); optional Datastar control build; one-page decision memo. Throwaway in `tools/spikes/`. [MANUALLY — Alexander calls it]
  - [ ] Spike-prove the shared-runtime assumption — biomes share ONE Svelte runtime, not one each #critical

- [ ] **Phase 0 — seam + Sprigs pilot**: explicit island mount in `main.py`; rebuild `Sprigs.svelte` as a no-build page on the existing JSON endpoints, zero Vite; its Cypress spec passes against old panel and new page.

- [ ] **Phase 1 — ui-Sprig contract** (marketplace can't launch without it): `validate_ui_bundle` (fragments only), graft branch mirroring `theme`, cookie auth bridge, per-Sprig scripting grant (default off).
  - [ ] Write "no framework sprigs" into the ui-Sprig spec — fragments + host runtime only; validator refuses bring-your-own-framework #sprigs #ui

- [ ] **Phases 2–4 — surfaces inward, then biomes**: ripe surfaces (theme/branding, wizard, diagnostics) → medium surfaces + shell flip (users, evals, settings tabs, chat list, workshop) → prune biomes (Functions, then chat core last, gated on the spike memo).
  - [ ] Count and pin the core biomes as a downward-only ratchet — chat core, rich-text editor, code editor, flow canvas, channels; the count only decreases #biomes #ratchet
  - [ ] Reimplement the flow canvas (`@xyflow/svelte`) framework-free
  - [ ] Slogan precision: "org-owned" not "user-owned"; keep yjs local-first for the editor #brand

### Founder Bio & Provenance

- [ ] **Etsy / islands provenance — firm up the sources**: make the "employee #4 / built the Etsy Mini / called them islands" bio citable. Public today: #4 (Fred Wilson/USV 2006, via zh.wikipedia); the Etsy Mini is a documented island-shaped widget. Detail in the `reference_etsy_islands_provenance` memory + the plan's provenance appendix. #brand #provenance
  - [ ] Retrieve the archived Fred Wilson / USV 2006 post from archive.org (the usv.com URL now 404s) — locks the #4 primary source
  - [ ] (Alexander) Confirm true hire order — recollection is possibly earlier than #4 (Stinchcomb joined later; came on ~after Forman, ~with Nuzzolillo)
  - [ ] Find receipts for Etsy Mini authorship (publicly credited to Etsy collectively)
  - [ ] Find evidence of internal "islands" vocabulary predating the 2019 public coinage

---

## Backlog

_Items deferred to a later planning cycle. Move here from TODO when deprioritized._

- [ ] **One-click GUI installer for non-CLI users + code signing** (captured 2026-07-17): a double-click installer for Sage.is AI-UI (+ its Rootstock™/Sprig™ runtime) for people who won't touch a terminal — not just the `ai-ui` brew CLI. Load-bearing prerequisite: **software signing**, or the flow dies at the OS "unidentified developer / can't be opened" warning (exactly the audience that bails). macOS: Apple Developer ID + **notarization** (+ stapling) of the `.app`/`.dmg`/`.pkg`. Windows: **Authenticode** (ideally EV) to clear SmartScreen. Relates to the `ai-ui` brew formula + Developer-Mode onboarding; prior art to mine is Osmantic ODS (item below). #onboarding

- [ ] **Review Osmantic ODS for onboarding ideas** (captured 2026-07-17): [github.com/Osmantic/ODS](https://github.com/Osmantic/ODS) — "Osmantic Deployment System." NOT just a wizard: a full local-AI-server orchestrator that bundles **Open WebUI** (same lineage as us) + llama-server + LiteLLM + n8n + Whisper + Kokoro + Qdrant + SearXNG + ComfyUI as Docker containers. Adjacent competitor; onboarding is their strength. Mine: single-command zero-prereq installers (bash + PowerShell) with GPU auto-detect → model selection; a **bootstrap "first chat in <2 min"** mode (vs. our wizard's up-front model downloads); a management dashboard; and **plug-and-play service folders** that rhyme with Sprigs™. Our edge stays the slim Rootstock™ + zero-egress Sprig™ runtime + marketplace. Feeds the one-click-installer item above. #onboarding

- [ ] **Configurable sprigs + sidecar-sprig variant** (captured 2026-07-18): sprigs should carry SETTINGS (per-entry schema — e.g. a service `url`), and there should be a **sidecar sprig** kind that points at an operator-run external service instead of shipping an artifact. Concrete driver: the Docling *standard* sprig is ~5GB (docling-serve hard-pulls `docling-jobkit[ray,rq,vlm]` → ray/codeflare/kubernetes); a sidecar variant (operator runs docling-serve, the sprig just sets `DOCLING_SERVER_URL` from a settings field) is the pragmatic path. Offer BOTH standard (in-container, zero-egress) + sidecar for tika/docling. This is the spec's currently-unimplemented `delivery: service-endpoint` shape. Work: (a) per-sprig settings schema + Admin UI field + persistence + dispatch read; (b) service-endpoint/sidecar delivery that skips the pull and points capability config at the URL (sidecar "graft" = "save URL"); (c) standard + sidecar catalog entries. #bonsai

- [ ] **Tighten the Vite build — it eats ~half the image build** (captured 2026-07-15 during the 3.0.0 release): full image build measured 3m37s with the Vite frontend stage taking roughly half. The cost doubles in `release_smoke` (native + amd64 builds) and the amd64 side pays QEMU tax on top. Levers, roughly in order of payoff: (1) the frontend build output is arch-neutral JS/CSS/wasm — build it ONCE and COPY the same `build/` into both arch images instead of re-running Vite under emulation; (2) buildx cache mounts for `node_modules` + `.svelte-kit` + Vite's cache dir so unchanged frontends skip the work; (3) Dockerfile layer ordering so backend-only changes never bust the frontend layer. Sourcemaps are already off in production builds (6c393d9). #perf **NOTE:** vite specific solutions may exist or svelte upgrades

- [ ] **Job queue for long-running processes** (idea captured 2026-07-06): knowledge-base population/reindex, image generation, model downloads, bulk transcription, and big uploads all run today as synchronous requests or fire-and-forget threads with ad-hoc status (`MODEL_DOWNLOAD_STATUS` dict, per-request `ThreadPoolExecutor` in audio.py) — no unified queue, no retry, no concurrency caps, no user-visible progress once the request returns. Sketch: a job table (id/type/owner/state/progress/error) + a bounded worker pool + one status endpoint (poll or SSE) + a small "running jobs" surface in both admin diagnostics and the requesting user's UI. Prior art in-repo to fold in: the download-watchdog TODO (stalled-download detection) and the upload/download UX memories (progress bars, time estimates). Design question to settle first: DB-backed queue in-process (single-container fit, Bonsai™-friendly) vs. redis-backed (already a dep) — lean DB-backed until multi-worker is real.
- [ ] **Spend/usage budgets per user AND per API key** (idea captured 2026-07-06): users can generate API keys and hand them to developers or embed them in apps — today a shared key spends indistinguishably from its owner, with no caps. Two ledgers needed: per-user and per-key (a key is the accounting unit when shared), tracking request counts + token usage + upstream cost estimates per model/connection. Then budget enforcement: soft cap (warn banner / email) and hard cap (429 with a clear "budget exhausted" body), admin-settable defaults + per-user overrides, monthly reset or rolling window. Admin UI: usage table sortable by user/key/model; user UI: own usage + remaining budget, per-key breakdown so a leaked/greedy shared key is visible and revocable. Load-bearing for workshops (cost containment on shared instances) and for the try.sage trial (hidden Groq connection is currently uncapped per user). Ties into Spaces multi-tenancy — a Space-level budget is the natural third ledger later.

- [ ] **`e2e_watch` transport: replace noVNC with the WebRTC alternative** #tests: `make e2e_watch` serves the interactive Cypress GUI via Xvfb → x11vnc → noVNC (`scripts/e2e/watch/`). Swap the VNC hop for a WebRTC stream (lower latency, no websockify middleman, plays nicer through tunnels). Same wrapper-image shape; only the transport layers in `scripts/e2e/watch/Dockerfile` + `entrypoint.sh` change. Decided 2026-07-02 with the P0/P1 Cypress revival.
- [ ] **`sprig-test-cypress` self-test graft prototype gate** #tests #bonsai: one-shot `transport: none` dev-family Sprig™ that runs the e2e suites against its own rootstock loopback and reports into Admin → Diagnostics ("Self-test: N/N ✅"). Prototype gate first: Electron/Chromium headless closure on the Wolfi base (X11/GTK libs, ~500MB–1GB artifact, per-arch). Kills the Cypress-binary CDN pull (north star). Greenlight pending after 8.I.4/8.I.5.

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
  - [ ] Publish the Custom Sage tutorial content package: three short videos plus a follow-up email with system prompts.
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

- [ ] **Wizard `whisper` status stuck at `pending` after a whisper Sprig™ graft (cosmetic — STT works)**: On the slim rootstock, grafting `whisper-base-ggml` serves STT correctly (`/api/v1/audio/transcriptions` → 200 through the sprig), but `GET /api/v1/retrieval/models/status` keeps `models.whisper != "ready"`. `point_stt_at` ([sprigs/stt_dispatch.py:40](app/backend/sage_is_ai/sprigs/stt_dispatch.py#L40)) flips it "ready" and IS called by the graft route ([routers/sprigs.py:113](app/backend/sage_is_ai/routers/sprigs.py#L113)); single worker (`UVICORN_WORKERS=1`), the status dict is seeded with a `whisper` key ([main.py:1119](app/backend/sage_is_ai/main.py#L1119)), and the endpoint returns that dict raw ([retrieval.py:439](app/backend/sage_is_ai/routers/retrieval.py#L439)) — so static analysis says it SHOULD read ready. Needs LIVE inspection: `KEEP=1 make sprig_smoke`, then `curl …/models/status` right after the whisper graft, plus a temp log in `point_stt_at`. Surfaced 2026-07-22 by `sprig_smoke` (which now self-heals auth + dumps the real status object on failure). Low severity — this is the wizard's HF-download-skippable optimization, not the STT capability itself. #bug
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

- [x] **try.sage Production Decisions**: (Alexander Somma + Izzy Plante) — Surfaced by Docker exploration. Block CapRover one-click rollout.
  - [x] Decide where `TRY_SAGE_LLM_API_KEY` lives in production: plain env, Docker secret mount, or external vault. Recommend Docker secret for try.sage.is itself, plain env for self-hosted workshops.
    - [x] note:As we use cap rover and the system injects env vars we're leaning this way


- [x] **Cypress E2E revival — docker-only headless + interactive-watch infra, three new specs** (2026-07-02 to 2026-07-03): Pinned `cypress/included:15.18.0` (not the 13.x devDep major — Cypress 13 bundles a Chromium whose `ReadableStream` isn't async-iterable and the app's streaming path throws on it). `scripts/e2e/run-cypress.sh` runs the suite headless against a fresh rootstock + Caddy TLS sidecar, no npm/cypress on the host. `scripts/e2e/run-cypress-watch.sh` + `scripts/e2e/watch/` adds an interactive GUI variant: Xvfb + x11vnc + noVNC served at `localhost:6080/vnc.html`, Sage-branded (logo, favicons, Archivo type via a subsetted font — see the font-subsetting TODO above). New specs: `degradation.cy.ts`, `sprigs-panel.cy.ts`, `users.cy.ts`; `registration.cy.ts` moved to `cypress/e2e/upstream/`. Headless run verified green: 10/10 specs passed. Decided 2026-07-02 alongside the noVNC-transport backlog item below (WebRTC swap still pending). #tests

> Archived 2026-07-03: the 8 bug-fix/feature entries that had accumulated here (try.sage env-gating bugs, homebrew tap, try.sage Phase A/B, four regression bugs, TodoScope alignment) moved to `docs/completed-todos.md`.
