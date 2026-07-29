// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { SURFACES, isNoBuild, type SurfaceName } from '../support/surfaces';

// The no-build pages must stay usable when startr.style is unreachable.
//
// They load it from an unversioned public URL, which is a single point of
// failure by construction and a known one — the versioned URL with SRI is
// coming, and until it does, every admin page depends on a third-party host
// being up. An air-gapped Rootstock is the same case permanently.
//
// So the standing rule is that the framework is polish and the local sheet is
// structure: `pages.css` carries anything that must not break, and startr.style
// carries the rest. This is what enforces that split, because otherwise it
// erodes one convenient inline prop at a time and nobody notices until the day
// the CDN 5xxs.
//
// A caution for whoever edits this: an aborted <link> still appears in
// `document.styleSheets` with its href, so "is startr.style loaded" is not a
// usable signal. Assert on what the framework would have DONE. The first
// version of this check used a glob that matched nothing, blocked zero
// requests, and passed while measuring the online page.
describe('No-build pages survive a startr.style outage', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
		// Regex, not a glob. See above.
		cy.intercept({ url: /startr\.style/ }, { forceNetworkError: true }).as('cdn');
	});

	(Object.keys(SURFACES) as SurfaceName[]).forEach((name) => {
		it(`${name}: renders every control and stays laid out without the framework`, () => {
			cy.visit(SURFACES[name].nobuild);

			// Content is server-rendered, so a missing stylesheet cannot cost us
			// any of it. If this drops, something moved into the framework that
			// should not have.
			cy.get('[data-cy]', { timeout: 30000 }).should('have.length.at.least', 5);

			// Rows keep their own layout from pages.css rather than inheriting it.
			cy.get('[data-cy="sprig-card"], [data-cy="diag-row"]')
				.first()
				.should('have.css', 'display', 'grid');

			// The failure that makes a page unusable on a phone rather than merely
			// plain: content wider than the viewport.
			cy.document().then((doc) => {
				const el = doc.documentElement;
				expect(el.scrollWidth, 'no horizontal overflow without the framework').to.be.at.most(
					el.clientWidth
				);
			});
		});
	});
});
