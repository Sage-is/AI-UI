// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The hollowed `/home` route.
//
// `/home` keeps its address and the app chrome, and hosts the server-rendered
// `/pages/home` inside it. There is ONE implementation of the dashboard behind
// two addresses, which is why this surface is not in `surfaces.ts` — parity
// would compare a route against itself and pass for the wrong reason.
//
// So this judges the HOST, not parity. Four things, and each one is a way the
// host can fail while looking fine:
//
//   1. The fetch happened at all. An empty host div renders as a blank page
//      with no error — the failure nobody reports.
//   2. What arrived is SERVER-RENDERED markup, not the SPA's own. `page-heading`
//      is the marker that proves a real page answered, and it is the only one
//      that can: nothing under `/pages/` can 404, because the SPA catch-all
//      returns the shell with a 200 for any unmatched path.
//   3. The marketplace slot came with it. That slot is the whole reason
//      `/pages/home` exists. `SetupDialog` strips it deliberately, so a host
//      that copied SetupDialog too closely would drop it and nothing else would
//      notice.
//   4. Only ONE shell. Injecting `body` instead of `<main>` grafts a second
//      copy of the page shell inside the first, and the page still looks
//      roughly right.
//
// The slot assertions need a grafted ui-Sprig, so they skip when none is
// active rather than failing on a bare instance. `make review_live` and
// `scripts/manual-check.sh --graft-ui` both graft `ui-workshop-welcome`.

const HOST = '[data-cy="home-host"]';

const activeUi = () =>
	cy
		.request({ url: '/api/v1/retrieval/sprigs/catalog', failOnStatusCode: false })
		.then((res) => String(res.body?.active_ui ?? ''));

describe('the hollowed /home hosts the server-rendered page', () => {
	beforeEach(() => cy.loginAdmin());

	it('fetches /pages/home and renders it inside the app chrome', () => {
		cy.visit('/home');

		// Wait on real hosted content rather than a fixed pause. The host is
		// empty until the fetch lands, and asserting too early would pass on the
		// SPA having painted its own chrome.
		cy.get(`${HOST} [data-cy="home-greeting"]`, { timeout: 30000 }).should('be.visible');

		// Server-rendered, proven by the one marker only `render_page` emits.
		cy.get(`${HOST} [data-cy="page-heading"]`).should('exist');

		// The dashboard's own controls arrived, not just the header.
		cy.get(`${HOST} [data-cy="home-recent"]`).should('exist');
		cy.get(`${HOST} [data-cy="home-pinned"]`).should('exist');
		cy.get(`${HOST} [data-cy="home-notes"]`).should('exist');

		// The app chrome is still there. Losing it is the regression that made
		// replacement the wrong mode for this surface in the first place.
		cy.get('nav, aside, [data-cy="sidebar"]').should('exist');

		// Exactly one shell. Two means the host injected `body` rather than
		// `<main>`, which looks almost right and is not.
		cy.get(`${HOST} #toasts`).should('not.exist');
		cy.get(`${HOST} main`).should('not.exist');

		// The host reports failure rather than showing an empty box.
		cy.get('[data-cy="home-failed"]').should('not.exist');
	});

	it('the starter hands off to a real chat with the message already sent', () => {
		cy.visit('/home');
		cy.get(`${HOST} [data-cy="home-starter-input"]`, { timeout: 30000 }).should('be.visible');

		// A plain GET form, so this asserts the CONTRACT rather than the markup:
		// the chat reads `?q=` and submits it unless `submit=false`. If the form
		// ever stops producing that query the handoff breaks silently — the box
		// would still look fine and simply open an empty chat.
		cy.get(`${HOST} [data-cy="home-starter"]`).should('have.attr', 'action', '/');
		cy.get(`${HOST} [data-cy="home-starter-input"]`).should('have.attr', 'name', 'q');

		cy.get(`${HOST} [data-cy="home-starter-input"]`).type('hello from the starter');
		cy.get(`${HOST} [data-cy="home-starter-submit"]`).click();

		// Assert the OUTCOME, not the address on the way to it.
		//
		// `/?q=…` is a state the chat page destroys on purpose: it reads the query,
		// submits it, then replaces the address — first clearing the query, then
		// again with `/c/<id>` once the chat exists. `should('eq', '/')` plus
		// `contain('q=hello')` is a race against that, and it was seen losing BOTH
		// ways on one build: `/c/76db38…` when the chat came back fast, and `/`
		// with an empty search when only the query had been cleared. Both of those
		// were the handoff WORKING.
		//
		// `cy.intercept` cannot rescue it either — it does not see a top-level
		// document navigation, which is what a GET form performs.
		//
		// So: the reader left the dashboard, and the message they typed is on the
		// screen they landed on. That is the sentence in this test's name, and it
		// is only reachable if the form produced `?q=` and the chat read it.
		cy.location('pathname', { timeout: 30000 }).should('not.eq', '/home');
		cy.contains('hello from the starter', { timeout: 30000 }).should('exist');
	});

	it('the marketplace slot comes with the page', function () {
		activeUi().then((name) => {
			// Nothing grafted: the slot renders as an empty string by design, so
			// there is nothing to assert. Skipping is honest; asserting absence
			// would pass on a broken host too.
			if (!name) this.skip();

			cy.visit('/home');
			cy.get(`${HOST} [data-cy="home-greeting"]`, { timeout: 30000 }).should('be.visible');
			cy.get(`${HOST} #sprig-ui-slot`).should('exist').and('have.attr', 'data-sprig-ui', name);
			// The fragment landed with content, not just its wrapper.
			cy.get(`${HOST} #sprig-ui-slot`).invoke('text').should('have.length.greaterThan', 20);
		});
	});

	it('/pages/home still answers on its own, and carries the same page', () => {
		// The hollow is an addition, not a replacement. The direct address stays
		// reachable — it is the fallback the failure message points at.
		cy.request('/pages/home').then((res) => {
			expect(res.status).to.eq(200);
			expect(res.body, 'a real server-rendered page, not the SPA shell').to.contain(
				'data-cy="page-heading"'
			);
			expect(res.body).to.contain('data-cy="home-recent"');
		});
	});
});
