// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Navigating INSIDE a hollowed route.
//
// WHY THIS EXISTS. Hollowing shipped on 2026-08-08 and 2026-08-09, and it
// covered arriving at a route. It did not cover moving around once there. The
// month controls on `/calendar` were plain anchors to `/pages/calendar?month=…`,
// so clicking "Next" walked the browser out of the app onto the bare server page
// and the sidebar disappeared. `/pages/settings/calendar` was worse: reached
// from the dashboard, its own "Back to the calendar" link pointed at another
// chrome-less page, so there was no route back into the app at all. A one-way
// door, and every existing spec was green through all of it — they only ever
// asserted the first render.
//
// Every test here marks the window and asserts the mark survived. A swap and a
// page load leave identical DOM, so nothing else can tell them apart.

const SENTINEL = '__swapAlive';
// DashboardShell's own nav, not `#sidebar-toggle-button`. That id is duplicated
// by three layouts and hidden by style when the sidebar is open, so it answers
// questions other than the one being asked. These links exist only in the
// chrome wrapped AROUND a hosted page, which is exactly what must survive.
const CHROME = '[data-cy="dash-nav-calendar"]';

const mark = () =>
	cy.window().then((win) => ((win as never as Record<string, unknown>)[SENTINEL] = 1));

const stillAlive = () =>
	cy.window().then((win) => {
		expect(
			(win as never as Record<string, unknown>)[SENTINEL] ? 'swapped' : 'A FULL PAGE LOAD',
			'the reader must stay inside the app, not be navigated onto the bare page'
		).to.eq('swapped');
	});

describe('the hollowed /calendar navigates without leaving the app', () => {
	beforeEach(() => cy.loginAdmin());

	// TWO clicks, not one, and this is the whole reason the test is shaped this
	// way. The first version clicked Next once and was green against a hollow
	// that chased every swap with a fetch of the un-parameterised page — the
	// clobber lands AFTER the new content, so a single click reads the right
	// month and then quietly goes back to the current one. Alexander found it by
	// clicking twice.
	it('the month controls advance and STAY advanced', () => {
		// Every fetch the swapper makes, so the last one can be inspected. The
		// failure was an extra request with no `month=` at all, which is invisible
		// in the DOM by the time anything asserts on it.
		cy.intercept('GET', '/pages/calendar*').as('cal');

		cy.visit('/calendar');
		cy.get('[data-cy="calendar-month"]', { timeout: 30000 }).should('be.visible');

		cy.get('[data-cy="calendar-month"]')
			.invoke('text')
			.then((first) => {
				cy.get('[data-cy="calendar-next"]').click();
				cy.get('[data-cy="calendar-month"]', { timeout: 20000 }).should('not.have.text', first);

				cy.get('[data-cy="calendar-month"]')
					.invoke('text')
					.then((second) => {
						cy.get('[data-cy="calendar-next"]').click();
						cy.get('[data-cy="calendar-month"]', { timeout: 20000 })
							.should('not.have.text', second)
							.and('not.have.text', first); // not walked back to where we started
					});
			});

		// Nothing came after the month the reader asked for. A trailing request
		// without `month=` is the clobber, and it is the thing that made the
		// second click appear to go backwards.
		cy.get('@cal.all').then((calls) => {
			const urls = (calls as unknown as { request: { url: string } }[]).map((c) => c.request.url);
			expect(
				urls[urls.length - 1],
				`the last fetch, of ${urls.length}:\n${urls.join('\n')}`
			).to.contain('month=');
		});
	});

	it('the month controls swap in place and keep the chrome', () => {
		cy.visit('/calendar');
		cy.get('[data-cy="calendar-month"]', { timeout: 30000 }).should('be.visible');
		cy.get(CHROME).should('exist');

		cy.get('[data-cy="calendar-month"]')
			.invoke('text')
			.then((first) => {
				mark();
				cy.get('[data-cy="calendar-next"]').click();

				// The month moved…
				cy.get('[data-cy="calendar-month"]').should('not.have.text', first);
				// …a server-rendered page answered, which is the only thing that
				// proves it was not the SPA painting something plausible…
				cy.get('[data-cy="page-heading"]').should('exist');
				// …the app chrome survived, which is the whole defect…
				cy.get(CHROME).should('exist');
				// …the address stayed shareable and inside the SPA, rather than
				// becoming `/pages/calendar?month=…`…
				cy.location('pathname').should('eq', '/calendar');
				cy.location('search').should('contain', 'month=');
				// …and none of it was a page load.
				stillAlive();
			});
	});

	it('the back button walks the months back', () => {
		cy.visit('/calendar');
		cy.get('[data-cy="calendar-month"]', { timeout: 30000 }).should('be.visible');

		cy.get('[data-cy="calendar-month"]')
			.invoke('text')
			.then((first) => {
				mark();
				cy.get('[data-cy="calendar-next"]').click();
				cy.get('[data-cy="calendar-month"]').should('not.have.text', first);

				cy.go('back');

				// SvelteKit's router owns this history entry — the hollow cancels
				// `swap:navigate` and pushes through `$app/navigation` for exactly
				// this reason. A raw `history.pushState` desynchronises the router's
				// bookkeeping, and the failure is a back button that silently stops
				// working rather than one that errors.
				cy.get('[data-cy="calendar-month"]').should('have.text', first);
				cy.location('pathname').should('eq', '/calendar');
				cy.get(CHROME).should('exist');
				// This assertion was missing on the first draft, and its absence let
				// the test PASS on the broken code: a hard navigation to the bare
				// page followed by `go('back')` also lands on `/calendar` showing
				// the first month with the chrome intact. Every observable thing
				// matched while nothing had swapped.
				stillAlive();
			});
	});

	it('a second visit re-runs the page scripts', () => {
		// The `onMount`-only host fetched once per component mount, and the adopted
		// script set is permanent for the document — so a second visit re-injected
		// the markup and skipped the script. `home-greeting.js` is an IIFE, so the
		// greeting silently stayed at the server's guess and nothing looked broken.
		cy.visit('/home');
		cy.get('[data-cy="home-greeting"]', { timeout: 30000 }).should('be.visible');

		cy.visit('/calendar');
		cy.get('[data-cy="calendar-month"]', { timeout: 30000 }).should('be.visible');

		cy.visit('/home');
		cy.get('[data-cy="home-greeting"]', { timeout: 30000 }).should('be.visible');
		cy.get('[data-cy="home-host"] [data-cy="page-heading"]').should('exist');
	});
});

describe('/settings/calendar is reachable and has a way back', () => {
	beforeEach(() => cy.loginAdmin());

	it('the dashboard link lands inside the app', () => {
		cy.visit('/home');
		cy.get('[data-cy="home-calendar-settings"]', { timeout: 30000 }).should('exist');

		cy.get('[data-cy="home-calendar-settings"]').click();

		cy.get('[data-cy="settings-calendar-form"]', { timeout: 30000 }).should('be.visible');
		// Before this route existed the reader landed on `/pages/settings/calendar`
		// with no sidebar and no route back.
		cy.get(CHROME).should('exist');
		cy.location('pathname').should('eq', '/settings/calendar');
	});

	it('"back to the calendar" returns to the app, not to a bare page', () => {
		cy.visit('/settings/calendar');
		cy.get('[data-cy="settings-calendar-back"]', { timeout: 30000 }).should('exist');

		cy.get('[data-cy="settings-calendar-back"]').click();

		cy.get('[data-cy="calendar-month"]', { timeout: 30000 }).should('be.visible');
		cy.get(CHROME).should('exist');
		cy.location('pathname').should('eq', '/calendar');
	});

	it('saving feeds swaps the result in and keeps the chrome', () => {
		// A POST inside a hollow, which nothing else covers. The form action is on
		// the surface, so the swapper claims it — and if the region resolution were
		// wrong the reader would be dropped onto the bare page mid-save, having
		// just handed over settings.
		cy.visit('/settings/calendar');
		cy.get('[data-cy="settings-calendar-feeds"]', { timeout: 30000 }).should('be.visible');
		mark();

		// A domain that cannot resolve, so the save path is exercised without the
		// test depending on anything off this machine.
		cy.get('[data-cy="settings-calendar-feeds"]').clear().type('https://example.invalid/cal.ics');
		cy.get('[data-cy="settings-calendar-save"]').click();

		cy.get('[data-cy="panel-message"]', { timeout: 30000 }).should('be.visible');
		cy.get('[data-cy="settings-calendar-feeds"]').should(
			'have.value',
			'https://example.invalid/cal.ics'
		);
		cy.get(CHROME).should('exist');
		cy.location('pathname').should('eq', '/settings/calendar');
		stillAlive();

		// Put it back, so the calendar tests above do not inherit a dead feed.
		cy.get('[data-cy="settings-calendar-feeds"]').clear();
		cy.get('[data-cy="settings-calendar-save"]').click();
		cy.get('[data-cy="panel-message"]', { timeout: 30000 }).should('be.visible');
	});

	it('/pages/settings/calendar still answers on its own', () => {
		// The hollow is an addition, not a replacement. The direct address stays
		// reachable — it is the fallback the failure message points at.
		cy.request('/pages/settings/calendar').then((res) => {
			expect(res.status).to.eq(200);
			expect(res.body, 'a real server-rendered page, not the SPA shell').to.contain(
				'data-cy="page-heading"'
			);
			expect(res.body).to.contain('data-cy="settings-calendar-form"');
		});
	});
});
