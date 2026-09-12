/* Sage.is AI service worker.
 *
 * main.py serves this file from the site root through a dedicated route.
 * Worker scope is limited: a copy under /pages/_assets/ could control only
 * that directory. The route replaces __VERSION__ with the release, removing
 * old caches, and sets Cache-Control: no-cache, so browsers pick up a redeploy
 * on the next navigation.
 *
 * We cache two kinds of public files.
 *
 *   /_app/immutable/   The build hashes these filenames, so the name changes
 *                      when the bytes change. A hit is always correct and
 *                      never needs revalidating.
 *   /static/, /pages/_assets/  Deploys version these, not hashes. Serve from
 *                      cache; refresh in the background. Worst case: one
 *                      release-old file once.
 *
 *
 *   - non-GET requests
 *   - /api/, /ws/, and /socket.io/ (authenticated, streaming, mutating)
 *   - navigations (always to the network; offline card only after a failure)
 *   - /manifest.json and /themes/active.css (live config; no-cache upstream)
 *   - Range requests (the Cache API mishandles 206, breaking audio/video seek)
 *   - cross-origin requests (opaque responses use large quota; uninspectable)
 *
 * Every branch fails open. A cache error must never break the app; the
 * request still reaches the network.
 *
 * TURNING IT OFF
 * --------------
 * Deploy with ENABLE_SERVICE_WORKER=false. The route answers with a worker
 * that deletes these caches and unregisters itself on the next load. The
 * visitor does nothing. This makes it safe to ship on by default.
 */

const VERSION = '__VERSION__';
const ASSET_CACHE = `sage-assets-${VERSION}`;
const OFFLINE_URL = '/pages/_assets/offline.html';

/* Build-hashed; the filename changes when the bytes change. Keep forever. */
const IMMUTABLE = /^\/_app\/immutable\//;

/* Deploy-versioned; serve fast from cache, then refresh for next time. */
const REFRESHABLE = /^\/(?:static|pages\/_assets)\/.+\.(?:css|js|mjs|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf)$/;

/* Never cached; listed here for the reader. */
const NEVER = /^\/(?:api|ws|socket\.io|themes|manifest\.json|health)\b/;

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches
			.open(ASSET_CACHE)
			.then((cache) => cache.add(new Request(OFFLINE_URL, { cache: 'reload' })))
			.catch(() => {})
			.then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) =>
				Promise.all(
					keys.filter((key) => key.startsWith('sage-') && key !== ASSET_CACHE).map((key) => caches.delete(key))
				)
			)
			.catch(() => {})
			.then(() => self.clients.claim())
	);
});

self.addEventListener('fetch', (event) => {
	const request = event.request;
	if (request.method !== 'GET') return;
	if (request.headers.has('range')) return;

	let url;
	try {
		url = new URL(request.url);
	} catch {
		return;
	}
	if (url.origin !== self.location.origin) return;
	if (NEVER.test(url.pathname)) return;

	if (request.mode === 'navigate') {
		event.respondWith(networkThenOfflineCard(request));
		return;
	}

	if (IMMUTABLE.test(url.pathname)) {
		event.respondWith(cacheFirst(request));
		return;
	}

	if (REFRESHABLE.test(url.pathname)) {
		event.respondWith(cacheThenRefresh(request));
	}
});

/* We never cache documents. A failed navigation gets the card, but only if the
   card survived install. Otherwise, the browser shows its own error page,
   which is still better than a blank frame. */
async function networkThenOfflineCard(request) {
	try {
		return await fetch(request);
	} catch (err) {
		const card = await caches.match(OFFLINE_URL);
		if (card) return card;
		throw err;
	}
}

async function cacheFirst(request) {
	const hit = await caches.match(request).catch(() => undefined);
	if (hit) return hit;

	const response = await fetch(request);
	if (response.ok && response.type === 'basic') {
		put(request, response.clone());
	}
	return response;
}

/* Serve the cached copy, then refresh the entry for next time. Ignore refresh
   failures; the visitor already has a response. */
async function cacheThenRefresh(request) {
	const hit = await caches.match(request).catch(() => undefined);

	const refresh = fetch(request)
		.then((response) => {
			if (response.ok && response.type === 'basic') {
				put(request, response.clone());
			}
			return response;
		})
		.catch(() => undefined);

	if (hit) return hit;

	const response = await refresh;
	if (response) return response;
	return fetch(request);
}

function put(request, response) {
	caches
		.open(ASSET_CACHE)
		.then((cache) => cache.put(request, response))
		.catch(() => {});
}
