// Phase S streaming spike — the island under judgement. THROWAWAY.
//
// No framework, no build step, no SvelteKit. Everything the chat core gets for
// free from Svelte has to be earned here in plain DOM:
//   1. incremental markdown that never renders a broken partial
//   2. autoscroll that sticks to the bottom but yields the moment a reader scrolls up
//   3. a stop button that aborts the SERVER, not just the paint
//
// Whether this reads as production-grade is the decision the memo records.

import md from './vendor/md.js';

const out = document.getElementById('output');
const scroller = document.getElementById('scroller');
const metrics = document.getElementById('metrics');

let controller = null;
let raw = '';
let stick = true;      // are we pinned to the bottom?
let firstTokenAt = 0;
let tokenCount = 0;

// --- autoscroll -----------------------------------------------------------
// Stay pinned while the reader is at the bottom; the instant they scroll away,
// stop yanking them back. Svelte gives you nothing here either — it is the same
// listener in both worlds — so this is a fair comparison, and it cost four
// attempts. THE REAL FINDING OF THIS SPIKE.
//
// 1. `scroll` + distance-from-bottom: reader gets dragged back (scrollTop
//    135->159, flag still "pinned"). `scroll` is async, so a token arriving in
//    the gap re-pins them.
// 2. Remember the position we scrolled TO, ignore events landing there: fails
//    too. A `scroll` event carries no position, and by delivery time our own
//    scroll has overwritten it.
// 3. Infer intent from gesture deltas (wheel up = release): passed every
//    automated check and was WRONG IN THE HAND. A trackpad emits tiny negative
//    deltas from the slightest contact, so it released on page load before the
//    view had moved; and `touchmove` fires early in a swipe while still near
//    the bottom, so touch measured "pinned" and momentum then carried the
//    reader away with nothing left to re-evaluate.
// 4. What is here: judge by POSITION on every scroll event, and separately
//    refuse to yank a reader who has moved the box (see scrollIfPinned). The
//    first covers momentum, scrollbar drags and keyboard paging with no
//    input-specific code; the second closes the async-delivery race that sank
//    attempt 1. No gesture listeners at all.
//
// The lesson worth carrying: every automated check passed at attempt 3. Only
// hands on a real trackpad found it.
const NEAR_BOTTOM_PX = 16;
const jump = document.getElementById('jump');

// Single owner of the pinned state, so the readout and the jump button can
// never disagree with the actual behaviour. Sticky-bottom is only pleasant if
// leaving it is reversible — otherwise the reader is stranded in scrollback
// with no way home but a manual drag.
function setStick(next) {
  stick = next;
  document.getElementById('stick').textContent = stick ? 'pinned' : 'released';
  // Keep the platform attribute for semantics and screen readers...
  jump.hidden = stick;
  // ...but startr.style declares `display: var(--d) !important`, which beats
  // both [hidden]'s UA rule and our own stylesheet. So the visual toggle has to
  // go through the custom property. Setting el.style.display here would look
  // right and do nothing — the button stayed visible after re-pinning until
  // this line existed.
  jump.style.setProperty('--d', stick ? 'none' : 'grid');
}

// Assert the initial state instead of trusting the markup to match: the label,
// the button and the flag must agree from the first frame. The page previously
// loaded with the button visible because nothing had called setStick yet.
setStick(true);

function evaluatePinning() {
  requestAnimationFrame(() => {
    const distance = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    setStick(distance <= NEAR_BOTTOM_PX);
  });
}

// Judge by POSITION, on every scroll, and never infer from gesture deltas.
//
// Two bugs came from the delta version, both found by hand, not by the suite:
//   * "released on page load" — a trackpad emits tiny negative deltas from the
//     slightest contact (and macOS rubber-banding emits them at rest), so ANY
//     upward delta released the pin before the view had moved at all.
//   * "touch scrolling doesn't work" — `touchmove` fires early in a swipe while
//     still near the bottom, so it measured "pinned"; momentum then carried the
//     reader away with no further touchmove and nothing re-evaluated, leaving
//     them scrolled up but flagged pinned, to be yanked back by the next token.
//
// Position on every scroll event fixes both: no movement means no change, and
// momentum keeps re-evaluating all the way through the glide. It also covers
// scrollbar drags and keyboard paging for free, with no input-specific code.
scroller.addEventListener('scroll', evaluatePinning, { passive: true });

// Instant, not smooth. Smooth looked nicer and was wrong: a smooth scroll emits
// intermediate `scroll` events at positions far from the bottom, and since we
// now judge pinning by position on every scroll, our own animation released the
// pin mid-flight and popped the button back up (distance=61px, "released").
// Snapping also matches the per-token scroll, which must stay instant or it
// fights the incoming text.
jump.addEventListener('click', () => {
  scroller.scrollTop = scroller.scrollHeight;
  lastAutoTop = scroller.scrollTop;
  setStick(true);
});

// Tight threshold: you are "pinned" only if you are genuinely at the bottom.
// A generous one is what "too stuck to the bottom" feels like — a small scroll
// up still measures as pinned and gets snapped back before you can read a line.
let lastAutoTop = -1;

function scrollIfPinned() {
  if (!stick) return;
  // The race that defeated position-checking on the first attempt: `scroll` is
  // async, so a token can arrive after the reader has moved the box but before
  // their event is delivered — and we would yank them back, then their late
  // event would measure the bottom and re-pin. Reading the position directly
  // here closes that window: if the box is not where we left it, the reader
  // moved it, so release instead of yanking. No event required.
  if (lastAutoTop >= 0 && Math.abs(scroller.scrollTop - lastAutoTop) > 2) {
    setStick(false);
    return;
  }
  scroller.scrollTop = scroller.scrollHeight;
  lastAutoTop = scroller.scrollTop;
}

// --- incremental markdown -------------------------------------------------
// The hard case is a fenced code block: the text is INVALID markdown from the
// opening fence until the closing one arrives, so a naive render flashes raw
// backticks and then reflows. We close the fence in a copy before rendering,
// which keeps the partial visually stable. Same trick works for inline code.
function renderPartial(text) {
  let safe = text;
  const fences = (safe.match(/```/g) || []).length;
  if (fences % 2 === 1) safe += '\n```';
  const ticks = (safe.match(/`/g) || []).length;
  if (ticks % 2 === 1) safe += '`';
  out.innerHTML = md(safe);
}

// --- the stream ------------------------------------------------------------
async function start() {
  raw = '';
  lastAutoTop = -1;
  tokenCount = 0;
  firstTokenAt = 0;
  out.innerHTML = '';
  controller = new AbortController();
  setBusy(true);

  const began = performance.now();
  let res;
  try {
    res = await fetch('/stream', { signal: controller.signal });
  } catch (err) {
    if (err.name === 'AbortError') return void finish('aborted-before-open', began);
    throw err;
  }

  // Read the byte stream directly. This is the whole transport story: no
  // framework, ~15 lines, and it is protocol-agnostic — the same code runs
  // over h2 without knowing it.
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);
        if (!frame.startsWith('data:')) continue;
        const payload = frame.slice(5).trim();
        if (payload === '[DONE]') return void finish('complete', began);

        if (!firstTokenAt) firstTokenAt = performance.now() - began;
        raw += JSON.parse(payload).tok;
        tokenCount++;
        renderPartial(raw);
        scrollIfPinned();
      }
    }
    finish('complete', began);
  } catch (err) {
    if (err.name === 'AbortError') finish('stopped', began);
    else throw err;
  }
}

function stop() {
  if (controller) controller.abort();
}

function setBusy(busy) {
  document.getElementById('send').disabled = busy;
  document.getElementById('stop').disabled = !busy;
  document.getElementById('status').textContent = busy ? 'streaming' : 'idle';
}

function finish(how, began) {
  setBusy(false);
  const elapsed = Math.round(performance.now() - began);
  metrics.textContent = JSON.stringify({
    outcome: how,
    tokens: tokenCount,
    ttft_ms: Math.round(firstTokenAt),
    total_ms: elapsed,
    protocol: window.__spikeProtocol || 'unknown',
  });
  // Surfaced for the Cypress spec to assert against.
  window.__spikeResult = { outcome: how, tokens: tokenCount, ttft_ms: Math.round(firstTokenAt) };
}

// htmx swaps the composer fragment in, so bind through the document rather than
// to nodes that may not exist yet — the shell owns that DOM, not the island.
document.addEventListener('click', (e) => {
  if (e.target.id === 'send') start();
  if (e.target.id === 'stop') stop();
});

// Report the negotiated protocol so "streams over HTTP/2" is measured, not assumed.
window.addEventListener('load', () => {
  const nav = performance.getEntriesByType('navigation')[0];
  window.__spikeProtocol = nav ? nav.nextHopProtocol : 'unknown';
  document.getElementById('protocol').textContent = window.__spikeProtocol;
});
