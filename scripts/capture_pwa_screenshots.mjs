#!/usr/bin/env node
/**
 * Capture the two screenshots the web app manifest points at, and prove the
 * service worker cached nothing it should not have.
 *
 *   ORIGIN=http://localhost:8080 node scripts/capture_pwa_screenshots.mjs
 *
 * Writes app/static/screenshots/{wide,narrow}-chat.png at exactly the sizes
 * declared in the manifest route in main.py. Chrome drops a screenshot whose
 * declared size misses the file, silently, which is the same trap the manifest
 * icons were already in — an icon claiming 512x512 while being 256x256. So the
 * dimensions live here and there and nowhere else, and this script asserts the
 * page really laid out at the width it asked for.
 *
 * WHY CDP AND NOT --window-size
 * -----------------------------
 * Headless Chrome will not lay out below about 500px wide. Ask for 412 and it
 * lays out at 500, then CROPS the image down to 412 — so the right-hand strip
 * is missing and nothing reports an error. Emulation.setDeviceMetricsOverride
 * on the loaded page is the only thing that produces a true phone viewport,
 * and `measured` below is the receipt.
 *
 * WHAT IT ASSERTS ABOUT THE WORKER
 * --------------------------------
 * The browser is already open and signed in, so it also walks the worker's
 * caches and fails if a document or an API response is in one. That property
 * is the whole reason the worker is safe to ship on by default: this product
 * is multi-user and its HTML is rendered for whoever is signed in. See the
 * header of app/backend/sage_is_ai/pages/assets/sw.js.
 *
 * Needs an instance with a signed-in-able account. Defaults match the seeded
 * administrator that `make dev` prints on boot.
 */

import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const ORIGIN = process.env.ORIGIN || 'http://localhost:8080';
const OUT = process.env.OUT || 'app/static/screenshots';
const EMAIL = process.env.PWA_EMAIL || 'admin@example.com';
const PASSWORD = process.env.PWA_PASSWORD || 'password';
const PORT = Number(process.env.CDP_PORT || 9333);
const CHROME =
	process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PROFILE = '/tmp/pwa-capture-profile';

// The agent the screenshots are taken as. Named rather than a raw model id,
// because the header is the first thing anyone reads in an install dialog.
const AGENT_ID = process.env.PWA_AGENT_ID || 'sage';
const AGENT_NAME = process.env.PWA_AGENT_NAME || 'Sage \u{1F353}';

// The line under the agent's name in both shots, adapted from Sage.is copy: the
// On-Prem page's subtitle and its Enterprise line on custom agents. Keep it to
// two lines at 412px. The app cuts an agent's description there, and a longer
// line loses its end in the narrow shot. Must match PWA_SCREENSHOT_LABEL in
// main.py, which captions these same images.
const AGENT_DESCRIPTION =
	process.env.PWA_AGENT_DESCRIPTION ||
	'Your hardware. Your data. Your AI. Work with your data and build custom agents.';

// Must match the `screenshots` entries in main.py's /manifest.json route.
const SHOTS = [
	{ name: 'wide-chat', width: 1280, height: 800, mobile: false },
	{ name: 'narrow-chat', width: 412, height: 915, mobile: true }
];

const problems = [];

mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, [
	'--headless=new',
	`--remote-debugging-port=${PORT}`,
	'--no-first-run',
	'--no-default-browser-check',
	'--disable-gpu',
	'--hide-scrollbars',
	`--user-data-dir=${PROFILE}`,
	ORIGIN + '/auth'
]);
chrome.stderr.on('data', () => {});

let target;
for (let i = 0; i < 40 && !target; i++) {
	await sleep(400);
	try {
		const res = await fetch(`http://127.0.0.1:${PORT}/json`);
		target = (await res.json()).find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
	} catch {}
}
if (!target) die('Chrome never exposed a page target');

// Node's built-in WebSocket is the WHATWG one: addEventListener, not .on().
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
	ws.addEventListener('open', resolve, { once: true });
	ws.addEventListener('error', reject, { once: true });
});

let id = 0;
const pending = new Map();
ws.addEventListener('message', (event) => {
	const msg = JSON.parse(event.data);
	if (msg.id && pending.has(msg.id)) {
		pending.get(msg.id)(msg);
		pending.delete(msg.id);
	}
});

function send(method, params = {}) {
	const n = ++id;
	return new Promise((resolve) => {
		pending.set(n, resolve);
		ws.send(JSON.stringify({ id: n, method, params }));
	});
}

async function evaluate(expression) {
	const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
	return r.result?.result?.value;
}

function die(message) {
	console.error('FAIL:', message);
	try {
		chrome.kill('SIGKILL');
	} catch {}
	process.exit(1);
}

await send('Page.enable');
await send('Runtime.enable');

async function navigate(url) {
	await send('Page.navigate', { url });
	for (let i = 0; i < 60; i++) {
		await sleep(300);
		if ((await evaluate('document.readyState')) === 'complete') return;
	}
}

/* The splash overlay sits above everything until the SPA mounts, and on the
   Vite dev server that is a compile rather than a paint. Waiting on the overlay
   beats guessing a number — a guessed sleep is how a loading spinner ends up in
   a store listing. */
async function waitForApp(label) {
	for (let i = 0; i < 120; i++) {
		const state = await evaluate(`
			(() => {
				const splash = document.getElementById('splash-screen');
				const visible = splash && getComputedStyle(splash).display !== 'none' && splash.offsetParent !== null;
				return JSON.stringify({ splash: !!visible, text: document.body.innerText.trim().length });
			})()
		`);
		const { splash, text } = JSON.parse(state || '{}');
		if (!splash && text > 0) return true;
		await sleep(500);
	}
	problems.push(`${label}: the app never finished mounting`);
	return false;
}

/* First run is a CHAIN of modals — release notes, then the setup wizard — so
   dismissing one reveals the next. Close whatever is on top and look again,
   rather than encoding an order that changes every release. */
async function closeModals() {
	for (let round = 0; round < 6; round++) {
		const open = await evaluate(`
			[...document.querySelectorAll('div,section')].filter((el) => {
				const s = getComputedStyle(el);
				return s.position === 'fixed' && s.display !== 'none'
					&& el.offsetWidth > 200 && el.offsetHeight > 200 && el.querySelector('button');
			}).length
		`);
		if (!open) return;
		for (const type of ['keyDown', 'keyUp']) {
			await send('Input.dispatchKeyEvent', {
				type,
				key: 'Escape',
				code: 'Escape',
				windowsVirtualKeyCode: 27,
				nativeVirtualKeyCode: 27
			});
		}
		await sleep(700);
		await evaluate(`
			(() => {
				const buttons = [...document.querySelectorAll('button')].filter((b) => {
					const r = b.getBoundingClientRect();
					return r.width > 0 && r.width < 60 && r.height < 60 && r.top < window.innerHeight * 0.35;
				});
				const rightmost = buttons.sort((a, b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right)[0];
				if (rightmost) rightmost.click();
			})()
		`);
		await sleep(900);
	}
}

/* "Set as default" is drawn --pos:absolute with a negative top margin
   (ModelSelector.svelte), so it overlaps the Temporary Chat control underneath
   and both render on top of each other. Clicking it is not a workaround for the
   camera: it puts the instance in the state most installs are actually in, with
   a default model chosen, and the label hides itself once that is true. */
async function chooseDefaultModel() {
	const clicked = await evaluate(`
		(() => {
			const button = [...document.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Set as default');
			if (button) { button.click(); return true; }
			return false;
		})()
	`);
	if (!clicked) return;

	await waitForToasts();
}

/* A toast caught mid-fade is worse in a still than one at full opacity. Wait
   for it to leave, and require it to STAY gone: sonner mounts its list a beat
   after the click, so a single "not there yet" reads as "already finished". */
async function waitForToasts() {
	let clearRuns = 0;
	for (let i = 0; i < 40; i++) {
		await sleep(400);
		const visible = await evaluate(`
			[...document.querySelectorAll('[data-sonner-toast], [data-sonner-toaster] li, [role="status"]')]
				.filter((el) => el.offsetParent !== null && el.textContent.trim()).length
		`);
		clearRuns = visible ? 0 : clearRuns + 1;
		if (clearRuns >= 4) return;
	}
	problems.push('a toast never cleared; the capture would show it mid-animation');
}

async function shoot({ name, width, height, mobile }) {
	await send('Emulation.setDeviceMetricsOverride', {
		width,
		height,
		deviceScaleFactor: 1,
		mobile
	});
	await sleep(1500);
	await waitForApp(name);
	await closeModals();
	await waitForToasts();

	// Park the pointer in a dead corner. It starts at 0,0, which sits on the
	// model selector and paints its hover state into the file.
	await send('Input.dispatchMouseEvent', {
		type: 'mouseMoved',
		x: Math.floor(width / 2),
		y: height - 4,
		button: 'none'
	});
	await sleep(1200);

	const measured = await evaluate('document.documentElement.clientWidth');
	if (measured !== width) {
		problems.push(`${name}: asked for ${width}px, the page laid out at ${measured}px`);
	}

	const shot = await send('Page.captureScreenshot', { format: 'png' });
	const file = `${OUT}/${name}.png`;
	writeFileSync(file, Buffer.from(shot.result.data, 'base64'));
	console.log(`  ${name}  ${width}x${height}  measured ${measured}px  ->  ${file}`);
}

/* Nothing tied to an account may sit in the worker's caches. This is the
   security property, so it is asserted rather than assumed. */
async function auditServiceWorkerCaches() {
	const report = await evaluate(`
		caches.keys()
			.then(async (keys) => {
				const named = keys.filter((k) => k.startsWith('sage-'));
				const offenders = [];
				let total = 0;
				for (const key of named) {
					const cache = await caches.open(key);
					for (const request of await cache.keys()) {
						total++;
						const response = await cache.match(request);
						const type = (response.headers.get('content-type') || '').split(';')[0];
						const path = new URL(request.url).pathname;
						if (path.startsWith('/api/')) offenders.push(path);
						else if (type === 'text/html' && path !== '/pages/_assets/offline.html') offenders.push(path);
					}
				}
				return JSON.stringify({ caches: named, total, offenders });
			})
			.catch((e) => JSON.stringify({ error: e.message }))
	`);
	const { caches: names = [], total = 0, offenders = [], error } = JSON.parse(report || '{}');
	if (error) {
		problems.push(`cache audit failed: ${error}`);
		return;
	}
	console.log(`  caches ${JSON.stringify(names)}  ${total} entr${total === 1 ? 'y' : 'ies'}`);
	if (offenders.length) {
		problems.push(`the worker cached account-scoped responses: ${offenders.join(', ')}`);
	}
}

// ── run ─────────────────────────────────────────────────────────────────────
await navigate(ORIGIN + '/auth');
const signin = await evaluate(`
	fetch('/api/v1/auths/signin', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email: ${JSON.stringify(EMAIL)}, password: ${JSON.stringify(PASSWORD)} })
	})
	.then((r) => r.json())
	.then((d) => { if (d.token) { localStorage.token = d.token; return 'ok'; } return JSON.stringify(d); })
	.catch((e) => 'ERR ' + e.message)
`);
if (signin !== 'ok') die(`could not sign in as ${EMAIL}: ${signin}`);

await navigate(ORIGIN + '/');
await waitForApp('boot');

// Settings live on the server here, not in localStorage, so the release-notes
// modal is stamped away through the API rather than clicked.
await evaluate(`
	fetch('/api/v1/users/user/settings/update', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + localStorage.token },
		body: JSON.stringify({ ui: { showChangelog: false } })
	}).then((r) => r.status + '').catch((e) => 'ERR ' + e.message)
`);
await navigate(ORIGIN + '/');
await waitForApp('after-dismiss');

/* The header shows whichever model is selected, and a raw
   "MichelRosselli/ternary-bonsai:1.7b-f16" in an install dialog reads as
   somebody else's half-configured instance. Ship a named agent instead.
   Idempotent: a second run updates it in place rather than adding another. */
async function ensureAgent() {
	return evaluate(`
		(async () => {
			const headers = { Authorization: 'Bearer ' + localStorage.token, 'Content-Type': 'application/json' };
			const mine = await fetch('/api/v1/models/', { headers }).then((r) => r.json()).catch(() => []);
			const existing = Array.isArray(mine) ? mine.find((m) => m.id === ${JSON.stringify(AGENT_ID)}) : null;

			// /api/v1/models/base lists custom models, which is empty on a fresh
			// instance. The models a connection actually offers come from the
			// aggregated /api/models. arena-model is a router, not a model.
			let base = existing && existing.base_model_id;
			if (!base) {
				const listed = await fetch('/api/models', { headers }).then((r) => r.json()).catch(() => null);
				const items = Array.isArray(listed) ? listed : (listed && listed.data) || [];
				base = (items.find((m) => m.id && m.id !== 'arena-model') || {}).id;
			}
			if (!base) return '';

			// Create it, or bring an existing one up to date. An agent left from an
			// earlier run would otherwise keep its old line and put it in the shot.
			// Its base model, params and sharing are kept; only the copy moves.
			const url = existing
				? '/api/v1/models/model/update?id=' + encodeURIComponent(${JSON.stringify(AGENT_ID)})
				: '/api/v1/models/create';
			const saved = await fetch(url, {
				method: 'POST',
				headers,
				body: JSON.stringify({
					id: ${JSON.stringify(AGENT_ID)},
					name: ${JSON.stringify(AGENT_NAME)},
					base_model_id: base,
					meta: {
						...((existing && existing.meta) || {}),
						profile_image_url: '/static/icons/favicon.png',
						description: ${JSON.stringify(AGENT_DESCRIPTION)}
					},
					params: (existing && existing.params) || {},
					access_control: existing ? existing.access_control : null
				})
			}).then((r) => r.json()).catch(() => null);
			return saved && saved.id ? saved.id : '';
		})()
	`);
}

const agent = await ensureAgent();
if (agent) {
	await navigate(`${ORIGIN}/?models=${encodeURIComponent(agent)}`);
	await waitForApp('agent-selected');
} else {
	problems.push(`could not create or update the ${AGENT_NAME} agent — no base model, or the save was refused`);
}

// Once, in setup. The default is stored server-side, so both captures inherit
// it — and neither races the toast that saving it raises.
await closeModals();
await chooseDefaultModel();

console.log(`capturing against ${ORIGIN} as ${agent || 'no agent'}`);
for (const spec of SHOTS) await shoot(spec);
await auditServiceWorkerCaches();

ws.close();
chrome.kill('SIGKILL');

if (problems.length) {
	console.error('\nFAIL');
	for (const problem of problems) console.error(`  - ${problem}`);
	process.exit(1);
}
console.log('\nOK — both viewports honoured, no account-scoped response cached');
process.exit(0);
