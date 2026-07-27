# Phase S — streaming spike: decision memo

**Date:** 2026-07-27 · **Verdict: GO**, with two conditions and one correction to the plan's assumptions.

## The question

Can a vanilla island in a server-rendered htmx shell stream a completion as well as the SvelteKit chat core does? It has to manage that over HTTP/2, with autoscroll, and with a stop button that really stops. If none of it felt production-grade, the fallback was contain-and-extend: Svelte keeps the chat core, no-build owns everything else.

## What was built

`server.py` (stdlib, ~140 lines) serves the shell and a token stream. `island.js` (~150 lines, no framework, no build step) consumes it. `vendor/md.js` is a spike-grade markdown subset; production would serve the `marked` we already depend on as one immutable static file. Caddy fronts the whole thing so the browser negotiates h2. All of it is throwaway, as the plan specified.

## What we measured

| Criterion | Result |
| --- | --- |
| Streams over HTTP/2 | `http_version 2` on shell, island, and vendored htmx |
| Delivery is incremental, not buffered | frame 1 at 0.000s, frame 150 at 3.337s |
| Stop button stops it | client: `{outcome: "stopped", tokens: 493/1211}`; server: `stream_aborted sent=21 total=164` |
| Autoscroll holds | pinned at `distance=0px` mid-stream; releases when the reader scrolls, and stays released |
| Decision memo exists | this file |

Browser criteria: 13/13 under Playwright, plus a manual pass on a real trackpad and touchscreen. Time to first token was 5ms.

The server-side abort is the line that matters. A stop button that only hides output is theatre. This one ends server work within two tokens of the click, because a plain `AbortController` closes the connection and the next write raises. Svelte uses the same mechanism. No framework does this part for you.

## Two findings that change how we proceed

**1. Our e2e harness cannot see streaming.** Cypress proxies the application under test and buffers the response body, so the page sees nothing until the stream finishes. The stop test failed with `aborted-before-open`, because the `fetch` promise had not resolved when stop fired. That is not a spike defect and better assertions will not fix it. Any streaming guard-rail needs a non-proxying driver. Playwright works. We deleted the spike's Cypress attempt rather than leave it failing. Phase 0 assumes one Cypress spec can pass against both the old surface and the new one; that holds for DOM surfaces and breaks for streaming ones.

**2. Autoscroll is harder than the plan implies.** It took four attempts, and the third passed every automated check while being broken on real hardware.

1. `scroll` plus distance-from-bottom drags the reader back down (`scrollTop 135→159`, with the flag still reading "pinned"). `scroll` is asynchronous, so a token that arrives before the reader's own event re-pins the view.
2. Remembering the position we scrolled to, then ignoring events that land there, fails as well. A `scroll` event carries no position, and by the time it is delivered our own scroll has overwritten the evidence.
3. Inferring intent from gesture deltas, where a `wheel` up releases the pin, produced two failures on real hardware. A trackpad emits tiny negative deltas from the slightest contact, so the pin released on page load before the view had moved at all. `touchmove` fires early in a swipe, while the reader is still near the bottom, so touch measured "pinned"; momentum then carried the reader away with nothing left to re-evaluate. Alexander found both by hand. The suite found neither.
4. What shipped judges pinning by position, on every scroll event. A second rule refuses to scroll a reader who has already moved the box, which closes the race from attempt 1. There are no gesture listeners at all, so momentum, scrollbar drags and keyboard paging all work without input-specific code. Confirmed by hand.

Two more bugs fell out of attempt 4, and the suite did catch these. A smooth jump-to-latest scroll released the pin mid-animation, because the intermediate scroll events sit far from the bottom. And the jump button rendered on page load, because startr.style declares `display: var(--d) !important`, which beats the `hidden` attribute.

Autoscroll costs the same in both worlds. Svelte does not solve it either; it is the same thirty-odd lines of listener whichever framework surrounds them. So the spike neither penalises nor rewards the migration on autoscroll. The discovery cost was not a wash, and that is the part worth carrying forward.

## Conditions on the GO

1. **A non-proxying browser driver has to land before we cut any streaming surface, and that driver is necessary rather than sufficient.** Attempt 3 was 13/13 green under Playwright and broken on a real trackpad, because synthetic input models neither trackpad jitter nor touch momentum. Every streamed surface also needs a human pass before we call it done. Treat that as a scheduling fact for Phases 2 through 4: on a streaming surface, an all-green suite is weaker evidence than we have been assuming.
2. **The shared-runtime assumption is still unproven.** The plan requires all biomes to share one Svelte runtime and marks that `#critical`. This spike did not test it, because vanilla streaming needs no runtime at all. Phase 4 stays gated on that probe. Nothing here licenses it.

## What this does not say

It does not say the chat core should be rewritten. It says the transport and rendering pattern holds up at spike scale. Roughly 260 lines of server plus island did what the SvelteKit path does, and the hard parts (abort semantics, partial markdown, pinning) were hard for reasons that have nothing to do with the framework. The 15–30% rewrite estimate in the plan is untested by this exercise.

**Recommendation:** proceed to Phase 0, the seam and the Sprigs pilot, which is a non-streaming surface. Settle the runtime probe and the driver question in parallel, then re-judge Phase 4 with both answers in hand, which is what the plan asks us to do with this memo.
