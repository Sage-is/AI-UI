<!-- A plain nested component. THROWAWAY.

     Deliberately carries no `<svelte:options customElement>`. Real biomes are
     trees: one custom element at the root, ordinary Svelte components beneath
     it. If the build turns EVERY .svelte into a custom element, that tree
     breaks. This file exists to prove the compiler option can be scoped to the
     root — see `dynamicCompileOptions` in vite.shared.config.js. -->
<script>
  export let label;
</script>

<span data-inner>{label} inner</span>
