# Decision record: the straggler dependencies

**Date:** 2026-08-03 · **Card:** The stragglers · **Type:** research · **Chart:** `app/TODO.md`

## Answer

Three of the eight reach a live path. Four are removable. One is a declaration-only cleanup.

`undici` runs in the build. `y-protocols` is resolved by the yjs editor at build time. `@tiptap/extension-link` ships inside StarterKit and is instantiated by the notes editor. `async`, `@pyscript/core`, `@tiptap/extension-drag-handle` and `@tiptap/extension-youtube` reach nothing. `@floating-ui/dom` reaches a live path only through packages that already declare it, so deleting the top-level entry frees zero bytes.

`.svelte-kit/output` is dated 2026-03-18 and predates the tiptap 3.x dependency set. It was not used as evidence.

## Per-package verdict

| Package | Verdict | Mechanism | Evidence |
|---|---|---|---|
| `undici` ^7.28.0 | USED-VIA-BUILD-SCRIPT | Imported by the pyodide prefetch script that gates `dev` and `build` | `app/scripts/prepare-pyodide.js:19`; `app/package.json:22` |
| `y-protocols` ^1.0.6 | USED-VIA-PEER-DEP | Peer of `y-prosemirror`; its ESM source imports `y-protocols/awareness` | `app/node_modules/y-prosemirror/src/plugins/cursor-plugin.js:4`; `app/bun.lock:2085` |
| `@tiptap/extension-link` ^3.0.7 | USED-VIA-TRANSITIVE | Hard dependency of `@tiptap/starter-kit`, instantiated when `link` is true | `@tiptap/starter-kit/dist/index.js:12,69-71`; `NoteEditor.svelte:1153` |
| `@floating-ui/dom` ^1.7.2 | REMOVABLE (declaration only) | Live via `bits-ui` → `@melt-ui/svelte`, which declares it itself | `app/bun.lock:423`; `bits-ui/package.json` |
| `async` ^3.2.5 | REMOVABLE | No module specifier anywhere; only `getos` needs it and declares it | `app/bun.lock:1249`, `:987` |
| `@pyscript/core` ^0.4.32 | REMOVABLE | Zero references repo-wide; the interpreter uses `pyodide` directly | `app/src/lib/workers/pyodide.worker.ts:1,22`; `app/bun.lock:461` |
| `@tiptap/extension-drag-handle` ^3.0.7 | REMOVABLE | No import, no dependents, and three of its five peers are not installed | `app/bun.lock:595` |
| `@tiptap/extension-youtube` ^3.0.7 | REMOVABLE | No import, no dependents, not in StarterKit | `app/package.json:77` |

## Evidence

**`undici`** — `app/scripts/prepare-pyodide.js:19` imports `setGlobalDispatcher` and `ProxyAgent` to route pyodide and PyPI downloads through `HTTPS_PROXY`/`ALL_PROXY`. `app/package.json:22` defines `pyodide:fetch`, which is the first command in `dev`, `dev:5050`, `build` and `build:watch`. Every build runs it. A separate `undici@6` resolves for `cheerio` via the dev-only `i18next-parser` and is unrelated.

**`y-protocols`** — `app/bun.lock:2085` lists it among `y-prosemirror@1.3.7`'s peers. `y-prosemirror` is `"type": "module"` and points its import export at raw source, so Vite resolves `src/plugins/cursor-plugin.js:4`, which imports `y-protocols/awareness`. `RichTextInput.svelte:64-72` imports the y-prosemirror plugins, and that component backs the notes editor, both message inputs, the knowledge base and the text-content modal. One qualifier: in `cursor-plugin.js` the `Awareness` binding appears only in JSDoc annotations, so Rollup drops it from the emitted bundle — but the specifier must still resolve at build time or Vite fails. `RichTextInput.svelte:407` carries its own awareness implementation over socket.io. Net: required to build, ships no bytes.

**`@tiptap/extension-link`** — `@tiptap/starter-kit/package.json` declares it a hard dependency; `dist/index.js:12` imports it statically and lines 69-71 push it unless disabled. `RichTextInput.svelte:912-913` passes `link` through to `StarterKit.configure`, defaulting false at `:119`, and `NoteEditor.svelte:1153` passes `link={true}`. The top-level declaration is redundant, but removing it gives up direct version control over an extension the app configures.

**`@floating-ui/dom`** — `app/bun.lock:423` shows `@melt-ui/svelte@0.76.2` declaring it; `bits-ui` declares melt-ui and is imported 29 times across `app/src`. Nothing imports `@floating-ui/dom` or `computePosition` directly.

**`async`** — a repo-wide grep for every import form returns nothing outside `package.json`, this chart, and two generated licence tables. `getos@3.2.1` declares it (`app/bun.lock:1249`) and getos is a dependency of `cypress`, a devDependency. `fastq`, `iconv-lite` and `tough-cookie` list it in devDependencies only, which installers ignore.

**`@pyscript/core`** — a case-insensitive repo-wide grep returns four hits: `package.json:62`, this chart, and two generated licence tables. Nothing in `backend/`, `scripts/`, `tools/`, the Makefile, the Dockerfile, or any of the fifteen `build-sprig-*.sh` files mentions it. The code interpreter uses pyodide directly: `pyodide.worker.ts:1` imports `loadPyodide` from `pyodide`, `:22` sets `indexURL: '/pyodide/'`, served from `app/static/pyodide` which `prepare-pyodide.js` fills. There is no `<py-script>` element, no `type="py"` script tag, no polyscript reference. The archived roadmap put it near 100 KB.

**`@tiptap/extension-drag-handle`** — no import, no dependents, and three of its five peers (`@tiptap/y-tiptap`, `@tiptap/extension-node-range`, `@tiptap/extension-collaboration`) are absent from `package.json`. It could not be constructed even if something tried. It is the second package pulling `@floating-ui/dom`.

**`@tiptap/extension-youtube`** — no import, no dependents, not in StarterKit. YouTube handling lives elsewhere: `VideoEmbed.svelte` builds a plain iframe and parses URLs by hand, and `HTMLToken.svelte:64` renders an iframe. Neither touches tiptap.

## What this means for the effort

Four packages delete with no runtime effect: `async`, `@pyscript/core`, `@tiptap/extension-drag-handle`, `@tiptap/extension-youtube`. Only `@pyscript/core` carries real weight.

`@floating-ui/dom` and `@tiptap/extension-link` are declaration-only cleanups — two manifest lines, zero install bytes. Count them separately in any before/after measurement, or the numbers overstate the win.

`undici` and `y-protocols` stay. `undici` is a build-time tool filed under `dependencies`, which puts it in the category already ruled out of scope as cosmetic. `y-protocols` is a peer that must resolve at build time and ships no bytes, so it will surface as a zero-import straggler in every future scan — record it as answered so it is not re-investigated.

**Open question, deliberately not guessed:** whether bun auto-installs the `y-protocols` peer if the top-level entry is dropped. Untested. Do not drop it without a clean install and a build.
