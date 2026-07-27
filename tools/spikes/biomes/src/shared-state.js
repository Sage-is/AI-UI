// One module, imported by both biomes. THROWAWAY.
//
// This is the whole question in four lines. If the build hands each biome its
// own copy of this module, `ticket` is two different objects and `count` is two
// different stores — a shattered SPA wearing an islands costume. If they share
// it, a write in one biome is visible in the other.
import { writable } from 'svelte/store';

export const count = writable(0);

// Object identity, deliberately. A string or a number would compare equal
// across two separate module instances and the probe would pass while being
// wrong — the Phase S lesson about assertions that cannot fail.
export const ticket = { id: 'shared-state-module' };
