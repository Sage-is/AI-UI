# Treeshake — Chart

Scoped chart for the dependency-pruning effort. Lives beside `package.json`
because that is the artifact it changes. The repo roadmap is `../TODO.md`; this
file is boarded separately by TodoScope and nothing here belongs on that board
until it ships.

> **Convention** — Sections map to kanban columns. Cards are `- [ ]` items with
> a bold name and a type hashtag. Refer to a card by its NAME, never a number.
> `KANBAN.canvas` auto-generates — do not hand-edit it.

## Destination

The 84 runtime dependencies are cut to those that reach a live code path, and
the cut is recorded as numbers, with no surface behaving differently afterwards.

**Revised 2026-08-03, first day, on the image research.** The original wording
promised image size. That is void: the runtime image carries no `node_modules`
at all, only the compiled bundle. The measures that remain real are dependency
count, `node_modules` size, builder install time, the `dev-svelte` sprig
artifact (297 MB compressed as published, which must be built, signed, pushed
and pulled), and `/app/build` bytes where a removal was genuinely imported.
Image size belongs to the 267 MB Python layer and is a different effort.
Baseline for all of these is recorded in the
[baseline record](../docs/decisions/2026-08-03-treeshake-baseline.md).

## Notes

**Domain.** `app/package.json`, the Vite/SvelteKit build, and the Docker image
that consumes both. Frontend only.

**The finding that shapes every card.** A scan for import statements across
`app/src/**/*.{svelte,ts,js}` says 21 of 84 runtime dependencies are never
imported. That is a list of QUESTIONS, not a delete list. **Proven by the first
card resolved:** both CodeMirror language packages came back REQUIRED — loaded
by a dynamic `import()` inside another dependency, where grep cannot reach.

**So the standing test before any removal is:**

```bash
grep -l '"<pkg>"' app/node_modules/*/package.json app/node_modules/@*/*/package.json
```

A package another installed package imports is alive, however dead it looks
from `src/`. Registries, dynamic imports, Vite/PostCSS/Tailwind config and
string-keyed loaders all hide call sites this way.

**Constraints, set 2026-08-03 (Alexander).** (1) Must not stall the no-build
strangler, which is mid Phases 3–4 — anything belonging to a surface the
migration will rewrite is out of scope, not fog. (2) Nothing that risks the
Realtor R demo on try.sage.is; removals are provably safe or they wait. (3)
Every card ends in a number that moved, not an impression of tidiness.

**Skills worth loading:** `muda` for the waste taxonomy, `poka-yoke` if a card
turns into a gate.

**Decision records** live in `../docs/decisions/`, named
`YYYY-MM-DD-treeshake-<slug>.md`.

## In Progress

<!-- claimed cards only: exactly what a session is resolving right now -->

All four research cards were fired together on 2026-08-03 by the charting
session — research is the one type a chart may resolve while drawing itself.

_Empty. All four research cards resolved 2026-08-03; the frontier is in TODO._

## TODO

- [ ] **The five proven removals**: `prosemirror-example-setup`, `async`,
  `@pyscript/core`, `@tiptap/extension-drag-handle`,
  `@tiptap/extension-youtube`. #task
  Every one is evidenced in a decision record: no import, no dependent, no
  registry or peer path. `@pyscript/core` is the only one carrying real weight.
  **Unblocked 2026-08-03** — the baseline is recorded. Afterwards re-run
  `bun install` and diff `bun.lock`: the prosemirror record flags that dropping
  entries relaxes version floors for `prosemirror-tables` and `-schema-list`.
  Watch `/app/build`: it should NOT move. If it does, the package was imported
  after all and the removal was wrong.

- [ ] **The declaration-only tidy — worth it or not?**: seven redundant-transitive
  `prosemirror-*` entries, plus `@floating-ui/dom` and `@tiptap/extension-link`.
  #interview
  Nine manifest lines, zero install bytes, and a real cost: each line pins a
  version floor the app would otherwise inherit from its parent package. A
  judgement about what the manifest is FOR, not a measurement — which is why it
  is not folded into [The five proven removals].

- [ ] **Duplicated capability — which one stays**: `jspdf` against
  `pdfjs-dist`; two emoji pickers; `marked` now that the server renders
  markdown for the no-build pages. #interview
  A choice about what the product keeps, not a fact to be discovered.

## Backlog

<!-- the fog: in-scope, not yet sharp enough to card -->

- Whether a check can keep a removed dependency from coming back, and whether
  that check belongs to this effort or to the pre-commit hooks. Sharpened by
  the research: any such check must survive the CodeMirror lesson, so a naive
  `depcheck` run would report required packages as dead and be worse than
  nothing.
- `y-protocols` will surface as a zero-import straggler in every future scan
  and is answered. Whether the answer belongs somewhere a future scan can read
  it — a comment in `package.json` is impossible, so perhaps a scan script with
  a known-good list — is not yet sharp.
- The 27 `devDependencies` are unexamined — the same scan has not been run on
  them, and their blast radius is different.
- Version-range hygiene: every entry is a caret range. Whether pinning belongs
  here at all is undecided.
- Duplicate transitive copies in the lockfile, which pruning may or may not
  collapse.
- Licence exposure: whether any dependency sits awkwardly with AGPL-3.0
  distribution. Suspected in scope, not yet phrased sharply.

## Out of scope

<!-- ruled beyond the destination. Never graduates. -->

- **The heavy biomes as a category** — `@xyflow/svelte`, the `@tiptap/*` set,
  `yjs`, `codemirror`, `pyodide`, `mermaid`, `katex`, `pdfjs-dist`. They belong
  to surfaces the strangler will rewrite or delete, so touching them here would
  compete with the migration (constraint 1). Counting and pinning them as a
  downward-only ratchet is already on the repo roadmap.
- **Deleting dead Svelte components and routes** — the strangler's own work,
  and scouting found only 2 files with no importer, so there is little here
  anyway.
- **Backend Python dependencies** — different toolchain, different gate, and
  `requirements.txt` has its own CVE-driven review cadence.
- **Shipping less to the browser** — the bundle-size destination was considered
  and not chosen. It is a sibling effort, not a step on this route.
- **Moving build tools from `dependencies` to `devDependencies`** —
  `@sveltejs/adapter-node`, `vite-plugin-static-copy` and `undici` (which the
  pyodide prefetch script needs at build time) are filed in the wrong list, and
  it does not matter: the build installs both lists in full and the
  runtime image carries neither. Zero bytes move, so the card cannot produce
  the number constraint 3 demands. Ruled out 2026-08-03 on the image research,
  not resolved. Manifest hygiene if anyone wants it, filed as such, never under
  a size or supply-chain heading.
- **Image size** — the original destination named it; the runtime image carries
  no `node_modules`, so no dependency change can move it. The 267 MB Python
  `site-packages` layer is where that work lives, and it is a different effort
  with a different toolchain.

## Done

<!-- one line per resolved card: gist plus link to its record -->

- [x] **The baseline nobody has taken**: recorded before any removal — 84 runtime
  plus 27 dev dependencies, `bun.lock` 2,463 lines, `node_modules` 1.0 GB across
  688 top-level entries, `/app/build` 29.6 MB in 476 files, `/app/static`
  11.2 MB, the `dev-svelte` sprig artifact 297 MB compressed, image 622 MB. The
  method is written down so the "after" compares; builder install time was
  deliberately NOT taken, because a warm run measures the cache —
  [decision](../docs/decisions/2026-08-03-treeshake-baseline.md)

- [x] **The stragglers**: four removable with no runtime effect — `async`,
  `@pyscript/core` (the only one carrying real weight, ~100 KB),
  `@tiptap/extension-drag-handle`, `@tiptap/extension-youtube`. `undici` is USED
  by the pyodide prefetch script that gates every build; `y-protocols` is a
  build-time peer of `y-prosemirror` that ships no bytes; `@tiptap/extension-link`
  arrives inside StarterKit and is live in the notes editor; `@floating-ui/dom`
  is declaration-only —
  [decision](../docs/decisions/2026-08-03-treeshake-stragglers.md)

- [x] **What the image actually installs**: only the built bundle — no
  `node_modules`, no node/npm/bun in the runtime image; `bun install` lives and
  dies in the builder stage, and devDependencies install in full. **Image size
  is off the table**; the payoff is builder time, CI cache, the ~1.0 GB
  `dev-svelte` sprig, and local installs —
  [decision](../docs/decisions/2026-08-03-treeshake-image-node-modules.md)

- [x] **The prosemirror cluster**: `@tiptap/pm` REQUIRED (peer dependency of
  `@tiptap/core` and twelve extensions); seven of eight `prosemirror-*` entries
  redundant-transitive via `@tiptap/pm@3.0.7`; **`prosemirror-example-setup` is
  the only true residue** and the only removal that shrinks the install. Do not
  touch `-model`/`-state`/`-view`/`-keymap`, imported directly by
  `RichTextInput` —
  [decision](../docs/decisions/2026-08-03-treeshake-prosemirror-cluster.md)

- [x] **The two unimported CodeMirror languages**: both REQUIRED — `language-data`
  loads them by dynamic `import()` from inside `node_modules`, so grep cannot see
  the call site; removing them breaks JS/TS/JSX/TSX and Python highlighting. The
  `package.json` lines are transitively redundant but worth zero bytes, so they
  stay — [decision](../docs/decisions/2026-08-03-treeshake-codemirror-languages.md)
