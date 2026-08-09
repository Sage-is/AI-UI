// Phase S — browser-level done-criteria. THROWAWAY.
//
// Playwright, not Cypress, and that is itself a finding: Cypress MITM-proxies
// the app under test and BUFFERS the streaming response, so the page sees
// nothing until the stream ends (its stop-button test failed with
// 'aborted-before-open' — the fetch had not resolved yet). A harness that
// cannot observe incremental delivery cannot guard streaming behaviour.
//
// Asserts what only a browser can: autoscroll pinning, the UI stop button, and
// that partial markdown never renders broken. HTTP/2 is proven separately by
// curl, because Playwright reports its own hop too.
import { chromium } from 'playwright';

const BASE = process.env.SPIKE_BASE || 'https://spike-tls:8443';
// Discovered, not hardcoded: the document changed once already and a stale
// constant would have made the stop assertion meaningless.
let TOTAL_TOKENS = 0;
const results = [];

const check = (name, pass, detail = '') => {
  results.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
};

TOTAL_TOKENS = await fetch(`${BASE}/meta`).then((r) => r.json()).then((m) => m.tokens);
console.log(`document is ${TOTAL_TOKENS} tokens`);

const browser = await chromium.launch({ args: ['--ignore-certificate-errors'] });
const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
const page = await ctx.newPage();
await page.goto(BASE, { waitUntil: 'load' });
await page.waitForSelector('#send', { timeout: 15000 });
check('shell and island coexist: htmx swaps in the server composer', true);

// --- page load -------------------------------------------------------------
// Found by hand, not by this suite: the previous build reported "released"
// before anything had streamed, because a trackpad's idle deltas tripped the
// gesture rule. Nothing has scrolled yet, so it must read pinned.
const stickOnLoad = await page.textContent('#stick');
const jumpOnLoad = await page.isVisible('#jump');
check('the view starts pinned on page load, with no jump button showing',
      stickOnLoad === 'pinned' && !jumpOnLoad, `label=${stickOnLoad} jump=${jumpOnLoad}`);

// --- incremental rendering -------------------------------------------------
await page.click('#send');
await page.waitForTimeout(500);
const midLen = (await page.textContent('#output')).length;
const midStatus = await page.textContent('#status');
check('content renders while the stream is still open',
      midLen > 0 && midStatus === 'streaming', `chars=${midLen} status=${midStatus}`);

// Partial markdown must not show a raw fence while the block is still open.
const midHasRawFence = (await page.textContent('#output')).includes('```');
check('partial markdown never shows an unclosed code fence', !midHasRawFence);

// --- autoscroll ------------------------------------------------------------
// Wait until the content actually OVERFLOWS the box. Before that, "scroll up"
// is a no-op and the release check would pass or fail meaninglessly — the first
// run of this script failed exactly there, with scrollTop 0->0 on 60 chars.
await page.waitForFunction(() => {
  const el = document.getElementById('scroller');
  return el.scrollHeight > el.clientHeight + 100;
}, { timeout: 20000 });

const pinned = await page.$eval('#scroller',
  (el) => el.scrollHeight - el.scrollTop - el.clientHeight);
check('autoscroll holds at the bottom while streaming', pinned < 60, `distance=${Math.round(pinned)}px`);

// A REAL scroll gesture, not `el.scrollTop = 0`. Setting scrollTop directly is
// something no reader can do, and it is indistinguishable from the island's own
// scrolling — testing with it asked the island to solve an impossible problem.
await page.mouse.move(400, 260);          // over the scroller
await page.mouse.wheel(0, -600);          // scroll UP, as a person would
await page.waitForTimeout(200);
const releasedLabel = await page.textContent('#stick');
const beforeTop = await page.$eval('#scroller', (el) => el.scrollTop);
await page.waitForTimeout(700); // more tokens land in this window
const afterTop = await page.$eval('#scroller', (el) => el.scrollTop);
check('a reader who scrolls up is not dragged back down',
      releasedLabel === 'released' && Math.abs(afterTop - beforeTop) < 6,
      `label=${releasedLabel} scrollTop ${beforeTop}->${afterTop}`);

// --- jump-to-latest --------------------------------------------------------
// The affordance that makes sticky-bottom bearable: it must appear only when
// the reader has left the bottom, and it must actually bring them back.
check('the jump button appears once the reader scrolls away', await page.isVisible('#jump'));

await page.click('#jump');
await page.waitForTimeout(250); // instant snap, just let the event land
const backAtBottom = await page.$eval('#scroller',
  (el) => el.scrollHeight - el.scrollTop - el.clientHeight);
const jumpHiddenAgain = !(await page.isVisible('#jump'));
const labelAfterJump = await page.textContent('#stick');
check('the jump button returns to the bottom, re-pins, and hides itself',
      backAtBottom < 60 && jumpHiddenAgain && labelAfterJump === 'pinned',
      `distance=${Math.round(backAtBottom)}px hidden=${jumpHiddenAgain} label=${labelAfterJump}`);

// --- touch scrolling --------------------------------------------------------
// Wheel is covered above; this is the OTHER real input path, and it was only
// assumed to work until now. Runs in a touch-enabled context and drives a
// genuine swipe, because `touchmove` never fires from a synthetic scroll.
const touchCtx = await browser.newContext({ ignoreHTTPSErrors: true, hasTouch: true });
const touchPage = await touchCtx.newPage();
await touchPage.goto(BASE, { waitUntil: 'load' });
await touchPage.waitForSelector('#send');
await touchPage.click('#send');
await touchPage.waitForFunction(() => {
  const el = document.getElementById('scroller');
  return el.scrollHeight > el.clientHeight + 100;
}, { timeout: 20000 });

const tbox = await touchPage.$eval('#scroller', (el) => {
  const r = el.getBoundingClientRect();
  return { x: r.x + r.width / 2, top: r.y + 40, bottom: r.y + r.height - 40 };
});
// Swipe DOWNWARD on the surface = content moves up = scrolling back.
await touchPage.touchscreen.tap(tbox.x, tbox.bottom);
await touchPage.evaluate(({ x, top, bottom }) => {
  const el = document.getElementById('scroller');
  const touch = (y) => new Touch({ identifier: 1, target: el, clientX: x, clientY: y });
  el.dispatchEvent(new TouchEvent('touchstart', { touches: [touch(top)], bubbles: true }));
  el.scrollTop = Math.max(0, el.scrollTop - 220);   // what the gesture produces
  el.dispatchEvent(new TouchEvent('touchmove', { touches: [touch(bottom)], bubbles: true }));
  el.dispatchEvent(new TouchEvent('touchend', { touches: [], bubbles: true }));
}, tbox);
await touchPage.waitForTimeout(250);
const touchLabel = await touchPage.textContent('#stick');
check('touch scrolling releases the pin', touchLabel === 'released', `label=${touchLabel}`);

const touchJumpVisible = await touchPage.isVisible('#jump');
check('the jump button appears for touch readers too', touchJumpVisible);
await touchCtx.close();

// --- stop ------------------------------------------------------------------
await page.click('#stop');
await page.waitForTimeout(300);
const stopped = await page.evaluate(() => window.__spikeResult);
check('the stop button stops the stream',
      stopped && stopped.outcome === 'stopped'
        && stopped.tokens > 0 && stopped.tokens < TOTAL_TOKENS,
      JSON.stringify(stopped));
const statusAfter = await page.textContent('#status');
check('the composer returns to idle after stop', statusAfter === 'idle', `status=${statusAfter}`);

// --- full run, markdown correctness ---------------------------------------
await page.click('#send');
await page.waitForFunction(
  () => document.getElementById('status').textContent === 'idle', { timeout: 30000 });
const codeBlocks = await page.$$('#output pre code');
const strong = await page.$$('#output strong');
const finalText = await page.textContent('#output');
check('the finished document renders both code blocks and emphasis, with no raw fences',
      codeBlocks.length >= 2 && strong.length > 0 && !finalText.includes('```'),
      `pre=${codeBlocks.length} strong=${strong.length}`);

await browser.close();

const failed = results.filter((r) => !r.pass);
console.log(`\n${results.length - failed.length}/${results.length} browser criteria passed`);
process.exit(failed.length ? 1 : 0);
