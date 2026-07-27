// Build shape B — the NEGATIVE CONTROL. THROWAWAY.
//
// Same sources, built one biome at a time as independent bundles. Nothing
// connects the two builds, so each must inline its own copy of the Svelte
// runtime and its own copy of shared-state.js. The probe is required to go RED
// against this page.
//
// Without a control, a green run proves only that the probe is incapable of
// saying no — which is exactly how the Phase S autoscroll went 13/13 green
// while being broken in the hand.
//
// BIOME=a|b|c npx vite build --config vite.split.config.js
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';

const which = process.env.BIOME || 'a';

export default defineConfig({
  resolve: {
    alias: { $app: fileURLToPath(new URL('./src/shims', import.meta.url)) }
  },
  plugins: [
    svelte({
      dynamicCompileOptions({ filename }) {
        return { customElement: /Biome[ABC]\.svelte$/.test(filename) };
      }
    })
  ],
  build: {
    outDir: `dist/split-${which}`,
    emptyOutDir: true,
    minify: false,
    rollupOptions: {
      input: { [`biome-${which}`]: `src/entry-${which}.js` },
      output: {
        format: 'es',
        entryFileNames: '[name].js',
        chunkFileNames: 'chunk-[name].js'
      }
    }
  }
});
