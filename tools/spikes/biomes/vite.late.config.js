// Build shape C — the biome that ships LATER. THROWAWAY.
//
// Shape A proves biomes share a runtime when they are built together. That is
// the Phase 3 shell flip, and it is the gate question. It is not the whole
// question: a ui-Sprig grafted next month, or a surface still living in the old
// SPA bundle during the strangler, is built by a DIFFERENT build. Shape B shows
// what that costs by default — a second runtime, and stores that no longer
// reach each other.
//
// This shape shows the escape hatch, and one trap inside it.
//
// THE TRAP: "externalise the runtime" is not one specifier. Marking only
// `svelte/internal` external left `import { onMount } from 'svelte'` to resolve
// through the package's own entry, which reaches the same source files under a
// different module id — so the late bundle inlined a SECOND copy of the
// lifecycle code whose `current_component` was a different variable. The build
// succeeded and the biome threw "Function called outside component
// initialization" at mount. A rule that catches `svelte/internal` and misses
// `svelte` fails loudly here; in a marketplace it would fail in someone else's
// deployment. (`svelte/internal` exports a superset of `svelte`'s 12 exports,
// checked, which is why both can point at the same host module.)
//
// This is why "no framework sprigs" is load-bearing rather than stylistic: the
// rule is not aesthetic preference, it is the only thing keeping a marketplace
// from shipping a second runtime per extension.
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';

// Resolve host imports to URLs the host already serves, and keep them
// untouched. `external: 'absolute'` is the part that matters — plain
// `external: true` lets Rollup rewrite an absolute id into a path relative to
// the chunk, which produced a 404 the first time round.
const borrowFromHost = {
  name: 'borrow-from-host',
  enforce: 'pre',
  resolveId(source) {
    if (source === 'svelte' || source === 'svelte/internal') {
      return { id: '/dist/shared/runtime.js', external: 'absolute' };
    }
    if (source.endsWith('shared-state.js')) {
      return { id: '/dist/shared/state.js', external: 'absolute' };
    }
    return null;
  }
};

export default defineConfig({
  resolve: {
    alias: { $app: fileURLToPath(new URL('./src/shims', import.meta.url)) }
  },
  plugins: [
    borrowFromHost,
    svelte({
      dynamicCompileOptions({ filename }) {
        return { customElement: /Biome[ABC]\.svelte$/.test(filename) };
      }
    })
  ],
  build: {
    outDir: 'dist/late',
    emptyOutDir: true,
    minify: false,
    rollupOptions: {
      input: { 'biome-b': 'src/entry-b.js' },
      output: { format: 'es', entryFileNames: '[name].js' }
    }
  }
});
