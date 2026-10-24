# Spaces survey: rooms, agents, themes and the Workshop

Pinned: aa25d9b + pending 3.2.1 paths

Scope: the Spaces feature (the `channel` table family), its live events, Space agents, theming, the Workshop agent and prompt panels, and what Trellis calls. Backend paths start `app/backend/sage_is_ai/`, SPA paths start `app/src/` (`C/` means `app/src/lib/components/`), Trellis paths start at that repo's root (commit 4600f88). Line counts come from `wc -l`. "Read, not run" marks a claim proven by reading code only. Tags: **K** carry over, **F** fix (an intended diff), **D** dies with a cut.

## 1. Surface

**Routes.** `routers/spaces.py` (1,070 lines) mounts at `/api/v1/spaces` (`main.py:1554`) with 15 endpoints. Every message route asks for `read` access only (edge case 1).

| Endpoint | Line | Gate | Callers |
| --- | --- | --- | --- |
| `GET /` | 82 | verified user | SPA, Trellis |
| `GET /list` | 87 | admin sees all | none found |
| `POST /create` | 99 | admin or facilitator | SPA, Trellis |
| `GET /{id}` | 118 | read | SPA, Trellis |
| `POST /{id}/update` | 136 | admin or facilitator | SPA, Trellis |
| `DELETE /{id}/delete` | 161 | admin or facilitator | SPA |
| `GET /{id}/participants` | 184 | read | SPA |
| `GET /{id}/messages` | 218 | read | SPA |
| `POST /{id}/messages/post` | 543 | read | SPA, Trellis |
| `GET /{id}/messages/{mid}` | 714 | read | none found |
| `GET /{id}/messages/{mid}/thread` | 749 | read | SPA |
| `POST /{id}/messages/{mid}/update` | 799 | read | SPA |
| `POST /{id}/messages/{mid}/reactions/add` | 869 | read | SPA |
| `POST /{id}/messages/{mid}/reactions/remove` | 929 | read | SPA |
| `DELETE /{id}/messages/{mid}/delete` | 992 | read | SPA |

The SPA client reaches 13 of the 15 (`lib/apis/spaces/index.ts:39-75`). Trellis reaches 5 (below). "None found" means no caller in `app/src`, `app/cypress` or Trellis. Model code: `models/spaces.py` (139 lines), `models/messages.py` (280 lines).

**Tables.** Four, one of them dead. Times are nanoseconds (`models/spaces.py:79-80`, `models/messages.py:101`).

- `channel`, 10 columns: `id`, `user_id`, `type`, `name`, `description`, `data`, `meta`, `access_control`, `created_at`, `updated_at` (`models/spaces.py:16-33`). The ORM class is still `Channel`, and the rename to `space` sits on the board as low priority (`models/spaces.py:17-18`).
- `message`, 9 columns: `id`, `user_id`, `channel_id` (the Space id), `parent_id`, `content`, `data`, `meta`, `created_at`, `updated_at` (`models/messages.py:35-50`).
- `message_reaction`, 5 columns: `id`, `user_id`, `message_id`, `name`, `created_at` (`models/messages.py:16-22`). No unique key.
- `channel_member`, 4 columns, created at `migrations/versions/3781e22d8b01_update_message_table.py:52-66`. No ORM class, no reader, no row. Membership lives in `channel.access_control`.

**Stored shapes.**

- `channel.access_control`: `{"read": {"user_ids": [], "group_ids": []}, "write": {…}}`. `None` reads as public read and no write (`utils/access_control.py:142-143`). All 3 snapshot Spaces carry both keys.
- `channel.data`: `{"agents": [{"model_id", "name", "profile_image_url"}]}`. Written by `C/channel/SpaceAgentsModal.svelte:45-54`, read by `Spaces.get_space_agents` (`models/spaces.py:132-136`).
- `channel.meta`: the form accepts it (`models/spaces.py:63`) and no code reads it.
- `message.data`: `files` (`C/channel/Space.svelte:213-216`); `agent` = `{model_id, name, profile_image_url, awaiting_reply_from}` (`routers/spaces.py:428-430`); `bridge` = `{platform, connection_id}` or `{ai_response: true}` (`bridges/pipeline.py:243-247,344`). `message.meta` is unused.
- An agent's `user_id` is the literal `__agent__` (`routers/spaces.py:43`), which is not a user row.

**Settings.** One flag, `ENABLE_SPACES` (`config.py:1441-1445`, path `spaces.enable`, default False). The config endpoint and admin forms read it (`main.py:1962`; `routers/auths.py:972,1016`). The Spaces router never does (edge case 18). Per user: `settings.ui.notifications.webhook_url` (`routers/spaces.py:277-279,523-525`). The box switch `ENABLE_USER_WEBHOOKS` (`config.py:1500-1503`) only hides the field in the SPA (`C/chat/Settings/Account.svelte:240`).

**Socket events.** `socket/main.py` (729 lines) serves `/ws/socket.io` (`:181-184`). Pools are dicts, or Redis-backed `RedisDict` when `WEBSOCKET_MANAGER=redis` (`:79-122`).

| Event | Dir | Lines | What it does |
| --- | --- | --- | --- |
| `connect` | in | 248-277 | token from `auth` or the `token` cookie; fills the pools; joins no room |
| `user-join` | in | 280-306 | repeats the auth; joins `space:<id>` for every Space the user can read |
| `join-spaces` | in | 309-327 | the same join, no reply; the SPA emits it after creating a Space (`C/layout/Sidebar.svelte:568`) |
| `space-events` | in | 361-386 | relays `typing` only; the sender must be in the room |
| `usage` | in | 234-245 | model-in-use beat; each generating tab sends one per second (`C/chat/Chat.svelte:1090-1096`) |
| `join-note`, five `ydoc:*` | in | 330-358, 389-623 | notes co-editing (carve-outs note) |
| `disconnect` | in | 625-640 | drops the pool entries |
| `space-events` | out | `routers/spaces.py` | `message`, `message:reply`, `message:update`, `message:delete`, `message:reaction:add`, `message:reaction:remove`, `thinking`, `typing` |
| `space-mention` | out | `routers/spaces.py:508-519` | one per session of a mentioned user |
| `chat-events` | out | `socket/main.py:643-726` | the chat, tool and code relay (ui note) |

Every outbound Space event carries `space.model_dump()` and a full user record. The `usage` pool feeds `GET /api/usage` (`main.py:2139-2147`), which only the user menu reads.

**The Space screen.** `C/channel/` holds 3,362 lines in 15 files, plus a stray 167-line `Messages/Message/ReactionPicker.svelte.backup`. The largest: `MessageInput.svelte` 951, `Space.svelte` 393, `Message.svelte` 362, `Thread.svelte` 244. The route file is 7 lines (`routes/(app)/space/[id]/+page.svelte`). The sidebar section shows only to admins, facilitators and anyone who already has a Space (`C/layout/Sidebar.svelte:830`). Opening a Space is three serial calls: the Space, 50 messages, the participants (`C/channel/Space.svelte:73,78,84`). The root layout also toasts and desktop-notifies on events from other Spaces (`routes/+layout.svelte:417-485`).

**Space agents.** An agent is a `model` row, a custom model with a base model, a system prompt, tools and knowledge. A Space lists agents by model id in `channel.data.agents`. The picker offers every model in `$models` not yet added (`C/channel/SpaceAgentsModal.svelte:22`). Personas are try.sage seed accounts (`utils/try_sage_seed.py:54-94`); the seed never touches a Space row (no `Spaces.` call in its 970 lines), so "persona" is not a Space concept. Space membership is `access_control`, nothing else.

**Workshop surfaces.** Both panels are server-rendered, plain HTML first, and call the API handlers in process instead of round-tripping HTTP.

- Agents: `pages/agents_panel.py` (526 lines) and `templates/agents.html` (211). Routes at `pages/router.py:524-609`: list, one verb route, two exports, import, avatar. The list is `routers/models.get_models(user)` (`agents_panel.py:156-167`), which filters by role: admin all, facilitator writable, others own. Pages of 24 (`:172`). Verbs `toggle`, `hide`, `clone`, `delete` sit in a table checked against a `Literal` at first request (`:177-195`). Avatars are served by content-hashed URL, cached a year (`:87,109-126`).
- Prompts: `pages/prompts_panel.py` (413 lines) and `templates/prompts.html` (169). Routes at `pages/router.py:626-686`. Verbs `clone`, `delete`; delete asks first, on the server (`:72,92-103,302-314`). `_canonical` finds a prompt under either slash spelling (`:139-148`) and import keeps the slash (`:359-413`), because the API stores `command` verbatim and looks it up as `/command` (board card: "A prompt stored without a leading slash").
- Shared: `templates/_workshop.html` (110 lines). Under both sit `routers/models.py` (216 lines, 8 endpoints) and `routers/prompts.py` (183 lines, 6 endpoints).
- SPA twin: `C/workshop/` (5,597 lines, 24 files), registered in `cypress/support/surfaces.ts` as `agents` and `prompts`. Measured on the snapshot: Svelte 126 requests and 9,174 kB cold, the page 11 requests and 472 kB (`docs/no-build-surface-convention.md:13-16`). The panel docstring quotes 20,520 kB from production (`agents_panel.py:5`); the two bases differ.

**Theming today is one global pointer.** `SPRIG_ACTIVE_THEME` (`config.py:1199-1203`, path `ui.sprig_active_theme`) names one grafted theme Sprig. `/themes/active.css` serves its `theme.css`, or an empty sheet (`main.py:2363-2377`), and `app.html` links it on every page. A theme is one stylesheet of at most 512 KiB, checked at graft: no `@import`, no external `url()`, nothing script-shaped (`sprigs/theme_dispatch.py:24,66-90`, 99 lines). `scripts/themes/workshop-bio/theme.css` and `workshop-math/theme.css` (23 lines each) set 12 gray steps plus `--primary`, `--secondary`, `--links`. While a theme is active, the admin branding colors step back (`pages/shell.py:220-243`). Box branding (`ui.branding`) and an admin `UI_CUSTOM_CSS` (`config.py:1190-1194`, injected at `routes/+layout.svelte:649`) are also box-wide. No per-Space theme exists; `channel.meta` is unread. The board card "Space theming" asks for creator-led accent and logo with no custom CSS.

**What Trellis calls.** Trellis is a CRM that posts nudges into one Space as its own AI-UI user.

| Call | Where in Trellis | Notes |
| --- | --- | --- |
| `POST /api/v1/spaces/{id}/messages/post` `{"content": text}`, Bearer `sk-` key | `crm/loop/notify.py:65-79` | any 200 is success; one plain line and a link, never a name; the Space's bridges carry it on |
| `GET /api/v1/spaces/{id}` | `crm/loop/aiui.py:59-62` | reads `name` for the status page |
| `GET /api/v1/spaces/`, `POST /create`, `POST /{id}/update` | `scripts/aiui_setup.py:108-122` | one-time setup: finds the Space by lower-cased name, creates it, or adds Trellis to its access lists |

Trellis's other AI-UI calls: `/api/version`, `/api/v1/auths/` with `signin`, `add` and `api_key`, and `/api/v1/configs/tool_servers` with `/verify` (`scripts/aiui_register.py`). A planned loop step adds `/api/chat/completions` (`crm/docs/plans/loop.md`). The key must pass the `sk-` door: API keys enabled, and the path inside `API_KEY_ALLOWED_ENDPOINTS` when restrictions are on (`utils/auth.py:165-181`). Both snapshots have restrictions off.

## 2. What really runs

**A post** (`routers/spaces.py:543-706`, from the SPA or from Trellis):

1. `_check_space_access`: admin passes; else `has_access(read)`; else a facilitator with `has_facilitator_access` (`:62-74`). The Space owner is not special-cased.
2. Insert the `message` row, ns timestamps (`models/messages.py:95-120`).
3. Emit `space-events` `message` to room `space:<id>` with the full user and `space.model_dump()` (`:563-588`). A reply also emits `message:reply` for its parent (`:590-613`).
4. Background task: webhook each readable user who is not in the room and has a `webhook_url` (`:265-292`, `:615-624`).
5. Unless `data.bridge` is set, background task: forward to every enabled `channel_bridge` connection linked to this Space (`:626-637`; `bridges/outgoing.py:11-68`).
6. Parse `@name` with `@([\w][\w-]*)` (`:647`). With none, look at the 2 newest top-level messages for an agent post that ends in `?` and carries `awaiting_reply_from`, and wake that agent (`:649-669`). With some, wake each agent whose lower-cased name, or its hyphenated form, matches (`:671-689`), then ping mentioned users by socket and webhook (`:692-699`, `:492-540`).
7. Return the message. Any exception answers 400 with a generic detail (`:702-706`), even after the insert and the emit succeeded.

**An agent reply** (`generate_agent_response`, `routers/spaces.py:295-489`), started with an unawaited `asyncio.create_task` per matched agent (`:663`, `:681`):

1. Find the model in `app.state.MODELS`, loading the list on a cold boot. A missing model returns with no message (`:299-311`).
2. Emit `thinking` true (`:327-338`).
3. Build the prompt: the model's `params.system` if any, then ONE user message, the trigger text (`:340-345`). No thread, no history, no speaker name, no attachments. The board knows this as context mode `single`.
4. Tools: the row's `meta.toolIds` become `tool_ids`; an empty `TOOL_SERVERS` cache is filled first (`:351-387`).
5. `process_chat_payload` (`utils/middleware.py:1143-1429`): model params, `meta.knowledge` as files, pipeline and filter functions, a prompt-based tool round, RAG context. `chat_id` and `message_id` are None. `space_id` rides in the metadata and nothing reads it.
6. `generate_chat_completion(..., bypass_filter=True)` (`:392-394`). That door is `utils/chat.py:157-171`: the privacy filter rewrites outbound text for an external connection (`:207-211`), the model-access check is skipped (`:219`), and a whole reply is reversed on return (`:169-170`). `routers/openai.py:925-929` then adds the system prompt a second time. The call is not streamed.
7. Post the answer as `__agent__` with the trigger's `parent_id`, so a thread question gets a thread answer (`:432-440`). An answer ending in `?` sets `awaiting_reply_from` (`:428-430`). Emit `thinking` false and `message` (`:406-471`). On any exception: log, clear the spinner, post nothing (`:473-489`).

A second AI path lives in the bridges: a bridge message that mentions `@sage` calls `_generate_space_ai_response` (`bridges/pipeline.py:282-384`). One message, the connection's model, `bypass_filter=True`, no tools or knowledge, posted as the bridge user with `data.bridge.ai_response`. Bridge messages never wake Space agents, because the bridge pipeline does not run the mention logic.

**Live feed.** `user-join` puts a socket in the rooms of every Space it can read, once, at connect (`socket/main.py:301-306`). `leave_room` is called nowhere for Spaces. The SPA dedupes by message id (`C/channel/Space.svelte:111`), clears a typing beat after 5 s (`:193`) and learns of a new Space it was added to only after a reload or its own `join-spaces`.

**A Workshop panel request** (agents): `GET /pages/workshop/agents` → `require_agents_reader` guard (`pages/auth.py`) → `render_agents` → `routers/models.get_models(user)` → filter by query and tag → page 24 → `templates/agents.html` → the shell, with `data-swap="/pages/"` on `<main>`. A row action is a form POST that re-renders the list. Everything works with JavaScript off.

## 3. Edge cases worth keeping

1. **Write access is stored and never enforced** — `_check_space_access` asks for `read` only (`routers/spaces.py:62-74`); post, edit, react and delete all call it (`:557,811,879,939,1002`) and the word "write" appears nowhere in the router. A reader can post to a Space whose `write` list excludes them. All 3 snapshot Spaces carry a `write` list. **F** (no card): `post` needs write, `manage` needs owner, admin or facilitator.
2. **Anyone with read can edit or delete anyone's message** — no author test in `update_message_by_id` (`:799-857`) or `delete_message_by_id` (`:992-1070`), and the edit event then names the editor as the author (`:840-842`). Read, not run. **F** (no card).
3. **The owner can lose their own Space** — `get_spaces_by_user_id` lists owned Spaces (`models/spaces.py:99-104`) while `_check_space_access` has no owner clause. A creator missing from `access_control.read` sees the Space listed and gets 403 on open. Read, not run. **F** (no card).
4. **Update replaces `data` and `meta`, drops `description`** — omitted fields become null (`models/spaces.py:111-124`); create lower-cases the name, update does not (`:76` against `:117`). Trellis's setup sends no `data` or `meta` when it adds itself to an existing Space (`scripts/aiui_setup.py:118-122`), which would erase that Space's agents. Read, not run. **F** (no card): merge fields.
5. **Delete is shallow** — only the `channel` row goes (`models/spaces.py:126-130`). Messages, reactions and `bridge_connection.channel_id` links stay, and a bridge then logs "Space not found" on every incoming message (`bridges/pipeline.py:233-237`). The census cannot show orphan messages. **F** (no card): cascade.
6. **Deleting a reply to an agent answers 400 after deleting** — the row is gone (`:1017`), then the parent's `message:reply` event looks up `__agent__` as a user, gets None and raises (`:1036-1063`; `models/users.py:151-157`). Replies of a deleted parent stay (`models/messages.py:269-277`; `delete_replies_by_id` has no caller). Read, not run. **F** (no card).
7. **A deleted user breaks the feed** — `_get_user_for_message` builds a name from None (`routers/spaces.py:58-59`), so one orphan author makes the page answer 500. `Users.delete_user_by_id` removes chats and the user row, not their messages or notes (`models/users.py:375-392`). Chats have 53 distinct owners against 32 user rows, so missing authors are normal. `GET /api/v1/notes/` has the same shape (`routers/notes.py:44-49`). **F** (no card): show a "deleted user" placeholder, as `agents_panel.py:258` does.
8. **Mentions break on spaces and punctuation** — the composer inserts `@First-Last` (`C/channel/MessageInput.svelte:605-610`). Agents match the hyphenated form (`routers/spaces.py:677-680`); users are looked up by the raw string with `ilike` (`:496`; `models/users.py:170`), which cannot match "First Last", so multi-word users are never pinged. The regex stops at `.`, `/` and `(` (`:647`), so a model named "claude-3.5-sonnet" mentions as "claude-3". Keyboard choice in the picker is dead: `C/channel/MessageInput.svelte:740` looks for an id that `MessageInput/Mentions.svelte:57` does not render. **F** (card: "Spaces mention keyboard navigation is dead"; the name cases have no card).
9. **Auto-reply is one condition, by design** — an agent post ending in `?` arms the room, and the next un-mentioned post by any member among the 2 newest top-level messages wakes that agent (`:429,649-669`; `models/messages.py:167`). A question asked inside a thread never arms, because only top-level messages are scanned. Decided 2026-08-18: any member may answer, so an assistant can reply for a principal. **K**.
10. **Agent context is one message and attachments are dropped** — `:340-345`, `:366`. 10 of the 50 snapshot messages carry `data.files`. The decision record picks context modes `conversation` and `full` with speaker names (`docs/decisions/2026-08-18-spaces-agent-integration.md`). **F** (card: "Agent context mode").
11. **The system prompt goes out twice** — the Space code adds `params.system` (`:341-344`), then `apply_model_system_prompt_to_body` prepends it to that system message (`routers/openai.py:925-929`; `utils/payload.py:35-37`; `utils/misc.py:164-168`). In chat the router adds the model's prompt once and the SPA sends no copy of it. 55 of 332 snapshot models carry a system prompt. Read, not run. **F** (no card).
12. **Failure is silent and unbounded** — a missing model returns without a word (`:309-311`), an exception only clears the spinner (`:473-489`), and the provider call has no deadline unless `AIOHTTP_CLIENT_TIMEOUT` is set (`env.py:464-467`). The client drops the spinner after 120 s (`C/channel/Space.svelte:159`). This is the board's "unresponsive Space Agent". **F** (card: "Diagnose the unresponsive Space Agent"): post a visible status line and set a deadline.
13. **Any member can spend any agent** — `bypass_filter=True` skips the model-access check (`utils/chat.py:219`), so a member can wake an agent they could not pick in chat. No budget holds the call and no receipt records it. The privacy filter still runs (`:207-211`). **K** (privacy), **F** (budget and receipt; card: per-user spend budgets).
14. **User webhooks block the loop** — `send_notification` and `send_mention_notifications` are async tasks that call the synchronous `post_webhook` (`routers/spaces.py:265-292,492-540`), whose `requests.post` has no timeout (`utils/webhook.py:54`). One slow URL stalls the single worker. Switching `ENABLE_USER_WEBHOOKS` off hides the field and stops nothing. The message text goes to a user-chosen URL with no privacy pass. Read, not run. **F** (no card).
15. **Rooms go stale** — sockets join at connect only (`socket/main.py:301-306,323-327`) and never leave. A member added later hears nothing until a reconnect, and a removed member keeps receiving events until disconnect. Read, not run. **F** (no card): check access per event.
16. **A page of messages costs 2N+1 queries** — per message the replies and the reactions (`routers/spaces.py:242,251`), plus a user lookup per distinct author (`:58`). 50 messages is over 100 queries. **F** (no card).
17. **Reactions can double** — `add_reaction_to_message` inserts blindly and the table has no unique key (`models/messages.py:212-228`; migration `3781e22d8b01_update_message_table.py:35-50`), so two tabs add two rows; remove deletes every match (`:247-255`). **F** (no card).
18. **`ENABLE_SPACES` hides the screen, not the API** — the router has no gate, against the repo rule to gate before auth so a disabled feature answers 404 (`AGENTS.md`; the model is `routers/sage_runtime.py`). The saved config also holds `channels.enable`, a key nothing reads. **F** (no card), **D** (stale key).
19. **Agent tasks float and share state** — tasks are not kept (`routers/spaces.py:663,681`) and every agent woken by one post shares one `request.state` (`:373`; `utils/chat.py:184-191,211`), so `metadata` and `privacy_active` cross between them. The impact is low today, since downstream reads only prompt variables (`routers/openai.py:929`). The board has a related low item, "Spaces `TOOL_SERVERS` check-then-act" (`:382`). **F**.
20. **Notes events skip the write check** — `ydoc:document:update` takes a change from any session for any document id (`socket/main.py:526-569`); join and save test `read` only (`:404-414,474-484`); `:595` calls `document_exists` without `await`. See the carve-outs note. **F** (no card).
21. **`usage` leaks and spams** — one beat per second per generating tab (`C/chat/Chat.svelte:1090-1096`) feeds `GET /api/usage`, which gives every verified user the ids of active users (`main.py:2139-2147`; `docs/federation.md:79`). **D**: derive "in use" from receipts.
22. **Trellis depends on the shapes** — a post needs only `content`, a Bearer `sk-` key and any 200 (`crm/loop/notify.py:65-79`); `GET /{id}` must return `name` (`crm/loop/aiui.py:59-62`); setup finds the Space by lower-cased name, so create keeps lower-casing (`models/spaces.py:76`; `scripts/aiui_setup.py:109`) and returns `id` (`:113,126`). **K**.

## 4. Ceremony to drop

- **Per-route boilerplate in `routers/spaces.py`**, counted by pattern: 12 handlers open with the same lookup, 404 and access check (92 lines); 8 end in `except → 400 DEFAULT()`, which hides the cause (40); 5 re-check `message.channel_id != id` (30); 5 repeat the message-404 (30). 192 of the 1,070 lines. One `can()` plus one fetch helper replaces them.
- **Event payloads.** 12 `sio.emit` blocks (188 lines) plus the 21-line `event_data` dict (`:562-582`). Each repeats `space.model_dump()` and a full user record. The Rootstock sends ids and one rendered fragment.
- **Unused code.** `GET /list` (`:87-91`), `GET /{id}/messages/{mid}` (`:714-741`, 28 lines), `Messages.delete_reactions_by_id` and `delete_replies_by_id` (`models/messages.py:257-267`), the `channel_member` table, `C/channel/Messages/Message/ReactionPicker.svelte.backup` (167 lines), the `metadata.space_id` key.
- **The `usage` machinery.** `periodic_usage_pool_cleanup` and the pool (`socket/main.py:131-178,187-190,234-245`), `GET /api/usage` (`main.py:2139-2147`), the per-second beat in `Chat.svelte`: about 75 backend lines.
- **Pool plumbing.** The Redis branch and pools in `socket/main.py:47-122` (76 lines), `RedisLock` and `RedisDict` in `socket/utils.py:7-94`, and the `WEBSOCKET_MANAGER`, Redis URL, lock-timeout and sentinel settings (`env.py:444-462`). The Rootstock runs one worker and needs none of it.
- **Per-Space SPA code.** `C/channel/` (3,362 lines) and `lib/apis/spaces` (76 lines) go when F4 flips.

## 5. Rootstock equivalent

**Where.** `conversations/spaces/` (spaces, live) inside the 2,700-line `conversations/` cap it shares with chat; agents, prompts and theming in `workshop/` (cap 1,400); the access rule in `identity/` (cap 1,750); model calls in `providers/` behind `privacy/`; one Receipt per agent reply in `receipts/`. Counted the CleanRoom way (non-blank, non-`#` lines), today's Spaces Python is 1,120 lines (`routers/spaces.py` 809, `models/spaces.py` 98, `models/messages.py` 213), and `socket/main.py` adds 561. Proposed budget for design.md: about 600 counted lines for Spaces (ops 250, live 120, agent reply 150, island 80).

**Tables.** No new table in F4. Unmanaged models over `channel`, `message` and `message_reaction`; `channel_member` stays in the file, unmodelled. Theme and per-agent context live in the JSON that exists: `channel.meta.theme` and `channel.data.agents[].context`. Reaction uniqueness is checked in code, inside one transaction, because an index would need an Alembic revision (the plan says both "new indexes ship as Alembic revisions" and "Alembic stays frozen"; settle it).

**Ops.** Nine public and one internal replace the 15 endpoints:

- `space_list`, `space_get` (with participants and agents), `space_save` (merges fields), `space_delete` (cascades messages, reactions and bridge links).
- `message_list` (one query for a page, with reply counts and reactions; `parent` selects a thread), `message_post`, `message_edit`, `message_delete`, `reaction_set` (idempotent).
- `space_reply`, internal, opened by `message_post`.

**Access.** One function, `can(user, space, "read" | "write" | "manage")`, in `identity/`. Read: admin, owner, a listed user or group, a facilitator of a listed group. Write: admin, owner or the `write` list. Manage: admin, owner or a facilitator of a listed group; today any facilitator manages any Space (`routers/spaces.py:99,136,161`). Edit and delete a message: its author, or manage. `access_control: null` needs a decision; today it reads as open to every verified user, to read and (edge case 1) to post. Keep that meaning for Spaces and write it down. A parity corpus asserts the whole matrix.

**Live.** One SSE stream per open Space, `GET /api/v2/space_events?space=<id>` (an `@op` with `stream=True`), sends rendered fragments for `message`, `edit`, `delete`, `reaction`, `thinking` and `typing`. It checks access at connect and on every event. A second stream per signed-in tab carries mention pings and the toast text the root layout builds today (`routes/+layout.svelte:417-485`). In-process fan-out is enough while the plan keeps one worker. This retires the room model, `user-join`, `join-spaces`, `space-events`, `space-mention` and edge cases 15 and 21. `chat-events` and `ydoc:*` stay on `/ws` until their own steps, so the socket server leaves only after the carve-outs do. Until upstream `data-swap-events` exists, a Space island of about 80 lines reads the stream with `EventSource` and appends the fragments.

**Agent replies.** `space_reply` runs as a kept background task (a set holds it) with a deadline. The system prompt is applied once, in `providers/call.py`. Context follows a per-agent mode: `single` (today), `conversation` (the last 5 messages) or `full`, each line prefixed with the speaker, as the 2026-08-18 decision record chose. Attached files are either extracted or refused; decide once. The call goes through `providers/call.py` with the privacy policy and never around it, and tools use the chat round (cap 10). Each reply opens a Receipt (`op=space_reply`, `subject=space:<id>`, `caller=user:<poster>`), is held against the poster's budget and closes with usage. A failure posts a visible agent line with the error code. The skipped model-access check (edge case 13) is the one bypass worth keeping on purpose, since any member may wake any agent the Space lists; write it into design.md.

**Mentions and notices.** One slug function serves the picker and the parser: lower-case, spaces to hyphens, drop everything but letters, digits, `_` and `-`. Agents and users match on the slug, never on raw names. User pings ride the second stream. The outbound webhook (edge case 14) becomes one background job with a 5 s timeout, a refusal of private addresses, a check of `ENABLE_USER_WEBHOOKS` and a privacy pass on the text; or the feature is left out, which is Alexander's call.

**Workshop.** F1 keeps both panels' shape: the verb table checked against a `Literal`, in-process calls, 24 per page, content-hashed avatars, export and import with counts, and a delete that asks first. The prompt slash rule is enforced at the write point. Counted, the two panels and three templates are 1,110 lines (406 + 310 + 176 + 141 + 77), and the models and prompts routers and model files add 576 (151 + 135 + 183 + 107). The `workshop/` cap is 1,400 and must also hold theming and the apps host. A straight port does not fit: rewrite the Python, adapt only the templates.

**Theming.** `channel.meta.theme = {preset, accent, logo}`. The server picks tokens from the kit palette, checks WCAG AA contrast in light and dark, and writes a `style` attribute on the Space root, never a stylesheet. The two presets (15 properties each) are either the two theme Sprigs read by the picker, as today, or two rows in a table that need no graft. `sprigs/theme_dispatch.py` (68 counted lines, adapted) serves the box-wide theme only; `UI_CUSTOM_CSS` stays box-wide and admin-only.

**Trellis.** Keep the five Space routes at their paths as `compat/` entries over the ops, plus what Trellis needs beside them: `/api/version`, `/api/v1/auths/` with `signin`, `add` and `api_key`, and `/api/v1/configs/tool_servers` with `/verify`. That is 12 URL templates in Trellis's code today, 13 with the planned `/api/chat/completions` (`crm/docs/plans/loop.md`). The plan's ceiling is 15 fixed-contract routes, and it must also hold OIDC (five views), OpenAI-compatible `compat/`, MCP, upload, the Sprig proxy, theme and health.

**Proof.** The guard is thin: `spaces-multiuser.cy.ts` (153 lines, 5 tests) and one opt-in live-agent test (222 lines). Nothing covers edit, delete, reactions, threads, user mentions or the access matrix, and `C/channel/` carries no `data-cy` hook (board card "Channel components carry zero `data-cy` hooks"). F4 adds those cases first, on the legacy side. Trellis's five calls are replayed against both.

**Census:** facts from `census/census-2026-10-23.json` (two databases: a 2026-07-12 production snapshot and a 2026-09-27 backup, both 3.1.0-era). Counts only. 3 Spaces in both, each with `read` and `write` lists, `type` and `description` null, 1 with a `data` dict of one key, none with a `meta` dict; 0 `channel_member` rows; 50 messages in both (4 replies, 47 with a `data` dict, 10 with `files`, dated 2025-08 to 2026-04, plus 2 from 2026-08 in the backup); 0 reactions; `spaces.enable` true and a dead `channels.enable` true; `ui.enable_user_webhooks` true, and 8 of the 19 users with saved settings have a `notifications` block; 32 users, active within 7, 30, 90 days: 3, 7, 8 (snapshot) and 3, 5, 5 (backup); 332 `model` rows (337 in the backup), 51 with a base model, 55 with `params.system`, and in the snapshot `meta` keys `toolIds` 18, `knowledge` 9, `suggestion_prompts` 65; 8 prompts; 1,982 chats (2,124 in the backup) from 53 owners.
