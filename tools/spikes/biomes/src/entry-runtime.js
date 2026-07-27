// The host's runtime, exposed as one addressable module so a biome built LATER
// can import it instead of inlining its own. This is the mechanism behind the
// plan's "no framework sprigs" rule: a fragment may use the host's runtime, and
// must not bring one.
export * from 'svelte/internal';
