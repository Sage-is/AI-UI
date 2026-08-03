# try.sage.is screen inventory — live readings, 2026-08-03

Resolves the **Screen inventory** card on [charts/friday-demo/TODO.md](../../charts/friday-demo/TODO.md).

Method: signed in to https://try.sage.is as the `admin` persona through the try-mode magic link, then read the API directly with `curl --compressed`. Single run per endpoint from one machine on a residential connection, so byte counts are firm and times are indicative. The magic token is not recorded here or anywhere in the tree.

**Headline: three of the chart's assumptions were wrong, and two of them were wrong in the direction that costs us Friday.**

---

## 1. The instance runs v3.0.0, cut 2026-07-16, and is 71 commits behind develop

`/api/config` reports `version 3.0.0`. `git log -1 v3.0.0` dates that tag 2026-07-16.
`git rev-list --count v3.0.0..develop` is **71**.

`git show v3.0.0:app/backend/sage_is_ai/main.py` contains no `pages_router`, no
`include_router(pages_router, prefix="/pages")`, and no `render_try_sage`. Confirmed against the running instance: `/pages/admin/sprigs`, `/pages/admin/diagnostics` and
`/pages/workshop/agents` all return the 6,532-byte SvelteKit shell with nine
`_app/immutable` references — the same document `/definitely-not-a-route-zzz` returns. The SPA catch-all answers 200 for any unknown path, so a missing route looks like a working one.

**No server-rendered surface is live on try.sage.is.** Not the Sprigs panel, not diagnostics, not the Agents page, and not the try.sage welcome page. The 52 files and ~7,000 lines of `sage_is_ai/pages/` are all on develop and unreleased.

Two consequences the chart had backwards:

- **Reviewer T's mobile cutoff is live.** The board records it as "fixed by migrating the surface", and the migration is real, but it sits on develop. The anonymous landing on try.sage.is is still the Svelte `TrySageWelcome`. There is a phone in the room Friday.
- **The −934 kB font-and-icon cut is not deployed.** The shell still carries   `<link rel="icon" type="image/svg+xml" href="/static/icons/favicon.svg" />`, and that file measures **198.2 kB decoded / 149.6 kB wire** on the live instance — the two byte-identical 2036×2040 PNGs base64-wrapped in an SVG that the board already diagnosed. `apple-touch-icon.png` is another 32.4 kB.

## 2. Four of the five agents return "Model not found"

`/api/v1/models/` lists five agents. `/api/models` lists six rows: those five plus exactly
one base model, `openai/gpt-oss-120b`.

| Agent | Base model | `POST /api/chat/completions` |
|---|---|---|
| Sage Strawberry | `openai/gpt-oss-120b` | **200**, streams, TTFT 1.15 s |
| Sage Startr.Style | `qwen/qwen3-32b` | **400** `404: Model not found` |
| AstroPi AI Tutor | `meta-llama/llama-4-scout-17b-16e-instruct` | **400** `404: Model not found` |
| _(agent named after a person)_ | `qwen/qwen3-32b` | **400** `Model not found` |
| No Worky | `meta-llama/llama-4-scout-17b-16e-instruct` | **400** `Model not found` |

The connection serves one model. Four agents point at two models it does not serve. On a product tour, four of the five things a visitor can click fail with an error toast.

`DEFAULT_MODEL_SELECTOR_FILTER` is `agents`, so the selector shows agents rather than base models — which is to say it shows the four broken ones.

Latency on the one that works: **TTFT 1.62 s** direct to `openai/gpt-oss-120b`, **1.15 s** through Sage Strawberry, 16 SSE frames each, max_tokens 16.

## 3. The School B residue is smaller and emptier than the chart assumed

Full contents, admin view:

- **Agents (5)** — Sage Strawberry, Sage Startr.Style, AstroPi AI Tutor, one named after a
  person, No Worky. No base64 avatars anywhere; every `profile_image_url` is the URL
  `/static/icons/favicon.png`.
- **Knowledge bases (5)** — "Housing in Ottawa" (_outlined Ottawa housing laws_),
  "American Revolution", "Guess who", plus the two `try_sage_kb_*` built-ins.
  **The first three hold zero files.** Only the built-ins have content, one markdown file
  each, 15.1 kB stored in total across the whole instance.
- **Prompts: 0. Functions: 0. Chats: 0. Magic links: 0. Banners: 0.**
- **Spaces (1)** — `the-steam-room`. **Notes (1)** — titled `2026-05-01`. **Tools (1)** —
  `searxng-markdown-server`. **Groups (2)** — Facilitators, Workshop.
- **Users (5)** — Admin, Facilitator, User 1, User 2, User 3. Every address is
  `@try.sage.is`. **No real accounts, no personal data, nothing to export.**

So the residue is three empty knowledge bases with school-flavoured names, two or three
stale agents, one Space and one note. "Ask them first" loses most of its force: there is
no data of theirs to take. The cleanup is deletion, and it is cheap.

## 4. `/api/models` is 11.9 kB here, not 2,304 kB

Measured live, decoded, with `--compressed`:

| Endpoint | wire | decoded |
|---|---|---|
| `/api/models` | 4.3 kB | **11.9 kB** |
| `/api/v1/models/` | 3.9 kB | 10.5 kB |
| `/api/v1/files/` | 6.6 kB | 16.2 kB |
| `/api/v1/knowledge/` | 0.7 kB | 2.7 kB |
| `/api/v1/users/?page=1` | 0.5 kB | 1.7 kB |
| `/api/config` | 0.2 kB | 0.4 kB |
| prompts, functions, chats, magic-links | 0.0 kB | 0.0 kB |

The board's 2,304 kB came from the restored **production snapshot** — 324 model rows, 51
agents, base64 avatars. try.sage.is has five agents and no inline avatars, so the payload
defect the chart treats as demo-blocking **does not exist on this instance**. It returns
the moment real content is seeded with avatars uploaded through `ModelEditor.svelte`, which is the path any real-estate seeding would take.

## 5. What could not be measured with curl

The signed-in shell references 11 assets totalling **226.5 kB wire / 330.6 kB decoded**, of which favicon.svg is 198.2 kB. That is a **lower bound and not the page cost**: SvelteKit loads route chunks by dynamic import, and those appear in no `href` or `src` in the HTML. No `@font-face` URL is reachable from the shell's CSS either. A real figure for the demo path needs a browser. The board's own numbers came from Cypress against a snapshot in a container, not from this instance.

## 6. Noted, by design, and it bears on the tenancy question

`GET /api/v1/sage/runtime/personas` returns **200 to an anonymous caller** and hands back working magic-link URLs for all five personas, the `admin` one included. `/api/v1/models/` and `/api/v1/knowledge/` both 403 anonymously, so this is the one public door.

This is deliberate — `sage_runtime.py` documents the endpoint as public when try-mode is on, and stable URLs an operator can hand out before a workshop are the point. It is recorded here because it sets a hard limit on the instance: **anyone who finds try.sage.is gets admin.** Nothing belonging to Realtor R can live there.

---

## What this changes on the chart

- **The `/api/models` cut** — demoted. Not demo-blocking as the instance stands. Reframed as conditional on seeding.
- **School B's residue** — premise corrected; three empty knowledge bases, no accounts, nothing to export.
- **Trial model set** — sharpened. One base model is served and four agents are broken against it.
- **New: Four broken agents** — delete, repoint, or extend the connection.
- **New: The version jump** — does try.sage.is move 71 commits four days before a demo? This now sits ahead of **The cut line**, which assumed a small flip.
- **New: Browser baseline** — a real measurement of the demo path on this instance.
- Backlog — the anonymous-admin door sharpens the "own tenant" fog item.
