# Migrating a surface to no-build

How we move an admin surface off SvelteKit onto server-rendered fragments.
Every rule below is here because it paid for itself on a real surface, and the
evidence is named so you can argue with it.

Two surfaces have gone through this: Sprigs (231 → 157 lines, 32%) and
Diagnostics (813 → 273, 67%). The difference between those two numbers is most
of what this document is about.

## The order of work

The order matters more than any individual step. Three of the four devices
below exist because doing this out of order cost us something.

**1. Register the surface** in `app/cypress/support/surfaces.ts`, mapping its
name to the legacy path and the no-build path. Do this before any code moves.
It is a one-line change whose real job is forcing the next step.

**2. Hook every interactive control on the LEGACY surface** with `data-cy`.
Buttons, disclosures, list rows, empty states, error states. This is the step
that gets skipped, and skipping it is how a migration ends up 40% done with a
green suite. You are enumerating what the old page can do while the old page is
still the only page.

**3. Write the guard-rail spec against the legacy surface and prove it green.**
Read data attributes, never translated words or class names — `data-status`
rather than the badge's text, `data-section="boot_status"` rather than the
heading "Boot status". That is what lets one spec judge two implementations.

**4. Build the fragment.** The design rules below are where the line count
comes from.

**5. Let the parity gate find what you missed.** `surface-parity.cy.ts` visits
both implementations, collects the `data-cy` hooks each one renders, and fails
naming the ones the no-build page does not. It never reads your spec, so it
cannot be satisfied by writing a narrower one. On diagnostics it went red with
`diag-command-library, diag-ghost-endpoints, diag-reprobe, diag-technical` —
four controls a human had already found broken by clicking.

**6. `make e2e_both`.** Runs the suite once per target. "Green against both" is
the migration's core rule, and running it twice by hand is how that rule
quietly becomes "green against whichever one was checked last".

**7. Measure, and report the number you actually got.** The first Sprigs
fragment was 208 lines and only reached 157 after someone asked whether it
could be cleaner. A first draft is not a measurement.

## Design rules that produced the numbers

**Call the API handler; never round-trip your own API.** The fragment view
imports `routers/sprigs.graft_sprig` and calls it. An HTTP hop to ourselves
would mean a second serialization, a second auth pass, and a copy of every
error contract. This is also a safety property: the diagnostics re-probe route
calls `probe_endpoint`, which refuses any URL not currently configured, so
routing around it to save a few lines would route around the SSRF defence.

**Native HTML before custom widgets.** `<details>` deleted the Svelte
`Collapsible` and the 267-line how-to-fix modal outright. This single rule is
most of the gap between the 32% cut and the 67% one.

**Data both sides need becomes JSON both sides read.** `fixRegistry.json` and
`commandLibrary.json` are imported by the Svelte component and read by the
server. Transcribing 40 remediation steps into Python would have been a second
copy to keep in step — the drift this migration exists to delete.

**Never make the browser carry what the server knows.** The client posts a
Sprig name to a path and nothing else: not the capability, not the current
state, not the deployment shape. A value the browser cannot send is a value it
cannot get wrong, and it is one fewer thing to validate.

**Swap the whole panel.** A mutation returns the entire fragment and htmx
replaces it. There is no client-side model to fall out of step with the
server's, so the class of bug where the two disagree cannot occur. It costs a
few hundred bytes per mutation.

**Sentences belong in the backend.** The prune response returns `messages`,
not just booleans, because the Svelte panel, the island and the fragment each
had their own copy of the same six strings. `post_graft_note` already worked
this way.

**Escape everything interpolated.** `pages/shell.py` escapes by default and
takes markup in exactly one parameter. The ui-Sprig slot is the single place
raw markup is rendered, and only because it passed a fail-closed validator to
get there.

## What the gates do and do not prove

The parity gate is a coverage **floor**. Identical hooks are not equivalent
behaviour — a button that renders and does nothing has the same `data-cy` as
one that works, which is exactly the bug it was built after. Behaviour is each
surface spec's job.

And a green suite is the weakest evidence on an interactive surface. Phase S
shipped an autoscroll that passed 13/13 under a real browser driver and was
broken on a real trackpad; Phase 2 shipped a fix button that rendered and did
nothing while every assertion passed. **Every migrated surface gets a human
pass before it takes over a route.** `scripts/manual-check.sh` boots a seeded
instance with both implementations live for exactly this.

## Still open

- **Styling.** These pages use plain CSS (`pages/assets/pages.css`). Tailwind
  belongs to the SPA and needs the compiler we are removing. `startr.style` is
  the obvious candidate and is first-party, but adopting it mid-pilot would have
  tangled the migration's result with a second decision. Now that the pilot has
  numbers, that decision is ripe.
- **Templating.** Roughly half the remaining Python is hand-built HTML strings,
  which is what a template engine deletes and nothing else will. Worth deciding
  against three call sites rather than one.
- **Locale.** Server-rendered pages read `en-US` only, because the reader's
  language lives in `localStorage` where no server can see it. This has to be
  solved before any migrated page takes over a real route.
