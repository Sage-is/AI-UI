# Migrating a surface to no-build

How we move an admin surface off SvelteKit onto server-rendered fragments. Every rule here earned its place on a real surface, and the evidence is named so you can argue with it.

Three surfaces have been through it: Sprigs (231 to 157 lines, 32%), diagnostics (813 to 273, 67%), and theme and branding (288 to 200, 31%). The spread between those numbers is most of what this document is about.

## The order of work

Order matters more than any single step. Most of what follows exists because someone did it backwards once and paid for it.

**1. Register the surface** in `app/cypress/support/surfaces.ts`, mapping its name to the legacy path and the no-build path. Do this before any code moves. It is a one-line change whose real job is forcing step 2.

**2. Hook every interactive control on the LEGACY surface** with `data-cy`. Buttons, disclosures, list rows, empty states, error states. This is the step that gets skipped, and skipping it is how a migration ends up 40% done with a green suite. You are writing down what the old page can do while the old page is still the only page.

Someone will ask why a dedicated attribute when the element already has an `id`. Five branding fields already had one. The hooks are not there so Cypress can find things, because `cy.get('#title')` works fine. They are there because the parity gate needs a curated set of what must exist in both implementations. Point it at `[id]` and it sweeps up framework-generated ids and layout ids on the single-page-app side, then reports gaps that are not gaps. There is a second reason: an `id` is load-bearing for the page itself, since `<label for>`, CSS and JS all read it. Pin a test to one and either a rename breaks the suite or the suite blocks a rename. A test attribute is inert, and that is what makes it a stable contract.

Output does not earn a hook. Preview text, computed labels, rendered values. The contract is controls. A spec can assert output through its container, so `[data-cy="branding-preview"]` containing the expected text covers the preview without a hook on every line inside it. Hooking output pads the parity set with things whose absence is not a missing capability.

**3. Write the guard-rail spec against the legacy surface and prove it green.** Read data attributes, never translated words or class names. Use `data-status` rather than the badge's text, `data-section="boot_status"` rather than the heading "Boot status". That is what lets one spec judge two implementations.

**4. Build the fragment.** The design rules below are where the line count comes from.

**5. Let the parity gate find what you missed.** `surface-parity.cy.ts` visits both implementations, collects the `data-cy` hooks each one renders, and fails naming the ones the no-build page does not. It never reads your spec, so a narrower spec cannot satisfy it. On diagnostics it went red with `diag-command-library, diag-ghost-endpoints, diag-reprobe, diag-technical`, four controls a human had already found broken by clicking.

**6. Run `make e2e_both`.** It runs the suite once per target. "Green against both" is the migration's core rule, and running it twice by hand is how that rule quietly becomes "green against whichever one was checked last".

**7. Measure, and report the number you actually got.** The first Sprigs fragment was 208 lines and only reached 157 after someone asked whether it could be cleaner. A first draft is not a measurement.

## The dev loop

Never run `make it_build` to look at something. These pages have no build step, and until 31 July 2026 that promise stopped at the container wall — every one-line style tweak meant rebuilding a 619 MB image. It does not any more.

| you want to | run |
| --- | --- |
| change a page and watch it | `make review_live` |
| judge whether it ships | `make review` |
| change anything Svelte | `make review_rebuild` |

Under `review_live` the pages package is mounted and watched, and **nothing needs a hand**:

- **Save a `.css` or `.js` under `pages/assets/`** and the stylesheet swaps in place. No reload, so the page keeps its scroll position and any open dialog. That matters more than it sounds: styling a wizard panel used to mean reopening the wizard after every save.
- **Save a `.py`** and the app restarts itself in about 2.8 seconds, then the tab reloads when it comes back.
- **Switching between `review_live` and `review`** takes about 7 seconds, because the data volume is kept and the admin is already seeded.

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

### Sentences belong in the backend

The prune response returns `messages` rather than booleans, because the Svelte panel, the island and the fragment each carried their own copy of the same six strings. `post_graft_note` already worked this way.

### Escape everything interpolated

`pages/shell.py` escapes by default and takes markup in exactly one parameter. The ui-Sprig slot is the single place raw markup is rendered, and only because it passed a fail-closed validator to get there.

## What the gates do and do not prove

The parity gate is a coverage floor. Identical hooks do not mean identical behaviour, since a button that renders and does nothing carries the same `data-cy` as one that works. That is the bug it was built after. Behaviour stays each surface spec's job.

A green suite is the weakest evidence on an interactive surface. Phase S shipped an autoscroll that passed 13/13 under a real browser driver and was broken on a real trackpad. Phase 2 shipped a fix button that rendered and did nothing while every assertion passed. So every migrated surface gets a human pass before it takes over a route, and `make review` boots a seeded instance for exactly that. Use `make review`, not `review_live`, for the pass that decides: a review of your working tree is not a review of the artifact you ship.

Be careful about the opposite mistake, though, because we made it on branding. The colour picker looked like a human-only control, since no driver can open an OS colour dialog. But that dialog is the browser's code. Ours is the handler underneath, and a synthetic `input` event reaches it exactly as a real one does, so both directions of the picker and its hex field are tested now. Before filing something as human-only, work out whether the part you care about is your code or the browser's.

## Still open

- Styling is decided and the split has moved. `startr.style` loads before `pages.css` so page rules still win, but props are the default now and `pages.css` is reserved for what props cannot express. The URL is unversioned by decision, with `/v1/` and SRI coming.
- Sprigs and diagnostics still use classes. They were built under the old split and their generated rows carry `.sprig-card` and `.diag-row`. Converting them is follow-up work rather than a rewrite, and it is worth doing for consistency rather than line count, since their CSS is already written and paid for.
- Templating is DONE. All twelve panels are Jinja2 as of 1 August 2026. The measurements that decided it, taken on one panel before the other eleven: a **template edit applies in 0.48 s with no app restart**, against **2.89 s and a restart** for the equivalent Python edit — because a template is data read from disk and Jinja's `auto_reload` re-reads it, while uvicorn's reloader watches `*.py` only. Across all twelve: **1,543 → 1,164 Python code lines (−379)**, plus 490 lines of template and a 16-line helper, so **+9% overall**. The 2026-07-28 measurement was right and still is: an engine RELOCATES markup rather than deleting it, and anyone arguing this on line count is arguing the wrong case. What it bought is the dev loop and **zero hand-written escape calls left in any panel** — escaping is structural now instead of remembered at every interpolation. Not one guard-rail spec was touched.

- The history, because the reasoning mattered more than the verdict: this entry said "no engine" on 28 July, on the measurement that markup is only 20–33% of each panel and an engine relocates rather than deletes it. That measurement was never wrong and still is not. What changed on 31 July is that the case stopped resting on line count — the dev loop and structural escaping are worth paying +9% for, and neither is something the original argument had weighed.

- `shell.py` stays an f-string, and that is a decision rather than an omission. Its markup does not change, so `auto_reload` buys nothing; and it interpolates three escaped values against four RAW ones, so a template would need four `| safe` markers — the escape hatch that undoes what autoescape is for. Revisit if that ratio flips or a second layout appears.


- Locale is solved. `pages/i18n.py` resolves a locale per request from `?lang=` or `Accept-Language`, the image ships all 56 catalogs, and every link and form carries the parameter onward. It travels in the URL rather than a cookie so each rendering stays cacheable on its own address — a cookie would force `Vary: Cookie`, and the auth cookie rides in the same header, so nothing would share. The keys *are* the English text, so an untranslated key renders as English rather than as a blank, which is what made it safe to apply at 67 call sites. `diagnostics_panel.py` is the one surface still English-only; it needs a locale threaded four signatures deep and is filed in TODO.md.
