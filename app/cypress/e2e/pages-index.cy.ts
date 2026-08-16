// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild } from '../support/surfaces';

// The route index at /pages/.
//
// Before this existed, `/pages/` answered with the SPA shell — the app mounts at
// `/` with an index.html fallback, so asking for a pages route silently gave you
// the chat window. Every server-rendered page was reachable only by knowing its
// URL.
//
// The assertion worth having is not that the list renders. It is that every
// entry on it GOES somewhere. An index is a promise about other pages, and a
// dead link on it is worse than no index at all: it sends a reader looking for a
// page that does not exist and leaves them unsure whether they typed it wrong.
// So this follows all thirteen.

describe('Pages index', () => {
	beforeEach(function () {
		// No-build only — there is no SvelteKit counterpart to this page.
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	it('answers on both /pages and /pages/', () => {
		// Registered as two paths rather than relying on redirect-on-slash,
		// because an unclaimed path here is answered by the SPA rather than
		// redirected — so the difference would have been a list versus the app.
		['/pages', '/pages/'].forEach((url) => {
			cy.request(url).its('body').should('contain', 'data-cy="pages-index"');
		});
	});

	it('lists every page and every one of them resolves', () => {
		cy.visit('/pages/');
		cy.get('[data-cy="pages-index"] [data-cy="index-link"]')
			.should('have.length.at.least', 13)
			.then(($links) => {
				const hrefs = [...$links].map((a) => a.getAttribute('href') ?? '');
				// Distinct, because a list that repeats one working link would
				// otherwise pass this while being useless.
				expect(new Set(hrefs).size, 'every entry points somewhere different').to.eq(
					hrefs.length
				);
				hrefs.forEach((href) => {
					cy.request({ url: href, failOnStatusCode: false }).should((res) => {
						expect(res.status, `${href} resolves`).to.eq(200);
						// 200 is not enough on its own, and this was measured
						// rather than reasoned: pointing a link at a route that
						// does not exist still returns 200, because the SPA is
						// mounted at `/` with an index.html fallback. The shell
						// answers. So the real check is that a SERVER-RENDERED
						// page came back.
						//
						// Asserted as a BOOLEAN, not with `.to.contain` on the
						// body. Chai prints the subject on failure, and the
						// subject there is the entire SPA document — several
						// screens of markup burying the one useful word, the
						// href. A gate whose failure you have to go investigate
						// is half a gate.
						//
						// The marker is `page-heading`, the one shell.py documents
						// as proof a server-rendered page answered. This used to
						// look for the literal string `<main>`, which broke the
						// day Startr Swap landed `data-swap` on that tag — a
						// bare-tag match is a bet no attribute ever appears.
						expect(
							String(res.body).includes('data-cy="page-heading"'),
							`${href} returned the SPA shell, not a server-rendered page`
						).to.eq(true);
					});
				});
			});
	});

	it('carries the reader language onto every link', () => {
		cy.request('/pages/?lang=es-ES')
			.its('body')
			.then((html: string) => {
				const hrefs = [...html.matchAll(/data-cy="index-link" href="([^"]+)"/g)].map((m) => m[1]);
				expect(hrefs, 'the index rendered links').to.have.length.at.least(13);
				hrefs.forEach((href) =>
					expect(href, 'language survives the hop').to.contain('lang=es-ES')
				);
			});
	});

	it('shows no development banner on a normal instance', () => {
		// The banner is the reloader announcing itself. This suite runs against
		// the baked image with no flag set, which is every shipped instance.
		cy.request('/pages/').its('body').should('not.contain', 'index-dev-banner');
	});
});
