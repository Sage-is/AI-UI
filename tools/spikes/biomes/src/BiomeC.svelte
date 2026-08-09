<!-- Biome C — the SvelteKit-dependency case. THROWAWAY.
     Imports `$app/navigation`, which does not exist outside a SvelteKit app.
     It builds only because an alias points that specifier at our shim. If the
     shim were wrong or missing, this file would fail the build, which is the
     assertion. -->
<!-- `shadow: 'none'` is the escape from the CSS boundary that biomes A and B
     hit. Same custom element, same runtime, but it renders into light DOM, so
     the app stylesheet applies as it would to any other markup. The cost is the
     other direction: no encapsulation, so a biome's own styles now leak out.
     The probe measures both ends rather than picking one. -->
<svelte:options customElement={{ tag: 'biome-c', shadow: 'none' }} />

<script>
  import { onMount } from 'svelte';
  import { flush } from 'svelte/internal';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { ticket } from './shared-state.js';

  onMount(() => {
    (window.__biomes ||= []).push({ tag: 'biome-c', flush, ticket });
  });
</script>

<div data-biome="c">
  <span data-styled-c class="app-themed">themed?</span>
  <button data-goto on:click={() => goto('/probe-navigated')}>navigate</button>
  <!-- `$page` must react to the shim's own navigation, or 26 components that
       read the current route would render stale after every goto. -->
  <output data-path>{$page.url.pathname}</output>
  <output data-browser>{browser}</output>
</div>
