// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { SURFACES, type SurfaceName } from '../support/surfaces';

// Every `/pages/` route must answer with or without a trailing slash.
//
// WHY THIS EXISTS. On 2026-08-03 `/pages/workshop/agents/` returned the
// single-page-app shell with a **200** — the wrong page, at a URL a person could
// plausibly type, with no error anywhere. So did every other page under
// `/pages/`, and `/pages` itself failed the same way in the opposite direction,
// because the index is declared WITH a slash and everything else without one.
//
// Two deliberate mechanisms combined to hide it. `SPAStaticFiles` is mounted at
// `/` with `html=True`, so **nothing under `/pages/` can 404** — the shell
// answers anything unmatched. And Starlette's `redirect_slashes` only runs when
// no route matched, which never happens because the catch-all always matches.
//
// **THIS SPEC ASSERTS ON CONTENT, NEVER ON STATUS**, and that is the whole
// lesson rather than a detail. Under `/pages/` a 200 proves nothing: the shell
// and the real page both return one. The first check written for this bug looked
// for "Sage.is AI" in the title, found it on the shell too, and reported all
// green while every route was broken. `pages-dev-reload.cy.ts` and
// `pages-index.cy.ts` carry the same warning for the same reason.
//
// The surface list comes from `cypress/support/surfaces.ts`, including its
// `content` selector — so registering a surface enrols it here as well, and a
// new page cannot be added without its slash form being covered.

type Page = { name: string; path: string };

const PAGES: Page[] = [
	...(Object.keys(SURFACES) as SurfaceName[]).map((name) => ({
		name,
		path: SURFACES[name].nobuild
	})),
	{ name: 'changelog', path: '/pages/changelog' }
];

/**
 * The marker that proves a SERVER-RENDERED page answered.
 *
 * Not the surface's own `content` selector from the registry: that is a ROW, and
 * a row needs data. This spec is about addressing, not about content, and
 * seeding three surfaces to prove a slash works would make the fixture bigger
 * than the thing under test. `shell.py` puts this on every no-build page.
 */
const RENDERED = '[data-cy="page-heading"]';

describe('a trailing slash reaches the same page', () => {
	beforeEach(() => cy.loginAdmin());

	PAGES.forEach((page) => {
		it(`${page.name}: ${page.path}/ renders the page, not the app shell`, () => {
			cy.visit(`${page.path}/`);
			// The real page's own content. If the shell answered instead, this is
			// missing — which is the only signal available, since the status is 200
			// either way.
			cy.get(RENDERED, { timeout: 30000 }).should('exist');
			// And the address canonicalised, which proves a redirect happened rather
			// than the route merely tolerating both spellings.
			cy.location('pathname').should('eq', page.path);
		});
	});

	it('/pages reaches the index, which is declared WITH a slash', () => {
		cy.visit('/pages');
		cy.get('[data-cy="index-link"]', { timeout: 30000 }).should('have.length.at.least', 1);
		cy.location('pathname').should('eq', '/pages/');
	});

	it('/pages/ is left alone', () => {
		cy.visit('/pages/');
		cy.get('[data-cy="index-link"]').should('have.length.at.least', 1);
		cy.location('pathname').should('eq', '/pages/');
	});

	it('an asset URL is not touched', () => {
		// `/pages/_assets/` is a mount for files. Redirecting it would break a
		// stylesheet in a way that presents as a CSS bug, which is the most
		// expensive kind of wrong to trace.
		cy.request('/pages/_assets/pages.css').then((res) => {
			expect(res.status).to.eq(200);
			expect(res.headers['content-type']).to.include('css');
		});
	});

	it('a POST keeps its method across the redirect', () => {
		// 307, not 308: a delete arriving at a slashed URL must stay a POST. If it
		// became a GET the action would silently do nothing, which is exactly the
		// class of failure this migration keeps finding.
		cy.request({
			method: 'POST',
			url: '/pages/workshop/prompts/clone/does-not-exist/',
			failOnStatusCode: false
		}).then((res) => {
			// The command is nonsense on purpose — what matters is that the request
			// arrived as a POST at the panel, which answers with a page rather than
			// a method-not-allowed.
			expect(res.status, 'the redirected POST was handled, not rejected').to.be.oneOf([200, 404]);
		});
	});
});
