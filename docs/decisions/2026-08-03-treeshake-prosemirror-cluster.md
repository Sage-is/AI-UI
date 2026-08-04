# Decision record: the prosemirror cluster

**Date:** 2026-08-03 · **Card:** The prosemirror cluster · **Type:** research

## Answer

Eight of the nine are removable. One is not.

`@tiptap/pm` is **required**. It is a declared `peerDependency` of `@tiptap/core` and of twelve other installed `@tiptap/*` packages. A peer dependency is the consumer's job to declare; that is why it sits in `app/package.json` with no import of its own.

Seven of the eight `prosemirror-*` entries are **redundant-transitive**. `@tiptap/pm@3.0.7` lists every one of them as a direct dependency. They arrive whether declared or not.

One, `prosemirror-example-setup`, is **residue**. Nothing in the dependency tree requires it and nothing in the repo imports it. It is the only entry in the cluster whose removal actually removes a package from the install.

The card asked whether the cluster predates tiptap. Git cannot answer that. The repository opens with a squashed `Initial commit` (`bbb4f10`, 2026-01-10) that already contains all nine entries alongside tiptap 3.0.7. There is no before.

## Per-package verdict

| package | verdict | evidence |
| --- | --- | --- |
| `@tiptap/pm` | **REQUIRED** | `peerDependencies: { "@tiptap/pm": "^3.0.7" }` in `app/node_modules/@tiptap/core/package.json`, and in twelve sibling `@tiptap/extension-*` packages. |
| `prosemirror-collab` | REDUNDANT-TRANSITIVE | dependency of `@tiptap/pm@3.0.7` (`^1.3.1`). |
| `prosemirror-commands` | REDUNDANT-TRANSITIVE | dependency of `@tiptap/pm` (`^1.6.2`), also of `prosemirror-menu` and `prosemirror-example-setup`. |
| `prosemirror-history` | REDUNDANT-TRANSITIVE | dependency of `@tiptap/pm` (`^1.4.1`), also of `prosemirror-menu`. |
| `prosemirror-markdown` | REDUNDANT-TRANSITIVE | dependency of `@tiptap/pm` (`^1.13.1`). |
| `prosemirror-schema-basic` | REDUNDANT-TRANSITIVE | dependency of `@tiptap/pm` (`^1.2.3`). |
| `prosemirror-schema-list` | REDUNDANT-TRANSITIVE | dependency of `@tiptap/pm` (`^1.5.0`). |
| `prosemirror-tables` | REDUNDANT-TRANSITIVE | dependency of `@tiptap/pm` (`^1.6.4`); reached in code through `@tiptap/extension-table`. |
| `prosemirror-example-setup` | **RESIDUE** | one reverse-dependency in `app/bun.lock` — the root package itself, line 68. No other package requires it. |

Not in the cluster, listed to prevent a mistake: `prosemirror-model`, `prosemirror-state`, `prosemirror-view` and `prosemirror-keymap` are **imported directly** and must stay declared. See evidence 4.

## Evidence

**1. tiptap requires the consumer to declare `@tiptap/pm`.**
`app/node_modules/@tiptap/core/package.json` carries `"peerDependencies": { "@tiptap/pm": "^3.0.7" }`. The same peer appears in `extension-bubble-menu`, `extension-code-block`, `extension-code-block-lowlight`, `extension-drag-handle`, `extension-file-handler`, `extension-floating-menu`, `extension-horizontal-rule`, `extension-link`, `extension-list`, `extension-table` and `extensions` — all installed and all used. Thirteen packages ask for it.

**2. `@tiptap/pm` owns the seven.**
`app/node_modules/@tiptap/pm/package.json` `dependencies` includes `prosemirror-collab`, `prosemirror-commands`, `prosemirror-history`, `prosemirror-markdown`, `prosemirror-schema-basic`, `prosemirror-schema-list` and `prosemirror-tables` — plus `changeset`, `dropcursor`, `gapcursor`, `inputrules`, `keymap`, `menu`, `model`, `state`, `trailing-node`, `transform`, `view`. It does **not** depend on `prosemirror-example-setup`.

**3. `@tiptap/pm` subpaths are plain re-exports, not bundled copies.**
`app/node_modules/@tiptap/pm/dist/state/index.js` is one line: `export * from "prosemirror-state";`. Same shape for `view`, `tables` and the rest. There is no second copy of any prosemirror module, and `find node_modules -type d -name "prosemirror-*"` returns exactly one directory per package. The app's direct `prosemirror-state` imports and tiptap's `@tiptap/pm/state` imports resolve to the same singleton. This matters: duplicate `prosemirror-state` instances would silently break plugin identity.

**4. Four prosemirror packages are imported directly and are not up for removal.**
`app/src/lib/components/common/RichTextInput.svelte` lines 57-59 and 73 import `Fragment, DOMParser` from `prosemirror-model`, `EditorState, Plugin, PluginKey, TextSelection, Selection` from `prosemirror-state`, `Decoration, DecorationSet` from `prosemirror-view`, and `keymap` from `prosemirror-keymap`. `app/src/lib/components/common/RichTextInput/AutoCompletion.js` line 15 imports `Plugin, PluginKey` from `prosemirror-state`. `y-prosemirror` additionally peer-requires `prosemirror-model`, `-state` and `-view`.

**5. Nothing imports `@tiptap/pm` or the eight, anywhere.**
`grep -rn "prosemirror\|@tiptap/pm" app/src/` returns only: the four direct imports above, `.ProseMirror` CSS selectors in `app/src/app.css`, prose comments, the Yjs fragment name string `'prosemirror'`, and a license table (evidence 8). Zero hits for `@tiptap/pm` as a module specifier. `app/cypress/`, `app/test/`, `app/scripts/`, `app/static/` and `app/backend/` have zero hits of any kind.

**6. No build-config reference.**
`app/vite.config.ts` line 103 and `app/vite.config.clean.ts` line 44 each declare `optimizeDeps: { exclude: ['pyodide'] }` and nothing else. Neither file, nor `app/svelte.config.js`, nor `app/tsconfig.json` names any prosemirror or tiptap package. There is no `ssr.noExternal` entry anywhere.

**7. Git history is uninformative by construction.**
`git log -S'"prosemirror-collab"' -- app/package.json` returns a single commit, `bbb4f10 2026-01-10 Initial commit`. Same result for `prosemirror-example-setup`, `prosemirror-tables`, `@tiptap/pm` and `@tiptap/core`. The 353-commit history begins with a squash. The "residue of an earlier editor" hypothesis cannot be confirmed or refuted from this repo; it is inherited upstream state.

**8. One non-code reference survives removal, and it is prose.**
`app/src/lib/data/licenseData.ts` (lines 80-91) and `app/src/lib/data/license-table.md` (lines 69-80) list all nine packages in a hand-maintained license table rendered by `app/src/lib/components/chat/Settings/About.svelte`. No script generates these files. Removing dependencies leaves the table stale but does not break the build.

**9. UNCERTAIN — version floors move slightly.**
For two packages the app's declared floor is above `@tiptap/pm`'s: `prosemirror-tables` `^1.7.1` vs `^1.6.4`, `prosemirror-schema-list` `^1.5.1` vs `^1.5.0`. For one it is below: `prosemirror-commands` `^1.6.0` vs `^1.6.2`. Removing the direct declarations hands resolution to `@tiptap/pm`'s ranges. Installed versions today (1.7.1, 1.5.1, 1.6.2) all still satisfy those ranges, so a fresh resolve should land in the same place — but that is a prediction, not an observation. Verify by re-running `bun install` and diffing `app/bun.lock` before accepting the removal.

## What this means for the effort

Nine of the twenty-one unimported entries resolve here. Eight lines come out of `app/package.json`; one, `@tiptap/pm`, stays and should be annotated as a peer requirement so no later audit re-raises it.

The install shrinks by exactly one package. `prosemirror-example-setup` is the only genuine removal — its own dependencies (`commands`, `dropcursor`, `gapcursor`, `history`, `inputrules`, `keymap`, `menu`, `schema-list`, `state`) are all also `@tiptap/pm` dependencies, so nothing else is orphaned. The other seven remain installed as transitive dependencies of `@tiptap/pm` at the same versions.

So this is a manifest-honesty change, not a size change. It makes `app/package.json` state what the app actually asks for. It does not move bundle bytes: the seven were never bundled, because nothing imported them.

Two follow-ups fall out. Update the license table in `app/src/lib/data/licenseData.ts` and `license-table.md` in the same commit, or the About screen will name packages the manifest no longer declares. And re-lock before merging, per evidence 9.

Acceptance test for the removal: `bun install`, then `bun run build`, then open the rich-text composer and confirm tables, links, code blocks, the bubble menu and Yjs collaborative cursors still work. Those are the paths that reach prosemirror through tiptap.
