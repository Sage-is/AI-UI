---
title: "Orientation"
description: "What this project is, how work is done here, and what to do first — for a new teammate or an agent."
date: 2026-08-03
tags:
  - orientation
  - onboarding
  - frontend
  - migration
---

# Orientation

Read this before touching anything. It is written for a person joining the work
and for an agent being pointed at it. Everything here is either measured or
sourced; where a number appears, the thing that produced it is named.

## 1. What the product is

**Sage.is AI** is an open-source AI platform, shipped AGPL-3.0. It began as a
fork of Open WebUI taken from its MIT-era code.

**Never merge or copy from current upstream Open WebUI.** Its licence changed and
the new terms are incompatible with what we ship. We keep tool and UX
compatibility by choice, not by pulling code. Do not cite "merge cost" as a
constraint on any design — there is no merge.

## 2. The project in flight

The frontend is being moved off the SvelteKit build onto **server-rendered pages
under `/pages/`**, one surface at a time, by the strangler pattern. The plan is
approved and has three legs: cut duplication, cut what a page costs to load, and
make pages shareable without a build step.

The end state is that the SvelteKit surface shrinks to nothing, or to "biomes" —
places like the chat core where a rich client genuinely earns itself.

### Where it stands

Five surfaces are built and measured. **None has been flipped**: the SvelteKit
routes are still what users reach. The setup wizard is the exception — its Svelte
was deleted outright.

| surface | SvelteKit | server-rendered | requests | to first row |
| --- | --- | --- | --- | --- |
| branding | 7,413 kB | **71 kB** | 132 → 6 | 1,665 → 36 ms |
| sprigs | 6,625 kB | **76 kB** | 122 → 6 | 1,548 → 34 ms |
| diagnostics | 6,674 kB | **98 kB** | 122 → 5 | 1,658 → 36 ms |
| agents | 8,233 kB | **350 kB** | 127 → 11 | 1,864 → 47 ms |
| prompts | measured, built, styled | — | — | — |

Line counts, code only: agents **1,332 → 345**, prompts **663 → 327**.

### The finding that should shape your priorities

Most of that SvelteKit column is not the surface. **A route with no data of its
own costs 6,641 kB decoded** — that is the floor every SvelteKit route pays
before rendering anything. Measured against it, each surface's own content adds:

```
prompts +121 kB · functions +206 · users +296 · knowledge +455
evaluations +1,269 · agents +1,714 · chat +5,170
```

So for six of eight routes, the list the page exists to show is **2–6% of what
opening it costs**. Ordering the migration by list size orders it by noise. Rank
by lines deleted and by how often a route is opened.

**The single largest item is not a route.** `/api/models` is 2,304 kB, fetched on
every route in the product, and never cached — **95% of the wire cost of any warm
page load**. Someone opening `/admin/functions` to look at one function downloads
2.3 MB of model metadata. It needs its own plan; it changes SPA code the
strangler intends to delete.

## 3. How work is done here

**Measure twice, build server-side, measure again.** Not a slogan — it is the
convention's steps 0 and 9, and it exists because reasoning has lost to
measurement repeatedly on this project.

Two different before-measurements, because they disagree:

1. **the data** — query `tools/db_snapshots/*` for what the surface holds;
2. **the document** — boot that snapshot and load the page in a browser.

The data query once said the workshop list cost ~1.5 MB. The browser said
9,174 kB. Acting on the first alone would have shipped a fix for the wrong thing.

**And never one sample.** The ledger takes three of everything and reports median
with spread. Decoded bytes repeat to within 0.1 kB; times have swung 2× on the
same route in the same run. **A delta smaller than the spread is not a result.**
That is why the budget gate judges bytes and never times.

The full order of work is `docs/no-build-surface-convention.md`. Do not skip
step 2 — hooking every control on the legacy surface *before* any code moves is
what makes the parity gate meaningful, and it is the step that gets skipped.

## 4. The failure mode this codebase keeps finding

Read this section twice. Nearly every real defect found here was **invisible to a
green suite**, and they are all the same shape: *a check whose failure is
indistinguishable from success.*

A catalogue, all real:

- A "Show me how to fix this" button that rendered and did nothing. Every
  assertion passed.
- An autoscroll that passed 13/13 under a real browser driver and was broken on
  a trackpad.
- `--list-style` — not a prop the framework reads. It fails silently.
- `curl … | grep -q` under `pipefail`: a **match** reports as a failure.
- A `unicode-range` guard asserting "en-US does not fetch the Persian face" that
  passed whether or not the change was present.
- A payload timing measured with `Date.now()` in a Cypress test body — stamped
  when commands are *queued*, so it silently included the app's whole boot.
- Row actions returning a bare fragment with no `<head>`: every action dropped
  the reader onto an unstyled page. The guard-rail asserted server state (true),
  parity counted hooks (all present), the ledger measured the GET.
- Trailing slashes returning the app shell **with a 200**.

**Under `/pages/`, a status code proves nothing.** `SPAStaticFiles` is mounted at
`/` with `html=True`, so nothing there can 404 — the shell answers anything
unmatched. Every gate that needs to know "did a real page come back?" reads
`[data-cy="page-heading"]`, which `shell.py` puts on every server-rendered page.

**The rule that follows: prove every new gate can fail before you trust it.**
Plant the defect, watch it go red, read the message, revert. A gate whose failure
has never been seen is decoration. This has caught bad gates repeatedly —
including one where the minifier rewrote `U+0600-06FF` as `U+6??` and the check
went red against correct code.

## 5. Settled conventions

- **Plain HTML first.** Every new page ships unstyled for review before any
  styling. Structure is what a review can judge; paint on a wrong structure hides
  the wrongness. Then style — either lift what the Svelte page has, or use
  startr.style props. Never invent a third visual language.
- **Props, not a stylesheet.** The workshop surfaces add **zero lines** to
  `pages.css`. Branding is the cautionary tale: 99 hand-written CSS lines went in
  before anyone asked, and deleting them took the cut from 8% to 31%.
- **One style vocabulary.** `pages/templates/_workshop.html`, imported. Five
  surfaces each holding their own `18rem` drift apart one reasonable tweak at a
  time.
- **Prune, don't port.** Carry what the page renders. `ModelUserResponse` and
  `PromptUserResponse` nest the owner's whole record including a base64 avatar,
  and the row shows a name as text — on prompts that is 115 kB of a 121 kB
  surface. A faithful port ships the waste with better line counts.
- **Registering a surface in `cypress/support/surfaces.ts` is step one.** It
  enrols the surface in the parity gate, the payload ledger and the budget gate
  at once. There is no second list to keep in step.
- **startr.style is first-party** (`~/Documents/Projects/GitHub/WEB-Startr.Style/`).
  When a footgun bites, name both the consumer workaround and the upstream fix.
  Never edit that repo silently — surface the trade-off and ask.

## 6. The gates, and what each proves

| gate | proves |
| --- | --- |
| `make e2e_both` | the suite passes against **both** implementations of every registered surface |
| `surface-parity.cy.ts` | the no-build page renders every `data-cy` the SvelteKit page offers. It never reads your spec, so a narrower spec cannot satisfy it |
| `make surface_budget` | a migrated surface weighs **less** than the one it replaces, by more than the spread, and the app-wide floor has not grown |
| `pages-action-response.cy.ts` | a row action answers with a document, not a bare fragment |
| `pages-trailing-slash.cy.ts` | every `/pages/` route answers with or without a trailing slash — asserted on content, never status |
| `font-unicode-range.cy.ts` | the Persian face reaches Persian readers and nobody else |
| `make docs_gate` | no doc names a `make` target that does not exist |
| `make gauntlet_full` | everything a robot would do on this machine |

## 7. Hard constraints

- **All git writes are Alexander's.** Never run `git add`, `commit`, `push`, or
  any staging command. Prepare the work and stop.
- **App dependencies are built and installed only inside Docker.** Never
  `pip install` or `npm install` on the host.
- **`/opt/homebrew` is write-locked on purpose.** Ask for brew installs; prefer a
  containerised tool.
- **Check hardlink counts before editing a Makefile** (`stat -f "%l %N"`). If
  greater than one, use `sed -i` — Edit and Write break the inode.
- **Wiring changes need a rebuild.** `LIVE=1` mounts `sage_is_ai/pages/`, so
  templates and panels are live; `main.py` is outside that mount.

## 8. Where things are

```
app/backend/sage_is_ai/pages/          the server-rendered surfaces
  router.py                            every /pages/ route, and the _PAGES table
  shell.py                             the page shell; carries page-heading
  auth.py                              cookie identity; guards are DEPENDENCIES
  agents_panel.py                      the fullest worked example — read this first
  templates/_workshop.html             the shared style vocabulary
  slashes.py                           trailing-slash canonicalisation
app/cypress/support/surfaces.ts        the surface registry — step one of any migration
app/cypress/e2e/upgrade/route-payload.cy.ts   the payload ledger (measurement, not a gate)
scripts/gates/                         gates that need a container
docs/no-build-surface-convention.md    the order of work, steps 0 through 9
TODO.md                                the board; every finding lands here
```

`agents_panel.py` is the template for a new surface, not merely a reference: the
`Literal` verb table cross-checked by `_check_verbs()`, the guard as a FastAPI
dependency, the `_url()` builder that keeps every filter in the query string.

## 9. Start here

```bash
make help                 # the curated command list
make review_live          # a Rootstock for a human, pages mounted and watched
make e2e_both             # the suite against both implementations
make surface_budget       # bytes: does the migration actually pay?
KEEP=1 make upgrade_gate  # boot a production snapshot copy, leave it up
```

Snapshots in `tools/db_snapshots/` are **read-only**; every gate copies them
before touching one. Check size and mtime after any run that used them.

## 10. Open threads

- **Nothing is flipped.** Four surfaces are built, measured and gated, and none
  is in front of a user. `/workshop/models` → `/workshop/agents` with a redirect
  is the obvious first.
- **`/api/models`** — the largest single win in the product, needs its own plan.
- **A prompt stored without a leading slash can never be fetched, edited or
  deleted**, and the UI's import path strips the slash. Every imported prompt is
  undeletable and nothing reports it. Fix at the write point, not the three read
  points.
- **htmx is 49.7 kB and 51–70% of each panel that loads it**, for three
  attributes a 956-byte iframe covers. Whether to retire it is open.
- **Where the swap enhancer lives** is undecided; the prototype is an inline
  `<script>` that cannot ship under a Content-Security-Policy.
- **How often each route is opened** is the one input nobody has. There is no
  telemetry. It is a judgement call, and it is the input most likely to reorder
  the work.
