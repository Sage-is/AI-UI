// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../../support/index.d.ts" />

// MEASUREMENT, not a gate. It asserts almost nothing and it must never be
// wired into `make e2e` — living under `upgrade/` keeps it out, because the
// default spec glob takes the top level only.
//
// WHY. Production `/workshop/models` was reported at 144 requests, 20,520 kB and
// 32 seconds. Two theories about where that goes have been published on the
// board and the first was refuted by one query: agent avatars are 868 kB, not
// 20 MB. The second explained ~1.5 MB. Roughly 19 MB is unaccounted for, and
// the board says in those words that guessing twice is enough. So this reads the
// browser's own resource timings on a copy of a production snapshot instead.
//
// Run it against the container `KEEP=1 make upgrade_gate` leaves up:
//
//   TARGET_URL=http://sage-upgrade:8080 \
//   CYPRESS_ADMIN_EMAIL=upgrade-gate@sage.is \
//   CYPRESS_ADMIN_PASSWORD=upgrade-gate-pw-1234 \
//   SPEC='cypress/e2e/upgrade/workshop-payload.cy.ts' scripts/e2e/run-cypress.sh
//
// NEVER point it at production: it signs in as an administrator. Writes are
// confined to the throwaway admin's OWN ui settings, which the gate injects into
// the COPY — nobody else's data is touched, and the snapshot file itself is
// read-only throughout.
//
// Three things this file does deliberately, each because the obvious version
// would flatter the migration:
//
// 1. It counts the NAVIGATION entry, not just resources. For a server-rendered
//    page the HTML *is* the payload; measuring only subresources would score the
//    no-build page's main cost as zero.
// 2. It reports the SPA route two ways — the cold document, which pays the whole
//    bundle, and the marginal cost of arriving at the route inside an
//    already-booted app, which is what a user in session actually pays. Charging
//    a session's boot to one page would be a number, not a result.
// 3. It records the no-build page's row count beside the SPA's. The no-build
//    page paginates at 24; the SPA renders every agent in one document. A 24-row
//    page measured against a 48-row page is not a comparison.

// `collect` and the snapshot admin live in support/perf.ts, shared with
// `route-payload.cy.ts`. One copy on purpose: the timing bug this file shipped
// first time round would otherwise have needed fixing in two places, which is
// how one of the two ends up wrong.
import { collect, SNAPSHOT_ADMIN, type Section } from '../../support/perf';

const ADMIN_EMAIL = SNAPSHOT_ADMIN.email();
const ADMIN_PASSWORD = SNAPSHOT_ADMIN.password();

const LEGACY = '/workshop/models';
const NOBUILD = '/pages/workshop/agents';
const ROW = '[data-cy="agents-row"]';

const REPORT: Record<string, Section | unknown> = {};

let token = '';
let version = '';

/** Seed the session so no login screen or setup dialog stands in the way. */
const seeded = (win: Window) => {
	win.localStorage.setItem('token', token);
	win.localStorage.setItem('locale', 'en-US');
	win.localStorage.setItem('version', version);
};

/**
 * Both credentials, because the two surfaces do not read the same one.
 *
 * The SPA reads `localStorage.token` and sends it as a bearer header. A
 * server-rendered page cannot read localStorage at all — that is the cookie
 * bridge `pages/auth.py` exists for — so it reads the `token` cookie. Cypress
 * resets both between tests, so seeding one and not the other sent the first
 * run to `/auth?next=/pages/workshop/agents` with a 307 and measured a login
 * screen. Setting only what the surface under test needs would have left the
 * same trap for the next spec.
 */
const signedIn = () => {
	cy.setCookie('token', token);
};

/** Visit, wait for real rows, and record what the browser fetched getting there. */
const measure = (key: string, path: string, note: string) => {
	cy.visit(path, { onBeforeLoad: seeded });
	cy.get(ROW, { timeout: 60000 }).should('have.length.at.least', 1);
	cy.get(ROW).then(($rows) => {
		cy.window().then((win) => {
			// `performance.now()` on a freshly loaded document counts from the
			// navigation start, so this is time-to-first-row with no Cypress
			// overhead in it.
			REPORT[key] = collect(win, note, Math.round(win.performance.now()), $rows.length, 0);
			const s = REPORT[key] as Section;
			cy.log(
				`${key}: ${s.requests} req  ${s.transferKB} kB wire  ${s.decodedKB} kB decoded  ${s.rows} rows  ${s.toContentMs} ms`
			);
		});
	});
};

describe('workshop payload — SPA vs server-rendered, on a production snapshot', () => {
	before(() => {
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			body: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD }
		})
			.then((login) => {
				expect(login.status, 'injected admin signs in').to.eq(200);
				token = login.body.token;
				return cy.request('/api/config');
			})
			.then((cfg) => {
				version = cfg.body.version;
				// The injected admin is brand new, so the setup dialog would open over
				// every page and its own fetches would land in the measurement.
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: { Authorization: `Bearer ${token}` },
					body: { ui: { version, setupCompleted: true, workingAlone: true, showChangelog: false } }
				});
				// The row count the snapshot actually holds. Recorded rather than
				// assumed, because "48 agents" is from a query run days ago against a
				// file that may not be the newest snapshot on disk.
				cy.request({
					url: '/api/v1/models/',
					headers: { Authorization: `Bearer ${token}` }
				}).then((res) => {
					REPORT.snapshot = {
						agentsInList: res.body.length,
						listPayloadKB: +(JSON.stringify(res.body).length / 1024).toFixed(1)
					};
				});
			});
	});

	beforeEach(signedIn);

	after(() => {
		cy.writeFile('cypress/perf-workshop.json', REPORT);
	});

	it('SPA: the cold document', () => {
		measure('legacy-cold', LEGACY, 'first visit — pays the whole SvelteKit bundle');
	});

	it('SPA: the marginal cost of the route inside a booted app', () => {
		// Boot at the chat page first, clear the buffer, then navigate through the
		// SPA's own router by clicking an anchor it will intercept.
		cy.visit('/', { onBeforeLoad: seeded });
		cy.get('#chat-input', { timeout: 60000 }).should('exist');
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(3000); // let the lazy chunks settle so they are not charged to the route

		cy.window().then((win) => {
			win.performance.clearResourceTimings();
			// The clock starts HERE, on the page's own timeline, stamped in the
			// browser at the instant the click is about to happen. Anything read
			// from the test body would be stamped when Cypress queued the command
			// instead, which is what made the first version of this number
			// unpublishable.
			const w = win as Window & { __warm?: boolean; __t0?: number };
			// A flag that cannot survive a document reload. If the router does NOT
			// intercept the click, this test would otherwise report a cold load as
			// a warm one — a failure indistinguishable from success, which is the
			// exact shape this repo keeps finding.
			w.__warm = true;
			w.__t0 = win.performance.now();
			const a = win.document.createElement('a');
			a.href = LEGACY;
			a.setAttribute('data-cy', 'warm-nav');
			a.textContent = 'warm nav';
			win.document.body.appendChild(a);
		});
		cy.get('[data-cy="warm-nav"]').click();
		cy.get(ROW, { timeout: 60000 }).should('have.length.at.least', 1);

		cy.get(ROW).then(($rows) => {
			cy.window().then((win) => {
				const w = win as Window & { __warm?: boolean; __t0?: number };
				REPORT['legacy-warm-route'] =
					w.__warm === true && typeof w.__t0 === 'number'
						? collect(
								win,
								'already-booted app, client-side navigation',
								Math.round(win.performance.now() - w.__t0),
								$rows.length,
								w.__t0,
								false
							)
						: {
								note: 'NOT MEASURED — the click caused a full document load, so this is not a warm number'
							};
				const s = REPORT['legacy-warm-route'] as Section;
				if (s.toContentMs !== undefined) cy.log(`legacy-warm-route: ${s.toContentMs} ms to rows`);
			});
		});
	});

	it('server-rendered: the cold document, page 1', () => {
		measure('nobuild-cold-page1', NOBUILD, 'first visit — its own document, no SvelteKit bundle');
	});

	it('server-rendered: page 2', () => {
		measure('nobuild-page2', `${NOBUILD}?page=2`, 'the second page of the same list');
	});

	it('server-rendered: a repeat visit with a warm cache', () => {
		measure('nobuild-warm-cache', NOBUILD, 'second visit — stylesheets and assets already cached');
	});
});
