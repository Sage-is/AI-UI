// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../../support/index.d.ts" />

// THE PAYLOAD LEDGER. A measurement, not a gate — it asserts almost nothing, and
// living under `upgrade/` keeps it out of `make e2e`, whose spec glob takes the
// top level only. `make surface_budget` is the gate that reads its output; the
// separation is deliberate, because a measurement that can fail its own run has
// a reason to report a number that passes.
//
// WHY. The board's migration order — "workshop FIRST, then users, evals,
// settings tabs, chat list" — had never been measured, and the first run of this
// file showed it sorted on 2–6% of the cost. It also measures every migrated
// surface before and after, so a migration's claim comes from the same
// instrument as its promise.
//
// THREE THINGS IT DOES DELIBERATELY, each because the obvious version misleads:
//
// 1. **Three samples of everything.** Alexander: "Measure at least twice for
//    each count." Two cannot identify an outlier; three can. Decoded bytes
//    repeat to within 0.1 kB, but one route timed 1,425 ms and then 3,241 ms.
//    A delta smaller than the spread is not a result and must not be published
//    as one.
// 2. **It reads `SURFACES` rather than restating paths.** That registry's own
//    comment says adding a surface to it is the first step of migrating one; so
//    registering a surface enrols it here too, and no one has to remember to
//    measure. Routes with no server-rendered twin yet live in CANDIDATES below.
// 3. **The navigation entry counts.** For a server-rendered page the HTML *is*
//    the payload, so measuring only subresources would score its main cost as
//    zero — a bias in the migration's favour, inside the check on the migration.
//
// Run it against the container `KEEP=1 make upgrade_gate` leaves up:
//
//   TARGET_URL=http://sage-upgrade:8080 \
//   CYPRESS_ADMIN_EMAIL=upgrade-gate@sage.is \
//   CYPRESS_ADMIN_PASSWORD=upgrade-gate-pw-1234 \
//   SPEC='cypress/e2e/upgrade/route-payload.cy.ts' scripts/e2e/run-cypress.sh
//
// NEVER point it at production: it signs in as an administrator.

import {
	collect,
	roll,
	SAMPLES,
	SNAPSHOT_ADMIN,
	type Rolled,
	type Section
} from '../../support/perf';
import { SURFACES, type SurfaceName } from '../../support/surfaces';

type Entry = { key: string; path: string; content: string; note: string };

// Routes with no server-rendered counterpart yet. Migrated surfaces are NOT
// listed here — they come from SURFACES, both sides, automatically.
//
// `/home` is deliberately absent: Spaces has no content hook, and measuring it
// against a shell selector would produce a confident number for the wrong thing.
const CANDIDATES: Entry[] = [
	{
		key: 'chat',
		path: '/',
		content: '#chat-input',
		note: 'the baseline this migration exists to beat'
	},
	{
		key: 'knowledge',
		path: '/workshop/knowledge',
		content: '[data-cy="knowledge-row"]',
		note: 'reported 18,203 kB on production; 5 kB of row data here'
	},
	{
		key: 'users',
		path: '/admin/users',
		content: '[data-cy="users-row"]',
		note: '32 users, 21 carrying base64 avatars; 3,126 component lines'
	},
	{
		key: 'evaluations',
		path: '/admin/evaluations/feedbacks',
		content: '[data-cy="evaluations-row"]',
		note: 'the bare /admin/evaluations redirects to the leaderboard, which has no rows'
	},
	{
		key: 'functions',
		path: '/admin/functions',
		content: '[data-cy="functions-row"]',
		note: 'ONE function in the snapshot — near-zero data, 1,249 lines'
	},
	{
		key: 'notes-empty',
		path: '/notes',
		content: '[data-cy="notes-empty"]',
		note: "THE FLOOR — an SPA route with NO data of its own. Notes are scoped per user and the snapshot's 14 belong to six other people, so the throwaway admin sees none. This is the gauge the app-wide font/icon/api-models work is measured against."
	}
];

/** Both sides of every registered surface, so before and after share an instrument. */
const registered: Entry[] = (Object.keys(SURFACES) as SurfaceName[]).flatMap((name) => {
	const s = SURFACES[name];
	return [
		{ key: `${name}-legacy`, path: s.legacy, content: s.content, note: 'SvelteKit' },
		{ key: `${name}-nobuild`, path: s.nobuild, content: s.content, note: 'server-rendered' }
	];
});

const ENTRIES: Entry[] = [...CANDIDATES, ...registered];

const REPORT: Record<string, Rolled | unknown> = {};

let token = '';
let version = '';

/** The SPA reads localStorage; a server-rendered page reads the cookie. Seed both. */
const seeded = (win: Window) => {
	win.localStorage.setItem('token', token);
	win.localStorage.setItem('locale', 'en-US');
	win.localStorage.setItem('version', version);
};

describe('payload ledger — every route and both sides of every surface', () => {
	before(() => {
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			body: { email: SNAPSHOT_ADMIN.email(), password: SNAPSHOT_ADMIN.password() }
		})
			.then((login) => {
				expect(login.status, 'injected admin signs in').to.eq(200);
				token = login.body.token;
				return cy.request('/api/config');
			})
			.then((cfg) => {
				version = cfg.body.version;
				// The injected admin is brand new, so the setup dialog would open over
				// every route and its fetches would land in every measurement.
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: { Authorization: `Bearer ${token}` },
					body: { ui: { version, setupCompleted: true, workingAlone: true, showChangelog: false } }
				});
			});
	});

	beforeEach(() => cy.setCookie('token', token));

	after(() => {
		cy.writeFile('cypress/perf-routes.json', REPORT);
	});

	// THE GUARD, and the reason any of these numbers can be trusted.
	//
	// A content selector that also matches on the chat page measures the app
	// SHELL, not the route. The run then reports plausible numbers for every
	// entry while measuring the same thing repeatedly, and every test passes.
	// That is a failure indistinguishable from success.
	//
	// Proved, not assumed: planting `button` as one route's selector made it
	// report 152 ms instead of 1,840 ms — a twelvefold "improvement" that was
	// pure measurement error — while nine other tests stayed green. This caught
	// it and named the offender.
	it('no entry reports on a selector the app shell already renders', () => {
		cy.visit('/', { onBeforeLoad: seeded });
		cy.get('#chat-input', { timeout: 60000 }).should('exist');
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(3000); // give the shell every chance to render its own furniture

		cy.document().then((doc) => {
			const leaked = ENTRIES.filter((e) => e.key !== 'chat').filter(
				(e) => doc.querySelectorAll(e.content).length > 0
			);
			// Assert on a STRING so the failure names the offender. An array
			// comparison renders as "expected [ Array(2) ] to deeply equal []",
			// which says something is wrong and not what.
			expect(
				leaked.map((e) => `${e.key} (${e.content})`).join(', ') || 'none',
				'selectors that also match on the chat page, so they measure the shell'
			).to.eq('none');
		});
	});

	ENTRIES.forEach((entry) => {
		it(`${entry.key}: ${entry.path}`, () => {
			const runs: Section[] = [];

			// A plain loop, not a recursive helper: Cypress queues all three
			// visits in order and each `cy.visit` is a fresh document, so every
			// sample starts from its own navigation timing.
			for (let i = 0; i < SAMPLES; i++) {
				cy.visit(entry.path, { onBeforeLoad: seeded });
				cy.get(entry.content, { timeout: 60000 }).should('have.length.at.least', 1);
				cy.get(entry.content).then(($found) => {
					cy.window().then((win) => {
						// `performance.now()` on a freshly loaded document counts from
						// the navigation start, so this is time-to-content with none of
						// Cypress's queue in it. Never time a Cypress step from the test
						// body — that mistake cost a published number once already.
						runs.push(
							collect(win, entry.note, Math.round(win.performance.now()), $found.length, 0)
						);
					});
				});
			}

			cy.then(() => {
				REPORT[entry.key] = roll(runs);
				const r = REPORT[entry.key] as Rolled;
				cy.log(
					`${entry.key}: ${r.decodedKB.median} kB decoded (±${r.decodedKB.spread})  ` +
						`${r.transferKB.median} kB wire  ${r.toContentMs.median} ms (±${r.toContentMs.spread})  ` +
						`${r.rows} rows`
				);
			});
		});
	});
});
