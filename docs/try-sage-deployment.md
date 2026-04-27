# try.sage Trial Deployment

## Overview

try.sage is a trial mode for Sage WebUI. It runs a shared Sage instance for a workshop or demo. The instance boots with a master switch, seeds five persona accounts, registers two tool servers, and routes inference through a hidden LLM connection that admins cannot see. Every 24 hours it wipes persona chats and uploaded files. Persona accounts and seeded knowledge bases survive the reset. The reset cycle is configurable. An admin can extend the window or reset on demand.

The mode solves three problems at once. It hides upstream LLM keys from anyone signed into the trial, including admins. It gives workshop facilitators a way to share signed-in personas through magic links. It guarantees a clean state at a known cadence so each cohort starts fresh.

## Quick Start

Minimum `.env` for a working trial:

```bash
ENABLE_TRY_SAGE=true
WEBUI_URL=https://try.sage.is

TRY_SAGE_LLM_API_URL=https://api.openai.com/v1
TRY_SAGE_LLM_API_KEY=sk-your-upstream-key
TRY_SAGE_LLM_MODELS=["gpt-4o-mini","gpt-4o"]
```

Then build and start:

```bash
make it_build_n_run
```

`WEBUI_URL` must point at the public origin. The dummy-tools server URL is derived from it. Magic-link URLs in the banner also use it. Without it, persona logins land on `localhost`.

`TRY_SAGE_LLM_MODELS` defaults to empty. An empty allowlist exposes zero models. Set at least one model ID before you open the trial to users.

## Environment Variables

Variables marked **secret** must never reach the config DB or any API response. They are read once at process start and held in memory.

### Master switch and hidden LLM (env-only)

| Variable | Default | Description |
| --- | --- | --- |
| `ENABLE_TRY_SAGE` | `false` | Master switch. When `false`, every `/api/v1/sage/runtime/*` endpoint returns 404 and no try-mode wiring runs. |
| `TRY_SAGE_LLM_API_URL` | `""` | OpenAI-compatible base URL for the hidden inference connection. **Secret.** |
| `TRY_SAGE_LLM_API_KEY` | `""` | API key for the hidden connection. **Secret.** |
| `TRY_SAGE_LLM_MODELS` | `""` | JSON array (`["a","b"]`) or CSV (`a,b`) of model IDs exposed from the hidden connection. Empty means zero models. |
| `TRY_SAGE_ADMIN_PASSWORD` | random | Optional password for `try-admin@try.sage.is`. Random + logged once at first boot if unset. |
| `TRY_SAGE_FACILITATOR_PASSWORD` | random | Same for the facilitator persona. |
| `TRY_SAGE_USER_PASSWORD` | random | Same for every `try-user-N` persona. |

### Runtime config (admin-tunable, persisted)

These are seeded from env vars but can also be edited via the admin config UI without a restart.

| Variable | Default | Description |
| --- | --- | --- |
| `TRY_SAGE_RESET_INTERVAL_HOURS` | `24` | Auto-reset cadence in hours. |
| `TRY_SAGE_ADMIN_EXTEND_HOURS` | `24` | How much one admin extension adds. One extension per window. |
| `TRY_SAGE_RESET_AT` | auto | ISO8601 timestamp for the next reset. Set automatically; safe to leave alone. |
| `TRY_SAGE_TOOL_SERVER_URL` | `https://markdown-search.production.openco.ca` | Real OpenAPI tool server registered at startup. |
| `TRY_SAGE_DUMMY_TOOL_SERVER_URL` | derived from `WEBUI_URL` | Override only if you point at an external dummy. |
| `TRY_SAGE_PERSONA_SEED_ENABLED` | `true` | Set `false` to skip persona/agent/KB seeding. Useful when you provision personas externally. |
| `TRY_SAGE_USER_SEAT_COUNT` | `3` | Number of `try-user-N` accounts. Capped at 5. Total personas = 2 + this. |
| `TRY_SAGE_TUTORIAL_STEPS_JSON` | `""` | JSON array of tutorial steps. Empty renders "video coming soon" placeholders. |
| `TRY_SAGE_BANNER_TEXT` | `try.sage trial` | Copy in the always-visible banner row. |
| `TRY_SAGE_KB_INGESTED_VERSION` | `{}` | Per-agent KB content hashes. Set to `{}` to force re-ingestion. Auto-managed. |

### Analytics (persisted)

Multiple providers can run at once. Empty values mean "not enabled".

| Variable | Default | Description |
| --- | --- | --- |
| `ANALYTICS_MATOMO_URL` | `""` | Matomo tracker URL (e.g. `https://analytics.example.com`). |
| `ANALYTICS_MATOMO_SITE_ID` | `""` | Matomo site ID. |
| `ANALYTICS_GA_MEASUREMENT_ID` | `""` | Google Analytics measurement ID (`G-XXXXXXXXXX`). |
| `ANALYTICS_PLAUSIBLE_DOMAIN` | `""` | Plausible site domain. |
| `ANALYTICS_PLAUSIBLE_SCRIPT_URL` | `https://plausible.io/js/script.js` | Override for self-hosted Plausible. |

## Persona Accounts

Five accounts seed at first boot. The exact list depends on `TRY_SAGE_USER_SEAT_COUNT`.

| Email | Role | Notes |
| --- | --- | --- |
| `try-admin@try.sage.is` | admin | Owns the seeded agents. Sees admin extend/reset controls. |
| `try-facilitator@try.sage.is` | user | Workshop facilitator. Group label `facilitator`. |
| `try-user-1@try.sage.is` | user | First trial seat. |
| `try-user-2@try.sage.is` | user | Second trial seat. |
| `try-user-3@try.sage.is` | user | Third trial seat. |

Set `TRY_SAGE_USER_SEAT_COUNT=5` for seven personas total. The cap is five user seats.

### Sharing personas

Personas sign in through long-lived magic-link JWTs, not email. The links live in two places:

1. The banner has a collapsible `<details>` block titled "Persona links". Closed by default so URLs do not appear on a projector. When open it shows a labeled button, the full URL, a copy icon, and a QR code per persona.
2. `GET /api/v1/sage/runtime/personas` returns the same list as JSON.

Anyone with a URL can sign in as that persona. That is the workshop UX — the facilitator opens the `<details>` and shares whatever they want, then closes it. Links rotate at every reset, so the previous cohort's URLs stop working when a new window starts.

If the seed cannot find a persona at reset time, the seed creates it. Persona accounts persist across resets — only their chats and uploaded files get wiped.

## Reset Semantics

A background task wakes every 5 minutes and checks `TRY_SAGE_RESET_AT`. When the deadline passes, the reset runs.

### What gets wiped

- Every chat owned by every persona (`Chats.delete_chats_by_user_id`).
- Every uploaded file owned by every persona (`Files.get_files_by_user_id` then `Storage.delete_file` per file).
- Per-file vector collections (the `file-{id}` ones).
- The persona magic-link cache. Every persona link is re-minted.

### What survives

- Persona user rows. Re-creating them would break foreign keys on the next reset.
- Seeded agents (Sage Strawberry, Sage Startr.Style, AstroPi AI Tutor).
- KB collections. The seed routine skips re-ingestion when the source folder hash is unchanged.
- Tool server registrations. The registrar is idempotent and dedupes by URL.
- Files whose path lives under `data/try_sage_agents/` — those are seed-managed KB sources.

### Manual control

- `POST /api/v1/sage/runtime/extend` — advances the deadline by `TRY_SAGE_ADMIN_EXTEND_HOURS`. Returns 409 if you already extended this window. Wait for the deadline or call `/reset` to start over.
- `POST /api/v1/sage/runtime/reset` — runs the wipe immediately and sets a new deadline.

## Tool Servers

Two servers register automatically at startup and after every reset:

1. **Real markdown-search** at `TRY_SAGE_TOOL_SERVER_URL`. Used for live retrieval demos.
2. **Dummy-tools** at `${WEBUI_URL}/api/v1/sage/dummy-tools`. Mounted in-process. Each endpoint (`/web_search_demo`, `/internal_kb_demo`, `/code_runner_demo`) returns `{"status": "not_available_in_try_mode", "message": "..."}`. Lets the LLM see the tool surface without firing real capabilities.

The registrar dedupes by URL, so restarts and resets do not stack duplicate entries.

To disable a server, edit `TOOL_SERVER_CONNECTIONS` in the admin Tool Servers panel after boot. To replace one, set `TRY_SAGE_TOOL_SERVER_URL` to your own OpenAPI endpoint. To add your own server alongside, add it through the Tool Servers panel — the seeded entries will not overwrite your additions.

## Hidden LLM Connection

The trial deployment ships with one upstream LLM provider that:

- Inference can use. `/api/openai/chat/completions`, `/api/models`, and the embeddings path all union the hidden connection into their provider list.
- Admins cannot see, edit, or delete. The Connections panel and every `/api/v1/configs/connections*` endpoint reads only the public list. The hidden connection lives on `app.state.try_sage_hidden_connections`, separate from `app.state.config.OPENAI_API_BASE_URLS`.

The contract is structural, not filtered. The hidden connection never touches the public list, so it cannot leak through any admin GET, POST, or DB dump.

`TRY_SAGE_LLM_MODELS` is the gate. Only models whose IDs appear in the allowlist are exposed through `/api/models`. The upstream provider may serve hundreds of models; the trial exposes only what you opt in.

### Warning: empty allowlist breaks the trial

`TRY_SAGE_LLM_MODELS` defaults to `""`. With the default, `/api/models` returns zero models from the hidden connection and the trial appears broken to users. This is intentional — safe-by-default. Set the variable explicitly:

```bash
TRY_SAGE_LLM_MODELS=["gpt-4o-mini","gpt-4o"]
```

Or as CSV:

```bash
TRY_SAGE_LLM_MODELS=gpt-4o-mini, gpt-4o
```

### Diagnostic

Hit `GET /api/v1/sage/runtime/llm-status` as admin to confirm the hidden connection is live:

```json
{"configured": true, "model_count": 2}
```

`configured` is `true` only when the connection is registered AND the allowlist is non-empty. The endpoint never returns the URL or the key.

## Knowledge Bases

Two seeded agents ship with KBs:

- `app/backend/sage_is_ai/data/try_sage_agents/sage-startr-style/kb/*.md`
- `app/backend/sage_is_ai/data/try_sage_agents/astropi-ai-tutor/kb/*.md`

Drop markdown files in those folders and rebuild the image. The seed routine hashes each folder and compares against `TRY_SAGE_KB_INGESTED_VERSION`. When the hash changes, only the affected agent's KB re-ingests. The other agent's embeddings are left alone. The reset cycle skips re-ingestion entirely so resets stay fast.

To force a full re-ingest, set the config key `TRY_SAGE_KB_INGESTED_VERSION` to `{}` via the admin config UI and restart. The seed will see no recorded hashes and re-embed every KB.

To add a third agent: drop a `data/try_sage_agents/{slug}.md` file with frontmatter, optionally a `data/try_sage_agents/{slug}/kb/` folder, and add the slug to `_DEFAULT_AGENT_SLUGS` (and `_AGENTS_WITH_KB` if applicable) in `utils/try_sage_seed.py`.

## Tutorial Videos

The tutorial overlay reads its step list from `TRY_SAGE_TUTORIAL_STEPS_JSON`. Schema per step:

```json
{
  "id": "model-switching",
  "title": "Switching models mid-chat",
  "video_url": "https://www.youtube.com/watch?v=...",
  "dismissible": true,
  "description": "Pick a different model from the chat header. Useful when you want a fast model for ideas and a strong model for the final draft."
}
```

Real example pointing at the team's working playlist:

```bash
TRY_SAGE_TUTORIAL_STEPS_JSON='[
  {"id":"welcome","title":"Welcome to try.sage","video_url":"https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u","dismissible":true,"description":"Workshop access overview."},
  {"id":"model-switching","title":"Switch models","video_url":"https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u","dismissible":true,"description":"Pick a different model mid-chat."},
  {"id":"chat-map","title":"Chat map","video_url":"https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u","dismissible":true,"description":"Branch and revisit conversation forks."},
  {"id":"artifacts","title":"Artifacts","video_url":"https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u","dismissible":true,"description":"Render code and HTML side-by-side with chat."},
  {"id":"bialik-sage","title":"Build a Bialik Sage","video_url":"https://www.youtube.com/playlist?list=PLQ_PIlf6OzqK-mgAzTjmjXE636iqwcZ-u","dismissible":true,"description":"Create a custom agent from a system prompt."},
  {"id":"done","title":"You are ready","video_url":"","dismissible":true,"description":"Wrap up. Re-open from the Help menu any time."}
]'
```

When `TRY_SAGE_TUTORIAL_STEPS_JSON` is unset, the frontend renders one placeholder card per default step with a "Video coming soon" message and the `description` text. No broken iframes. Swap real URLs in as videos land — no rebuild needed.

## Analytics

The frontend reads provider settings from `/api/config` and dispatches to whichever providers are configured. All four can run at once.

```bash
ANALYTICS_MATOMO_URL=https://analytics.example.com
ANALYTICS_MATOMO_SITE_ID=42
ANALYTICS_GA_MEASUREMENT_ID=G-XXXXXXXXXX
ANALYTICS_PLAUSIBLE_DOMAIN=try.sage.is
ANALYTICS_PLAUSIBLE_SCRIPT_URL=https://plausible.io/js/script.js
```

When all values are empty the shim is a no-op. No outbound network calls.

## CapRover One-Click Deployment

Paste this block into the CapRover app's Environmental Variables panel. Fill in the secrets first.

```
ENABLE_TRY_SAGE=true
WEBUI_URL=https://your-trial-domain.example.com

TRY_SAGE_LLM_API_URL=https://api.openai.com/v1
TRY_SAGE_LLM_API_KEY=sk-your-upstream-key
TRY_SAGE_LLM_MODELS=["gpt-4o-mini","gpt-4o"]

TRY_SAGE_RESET_INTERVAL_HOURS=24
TRY_SAGE_ADMIN_EXTEND_HOURS=24
TRY_SAGE_USER_SEAT_COUNT=3
TRY_SAGE_BANNER_TEXT=try.sage trial

ANALYTICS_MATOMO_URL=
ANALYTICS_MATOMO_SITE_ID=
ANALYTICS_GA_MEASUREMENT_ID=
ANALYTICS_PLAUSIBLE_DOMAIN=
```

Set `srv-captain--<your-app>` for the upstream once the app boots, then map the public domain to `WEBUI_URL`. The dummy-tools server URL derives from `WEBUI_URL`, so set the domain before the first restart.

## Troubleshooting

**No models showing up.** `TRY_SAGE_LLM_MODELS` is empty. The default exposes zero models. Set at least one model ID. Confirm with `GET /api/v1/sage/runtime/llm-status` as admin — `configured` must be `true` and `model_count` must be `> 0`.

**Personas do not exist.** Either `TRY_SAGE_PERSONA_SEED_ENABLED` is `false`, or the first boot has not finished yet, or the seed errored. Check the boot logs for `try_sage_seed: seeded N personas`. If you see `try_sage_seed: admin persona missing; cannot seed agents`, the User model layer rejected the admin row — usually a unique-constraint clash from an older deployment. Resolve the duplicate email in the DB and restart.

**Reset never fires.** Look for `try_sage.reset.skip reason=parse_error raw=...` in logs. `TRY_SAGE_RESET_AT` was hand-edited to a non-ISO8601 string. Edit it through the admin config UI to a valid ISO8601 timestamp, or clear it — the next `/status` call initialises it cleanly.

**Magic links 401.** Two causes. The JWT secret rotated since the link was minted (restart, or rotate the cohort's URLs by hitting `/reset`). Or `WEBUI_URL` is wrong — the link points at a host the app does not serve from. Set `WEBUI_URL` to the public origin and restart.

**Tool servers duplicate after restart.** Should not happen. The registrar dedupes by URL. If you see duplicates, the `url` field on existing entries was edited (trailing slash, scheme change). Trim the duplicates manually in the Tool Servers panel.

**Hidden connection logs `not registered: TRY_SAGE_LLM_API_URL or TRY_SAGE_LLM_API_KEY is empty`.** One or both env vars are missing. The trial falls back to whatever public connections an admin has set up. Set both env vars and restart.

## API Reference

All endpoints return 404 when `ENABLE_TRY_SAGE` is `false`.

### `GET /api/v1/sage/runtime/status` (public)

```json
{
  "enabled": true,
  "reset_at": "2026-04-28T08:00:00+00:00",
  "hours_until_reset": 18.4267,
  "banner_text": "try.sage trial",
  "tutorial_steps": [/* parsed from TRY_SAGE_TUTORIAL_STEPS_JSON */]
}
```

### `GET /api/v1/sage/runtime/personas` (public)

```json
[
  {"key": "admin", "label": "Sage Admin", "role": "admin", "login_url": "https://.../auth#magic_token=..."},
  {"key": "facilitator", "label": "Workshop Facilitator", "role": "user", "login_url": "..."},
  {"key": "user-1", "label": "Trial User 1", "role": "user", "login_url": "..."}
]
```

Magic links rotate silently when their JWT crosses 50% TTL.

### `GET /api/v1/sage/runtime/limits` (public)

```json
{
  "allowed_models": ["gpt-4o-mini", "gpt-4o"],
  "seat_count": 3,
  "reset_interval_hours": 24
}
```

### `GET /api/v1/sage/runtime/llm-status` (admin)

```json
{"configured": true, "model_count": 2}
```

Never returns the URL or key.

### `POST /api/v1/sage/runtime/extend` (admin)

```json
{"reset_at": "2026-04-29T08:00:00+00:00", "extended_by_hours": 24}
```

Returns 409 if the window is already extended.

### `POST /api/v1/sage/runtime/reset` (admin)

```json
{"reset_at": "2026-04-28T14:32:00+00:00", "wiped_personas": 5}
```

Logs `try_sage.admin.reset actor=<email>` before the wipe runs, so the audit line lands even if the wipe fails midway.
