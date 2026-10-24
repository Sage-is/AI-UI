# UI survey: the screens people use and what they cost

Pinned: aa25d9b + pending 3.2.1 paths

Scope: the Svelte app (layout, sidebar, chat, settings, admin), the no-build pages that exist, the measured payloads, the parity harness, startr.style in the Svelte, and the locales. Backend paths start `app/backend/sage_is_ai/`, SPA paths start `app/src/` (`C/` means `app/src/lib/components/`). Line counts come from `wc -l`. "Read, not run" marks a claim proven by reading code only. Tags: **K** carry over, **F** fix (an intended diff), **D** dies with a cut.

## 1. Surface

**The app.** SvelteKit 2.20 on Svelte 4.2 and Vite 5, built with `adapter-static` and a fallback `index.html`, client-side only (`app/svelte.config.js:13-17`, `routes/+layout.ts:5`). Tailwind 4 is still in the build. 84 npm dependencies and 27 dev dependencies (`app/package.json`). 70,606 lines of Svelte and 9,670 of TS and JS, locales excluded. 45 route files, 4,084 lines.

| Screen | Route files | Component weight |
| --- | --- | --- |
| Shell | `routes/+layout.svelte` 679, `(app)/+layout.svelte` 530 | `C/layout/` 5,747 lines, 22 files |
| New chat, a chat, a shared chat | `(app)/+page` 5, `c/[id]` 7, `s/[id]` 213 | `C/chat/` 23,248 lines, 85 files |
| A Space | `space/[id]` 7 | `C/channel/` 3,362, 15 files |
| Notes | `notes/*` 128 | `C/notes/` 2,912 and `common/RichTextInput.svelte` 1,291 |
| Workshop: agents, prompts, knowledge, functions | `workshop/*` 506 | `C/workshop/` 5,597, 24 files |
| Admin: 16 settings tabs, users, functions, evaluations, diagnostics, Sprigs | `admin/*` 413 | `C/admin/` 17,936, 61 files |
| Sign in, join, home, calendar | `auth` 980, `join/[token]` 117, `home` 65, `calendar` 51, `settings/calendar` 50 | `auth` and `join` are self-contained; the other three host `/pages/` through `lib/utils/pageHost.ts` |

**The shell.**

- `routes/+layout.svelte` (679 lines) loads config and session, opens the socket, and holds every browser-side handler for server events: chat notifications, title and tag refresh, Pyodide runs, browser-side tool calls, direct-connection model calls, Space toasts, token expiry (`:102`, `:121-415`, `:417-485`, `:497`).
- `(app)/+layout.svelte` (530): the boot wave (`:69-132`), ten keyboard shortcuts (`:134-230`), the setup and changelog dialog for admins (`:232-241`), a model-download poll (`:284-322`), the version toast, a dev-mission nag (`:333-372`) and a 58-line IndexedDB migration overlay (`:415-472`).
- `C/layout/Sidebar.svelte` (1,368): New chat, Search, Notes, Workshop, Spaces, pinned chats, folders, chats grouped by time with paging, chats shared with and by the user, drag-and-drop import. On mount it fetches branding, Spaces, chat list, tags, pinned, folders and shared chats (`:456-552`). Beside it: `RecursiveFolder` 588, `ChatItem` 512, `ChatMenu` 373, `UserMenu` 280, `SearchInput` 259, `SearchModal` 372, `ChatsModal` 377.

**Chat.** Largest files in `C/chat/`: `Chat.svelte` 2,297; `MessageInput.svelte` 1,941; `Messages/ResponseMessage.svelte` 1,363; `MessageInput/CallOverlay.svelte` 955; `Settings/About.svelte` 909; `SettingsModal.svelte` 895; `ModelSelector/Selector.svelte` 643; `Messages/CodeBlock.svelte` 608; `MessageInput/VoiceRecording.svelte` 562; `Settings/Advanced/AdvancedParams.svelte` 547; `Messages/UserMessage.svelte` 523; `Messages.svelte` 460. The browser renders messages with marked, DOMPurify, KaTeX, highlight.js and mermaid.

**Settings modal, 9 tabs.** `C/chat/SettingsModal.svelte` (895 lines; tab ids at `:33,65,196,215,231,253,329,366,416`) and nine tab files totalling 3,260 lines: general 301; interface 565, a data table of 38 entries in four sections (`C/chat/Settings/Interface.svelte:21-293`); connections 163 and tools 133, shown only with direct connections and direct tool servers; personalization 97 plus three memory modals; audio 422; chats 256; account 414; about 909.

**Admin, 16 tabs.** The tab list is `C/admin/Settings.svelte:43-59`. The tab files hold 8,104 lines and their subfolders 2,418 more: general 427, auth 849 (OAuth and LDAP), theme 348, connections 490, models 605, evaluations 186, tools 134, documents 1,340, code-execution 330, interface 573, audio 724, images 703, pipelines 546, bridges 516, db 150, trial-mode 183. By regex they hold 47 `<Switch>`, 25 `<select>`, 116 `<input>`, 25 `<SensitiveInput>` and 1 `<textarea>`: 214 controls, where the plan says about 204. Outside the tabs: users 3,126, functions 1,253, evaluations 1,361, diagnostics 1,002, Sprigs 252.

**No-build pages.** `pages/` is mounted at `/pages` (`main.py:2429`).

- 27 Python files, 6,794 lines: `router.py` 1,303 (57 route decorators), `shell.py` 290, `i18n.py` 201, `auth.py` 136, `slashes.py` 103, `templates.py` 54, `calendar_card.py` 543 and 19 `*_panel.py` modules (4,155 lines; agents 526, prompts 413, auth 273, diagnostics 255, branding 234, home 233, privacy 222).
- 21 Jinja2 templates, 1,920 lines (1,739 not blank).
- Assets: `pages.css` 430 lines, `startr-swap.js` 329 (13,802 bytes), `sw.js` 156, `changelog-pager.js` 96, `dev-reload.js` 79, `color-pair.js` 41, `home-greeting.js` 27, `try-sage-slideshow.js` 19, `offline.html` 53, and a vendored `htmx.min.js` (50,917 bytes).
- What they serve today: the nine setup-wizard panels (the Svelte wizard is deleted), the try.sage welcome page, `/home`, `/calendar` and `/settings/calendar` (hollowed into the SPA chrome), Workshop agents and prompts, admin Sprigs, Diagnostics, Privacy and Branding, the calendar and its settings, the changelog.
- The shell is an f-string on purpose (`shell.py:1-50`). It puts `data-swap="/pages/"` on `<main>`, loads the rolling startr.style stylesheet (`shell.py:261`), then `pages.css`, then the brand colors (`:220-243`), and appends `startr-swap.js` to every page (`:204`).

**`startr-swap.js`** is byte-identical to upstream v1 (`WEB-Startr.Style/src/static/v1/swap.js`: md5 `d310cade…`, 13,802 bytes, 5,356 gzipped). Upstream v1.1 sits beside it (`src/static/v1.1/swap.js`: md5 `ab657420…`, 334 lines, 13,748 bytes, 5,445 gzipped). The one behaviour change: `adoptScripts` and the `swap:after` event run inside the view-transition callback, so a listener sees the new content. It also gains an MIT header and ASCII comments. The app ships v1.

**Parity harness.**

- `app/cypress/support/surfaces.ts` (177 lines) maps a surface name to a legacy path, a no-build path and a `content` selector. Five entries: `sprigs`, `diagnostics`, `branding`, `agents`, `prompts`. A hollowed surface leaves the registry (`:127-139`).
- `make e2e_both` (`Makefile:523-528`) runs the whole Cypress suite twice on the baked image, `SURFACE_TARGET=legacy` then `nobuild`. There are 48 top-level specs.
- `make surface_budget` (`Makefile:704-705`) runs `scripts/gates/surface-budget/run-gate.sh` (151 lines) on a restored snapshot: bytes only, the median of 3 against the spread, and the app-wide floor must not grow. The instrument is `cypress/e2e/upgrade/route-payload.cy.ts` (216 lines) with `cypress/support/perf.ts`.
- `surface-parity.cy.ts` (82 lines) compares the `data-cy` hooks each side renders. The SPA carries 127 (124 unique) in about 25 files; the pages carry 229 (219 unique). Chat has one (`C/chat/MessageInput.svelte`); `Sidebar.svelte`, `Chat.svelte`, `ResponseMessage.svelte` and `Space.svelte` have none.

**What the screens cost.** Decoded kB unless stated. The measured pages are in `docs/orientation.md:44-71` and `docs/no-build-surface-convention.md:9-22,89-98`; the rest are board cards, cited by title because `TODO.md` lines move.

| Measure | Value | Source |
| --- | --- | --- |
| Floor: a SvelteKit route with no data of its own | 6,642 kB decoded after the font fix; 127 requests and 781 kB wire when warm, measured before it | cards "SURVEYED…" and "THE FLOOR" |
| `/api/models`, inside the floor | 2,304 kB; 741 kB wire on every navigation, never cached; base64 avatars from `utils/models.py:175` | "THE FLOOR" |
| `/api/v1/models/` | 1,503 kB; with `/api/models` 3,807 kB, 41% of the Workshop load | "The list payload repeats…" |
| Own data above the floor | prompts +121, functions +206, users +296, knowledge +455, evaluations +1,269, agents +1,714, chat +5,170 | `docs/orientation.md:60-63`, before the font fix |
| A conversation load | 172 requests, 7.9 MB, about 19 s | the 2026-07-25 plan, `TODO.md:805-809`; basis not stated |
| Workshop agents, snapshot, cold | SPA 126 requests, 3,604 kB wire, 9,174 kB, 5,442 ms; page 11 requests, 234 kB wire, 472 kB, 152 ms; repeat visit 7 kB, 44 ms | `docs/no-build-surface-convention.md:13-16` |
| Workshop agents, production | 144 requests, 20,520 kB, 32 s | `pages/agents_panel.py:5` |
| Four moved surfaces, SPA to page | sprigs 6,626 to 76; diagnostics 6,676 to 98; branding 7,415 to 71; agents 8,235 to 350 | `docs/no-build-surface-convention.md:91-96` |
| Out of the image already | pyodide 62 MB, CJK fonts 59 MB, onnx wasm 22 MB | `Dockerfile:67-89` |

Three cautions. The floor already contains `/api/models` (the card says "2,304 kB of it"), so the plan's first-screen row, "6,642 kB baseline + 2,304 kB", counts it twice. The chat delta (+5,170, snapshot, 2026-08-02) and the 7.9 MB conversation (the 2026-07-25 plan) come from different runs and do not add. Agents has three unreconciled figures: 20,520, 9,174 and 8,235. Send, time to first token and a Space open have never been measured.

**Inline props against classes.** Counts of `style="--` and `class=` in `.svelte` files, by regex:

| Area | props | `class=` |
| --- | --- | --- |
| `C/chat/` | 1,252 | 268 |
| `C/layout/` | 386 | 59 |
| `C/channel/` | 187 | 38 |
| `C/workshop/` | 471 | 36 |
| `C/admin/` | 2,017 | 247 |
| `C/common/` | 193 | 76 |
| `C/notes/` | 160 | 24 |
| `routes/(app)/` | 73 | 23 |
| all Svelte | 5,028 | 843 |

Files the plan names: `Sidebar.svelte` 72 and 20; `MessageInput.svelte` 52 and 23 (the plan's class counts are 17 and 18; the prop counts match). Others: `ResponseMessage` 45 and 28, `UserMessage` 42 and 14, `SettingsModal` 40 and 4, `chat/Navbar` 30 and 7. By a rough test for utility tokens, about 530 of the 843 `class=` values still carry Tailwind (chat 144 of 268, layout 32 of 59, channel 16 of 38), 15 use container-query variants, 47 use `group-hover:`, and 703 `className=` props pass classes into child components. The plan's remaining list is container queries, `group-hover`, `markdown-prose` and spinners.

**Locales.** `app/src/lib/i18n/locales/` holds 55 locale directories, each with one `translation.json`, plus `languages.json`. The plan, `pages/i18n.py:12` and `docs/no-build-surface-convention.md:227` say 56; they count that extra file. The catalogs total 5,082,129 bytes (72,343 for en-US, 105,668 for ar). en-US has 1,538 keys, and the keys are the English text, so only 27 of its values are filled. Coverage, filled values over the en-US keys: median 70.7%, best zh-CN 95.3%, and 20 locales under 50%. That 20 includes en-US and en-GB (1.8% and 1.0%); the real figure is 18. The SPA loads one catalog by dynamic import (`lib/i18n/index.ts:47-48`) and has 2,449 `i18n.t(` call sites. `pages/i18n.py` (201 lines) picks a locale from `?lang=` or `Accept-Language`. The pages use 167 distinct literal `_("…")` keys: 47 appear in some catalog and 120 in none, because the extractor reads only `src/**/*.{js,svelte}` (`app/i18next-parser.config.ts:29`) and drops keys it does not find (`:15`).

## 2. What really runs

**Cold load of any SPA route.**

1. `app.html` head: viewport (`:26`), the rolling startr.style stylesheet (`:31`), `/assets/custom.css`, `/themes/active.css` (23 bytes when no theme is grafted, `no-cache`), `loader.js`, an inline theme bootstrap, a service-worker registration (`:111-143`).
2. SvelteKit hydrates. `routes/+layout.ts` runs `getBackendConfig`, then `getSessionUser`, one after the other (`:14,22`), and redirects to `/auth` without a session.
3. The root layout opens the socket and emits `user-join` (`routes/+layout.svelte:83-103`).
4. `(app)/+layout.svelte` probes IndexedDB, loads user settings, then fetches models (2,304 kB), banners, tools and tool servers in one `Promise.all` (`:75-127`). The route slot shows a spinner until `loaded` is set (`:281`, `:476-482`).
5. In parallel, the Sidebar fetches branding, Spaces, chats, tags, pinned chats, folders and shared chats (`C/layout/Sidebar.svelte:456-552`), and the route component fetches its own data.

**Send.** The send button posts to `/api/chat/completions` and receives `{status, task_id}`, not a stream (`C/chat/Chat.svelte:1682-1745`; `utils/middleware.py:2254-2259`). The server consumes the provider stream in a background task, pushes tokens to the browser over socket.io as `chat-events` of type `chat:completion` (`socket/main.py:643-710`; `C/chat/Chat.svelte:297-315,1223-1360`), and writes the answer to the database itself. Stop is `POST /api/tasks/stop/{id}` (`lib/apis/index.ts:223-224`). Only a caller that sends no `session_id`, `chat_id` and `message_id` gets a streamed HTTP body (`utils/middleware.py:2262-2297`).

**A no-build page.** The browser asks for `/pages/...`. The route's cookie guard resolves the user through the same `get_current_user` the API uses (`pages/auth.py:9-21`). The panel builds its context from API handlers called in process, `templates.render` fills a Jinja2 template, and `shell.render_page` wraps it. `startr-swap.js` then takes over clicks and GET or urlencoded POST forms inside `/pages/`: it fetches with `credentials: 'same-origin'`, parses with DOMParser, swaps the region, runs a View Transition and keeps history right. With JavaScript off, links and forms navigate normally.

**A hollowed route** (`/home`). The SPA keeps the address and the chrome; `lib/utils/pageHost.ts` fetches `/pages/home`, moves the children of `<main>` into the route and re-creates its scripts (`lib/utils/pageHost.ts:1-60`; `docs/decisions/2026-08-08-hollowing-a-svelte-route.md`). It costs bytes: the SPA floor plus the page.

## 3. Edge cases worth keeping

1. **Fourteen chords, not eight** — the layout registers 10 (`(app)/+layout.svelte:134-229`), all with Ctrl or Cmd except the last: K search, Shift+O new chat, Shift+; copy last code block, Shift+C copy last response, Shift+S toggle sidebar, Shift+Backspace or Delete delete chat, `.` settings, `/` shortcut list, Shift+' temporary chat, and Shift+Esc focus input. The composer adds four: Esc (stop), Ctrl or Cmd+Shift+Enter (prompt pair), Ctrl or Cmd+R on an empty prompt, and a held Shift on paste, which keeps a long paste as text. The first three repeat in three keydown blocks (`C/chat/MessageInput.svelte:1144-1159,1341-1357,1463-1466`); the paste rule tracks Shift at `:776-794,1115`. The shortcuts modal lists 12 and omits temporary chat and Ctrl+R (`C/chat/ShortcutsModal.svelte:12-86`). The plan says 8. Targets are found by DOM id or class (`sidebar-new-chat-button`, `copy-code-button`, `delete-chat-button`), so a new composer keeps those hooks or rewires them. **K**.
2. **Streaming rides the socket, not the response** — the send call returns a task id and tokens arrive as `chat-events` (section 2). Two parts are worth keeping: generation outlives the tab, because the server owns the task (`utils/middleware.py:2254-2259`), and every tab of that user gets the same events (`socket/main.py:647-656`). The transport is replaced by the plan's SSE with `?after=<seq>` reconnect. The database write waits for the end of the stream unless `ENABLE_REALTIME_CHAT_SAVE` is on, and its default is False (`env.py:328-330`). **K** (task survives the tab), **F** (transport).
3. **One socket channel carries six jobs** — `chat-events` brings chat tokens, notifications and sound, title and tag refresh, `execute:python` (a Pyodide worker), `execute:tool` (browser-side tool servers) and `request:chat:completion` (a direct connection: the browser calls the model and streams lines back over the socket) (`routes/+layout.svelte:121-415`; `utils/chat.py:62-150`; `utils/middleware.py:2104-2200`). `direct.enable` is true in both snapshots. Direct connections and direct tool servers are in none of the plan's keep, Sprig or cut lists. **F** (no card): decide.
4. **`/api/models` rides the boot wave** — `(app)/+layout.svelte:120-127` fetches 2,304 kB before any route renders, even `/notes`, and never caches it (741 kB wire per navigation). The main chunk also imports a 53,602-byte emoji table (`lib/stores/index.ts:7`). **F** (card: "THE FLOOR").
5. **`100vh` appears 25 times** — the sidebar scrim has `--h:100vh` and no `100dvh` cap (`C/layout/Sidebar.svelte:587`); the column beside it has both (`:615`). 22 sites carry `100dvh`. The phone cutoff is a board card. **F**.
6. **Same-origin frames sit beside the token** — `C/chat/Messages/CitationsModal.svelte:292-297` hardcodes `sandbox="allow-scripts allow-forms allow-same-origin"` on a `srcdoc` of retrieved HTML. The user toggle `iframeSandboxAllowSameOrigin` (`C/chat/Settings/Interface.svelte:244`) adds the same flag at `Artifacts.svelte:315-319` and at `Messages/Markdown/HTMLToken.svelte:112-116`, which the plan does not name. The SPA keeps its token in `localStorage`. **D**: never ported.
7. **The shell keeps one-off prompts** — a 58-line IndexedDB overlay, dev-mission nag toasts every 30 to 60 minutes, an update toast, and four imports nothing calls: `getKnowledgeBases`, `getFunctions`, `getAllTags`, `getPrompts` (`(app)/+layout.svelte:14-19,333-372,415-472`). **D**.
8. **Two identities, one rule** — the SPA sends a Bearer token from `localStorage`; the pages use the `token` cookie; both resolve through `get_current_user` (`pages/auth.py:9-21`; `utils/auth.py:150-167`). A first draft of the pages' own check missed the try.sage reset cutoff. The Rootstock keeps one door. **K**.
9. **A 200 proves nothing under `/pages/`** — the SPA mount answers every unmatched path with the shell, so gates read `[data-cy="page-heading"]` (`docs/orientation.md:121-125`; `pages/shell.py:272-278`). **K** until the catch-all goes.
10. **Parity has no handle on chat** — hooks: chat 1, Sidebar 0, Chat 0, ResponseMessage 0, Space 0. F3 and F4 add hooks to the legacy side before code moves, as step 2 of the convention requires. **F** (card: "Channel components carry zero `data-cy` hooks").
11. **startr.style is a rolling, render-blocking CDN link** — `app/src/app.html:31` and `pages/shell.py:261`. It is the one off-box request on a normal load (`shell.py:36-50`). Layout that must survive an outage lives in `pages.css` (`pages-cdn-outage.cy.ts`). No version, no SRI (`docs/no-build-surface-convention.md:219`). **F** (board: versioned URL with SRI).
12. **Page strings cannot be translated** — 120 of 167 literal keys in `pages/` appear in no catalog, and a hand-added key would be dropped by the next extraction (`i18next-parser.config.ts:15,29`). **F** (no card): extract from Jinja and Python.
13. **Swap limits** — multipart forms bypass the swapper (`startr-swap.js:294`), the fetch carries no request header (`:170-174`), nothing aborts an older swap, and there is no busy state. Four panels (branding, diagnostics, privacy, Sprigs) still carry `hx-` attributes and ship 50,917 bytes of htmx (`pages/assets/vendor/htmx.min.js`; card "Remove htmx"; the docs say three). **F** (the plan's upstream proposals), **D** (htmx).
14. **Message actions hide behind hover** — 47 `group-hover:` classes (chat 26, layout 3, channel 4) leave actions unreachable on touch. The plan's rule is `:focus-within` plus `(hover:none)`. **F** (no card).
15. **Two viewport metas, neither handles the keyboard** — the SPA sets `maximum-scale=5, viewport-fit=cover` (`app/src/app.html:26`), the pages `width=device-width, initial-scale=1` (`pages/shell.py:250`). Neither sets `interactive-widget=resizes-content`. **F**.
16. **Docs name an instrument that is gone** — `docs/no-build-surface-convention.md:9` and two board entries cite `cypress/e2e/upgrade/workshop-payload.cy.ts`; it was folded into `route-payload.cy.ts` and `cypress/support/perf.ts` (`app/cypress/support/perf.ts:5`). The locale count (56) and the htmx count (three) are stale the same way. **F** (docs).
17. **The theme bootstrap beats a theme Sprig** — `app.html:52` writes `localStorage.theme = 'light'` on first load, and `oled-dark` sets four gray steps as inline style (`:69-75`) that win over any `:root` rule in a theme's `theme.css`; the `workshop-bio` header says so. A Space `style` attribute on a child element wins for its subtree. **K**.
18. **The service worker is fail-open and switchable** — it caches `/_app/immutable/`, `/static/` and `/pages/_assets/`, never navigations, `/api`, `/ws`, themes or range requests, and `ENABLE_SERVICE_WORKER=false` makes `/sw.js` 404 so the page unregisters it (`pages/assets/sw.js:1-45`; `app.html:111-143`; `main.py:2456-2470`). The plan adapts it. **K**.

## 4. Ceremony to drop

- **Svelte by step.** The plan's deletion rows: F1 `C/workshop/` 5,597; F2 `routes/auth` 980; F3 `C/chat/` 23,248 and `C/layout/` 5,747; F4 `C/channel/` 3,362; F6 `C/admin/` 17,936. That is 56,870 of the 70,606 Svelte lines. Left for the carve-outs and F8: `C/notes/` 2,912, `C/common/` 5,783 and the rest of `routes/`.
- **Client plumbing.** `lib/apis` 3,845 lines in 30 files of fetch wrappers; `lib/utils` 3,571; `lib/stores` 369; `lib/workers` 341; `lib/pyodide` 204. Dead on arrival: `emoji-shortcodes-ultra-clean.json` (74,940 bytes) and `lib/utils/_template_old.ts` (66 lines) have no importer; `routes/dev/icons` (168 lines) is a dev page; `ReactionPicker.svelte.backup` is 167 lines.
- **Dependencies, 84 plus 27 dev.** By feature: Notes and rich text 33 packages (16 `@tiptap/*`, 12 `prosemirror-*`, `yjs`, `y-prosemirror`, `y-protocols`, `turndown`, `turndown-plugin-gfm`); code 9 (4 `@codemirror/*`, `codemirror` and 2 language packs, `pyodide`, `@pyscript/core`); voice 2 (`kokoro-js`, `@huggingface/transformers`); rendering 6 (`marked`, `dompurify`, `katex`, `highlight.js`, `lowlight`, `mermaid`), which server rendering replaces. Single-use: `leaflet` (one valves map), `@azure/msal-browser` (the OneDrive picker, 438 lines; the Drive picker adds 215), `jspdf` and `html2canvas-pro` (chat and note export), `pdfjs-dist` and `heic2any` (attachments), `@xyflow/svelte` (chat overview). `@pyscript/core` and `async` have no importer in `src/` or `scripts/`.
- **Build.** Tailwind 4 with two plugins, postcss, sass, `adapter-static`, a Node build with a 4 GB heap (`Dockerfile:62`), and the Vite proxy allowlist that 404s any new backend prefix (`app/vite.config.ts:28`).
- **Browser i18n.** 55 catalogs loaded by dynamic import and 2,449 `i18n.t(` call sites, replaced by server gettext.
- **Legacy twins of built pages.** `C/admin/Settings/Theme.svelte` 348, `C/admin/Sprigs.svelte` 252, `C/admin/Diagnostics.svelte` 426 with `Diagnostics/` 576, and `C/workshop/Models.svelte` and `Prompts.svelte`: each has a no-build page already (registry above).

## 5. Rootstock equivalent

**Shell and sidebar** → `shell/` (cap 650) and `conversations/` (cap 2,700). A server-rendered `<aside>` beside `<main id="chat" data-swap="/">`; each sidebar link names its target with `data-swap-target`. Items: New chat, Search, Home, Workshop, Spaces, pinned chats, folders, chats by time; Notes appears only when the notes Sprig is grafted. The sidebar's separate fetches become one render. The boot wave of `(app)/+layout.svelte` disappears: no settings fetch, no model JSON, no IndexedDB probe.

**Chat** → `conversations/chat/` with `chat.js` and `composer.js` (12 kB gzipped together). `composer.js` carries the 14 chords of edge case 1, the `/`, `#` and `@` popups and the Tab rule (`C/chat/ShortcutsModal.svelte:67-85`), and keeps the ids those shortcuts target. Send, stop and reconnect follow the plan's SSE design. Copy one thing from today: generation outlives the tab.

**Settings** → one `<dialog>` of 4 sections and at most 15 controls, from 9 tabs, 38 interface entries and 3,260 lines. Proposed: General (language, theme), Chats (import, export, archive), Account (password, API key, webhook if kept), About (version, licence). Personalization (memory, 0 rows) leaves the core, audio goes to the voice Sprig, and the direct-connection tabs wait on edge case 3. The rule is the plan's: what an operator decides once is a wire, not a user setting.

**Admin** → 8 pages with at most 80 controls, from 16 tabs and 214 controls. The plan's table: by hand (general, auth, theme, documents, interface); generated (connections, models, tools, users and groups); Sprig-provided when grafted (audio, images, code-execution, bridges, pipelines); Django admin (db, trial-mode). It also lists `evaluations` as Sprig-provided while cutting it elsewhere (plan lines 31, 218, 272); settle one. The auth page keeps OAuth and magic links and loses LDAP (the tab is 849 lines now).

**No-build pages** → nine templates adapted (plan), their Python rewritten against ops. Keep the verb-table check, the 229 `data-cy` hooks, the cookie door and the `page-heading` marker.

**Assets.** Vendor `startr-swap.js` v1.1 with SRI, since chat needs `swap:after` to fire after the content is in. Self-host or pin the style kit with a versioned URL and SRI, so a normal load makes no off-box request. Adapt `sw.js` and `color-pair.js`. Drop htmx (50,917 bytes) and keep `dev-reload.js` out of production. The plan's upstream proposals stay as patches: `Swap-Target` header, abort per region, `aria-busy`, multipart, `data-swap-events`, `:focus-within`, container-query tiers.

**Locales.** Django gettext with all 55 locales. The keys already are the English text, so `.po` conversion is direct. The starting set is the 167 page keys plus whichever SPA keys the new templates reuse; 1,538 is the ceiling, not the count the plan implies ("the keys core templates use"). Extract from Jinja and Python, so the 120 orphaned page keys enter the catalogs. Report coverage per locale (median 70.7%, 18 non-English locales under 50%) and do not gate on it.

**Proof.** Register each Rootstock address as `nobuild` in `SURFACES`, add `data-cy` hooks to the legacy chat, sidebar and Space first (step 2 of the convention), and run `make e2e_both` and `make surface_budget` unchanged. The plan's byte ceilings go into the ledger; times are reported and never gated. Streamed screens need a driver that does not buffer (Playwright) and a human pass on a trackpad and a phone. The three-sample median with spread in `route-payload.cy.ts` is the standard for "snappier". Measure what has never been measured before F3 starts: send, time to first token, a Space open.

**Census:** facts from `census/census-2026-10-23.json` (two databases: a 2026-07-12 production snapshot and a 2026-09-27 backup, both 3.1.0-era). Counts only. 32 users (5 admin, 27 user), active within 7, 30, 90 days: 3, 7, 8 (snapshot), 3, 5, 5 (backup); 19 users hold saved UI settings, and the keys two or more of them share are `models` 13, `version` 9, `notifications` 8, `params` 7, `audio` 5, `setupCompleted` 3, `copyFormatted` 2, `imageCompressionSize` 2, `pinnedModels` 2; 1,982 chats (2,124 in the backup), 58 in folders, 29 shared, 15 pinned, 1,556 with tags; 14 folders; 1,395 tags (1,494); `ui.model_order_list` holds 407 ids, `ui.prompt_suggestions` 7, no banners; branding sets a primary color and nothing else; `direct.enable`, `ui.enable_message_rating` and `ui.enable_community_sharing` are true; `tool_server.connections` holds 2; OAuth client ids are empty; magic-link login, LDAP and Ollama are off.
