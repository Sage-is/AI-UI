// Phase 4 gate probe — one Svelte runtime, or one per biome? THROWAWAY.
//
// The plan's biome strategy rests on a claim it explicitly refuses to assume:
// "all biomes share ONE Svelte runtime — each inlining its own would be a
// shattered SPA, not islands." This measures it two ways, in bytes and at
// runtime, and then measures the same thing against a build shape that MUST
// fail. The control is the point. Phase S shipped an autoscroll that went 13/13
// green and was broken in the hand, so a suite that has never said no is not
// evidence.
import { chromium } from 'playwright';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const BASE = process.env.BIOME_BASE || 'http://biome-web:8000';

// Two markers, both surviving an unminified build intact.
//
// The runtime marker is the DECLARATION of Svelte's dirty-component queue, not
// a mention of it. That distinction bit: the first version matched any mention
// and reported two runtimes in a build that has one, because Rollup had split
// the runtime across two cooperating chunks — one defines the queue, the other
// re-exports through it. Counting mentions measures chunking; counting
// declarations measures instances, which is the question.
const RUNTIME_DECL = /(?:const|let|var)\s+dirty_components\s*=/;
const SHARED_MARKER = 'shared-state-module';

const results = [];
const check = (name, pass, detail = '') => {
  results.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
};

function chunkGraph(dirs) {
  const files = [];
  for (const dir of dirs) {
    for (const f of readdirSync(dir)) {
      if (!f.endsWith('.js')) continue;
      const p = join(dir, f);
      const src = readFileSync(p, 'utf8');
      files.push({
        path: p.replace(/^dist\//, ''),
        bytes: statSync(p).size,
        runtime: RUNTIME_DECL.test(src),
        shared: src.includes(SHARED_MARKER)
      });
    }
  }
  return files;
}

function reportGraph(label, files) {
  console.log(`\n  ${label}`);
  for (const f of files) {
    const tags = [f.runtime ? 'runtime' : null, f.shared ? 'shared-state' : null]
      .filter(Boolean).join(' + ') || '—';
    console.log(`    ${String(f.bytes).padStart(7)} B  ${f.path.padEnd(34)} ${tags}`);
  }
}

// --- what the browser sees --------------------------------------------------
async function inspect(page, url) {
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => (window.__biomes || []).length >= 2, { timeout: 15000 });

  const identity = await page.evaluate(() => {
    const b = window.__biomes;
    // Identity comparisons happen IN the page — functions and objects cannot
    // cross the evaluate boundary, only the verdict can.
    const allSameFlush = b.every((x) => x.flush === b[0].flush);
    const allSameTicket = b.every((x) => x.ticket === b[0].ticket);
    return { mounted: b.map((x) => x.tag), allSameFlush, allSameTicket };
  });

  // Cross-talk: a write inside biome A, observed inside biome B. This is the
  // consequence that actually matters — identity is the mechanism, shared state
  // is what the shell flip depends on.
  await page.locator('[data-inc="a"]').click();
  await page.waitForTimeout(100);
  const counts = await page.evaluate(() => ({
    a: document.querySelector('biome-a')?.shadowRoot?.querySelector('[data-count="a"]')?.textContent,
    b: document.querySelector('biome-b')?.shadowRoot?.querySelector('[data-count="b"]')?.textContent
  }));

  const css = await page.evaluate(() => {
    const shadowed = document.querySelector('biome-a')?.shadowRoot?.querySelector('[data-styled]');
    // Biome C opts out of the shadow root, so it lives in light DOM.
    const light = document.querySelector('biome-c [data-styled-c]');
    const control = document.querySelector('[data-control]');
    const colour = (el) => (el ? getComputedStyle(el).color : null);
    return { shadowed: colour(shadowed), light: colour(light), control: colour(control) };
  });

  return { ...identity, counts, css };
}

const browser = await chromium.launch();
const page = await browser.newPage();

// --- the shape we would ship ------------------------------------------------
console.log('=== shape A: one build, three biomes (what we would ship) ===');
const sharedFiles = chunkGraph(['dist/shared']);
reportGraph('chunk graph', sharedFiles);

const sharedRuntimeCopies = sharedFiles.filter((f) => f.runtime).length;
const sharedStateCopies = sharedFiles.filter((f) => f.shared).length;
console.log('');
check('the Svelte runtime is in exactly one file',
  sharedRuntimeCopies === 1, `${sharedRuntimeCopies} of ${sharedFiles.length} chunks carry it`);
check('the shared app module is in exactly one file',
  sharedStateCopies === 1, `${sharedStateCopies} copies`);

const shared = await inspect(page, `${BASE}/shared.html`);
check('all three biomes mount from plain HTML, no SvelteKit',
  shared.mounted.length === 3, shared.mounted.join(', '));
check('every biome holds the SAME runtime scheduler', shared.allSameFlush);
check('every biome holds the SAME shared module instance', shared.allSameTicket);
check('a store written in biome A is observed in biome B',
  shared.counts.a === '1' && shared.counts.b === '1',
  `a=${shared.counts.a} b=${shared.counts.b}`);

// The SvelteKit shims — the per-biome work the plan calls small. Measured
// against the real surface: 64 of 317 components in app/src import `$app/*`,
// and between them use 9 symbols. `goto` (54) and `page` (26) are 80 of the 81
// import sites, so these two are essentially the whole job.
//
// Biome C imports all three modules and only built because the alias resolved.
// Prove it also RUNS, and that `$page` reacts — a `page` store that never
// updates would leave 26 components rendering a stale route after every goto,
// silently.
const beforeUrl = page.url();
const pathBefore = await page.textContent('[data-path]');
await page.locator('[data-goto]').click();
await page.waitForTimeout(100);
const afterUrl = page.url();
const pathAfter = await page.textContent('[data-path]');
check('a biome importing $app/navigation builds and navigates through the shim',
  afterUrl.endsWith('/probe-navigated') && afterUrl !== beforeUrl, afterUrl);
check('the $app/stores `page` shim tracks that navigation',
  pathAfter === '/probe-navigated' && pathAfter !== pathBefore,
  `${pathBefore} -> ${pathAfter}`);
check('the $app/environment shim reports a browser',
  (await page.textContent('[data-browser]')) === 'true');

// --- the negative control ---------------------------------------------------
console.log('\n=== shape B: independent builds (control — these MUST fail) ===');
const splitFiles = chunkGraph(['dist/split-a', 'dist/split-b', 'dist/split-c']);
reportGraph('chunk graph', splitFiles);

const splitRuntimeCopies = splitFiles.filter((f) => f.runtime).length;
console.log('');
check('CONTROL: independent builds duplicate the runtime (probe can detect it)',
  splitRuntimeCopies > 1, `${splitRuntimeCopies} copies`);

const split = await inspect(page, `${BASE}/split.html`);
check('CONTROL: independently-built biomes do NOT share a scheduler',
  split.allSameFlush === false, `allSameFlush=${split.allSameFlush}`);
check('CONTROL: independently-built biomes do NOT share module state',
  split.allSameTicket === false, `allSameTicket=${split.allSameTicket}`);
check('CONTROL: the store does not cross between independently-built biomes',
  split.counts.a === '1' && split.counts.b === '0',
  `a=${split.counts.a} b=${split.counts.b}`);

// --- the biome that ships later ---------------------------------------------
// A ui-Sprig grafted next month is a separate build. Shape B is what that costs
// by default. This is the escape hatch: externalise the runtime and the host
// stores, and a late biome carries only itself.
console.log('\n=== shape C: a biome built later, borrowing the host runtime ===');
const lateFiles = chunkGraph(['dist/late']);
reportGraph('chunk graph', lateFiles);
console.log('');
check('a late biome carries NO runtime of its own',
  lateFiles.every((f) => !f.runtime), `${lateFiles.filter((f) => f.runtime).length} copies`);

const late = await inspect(page, `${BASE}/late.html`);
check('a late biome shares the host runtime scheduler', late.allSameFlush);
check('a store written in the host biome reaches the late biome',
  late.counts.a === '1' && late.counts.b === '1',
  `a=${late.counts.a} b=${late.counts.b}`);

// --- observed, not asserted -------------------------------------------------
// A biome's shadow root is a CSS boundary. Whether that is a feature or a
// migration cost is a decision, not a pass/fail, so the probe reports it — and
// reports that the boundary is optional, since `shadow: 'none'` removes it.
const reaches = (c) => (c === shared.css.control ? 'REACHES' : 'DOES NOT REACH');
console.log('\n=== observed (not a pass/fail) ===');
console.log(`  app rule in light DOM (control)        : ${shared.css.control}`);
console.log(`  same rule inside a shadowed biome      : ${shared.css.shadowed}  => ${reaches(shared.css.shadowed)}`);
console.log(`  same rule inside a shadow:'none' biome : ${shared.css.light}  => ${reaches(shared.css.light)}`);

// What the shapes cost. Unminified, so read the ratios, not the absolutes.
const total = (files) => files.reduce((n, f) => n + f.bytes, 0);
const minFiles = chunkGraph(['dist/shared-min']);
const isEntry = (f) => /biome-[abc]\.js$/.test(f.path);

console.log('\n=== what each shape costs (unminified — read the ratios) ===');
console.log(`  Phase 3 shape, tree-shaken  : ${total(minFiles)} B ` +
  `(${total(minFiles.filter(isEntry))} B of it is the three biomes)`);
console.log(`  host publishes its runtime  : ${total(sharedFiles)} B ` +
  `— the price of letting biomes ship later, because an \`export *\` keeps the`);
console.log('                                whole runtime surface alive and defeats tree-shaking');
console.log(`  a late biome then costs     : ${total(lateFiles)} B, and nothing more`);
console.log(`  three independent builds    : ${total(splitFiles)} B, one runtime each, no shared state`);

await browser.close();

const failed = results.filter((r) => !r.pass);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
