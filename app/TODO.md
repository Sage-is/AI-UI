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
the cut is recorded as numbers — dependency count, install size, image size,
bundle bytes — with no surface behaving differently afterwards.

## Notes

**Domain.** `app/package.json`, the Vite/SvelteKit build, and the Docker image
that consumes both. Frontend only.

**The finding that shapes every card.** A scan for import statements across
`app/src/**/*.{svelte,ts,js}` says 21 of 84 runtime dependencies are never
imported. That is a list of QUESTIONS, not a delete list: `@tiptap/pm` is
tiptap's peer requirement, `@codemirror/language-data` may load language
packages at runtime, and two entries are build tools filed in the wrong
section. Each cluster is its own decision.

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

- [ ] **What the image actually installs**: does the runtime image carry
  `node_modules`, or only the built bundle? (Sage.is AI) #research
  The answer decides what this whole effort can claim. If the image ships only
  the compiled output, pruning moves build time and bundle bytes but not image
  size, and several cards below shrink to cosmetics.

- [ ] **The prosemirror cluster**: eight `prosemirror-*` packages plus
  `@tiptap/pm` are declared and never imported. (Sage.is AI) #research
  Peer requirement of tiptap 3, or residue of the editor that came before it?
  Nine of the twenty-one unimported entries sit here, so this is the largest
  single answer available.

- [ ] **The two unimported CodeMirror languages**: `@codemirror/lang-javascript`
  and `@codemirror/lang-python` have no import, while `lang-data` and four other
  CodeMirror packages do. (Sage.is AI) #research
  `@codemirror/language-data` loads languages dynamically, which would make
  these required and invisible to a grep. Prove which, because guessing wrong
  breaks syntax highlighting in the code editor.

- [ ] **The stragglers**: `async`, `undici`, `@pyscript/core`,
  `@floating-ui/dom`, `y-protocols`, and three unimported `@tiptap/extension-*`
  entries. (Sage.is AI) #research
  One pass, one verdict each: reaches a live path, or does not.

## TODO

- [ ] **The baseline nobody has taken**: record dependency count, `node_modules`
  size, image size and cold-load bundle bytes BEFORE anything is removed. #task
  Constraint 3 is unmeetable without it, and it cannot be reconstructed after
  the fact.

- [ ] **Build tools filed as runtime dependencies**: `@sveltejs/adapter-node`
  and `vite-plugin-static-copy` are build-time and sit in `dependencies`. #task
  Blocked by [What the image actually installs].

- [ ] **Duplicated capability — which one stays**: `jspdf` against
  `pdfjs-dist`; two emoji pickers; `marked` now that the server renders
  markdown for the no-build pages. #interview
  A choice about what the product keeps, not a fact to be discovered.

## Backlog

<!-- the fog: in-scope, not yet sharp enough to card -->

- Whether a check can keep a removed dependency from coming back, and whether
  that check belongs to this effort or to the pre-commit hooks.
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

## Done

<!-- one line per resolved card: gist plus link to its record -->
