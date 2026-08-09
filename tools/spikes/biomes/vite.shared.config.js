// Build shape A — the shape we would actually ship. THROWAWAY.
//
// ONE Rollup build, three entries. Rollup hoists anything two entries both
// need into a shared chunk, so the Svelte runtime should land in exactly one
// file that all three biomes import. That is the hypothesis; probe.mjs is what
// tests it, and vite.split-*.config.js is the control that proves the test can
// fail.
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';

// Publishing the runtime as a stable module for late biomes is not free: an
// `export *` keeps the WHOLE surface alive, so Rollup can no longer shake it
// down to the handful of helpers three biomes actually use. Build both ways and
// let the probe price the difference instead of guessing at it.
//   HOST_EXPORTS=0 → dist/shared-min, tree-shaken, no late biomes possible
//   default        → dist/shared,     full runtime published
const hostExports = process.env.HOST_EXPORTS !== '0';

const biomes = {
  'biome-a': 'src/entry-a.js',
  'biome-b': 'src/entry-b.js',
  'biome-c': 'src/entry-c.js'
};

export default defineConfig({
  resolve: {
    alias: {
      // The per-biome work, in one line.
      $app: fileURLToPath(new URL('./src/shims', import.meta.url))
    }
  },
  plugins: [
    svelte({
      // Scoped, not global. `customElement: true` applied to every .svelte
      // would compile Inner.svelte as a custom element too and break the
      // component tree. Only the roots become elements.
      dynamicCompileOptions({ filename }) {
        return { customElement: /Biome[ABC]\.svelte$/.test(filename) };
      }
    })
  ],
  build: {
    outDir: hostExports ? 'dist/shared' : 'dist/shared-min',
    emptyOutDir: true,
    // Unminified on purpose: the probe counts copies of the runtime by
    // grepping for an identifier. Minified names would make that count a guess.
    minify: false,
    rollupOptions: {
      // Without this, `runtime.js` ships its exports MANGLED to single letters
      // (`SvelteComponent as S`, `flush as j`) — fine for chunks that were
      // built together and renamed in lockstep, useless as a public interface.
      // A late biome importing the real names got a resolution error and never
      // mounted. Vite defaults entries to `false` here; a host that publishes
      // its runtime has to opt back in.
      preserveEntrySignatures: 'strict',
      // Addressable host modules, so a biome built out of band can borrow the
      // runtime and the stores rather than duplicate them. See
      // vite.late.config.js.
      input: hostExports
        ? { ...biomes, runtime: 'src/entry-runtime.js', state: 'src/entry-state.js' }
        : biomes,
      output: {
        format: 'es',
        entryFileNames: '[name].js',
        chunkFileNames: 'chunk-[name].js'
      }
    }
  }
});
