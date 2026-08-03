// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The try.sage welcome page, server-rendered at `/` for anonymous visitors.
//
// Two suites, gated on how the container was started:
//
//   Flag OFF (the default harness): the routes must not exist. `/` is the SPA
//   index, and `/welcome` falls through to the SPA catch-all. This is the half
//   that protects every non-trial deploy, and it runs on `make e2e` untouched.
//
//   Flag ON  (ENABLE_TRY_SAGE=true SPEC=try-sage-welcome.cy.ts make e2e): the
//   welcome renders in the first response, and — the reason this surface moved
//   at all — the page SCROLLS on a phone. The Svelte version pinned a fixed
//   100vh layer and flex-centered its overflow off both ends, which is
//   Reviewer T's bottom-of-page cutoff. The teeth: on a 375×667 viewport the
//   footer must be reachable by scrolling, and the document must actually
//   scroll rather than clip.
const PHONE = { width: 375, height: 667 };

const trySageOn = () =>
	cy
		.request('/api/config')
		.then((res) => Boolean(res.body?.features?.enable_try_sage));

describe('try.sage welcome surface', () => {
	it('flag off: `/` stays the SPA and the welcome route does not exist', function () {
		trySageOn().then((on) => {
			if (on) this.skip();
			cy.clearCookies();
			cy.request('/').then((res) => {
				expect(res.status).to.eq(200);
				expect(res.body, 'the SPA shell, not the welcome page').to.not.contain(
					'data-cy="try-sage-welcome"'
				);
			});
			cy.request('/welcome').then((res) => {
				// The SPA catch-all answers unmatched paths with the shell.
				expect(res.body).to.not.contain('data-cy="try-sage-welcome"');
			});
		});
	});

	it('flag on: an anonymous `/` is the welcome page in the first response', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			cy.clearCookies();
			cy.request('/').then((res) => {
				expect(res.status).to.eq(200);
				expect(res.body).to.contain('data-cy="try-sage-welcome"');
				// Invite-only contract: no sign-in form, no signup escape hatch.
				expect(res.body).to.not.contain('type="password"');
			});
		});
	});

	it('flag on: the page scrolls on a phone and the footer is reachable', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			cy.clearCookies();
			cy.viewport(PHONE.width, PHONE.height);
			cy.visit('/');
			cy.get('[data-cy="try-sage-welcome"]').should('exist');

			// The cutoff's exact shape: content below the first screen must be
			// reachable. Scroll to the bottom and the footer must be visible —
			// under the old fixed-layer layout it sat behind the browser chrome
			// or off the unreachable end of a centered overflow.
			cy.scrollTo('bottom');
			cy.get('[data-cy="try-sage-footer"]').should('be.visible');

			// And the document really scrolled — the page is taller than the
			// viewport on a phone, so a scrollTop of 0 after scrollTo means a
			// clipped layout swallowed the scroll.
			cy.window().then((win) => {
				const doc = win.document.scrollingElement as Element;
				expect(doc.scrollHeight, 'content taller than one phone screen').to.be.greaterThan(
					PHONE.height
				);
				expect(doc.scrollTop, 'the scroll actually happened').to.be.greaterThan(0);
			});
		});
	});

	it('flag on: a signed-in reader still gets the SPA at `/`', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			// API sign-in, not cy.loginAdmin(): that command drives the /auth
			// FORM, and trial mode redirects an anonymous /auth to `/` — the
			// form does not exist, which is the invite-only contract working.
			// The signin response sets the `token` cookie; the jar carries it.
			cy.clearCookies();
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/signup',
				body: { name: 'admin', email: 'admin@example.com', password: 'password' },
				failOnStatusCode: false // 200 created, 400/403 already there
			});
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/signin',
				body: { email: 'admin@example.com', password: 'password' }
			});
			cy.getCookie('token').should('exist');
			cy.request('/').then((res) => {
				expect(res.status).to.eq(200);
				expect(res.body, 'the SPA shell for the signed-in').to.not.contain(
					'data-cy="try-sage-welcome"'
				);
			});
		});
	});
});
