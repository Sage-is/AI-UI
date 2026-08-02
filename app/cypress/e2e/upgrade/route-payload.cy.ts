// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../../support/index.d.ts" />

// MEASUREMENT, not a gate. Never wire it into `make e2e` — living under
// `upgrade/` keeps it out, because the default spec glob takes the top level.
//
// WHY. The board's migration order — "workshop FIRST, then users, evals,
// settings tabs, chat list" — has never been measured. It is the same kind of
// claim as three that fell this week: the avatar theory (868 kB, not 20 MB),
// the double-fetch wording, and a timing I could not stand behind. Alexander,
// after the Agents pass: "let's think about what other routes would benefit."
//
// So this measures every candidate on one booted snapshot and lets the numbers
// pick the order, on the four things he asked to rank by — time to first
// content, bytes over the wire, lines deleted, and how often a route is opened.
// The first two are here. Lines are counted statically. **How often a route is
// opened is not measured anywhere, because this product has no telemetry** —
// that column is left blank for a human rather than filled with a proxy.
//
// THE HYPOTHESIS THIS IS BUILT TO KILL. `/workshop/knowledge` was reported at
// 18,203 kB on production, yet its 17 rows hold 5 kB of data between them, and
// all 8 prompts hold 6 kB. Meanwhile every route under `(app)` pays the same
// toll before rendering anything of its own: `getModels` in the boot wave
// (2,304 kB on this snapshot), ~2,505 kB of chunks, a 636 kB unsubsetted font
// and 332 kB of full-resolution icons. If that fixed cost dominates, list size
// is the wrong sorting key and the board's order is wrong.
//
// `prompts` is the CONTROL. Six kilobytes of data. If it still costs megabytes,
// the fixed-cost thesis holds. If it comes in cheap, list size really does drive
// cost. Both outcomes are readable from the output; neither is assumed.
//
// Run it against the container `KEEP=1 make upgrade_gate` leaves up:
//
//   TARGET_URL=http://sage-upgrade:8080 \
//   CYPRESS_ADMIN_EMAIL=upgrade-gate@sage.is \
//   CYPRESS_ADMIN_PASSWORD=upgrade-gate-pw-1234 \
//   SPEC='cypress/e2e/upgrade/route-payload.cy.ts' scripts/e2e/run-cypress.sh
//
// NEVER point it at production: it signs in as an administrator.

import { collect, SNAPSHOT_ADMIN, type Section } from '../../support/perf';

type Route = { key: string; path: string; ready: string; note: string };

// Every entry's `ready` selector must match something ONLY that route renders.
// The guard below enforces it. Routes with no such selector are omitted and
// said so out loud rather than measured against the shell — `/home` is the one
// currently missing, since Spaces has no list hook yet.
const ROUTES: Route[] = [
	{
		key: 'chat',
		path: '/',
		ready: '#chat-input',
		note: 'the baseline this migration exists to beat'
	},
	{
		key: 'agents',
		path: '/workshop/models',
		ready: '[data-cy="agents-row"]',
		note: 'already migrated — the reference point'
	},
	{
		key: 'nobuild-agents',
		path: '/pages/workshop/agents',
		ready: '[data-cy="agents-row"]',
		note: 'the server-rendered answer to the row above'
	},
	{
		key: 'knowledge',
		path: '/workshop/knowledge',
		ready: '[data-cy="knowledge-row"]',
		note: 'reported 18,203 kB on production; 5 kB of row data here'
	},
	{
		key: 'prompts',
		path: '/workshop/prompts',
		ready: '[data-cy="prompts-row"]',
		note: 'THE CONTROL — 6 kB of data across 8 rows'
	},
	{
		key: 'users',
		path: '/admin/users',
		ready: '[data-cy="users-row"]',
		note: '32 users, 21 carrying base64 avatars; the biggest component at 3,126 lines'
	},
	{
		key: 'evaluations',
		path: '/admin/evaluations/feedbacks',
		ready: '[data-cy="evaluations-row"]',
		note: 'the bare /admin/evaluations redirects to the leaderboard, which has no rows'
	},
	{
		key: 'functions',
		path: '/admin/functions',
		ready: '[data-cy="functions-row"]',
		note: 'ONE function in the snapshot — near-zero data, 1,249 lines'
	},
	{
		key: 'notes-empty',
		path: '/notes',
		ready: '[data-cy="notes-empty"]',
		note: "THE FLOOR — an SPA route with NO data of its own. `Notes.get_notes_by_user_id` scopes notes per user and the snapshot's 14 belong to six other people, so the throwaway admin sees none. That makes this the purest reading of what the shell costs before a route adds anything."
	}
];

const REPORT: Record<string, Section | unknown> = {};

let token = '';
let version = '';

/** The SPA reads localStorage; a server-rendered page reads the cookie. Seed both. */
const seeded = (win: Window) => {
	win.localStorage.setItem('token', token);
	win.localStorage.setItem('locale', 'en-US');
	win.localStorage.setItem('version', version);
};

describe('route payload survey — every migration candidate on one snapshot', () => {
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

	// THE GUARD, and the reason this survey is trustworthy at all.
	//
	// A `ready` selector that also matches on the chat page is measuring the app
	// SHELL, not the route. The run would then report plausible-looking numbers
	// for eight routes while measuring the same thing eight times, and every one
	// of them would pass. That is a failure indistinguishable from success —
	// the shape this repo keeps finding, and the reason the diagnostics page
	// once shipped a button that rendered and did nothing.
	//
	// So: load the chat page and prove that no other route's content is on it.
	it('no route reports on a selector the app shell already renders', () => {
		cy.visit('/', { onBeforeLoad: seeded });
		cy.get('#chat-input', { timeout: 60000 }).should('exist');
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(3000); // give the shell every chance to render its own furniture

		cy.document().then((doc) => {
			const leaked = ROUTES.filter((r) => r.key !== 'chat').filter(
				(r) => doc.querySelectorAll(r.ready).length > 0
			);
			// Assert on a STRING so the failure names the offender. An array
			// comparison renders as "expected [ Array(2) ] to deeply equal []",
			// which tells you something is wrong and not what.
			expect(
				leaked.map((r) => `${r.key} (${r.ready})`).join(', ') || 'none',
				'route selectors that also match on the chat page, so they measure the shell'
			).to.eq('none');
		});
	});

	ROUTES.forEach((route) => {
		it(`${route.key}: ${route.path}`, () => {
			cy.visit(route.path, { onBeforeLoad: seeded });
			cy.get(route.ready, { timeout: 60000 }).should('have.length.at.least', 1);
			cy.get(route.ready).then(($rows) => {
				cy.window().then((win) => {
					// `performance.now()` on a freshly loaded document counts from the
					// navigation start, so this is time-to-first-content with none of
					// Cypress's queue in it. Never time a Cypress step from the test
					// body — that mistake cost a published number once already.
					REPORT[route.key] = collect(
						win,
						route.note,
						Math.round(win.performance.now()),
						$rows.length,
						0
					);
					const s = REPORT[route.key] as Section;
					cy.log(
						`${route.key}: ${s.requests} req  ${s.transferKB} kB wire  ${s.decodedKB} kB decoded  ${s.rows} rows  ${s.toContentMs} ms`
					);
				});
			});
		});
	});
});
