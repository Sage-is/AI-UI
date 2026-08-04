# Decision record: the unimported CodeMirror languages

**Date:** 2026-08-03 · **Card:** The two unimported CodeMirror languages · **Type:** research · **Chart:** `app/TODO.md`

## Answer

Both packages are required. Do not remove them.

`@codemirror/lang-javascript` and `@codemirror/lang-python` are loaded at runtime by `@codemirror/language-data`, which imports them with a dynamic `import()` from inside `node_modules`. A grep of `app/src` cannot see that call site. Deleting them breaks syntax highlighting for JavaScript, TypeScript, JSX, TSX and Python.

The two lines in `app/package.json` are technically redundant — `language-data` pulls both in transitively and bun hoists them, so removing the lines would break nothing and save nothing. A two-line diff with no payoff. Leave them. They also record a tighter version floor (`^6.2.2`) than language-data's `^6.0.0` and are attributed in `app/src/lib/data/licenseData.ts:21-22`.

## Evidence

- `app/node_modules/@codemirror/language-data/package.json` declares both as runtime dependencies.
- `app/node_modules/@codemirror/language-data/dist/index.js:141` — the Python entry is `import('@codemirror/lang-python').then(m => m.python())`. Lines 69, 84, 178 and 186 do the same for JavaScript, JSX, TSX and TypeScript, all loading `lang-javascript`.
- `app/src/lib/components/common/CodeEditor.svelte:10` imports `languages` from language-data; lines 107-110 resolve a language by alias and call `load()`.
- `app/node_modules/@codemirror/language/dist/index.js:749` — `LanguageDescription.of` lowercases the name into the alias list, so `lang="python"` matches the Python entry.
- `CodeEditor.svelte:88-105` pushes hand-written descriptions for HCL (`:93`) and Elixir (`:102`), each with its own dynamic `import()`. Those two are grep-visible **only** because language-data does not ship them — the same mechanism, written out by hand. That is the proof that registry entries are loaders rather than decoration.
- `app/src/lib/components/admin/Functions/FunctionEditor.svelte:375` hardcodes `lang="python"`. The admin Functions editor is Python-only.
- `app/src/lib/components/chat/Messages/Markdown/MarkdownTokens.svelte:103` passes the markdown fence tag straight through, so any language a model emits is reachable.
- `app/src/lib/components/chat/Messages/CodeBlock.svelte:473` gates in-browser execution on `python`/`py`.
- `app/bun.lock:187`, `:199` — one hoisted copy each; `:217` is language-data's dependency set. `lang-html` (`:183`) and `lang-vue` (`:207`) also depend on lang-javascript.

**Uncertainty, stated rather than papered over:** whether the tighter `^6.2.2` floor is load-bearing was not verified. Nothing in `src/` uses a 6.2-only API.

## What this means for the effort

**"No import in `app/src`" is not evidence of waste. It is evidence that grep cannot see the call site.** Any dependency reached through a plugin registry, a dynamic `import()` inside another package, a Vite/PostCSS/Tailwind config, or a string-keyed loader looks dead and is alive.

Every remaining card must apply this test before calling anything removable:

```bash
grep -l '"<pkg>"' app/node_modules/*/package.json app/node_modules/@*/*/package.json
```

This also downgrades the headline number. "21 of 84 unimported" is not a budget of 21 removals; it is 21 questions, and the first one answered came back REQUIRED.
