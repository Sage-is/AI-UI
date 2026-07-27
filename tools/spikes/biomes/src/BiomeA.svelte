<!-- Biome A — a Svelte surface compiled to a custom element. THROWAWAY. -->
<svelte:options customElement="biome-a" />

<script>
  import { onMount } from 'svelte';
  // `flush` is Svelte's own scheduler entry point, and it closes over
  // module-level state (the dirty-component queue). Comparing it across two
  // biomes asks the exact question the plan asks: one runtime, or two?
  // We compare the RUNTIME's export, not one of our own modules — our module
  // could be shared while the runtime is not.
  import { flush } from 'svelte/internal';
  import { count, ticket } from './shared-state.js';
  import Inner from './Inner.svelte';

  onMount(() => {
    (window.__biomes ||= []).push({ tag: 'biome-a', flush, ticket });
  });
</script>

<div data-biome="a">
  <Inner label="a" />
  <!-- The page's own stylesheet targets this class. Whether the colour lands
       tells us if app CSS reaches inside a biome — a separate question from
       the runtime, but free to ask while we are here. -->
  <span data-styled class="app-themed">themed?</span>
  <button data-inc="a" on:click={() => count.update((n) => n + 1)}>A +1</button>
  <output data-count="a">{$count}</output>
</div>
