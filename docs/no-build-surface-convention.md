# Migrating a surface to no-build

How we move an admin surface off SvelteKit onto server-rendered fragments. Every rule here earned its place on a real surface, and the evidence is named so you can argue with it.

Five surfaces have been through it: Sprigs (231 to 157 lines, 32%), diagnostics (813 to 273, 67%), theme and branding (288 to 200, 31%), the setup wizard (1,816 to 1,294, 29% — and the only one where the Svelte was deleted outright rather than left running beside it), and Agents. The spread between those numbers is most of what this document is about.

Agents is the first one chosen for a measured user cost rather than for being ripe: `/workshop/models` was 144 requests, 20,520 kB and 32 seconds on production — a list of agents loading slower than a conversation. It is also the first surface to need **no client library at all** — plain forms, links and `<details>` — which is a better result than either htmx or an island.

The payload figures quoted here used to be JSON-against-markup, which is the number that flatters us. Measured in a real browser instead, on a restored production snapshot with 51 agents (`cypress/e2e/upgrade/workshop-payload.cy.ts`):

| | requests | wire | decoded | to first row | rows |
| --- | --- | --- | --- | --- | --- |
| SvelteKit `/workshop/models`, cold | 126 | 3,604 kB | 9,174 kB | 5,442 ms | 51 |
| the same route inside a booted app | 10 | 919 kB | 1,770 kB | **1,504 ms** | 51 |
| `/pages/workshop/agents`, cold | 11 | 234 kB | 472 kB | 152 ms | 24 |
| the same page, repeat visit | 11 | 7 kB | 472 kB | 44 ms | 24 |

Read the third row against the second, not the first: charging a whole session's bundle to one page would be arithmetic rather than a result. Page 1 is 24 rows against the SPA's 51, so the honest like-for-like is both pages — 22 requests and about 477 kB, still 7.6× less over the wire.

Time is measured **inside the browser**, from navigation start for a document load and from the click instant for an in-app one, until the first row is in the DOM. That is deliberate and it was learned the hard way: `Date.now()` read in a Cypress test body is stamped when the commands are queued rather than when they run, which made the in-app figure include the app's entire boot. Never time a Cypress step from the test body.

Two findings from that measurement belong in this document rather than only on the board. `/api/models` and `/api/v1/models/` together are **41% of the SPA page load** — two endpoints carrying the same base64 avatars for one list, which is why "prune, don't port" is a rule here. And the server-rendered page carries **zero** `data:` URIs against 66 in the JSON, because avatars became content-hashed URLs the browser can cache; that is what turns a repeat visit into 7 kB.

## Two modes: replace, or hollow

Decided 8 August 2026. Choose before step 0, because it changes what "done" means.

The migration had one mode — **replace**: the server-rendered page takes the address, the Svelte file is deleted. That is right for a surface a reader reaches directly. The try.sage welcome page is the worked example.

It is wrong for a surface that lives **inside the app chrome**. `/home` sits in the `(app)` route group — sidebar, chat list, navigation. Replace it and the reader loses all of that. try.sage welcome could be replaced outright precisely because an anonymous visitor had no chrome to lose.

So there is a second mode. **Hollow** the route: it keeps its address and its chrome, gives up its own content, and hosts the server-rendered page inside itself. One implementation of the view, at the address people already use. `app/src/lib/utils/pageHost.ts` is the mechanism; `/home` is the first one.

**Choosing is one question: does the reader lose anything if the SPA shell goes away?** If yes, hollow it.

A hollow tree is alive — only the cambium under the bark carries sap, and old trees are routinely hollow and healthy. The name carries the warning too: **a hollow tree eventually comes down.** A hollowed route is a Svelte file kept past its content, so record what has to be true before it is deleted, or it becomes permanent.

**Hollowing costs bytes.** The route boots the SPA floor and then fetches a page on top — more than either alone. It buys reach and a single implementation, never payload. Do not cite it as a payload win.

Full reasoning, the names considered and rejected, and what it does to the parity gate: [`docs/decisions/2026-08-08-hollowing-a-svelte-route.md`](decisions/2026-08-08-hollowing-a-svelte-route.md).

## The order of work

Order matters more than any single step. Most of what follows exists because someone did it backwards once and paid for it.

**0. Measure the surface before you touch it — twice, and three times each.** This step was added on 2 August 2026, after the Agents surface was built before anyone knew what it would save and the board's migration order turned out to be sorted on 2–6% of the cost. Alexander: *"measure twice, then build server side, then measure again."*

Two different measurements, because they disagree and the disagreement is the point:

- **the data** — query `tools/db_snapshots/*` for what the surface actually holds. Cheap, and it sets the expectation the next measurement will test.
- **the document** — boot that snapshot (`KEEP=1 make upgrade_gate`) and load the page in a browser, reading its own resource timings via `cypress/e2e/upgrade/route-payload.cy.ts`.

The data query once said the workshop list cost ~1.5 MB. The browser said 9,174 kB. Acting on the first alone would have shipped a fix for the wrong thing, which is exactly what the refuted avatar theory was.

**And never one sample.** The ledger takes three of everything and reports median with spread. Decoded bytes repeat to within 0.1 kB; times have swung 2× on the same route in the same run. **A delta smaller than the spread is not a result** — say so rather than claim it. This is also why the budget gate judges bytes and never times.

**1. Register the surface** in `app/cypress/support/surfaces.ts`, mapping its name to the legacy path, the no-build path, and a `content` selector for something only that surface renders. Do this before any code moves. It is a few lines whose real job is forcing step 2 — and it also enrols the surface in the payload ledger and in `make surface_budget`, so the before-and-after costs nothing extra to remember.

The `content` selector must not match anything the app shell renders. A selector that also appears on the chat page measures the shell, produces a plausible number, and passes. Planting `button` there once made a route report 152 ms instead of 1,840 ms while every other test stayed green; the ledger now asserts against that specifically.

**2. Hook every interactive control on the LEGACY surface** with `data-cy`. Buttons, disclosures, list rows, empty states, error states. This is the step that gets skipped, and skipping it is how a migration ends up 40% done with a green suite. You are writing down what the old page can do while the old page is still the only page.

Someone will ask why a dedicated attribute when the element already has an `id`. Five branding fields already had one. The hooks are not there so Cypress can find things, because `cy.get('#title')` works fine. They are there because the parity gate needs a curated set of what must exist in both implementations. Point it at `[id]` and it sweeps up framework-generated ids and layout ids on the single-page-app side, then reports gaps that are not gaps. There is a second reason: an `id` is load-bearing for the page itself, since `<label for>`, CSS and JS all read it. Pin a test to one and either a rename breaks the suite or the suite blocks a rename. A test attribute is inert, and that is what makes it a stable contract.

Output does not earn a hook. Preview text, computed labels, rendered values. The contract is controls. A spec can assert output through its container, so `[data-cy="branding-preview"]` containing the expected text covers the preview without a hook on every line inside it. Hooking output pads the parity set with things whose absence is not a missing capability.

**3. Write the guard-rail spec against the legacy surface and prove it green.** Read data attributes, never translated words or class names. Use `data-status` rather than the badge's text, `data-section="boot_status"` rather than the heading "Boot status". That is what lets one spec judge two implementations.

**4. Build the fragment as plain HTML, and get it reviewed before you style it.** Alexander, 1 August 2026: *"before adding any style or start.style get things working as pure html and then I'll review (this is for all new pages as we move forward) or use the same style and classes from the svelte. Don't go reinventing things."*

Two acceptable paths, then. Ship it unstyled and hand it over for a look, or lift the styling the Svelte surface already has. What is not acceptable is inventing a third visual language on the way past, which is how a migration turns into a redesign nobody asked for and how a regression gets argued about as a taste question.

The order is the point. Structure is the thing a review can judge — whether the right elements are there, whether the controls are all present, whether the page works with no CSS at all. Styling on top of a wrong structure hides the wrongness, and a reviewer then spends their attention on the paint. It also keeps the two failure modes separable: a plain page that behaves correctly and a styled page that does not are different bugs, and finding out which you have is free if you built them in that order.

Branding is the cautionary tale in the other direction, at [the props rule](#startrstyle-props-not-a-parallel-stylesheet): 99 lines of hand-written CSS went in before anyone asked whether they were needed, and deleting them took the cut from 8% to 31%. Unstyled first would have caught that before it was written.

**5. Style it, once the structure has been looked at.** The design rules below are where the line count comes from, and the props rule is the reason the answer is usually that no stylesheet is needed at all.

**6. Let the parity gate find what you missed.** `surface-parity.cy.ts` visits both implementations, collects the `data-cy` hooks each one renders, and fails naming the ones the no-build page does not. It never reads your spec, so a narrower spec cannot satisfy it. On diagnostics it went red with `diag-command-library, diag-ghost-endpoints, diag-reprobe, diag-technical`, four controls a human had already found broken by clicking.

**7. Run `make e2e_both`.** It runs the suite once per target. "Green against both" is the migration's core rule, and running it twice by hand is how that rule quietly becomes "green against whichever one was checked last".

**8. Measure the LINES, and report the number you actually got.** The first Sprigs fragment was 208 lines and only reached 157 after someone asked whether it could be cleaner. A first draft is not a measurement.

**9. Measure the payload again — the same spec, not a different method.** Re-run the ledger from step 0 and publish the delta against the spread. Using the identical instrument for the before and the after is the whole reason it is one file: a before and an after taken different ways is not a delta, it is two numbers.

Then let `make surface_budget` hold the result. It reads the ledger and fails if a server-rendered surface is not lighter than the one it replaces by more than the observed spread, or if the app-wide floor has grown. It is in `gauntlet_full`, costs about three minutes for its snapshot boot, and it is the only gate that judges what this migration *claims* rather than whether the code runs.

What the four migrated surfaces cost, measured this way on a production snapshot:

| surface | SvelteKit | server-rendered |
| --- | --- | --- |
| sprigs | 6,626 kB | **76 kB** |
| diagnostics | 6,676 kB | **98 kB** |
| branding | 7,415 kB | **71 kB** |
| agents | 8,235 kB | **350 kB** |

Most of the SvelteKit column is not the surface. A route with *no data of its own* costs 6,642 kB decoded — that is the floor every SvelteKit route pays before rendering anything, and `notes-empty` in the ledger is the gauge for it. Which is why a surface's own list size is a poor guide to whether migrating it is worth doing, and why the order of work here is about lines and usage rather than payload.

## The dev loop

Never run `make it_build` to look at something. These pages have no build step, and until 31 July 2026 that promise stopped at the container wall — every one-line style tweak meant rebuilding a 619 MB image. It does not any more.

| you want to | run |
| --- | --- |
| **build anything** | **`make dev`** |
| judge whether it ships | `make review` |
| judge a page without rebuilding | `make review LIVE=1` |
| judge Svelte changes | `make review REBUILD=1` |

**Two commands, as of 9 August 2026.** There were four, and they differed by two booleans that `scripts/manual-check.sh` already read from the environment, so three of them were preset calls to one script. `dev_run`, `review_live` and `review_rebuild` survive as aliases.

**`make dev` is the one to reach for whenever you are building.** It publishes 5173, mounts the frontend source, the static dir, the whole backend and every Vite/Svelte config, then runs `uvicorn --reload` and `vite dev` side by side in one container. Svelte hot-reloads, Python reloads, and neither needs a rebuild or a teardown.

It also seeds `admin@example.com` / `password` and grafts the example ui-Sprig™, so the instance is usable with no follow-up step. **That is why dev has its own volume, `sage-ai-dev-data`.** A user is only made an administrator when they are the *first* to sign up; every later one lands on `DEFAULT_USER_ROLE`, which is `pending`. Sharing the volume with `it_run` meant the seed quietly produced a pending account on any volume that had been used before, and the ui-Sprig graft was then refused. Reach a specific volume when you mean to: `DEV_VOLUME=sage-open-webui make dev`.

**The Vite dev proxy is an allowlist, and it is the one thing that can make a working page 404.** `vite.config.ts` forwards a fixed list of prefixes to the backend on 8080; anything not on it never leaves Vite. `/pages` was missing until 9 August 2026, so every no-build surface 404'd under `make dev` while working perfectly in the image. Add a backend route with a new top-level prefix and add it to the `BACKEND` array in that file — one line, and the comment there says the same.

Until 2 August 2026 it was missing one thing: `PAGES_RELOAD_DIRS`. The backend was already reloading, but the pages shell reads that variable to decide whether to serve the browser-refresh island, and `/pages/_dev/reload` is not registered without it — so a template edit reloaded the server and no open tab had any reason to ask for it. One environment variable, and the two dev modes stopped disagreeing.

`make review LIVE=1` is still the right tool for judging a page, because it boots the seeded review instance against the BAKED bundle with the walkthrough printed. The split is honest: `dev` is for building, `review` is for looking.

**`review LIVE=1` does NOT rebuild Svelte, and nothing warns you.** It mounts `sage_is_ai/pages/` and nothing else; the bundle is baked into the image at `/app/build`. Edit a Svelte file under `review LIVE=1` and you will be looking at whatever `it_build` last produced, silently. That only bites on surfaces the SPA still owns — `SetupDialog.svelte` is the live example — but it bites without a message.

Under `review LIVE=1` the pages package is mounted and watched, and **nothing needs a hand**:

- **Save a `.css` or `.js` under `pages/assets/`** and the stylesheet swaps in place. No reload, so the page keeps its scroll position and any open dialog. That matters more than it sounds: styling a wizard panel used to mean reopening the wizard after every save.
- **Save a `.py`** and the app restarts itself in about 2.8 seconds, then the tab reloads when it comes back.
- **Switching between `review LIVE=1` and `review`** takes about 7 seconds, because the data volume is kept and the admin is already seeded.

Open `/pages/` for an index of every server-rendered page. It carries a banner naming what is watched whenever the reloader is on.

One environment variable drives both halves, `PAGES_RELOAD_DIRS`, so the reloader and the thing that tells the browser about it cannot drift apart. It is off in production and `/admin/diagnostics` reports it as degraded whenever it is on.

**Two things about this are worth knowing rather than rediscovering.**

The Python half needs no file watcher. A uvicorn restart drops every open connection, and `EventSource` reconnects by itself, so the restart *is* the signal — a reconnect means the server went away and came back. Only assets need watching, because they are served from disk and restart nothing.

The gates deliberately have no live mode. `make e2e`, `e2e_both` and `wizard_smoke` always boot the baked image with nothing mounted, because a guard-rail run against a working tree tests something we do not ship. Do not add one.

## Design rules that produced the numbers

### Call the API handler, never round-trip your own API

The fragment view imports `routers/sprigs.graft_sprig` and calls it. An HTTP hop to ourselves would mean a second serialization, a second auth pass, and a copy of every error contract. It is also a safety property. The diagnostics re-probe route calls `probe_endpoint`, which refuses any URL not currently configured, so routing around it to save a few lines would route around the server-side request forgery (SSRF) defence.

### Native HTML before custom widgets, and before custom anything

`<details>` deleted the Svelte `Collapsible` and the 267-line how-to-fix modal outright. This one rule is most of the gap between the 32% cut and the 67% one.

It goes further than widgets. Reach for the element that already means what you need before you invent structure. A `<fieldset>` with a `<legend>` is a group of related controls with an accessible name. A `<p>` holding a `<label>` and a `<small>` is a form row with its caption and fine print. An `<output>` is a value derived from a form, and it carries a status role, so the branding preview announces itself after a save with no ARIA attribute written. That panel has no heading-plus-div scaffolding left in it.

### Startr.Style props, not a parallel stylesheet

Startr.Style IS more flexible and quick to edit... don't go reinventing the wheel. The framework is first-party. Use inline props on markup you author by hand, and keep `pages.css` for what the prop vocabulary cannot express. `@keyframes` is the real example (for now, and we can later add animation to Startr.Style), and the self-fading toast is the one class left on the branding surface.

The cost argument: A rule that appears on five generated fields is one string in the render module, so props cost about as many source lines as a class does and remove the need for a stylesheet entirely. Writing 99 lines of CSS for that surface put it at an 8% cut. Deleting them for props put it at 31%, and ended the argument about whether the stylesheet counted.

How far that generalizes is untested. Branding is seven fields with near-identical markup, which is the best case for one shared prop string. A surface with thirty structurally different rows might well pay more, and if you hit one, measure it rather than assuming this rule holds.

What it costs is already known: a surface styled with props cannot keep its layout when the CDN is unreachable, because the layout is the framework. `pages-cdn-outage.cy.ts` now asks each surface which promise it makes. The list surfaces still hold their grid from `pages.css`. Branding degrades to plain flow and only promises to stay usable.

### Data both sides need becomes JSON both sides read

`fixRegistry.json` and `commandLibrary.json` are imported by the Svelte component and read by the server. Transcribing 40 remediation steps into Python would have been a second copy to keep in step, which is the drift this migration exists to delete.

### Never make the browser carry what the server knows

The client posts a Sprig name to a path and nothing else. Not the capability, not the current state. The catalog is the authority on both. A value the browser cannot send is a value it cannot get wrong, and it is one fewer thing to validate.

### Swap the whole panel

A mutation returns the entire fragment and htmx replaces it. There is no client-side model to fall out of step with the server's, so the class of bug where the two disagree cannot occur. It costs a few hundred bytes per mutation. It also buys something nobody designed for: every swap is a new element, so a CSS animation on a message restarts by itself, with no script.

### Links swap themselves, and a page usually declares nothing

`shell.py` puts `data-swap="/pages/"` on `<main>` and appends `startr-swap.js` to every page, so links and forms inside `/pages/` swap in place instead of reloading. A new page inherits this and declares nothing.

Three cases need a word, and only three:

- **A region that updates on its own** — a results list under a pager — gets `data-swap` *and an `id`*. The id is not decoration: it is how the response names the piece coming back. `#prompts-results` is the worked example.
- **A control outside the region it updates** — a search form above its own results — names it with `data-swap-target="#that-id"`. Controls *inside* a region need nothing; the nearest region above a control is the one it updates.
- **A form whose endpoint answers with a fragment** gets `data-swap-off`. The swapper expects a document it can find a region in, and without the opt-out the fallback is a real navigation to a bare panel with no stylesheet — the bug `pages-action-response.cy.ts` exists for.

Everything still works with JavaScript off: the server emits no attribute the swapper needs, so a link is a link and a form is a full-page POST. That is why the routes above must keep answering with whole documents.

The library itself knows nothing about this application, because it is meant to be published for other projects. `make startr_swap_check` fails if a token from this repo appears in it.

### Sentences belong in the backend

The prune response returns `messages` rather than booleans, because the Svelte panel, the island and the fragment each carried their own copy of the same six strings. `post_graft_note` already worked this way.

### Escape everything interpolated

`pages/shell.py` escapes by default and takes markup in exactly one parameter. The ui-Sprig slot is the single place raw markup is rendered, and only because it passed a fail-closed validator to get there.

## What the gates do and do not prove

The parity gate is a coverage floor. Identical hooks do not mean identical behaviour, since a button that renders and does nothing carries the same `data-cy` as one that works. That is the bug it was built after. Behaviour stays each surface spec's job.

**A surface has three states, not two.** The registry used to be binary — registered means compared, removed means gone. Hollowing added a middle one.

| State | Implementations | Addresses | Parity |
| --- | --- | --- | --- |
| **Registered** | two | two | compared every run |
| **Hollowed** | one | two | **exempt** — a host spec replaces it |
| **Deleted** | one | one | entry removed, same commit as the deletion |

**The exemption is triggered by hollowing or deletion — a structural fact — never by "parity achieved", which is a judgement.** Parity reached once does not mean parity holds. The gate's value is catching what an author did not think to test *later*, when somebody edits the no-build page and quietly drops a control. Stopping the comparison the moment parity is reached would remove the guard exactly when editing starts.

A hollowed surface is different in kind: both addresses serve the same bytes, so comparison is a route judged against itself — the mirror that `surfaces.ts` warns about, whose failure is indistinguishable from success. What replaces it judges the host: that the fetch happened, that server-rendered markup arrived, that the marketplace slot came with it, and that a failure says so instead of showing an empty box. `home-hollow.cy.ts` is the worked example.

A green suite is the weakest evidence on an interactive surface. Phase S shipped an autoscroll that passed 13/13 under a real browser driver and was broken on a real trackpad. Phase 2 shipped a fix button that rendered and did nothing while every assertion passed. So every migrated surface gets a human pass before it takes over a route, and `make review` boots a seeded instance for exactly that. Use plain `make review`, not `LIVE=1`, for the pass that decides: a review of your working tree is not a review of the artifact you ship.

Be careful about the opposite mistake, though, because we made it on branding. The colour picker looked like a human-only control, since no driver can open an OS colour dialog. But that dialog is the browser's code. Ours is the handler underneath, and a synthetic `input` event reaches it exactly as a real one does, so both directions of the picker and its hex field are tested now. Before filing something as human-only, work out whether the part you care about is your code or the browser's.

## Still open

- Styling is decided and the split has moved. `startr.style` loads before `pages.css` so page rules still win, but props are the default now and `pages.css` is reserved for what props cannot express. The URL is unversioned by decision, with `/v1/` and SRI coming.
- Sprigs and diagnostics still use classes. They were built under the old split and their generated rows carry `.sprig-card` and `.diag-row`. Converting them is follow-up work rather than a rewrite, and it is worth doing for consistency rather than line count, since their CSS is already written and paid for.
- Templating is DONE. All twelve panels are Jinja2 as of 1 August 2026. The measurements that decided it, taken on one panel before the other eleven: a **template edit applies in 0.48 s with no app restart**, against **2.89 s and a restart** for the equivalent Python edit — because a template is data read from disk and Jinja's `auto_reload` re-reads it, while uvicorn's reloader watches `*.py` only. Across all twelve: **1,543 → 1,164 Python code lines (−379)**, plus 490 lines of template and a 16-line helper, so **+9% overall**. The 2026-07-28 measurement was right and still is: an engine RELOCATES markup rather than deleting it, and anyone arguing this on line count is arguing the wrong case. What it bought is the dev loop and **zero hand-written escape calls left in any panel** — escaping is structural now instead of remembered at every interpolation. Not one guard-rail spec was touched.

- The history, because the reasoning mattered more than the verdict: this entry said "no engine" on 28 July, on the measurement that markup is only 20–33% of each panel and an engine relocates rather than deletes it. That measurement was never wrong and still is not. What changed on 31 July is that the case stopped resting on line count — the dev loop and structural escaping are worth paying +9% for, and neither is something the original argument had weighed.

- `shell.py` stays an f-string, and that is a decision rather than an omission. Its markup does not change, so `auto_reload` buys nothing; and it interpolates three escaped values against four RAW ones, so a template would need four `| safe` markers — the escape hatch that undoes what autoescape is for. Revisit if that ratio flips or a second layout appears.

- Locale is solved. `pages/i18n.py` resolves a locale per request from `?lang=` or `Accept-Language`, the image ships all 56 catalogs, and every link and form carries the parameter onward. It travels in the URL rather than a cookie so each rendering stays cacheable on its own address — a cookie would force `Vary: Cookie`, and the auth cookie rides in the same header, so nothing would share. The keys *are* the English text, so an untranslated key renders as English rather than as a blank, which is what made it safe to apply at 67 call sites. `diagnostics_panel.py` is the one surface still English-only; it needs a locale threaded four signatures deep and is filed in TODO.md.
