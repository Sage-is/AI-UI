# Phase 4 gate — the shared-runtime probe: decision memo

**Date:** 2026-07-27 · **Verdict: the assumption holds.** Biomes share one Svelte runtime. Three costs came with the answer, and the plan had priced none of them.

## The question

The plan makes biomes load-bearing. Every legacy Svelte surface survives inside the server-rendered shell as a compiled custom element, and the shell flip at Phase 3 depends on that working. It also refuses to assume the part that matters: "all biomes share **one** Svelte runtime — each inlining its own would be a shattered SPA, not islands."

Nothing in Phase S touched this. Vanilla streaming needs no runtime at all.

## What was measured

Three build shapes, one probe, 16 checks. Four of those checks run against a shape that **must** fail, because a suite that has never said no is not evidence. That lesson came from Phase S, where an autoscroll went 13/13 green and was broken in the hand.

| Shape | What it is | Result |
| --- | --- | --- |
| A | one build, three biomes | one runtime, one store instance, writes cross biomes |
| B | three independent builds (control) | three runtimes, no shared scheduler, no shared store |
| C | a biome built later, borrowing the host's runtime by URL | 1.6 kB, shares both |

Shape A is the Phase 3 flip. Shape B is what you get by accident. Shape C is a ui-Sprig, or a surface migrated after the shell has already shipped.

The runtime check is identity, not resemblance. Each biome hands the page its own reference to Svelte's scheduler, and the page compares them. A separate check counts *declarations* of the scheduler's dirty-component queue in the built bytes. The first version of that check counted mentions instead and reported two runtimes in a build that has one, because Rollup had split the runtime across two cooperating chunks. Mentions measure chunking. Declarations measure instances.

## Three findings the plan had not priced

**1. "Externalise the runtime" is not one specifier.** Shape C marked `svelte/internal` external and left `svelte` alone. The package's own entry reaches the same source files under a different module id, so the late biome inlined a second copy of the lifecycle code with its own `current_component`. The build succeeded. The biome threw `Function called outside component initialization` at mount. Here that cost twenty minutes. In a marketplace it would fail in someone else's deployment, after graft, with a stack trace pointing at Svelte.

**2. Publishing the runtime defeats tree-shaking.** A host that exposes its runtime as a stable module has to export all of it, so Rollup can no longer shake it down to the helpers the biomes actually use. Unminified, that is 27.3 kB against 95.4 kB — three and a half times. Phase 3 does not pay it, because all biomes build together. The Sprig marketplace does. Each late biome then costs 1.6 kB and nothing more, so the trade is a fixed premium against a per-extension saving, and it turns on how many extensions we expect.

**3. Vite mangles entry exports by default.** With `preserveEntrySignatures: false`, the published runtime shipped `SvelteComponent as S` and `flush as j`. Fine between chunks renamed in lockstep, useless as a public interface. The late biome asked for the real names, got a resolution error, and never mounted.

All three are the same shape of problem: the host has to publish a deliberate interface, and every default is against it.

## Two things observed, not asserted

**A biome is a CSS boundary.** An app stylesheet rule does not reach inside a shadowed biome. `shadow: 'none'` removes the boundary in one line, and removes the encapsulation with it — the biome's own styles then leak out. Both were measured. Every migrated surface has to pick one, and the picking is a design decision, not a build setting.

**The SvelteKit surface is smaller than it looks.** 64 of 317 components import `$app/*`, using nine symbols between them. `goto` accounts for 54 import sites and `page` for 26, which is 80 of 81. Shims for navigation, stores and environment come to about fifty lines, and a biome importing all three builds and runs. `$page` reacts to the shim's own navigation, which matters: a store that never updated would leave 26 components rendering a stale route after every navigation, quietly.

## What this does not say

It does not test a biome sharing a page with the **legacy SvelteKit bundle**. During phases 2 and 3 both exist, and that page has two runtimes by construction — the SPA's and the biome build's. The plan's flip removes the SPA router at Phase 3, so the overlap is bounded, but nobody has built that page.

It does not test a **real component**. These biomes are toys. The chat core carries 710 click handlers and 859 bindings; nothing here says it compiles as a custom element, only that the runtime would be shared if it did.

## Recommendation

The gate is satisfied for the question it asked. Phase 4 is unblocked on runtime grounds.

Two things should land while the finding is fresh. Write findings 1 and 2 into the ui-Sprig spec, because they are the mechanism behind "no framework sprigs" — that rule is not a matter of taste, it is the only thing standing between a marketplace and a second runtime per extension. And pin the biome ratchet now, while the count is still the inherited five.

## Running it

```sh
tools/spikes/biomes/run.sh     # builds all four shapes, serves them, runs the probe
```

Everything runs in containers, against `app/node_modules`, so the probe measures the toolchain the app actually builds with. Throwaway, as the plan specified.
