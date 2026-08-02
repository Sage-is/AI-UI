/// <reference types="cypress" />

// What a page cost, read from the browser rather than reasoned about.
//
// This lived inside `cypress/e2e/upgrade/workshop-payload.cy.ts` until a second
// measurement needed it. It is here rather than copied because the first version
// shipped a timing bug — see `origin` below — and a copy would have needed the
// same fix twice, which is how one of the two copies ends up wrong.
//
// Nothing here asserts. These are measurements; the specs that use them live
// under `cypress/e2e/upgrade/` so the default spec glob never picks them up.

export type Res = { url: string; transfer: number; decoded: number };

export type Section = {
	note: string;
	requests: number;
	/** Bytes over the wire — what the network paid for. */
	transferKB: number;
	/** Bytes after decompression — what the main thread had to parse. */
	decodedKB: number;
	/** The HTML document alone. For a server-rendered page this IS the payload. */
	documentDecodedKB: number;
	rows: number;
	/** Milliseconds from the start of this measurement until the content is in the DOM. */
	toContentMs: number;
	lastByteMs: number;
	modelsEndpointCalls: string[];
	top: Res[];
};

/**
 * Everything the browser fetched for THIS document, navigation entry included.
 *
 * The navigation entry is counted on purpose. For a server-rendered page the
 * HTML is the payload, so measuring only subresources would score its main cost
 * as zero — a bias in the migration's favour, in a measurement that exists to
 * check the migration.
 */
export const collect = (
	win: Window,
	note: string,
	toContentMs: number,
	rows: number,
	// Where this measurement's clock starts, on the page's own `performance`
	// timeline. 0 for a document load; the click instant for an in-app one.
	origin: number,
	// An in-app navigation happens INSIDE an already-loaded document, so the
	// navigation entry belongs to the page it started from. Counting it there
	// would charge the previous page's bytes to the route being measured.
	withDocument = true
): Section => {
	const strip = (u: string) => u.replace(win.location.origin, '');
	const resEntries = win.performance.getEntriesByType('resource') as PerformanceResourceTiming[];
	const resources = resEntries.map((r) => ({
		url: strip(r.name),
		transfer: r.transferSize || 0,
		decoded: r.decodedBodySize || 0
	}));

	const nav = (win.performance.getEntriesByType('navigation') as PerformanceNavigationTiming[])[0];
	const doc: Res[] =
		withDocument && nav
			? [
					{
						url: `${strip(nav.name)}  (document)`,
						transfer: nav.transferSize || 0,
						decoded: nav.decodedBodySize || 0
					}
				]
			: [];

	const all = [...doc, ...resources];
	const sum = (k: 'transfer' | 'decoded') => all.reduce((a, r) => a + r[k], 0);
	// Timing is measured INSIDE the browser and relative to `origin`. The first
	// version used `Date.now()` in the test body, which executes when Cypress
	// QUEUES the commands rather than when they run — so the in-app number
	// silently included the app's whole boot and a deliberate 3-second settle,
	// and was dashed out rather than published. An empty cell beside 919 kB
	// reads as "too fast to matter" when the bytes say the opposite. A timing
	// wrong by the size of the thing being measured is worse than no timing, and
	// a blank you decline to explain is still a claim.
	const ends = resEntries.map((r) => r.responseEnd - origin);
	if (withDocument && nav) ends.push(nav.responseEnd);

	return {
		note,
		requests: all.length,
		transferKB: +(sum('transfer') / 1024).toFixed(1),
		decodedKB: +(sum('decoded') / 1024).toFixed(1),
		documentDecodedKB: +((doc[0]?.decoded ?? 0) / 1024).toFixed(1),
		rows,
		toContentMs,
		lastByteMs: ends.length ? Math.round(Math.max(...ends)) : 0,
		// `/api/models` rides in the `(app)` layout's boot wave, so EVERY route
		// pays it. Counting it per route is what turns "the workshop page is
		// heavy" into "every page is heavy and this one adds to it".
		modelsEndpointCalls: all
			.filter((r) => /\/api\/models|\/api\/v1\/models/.test(r.url))
			.map((r) => `${r.url}  ${(r.decoded / 1024).toFixed(1)} kB`),
		top: [...all].sort((a, b) => b.decoded - a.decoded).slice(0, 25)
	};
};

/** The throwaway admin `scripts/smoke/upgrade-gate.sh` injects into the snapshot COPY. */
export const SNAPSHOT_ADMIN = {
	email: () => Cypress.env('ADMIN_EMAIL') || 'upgrade-gate@sage.is',
	password: () => Cypress.env('ADMIN_PASSWORD') || 'upgrade-gate-pw-1234'
};
