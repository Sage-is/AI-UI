<!-- Biome B — a second, independently-built surface. THROWAWAY.
     It never imports A. Its only tie to A is the shared store, which is
     precisely the tie the plan needs to hold across biomes. -->
<svelte:options customElement="biome-b" />

<script>
  import { onMount } from 'svelte';
  import { flush } from 'svelte/internal';
  import { count, ticket } from './shared-state.js';

  onMount(() => {
    (window.__biomes ||= []).push({ tag: 'biome-b', flush, ticket });
  });
</script>

<div data-biome="b">
  <output data-count="b">{$count}</output>
</div>
