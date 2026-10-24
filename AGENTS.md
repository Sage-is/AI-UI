# AGENTS.md

## What this is

Sage.is AI-UI is a self-hosted AI workspace, a fork cut from MIT-era Open WebUI. Start with [README.md](README.md), then [docs/orientation.md](docs/orientation.md), the map.

## Dev loop

- `make review_live` serves no-build pages. `make dev_run` runs Svelte with HMR. `make it_build` bakes the image, so use it only for gates.
- Docker runs on Colima by default.
- App dependencies build only in Docker. Never run bare `pip` or `npm` on the host.
- Plan first: add the task to `TODO.md` before any work. Follow SOLID, YAGNI, KISS and DRY. See [docs/development-workflow.md](docs/development-workflow.md).

## Key docs

- [docs/orientation.md](docs/orientation.md): the map, settled conventions, gates.
- [docs/no-build-surface-convention.md](docs/no-build-surface-convention.md): how a page moves to plain HTML.
- [docs/development-workflow.md](docs/development-workflow.md): styling, testing and the Cypress e2e harness (`make e2e`, `make e2e_both`).
- [docs/release-runbook.md](docs/release-runbook.md): cutting a release.
- [docs/federation.md](docs/federation.md): boxes, the privacy filter, the raw proxy routes.
- [docs/file-handling-field-rules.md](docs/file-handling-field-rules.md): rules for delegated edits.

## Hard rules

- **Git writes are Alexander's.** Agents prepare changes. He commits.
- **Clients go by codename.** Real details stay in an untracked `.clients.md`.
- **Privacy filter.** It is on by default for external connections. Send model calls through `/api/chat/completions`. The raw `/openai` and `/ollama` routes skip the filter.
- **Licence.** The fork is cut from MIT-era Open WebUI and ships AGPL-3.0 (see `LICENSE`). It never merges upstream Open WebUI.
- **Hardlinked files** (Makefile, `*.env`, shared scripts): run `stat -f "%l" <file>` first. Above 1, edit with `sed '…' file > tmp && cat tmp > file`. Never use Edit, Write or `sed -i`: on macOS they replace the inode. Re-check the count afterwards.
- **Hidden artifacts.** Dotfiles are denied by default. Commit one only if `.gitignore` allowlists it, nested ones included. Sanitized `.example` files pass the `!.*.example` rule. Editor state, automation state and secret-bearing files stay out.
- **FastAPI env-gated routes.** Put the env gate before the auth dependency in the handler's parameters, so a disabled feature returns 404, not 403. See `routers/sage_runtime.py`.

## Design

- AI-UI is moving to a no-build strangler: plain HTML pages and htmx islands. Svelte stays only as biomes until it reaches zero.
- Convert Tailwind markup with `tools/tw2startr`.
- Each Space gets creator-led theming.
- Pages load the rolling `https://startr.style/style.css` today (`app/src/app.html` and `app/backend/sage_is_ai/pages/`).
- The one-brand design rules for Trellis, AI-UI and Tinker.Click live in the Trellis repo (private), `crm/docs/design-drafts/AGENTS.md`.

## Shared rules

The same block sits in every Sage.is and Startr repo's AGENTS.md; change it everywhere or nowhere.

- **Git.** Agents commit and push only when the person they work for says so in that session. Commits are authored as that person and carry an AI co-author trailer. Subjects read `type(scope): subject` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
- **Design.** startr.style inline props in `style` attributes, never classes. Write the base (phone) value first; add an `-sm`/`-md`/`-lg`/`-xl` tier only where the layout changes, and never repeat the base value in a tier. New pages ship plain HTML first; never a third visual language. The kit's manual is [design-ingest.md](https://github.com/Startr/WEB-startr.style.core/blob/master/docs/design-ingest.md).
- **Browser checks are scripts.** `bun run probe:hover`, `probe:tap` and `probe:diff` run from a WEB-startr.style.core checkout and take seconds; they replace long agent sessions clicking through pages.
- **Board.** `TODO.md` sections are the kanban columns. Each card is one short claim line (under about 350 characters) with a sub-checklist; narration goes to `board-dossiers.md` in the docs folder. `KANBAN.canvas` is generated from `TODO.md`; never hand-edit it.
- **Names.** Tracked files name work paths, not people; only Alexander is named. Clients go by codename.
- **Secrets.** In the environment or the team vault; never in chat, a command line or a tracked file.
