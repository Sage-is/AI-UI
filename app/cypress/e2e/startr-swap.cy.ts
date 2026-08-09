// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Startr Swap — the library, judged as a library.
//
// It ships from `pages/assets/startr-swap.js` and is meant to be published for
// other projects, including static sites. So the first thing asserted here is
// not an application behaviour at all: it is that two bare HTML documents with
// one word of markup between them — `data-swap` — and no framework and no
// configuration swap correctly. If that ever needs something AI-UI-shaped, the
// file has stopped being publishable and this is where it shows.
//
// That one word is load-bearing and replaced a `<main>` default. Any document
// can end up running this file: a host application that adopts a fetched page's
// scripts adopts this one too. Claiming `<main>` by default would then take
// over every link in a document that never asked for it — which is exactly what
// `SetupDialog` does with `/pages/*` panels, and the SPA happens to render no
// `<main>` today. Working by luck is the failure shape this repo keeps finding.
//
// THE SENTINEL IS THE POINT. Every test writes a value onto `window` and then
// asserts it survived. A swap and a full page load look identical in the DOM —
// same markup, same heading, same everything — so a DOM assertion passes on
// both and proves nothing about the mechanism. A real navigation destroys the
// window, so only the sentinel can tell them apart. That is the same distinction
// `pages-action-response.cy.ts` was written on.
//
// The one thing this harness cannot make literal is the byte source: the fixture
// pages load the script from the app's own asset mount, because that is the
// static host available in a container. Serving a file is not application
// behaviour, and nothing else here touches the app.

const SENTINEL = '__swapAlive';

/** Mark the current window, so a full page load can be detected by its absence. */
const mark = () =>
	cy.window().then((win) => ((win as never as Record<string, unknown>)[SENTINEL] = 1));

/** The window was never replaced — the page swapped rather than navigating. */
const stillAlive = () =>
	cy.window().then((win) => {
		expect(
			(win as never as Record<string, unknown>)[SENTINEL] ? 'swapped' : 'A FULL PAGE LOAD',
			'the page must have swapped in place, not navigated'
		).to.eq('swapped');
	});

const servePlainFixtures = () => {
	const page = (name: string) =>
		cy.intercept('GET', `/swap-fixture/${name}`, {
			statusCode: 200,
			headers: { 'content-type': 'text/html; charset=utf-8' },
			fixture: `swap/${name}`
		});
	page('a.html');
	page('b.html');
	page('none.html');
	// Not every address answers with a page. This is the download case.
	cy.intercept('GET', '/swap-fixture/data.json', {
		statusCode: 200,
		headers: { 'content-type': 'application/json' },
		body: { exported: true }
	});
};

describe('the library works on a plain static site', () => {
	beforeEach(servePlainFixtures);

	it('swaps between two bare documents with zero configuration', () => {
		cy.visit('/swap-fixture/a.html');
		cy.get('#who').should('have.text', 'A');
		mark();

		cy.get('#to-b').click();

		// The content changed…
		cy.get('#who').should('have.text', 'B');
		// …the title followed, because a whole-page swap did change page…
		cy.title().should('eq', 'Page B');
		// …the address followed…
		cy.location('pathname').should('eq', '/swap-fixture/b.html');
		// …and none of it was a page load.
		stillAlive();
	});

	it('the back button walks back without reloading', () => {
		cy.visit('/swap-fixture/a.html');
		cy.get('#who').should('have.text', 'A');
		mark();

		cy.get('#to-b').click();
		cy.get('#who').should('have.text', 'B');

		cy.go('back');

		cy.get('#who').should('have.text', 'A');
		cy.location('pathname').should('eq', '/swap-fixture/a.html');
		// The history entry the library pushed is one it can restore. If `popstate`
		// were unhandled the address would go back and the content would not — the
		// two would disagree and only the address would look right.
		stillAlive();
	});

	it('a document that declares no region is left completely alone', () => {
		// The guard against the worst failure this file could have. Loading the
		// script must never be enough to take over a document — only declaring a
		// region is. Without that rule an application that adopts a fetched page's
		// scripts would silently lose control of every link it owns.
		//
		// The fixture has a `<main>`, because `<main>` was the default that made
		// this possible.
		cy.visit('/swap-fixture/none.html');
		cy.get('#who').should('have.text', 'none');
		mark();

		cy.get('#to-b').click();

		cy.location('pathname').should('eq', '/swap-fixture/b.html');
		cy.window().then((win) => {
			expect(
				(win as never as Record<string, unknown>)[SENTINEL] ? 'HIJACKED' : 'navigated',
				'an undeclared document must behave as if the script were not there'
			).to.eq('navigated');
		});
	});

	it('a link that does not answer with a page is left to the browser', () => {
		cy.visit('/swap-fixture/a.html');
		mark();

		cy.get('#to-json').click();

		// A real navigation, which is what makes a download download. Swapping it
		// would put raw JSON where the page was and lose the file entirely.
		cy.location('pathname').should('eq', '/swap-fixture/data.json');
		cy.window().then((win) => {
			expect(
				(win as never as Record<string, unknown>)[SENTINEL] ? 'SWALLOWED BY A SWAP' : 'navigated',
				'a non-HTML response must fall through to a real navigation'
			).to.eq('navigated');
		});
	});
});

describe('the library on the app: whole-page and sub-swap', () => {
	beforeEach(() => cy.loginAdmin());

	it('an in-surface link swaps the page in place and keeps the address', () => {
		// Arrive WITH a query, so "clear search" is rendered. A fresh container has
		// no agents and no tags, so every other in-surface link on this page is
		// conditional — the first draft of this test asked for one of those and
		// failed on an empty instance rather than on a defect.
		cy.visit('/pages/workshop/agents?q=zzz-no-such-agent');
		cy.get('[data-cy="page-heading"]').should('exist');
		mark();

		cy.get('[data-cy="agents-search-clear"]').click();

		// A server-rendered page answered, and the query is gone from the address.
		cy.get('[data-cy="page-heading"]').should('exist');
		cy.location('pathname').should('contain', '/pages/workshop/agents');
		cy.location('search').should('not.contain', 'zzz-no-such-agent');
		stillAlive();
	});

	it('a sub-swap replaces its region and nothing else', () => {
		cy.visit('/pages/workshop/prompts');
		cy.get('#prompts-results').should('exist');
		mark();

		// The search form is OUTSIDE `#prompts-results` and names it with
		// `data-swap-target`. That is the case the nearest-ancestor rule cannot
		// reach, and the only reason the attribute exists.
		cy.get('[data-cy="prompts-search"]').as('input').type('zzz-no-such-prompt');

		// Hold the identity of a node outside the region. A whole-page swap and a
		// sub-swap look the same to a reader; this is what tells them apart.
		cy.get('[data-cy="prompts-create"]').then(($outside) => {
			const before = $outside[0];

			cy.get('@input').type('{enter}');
			cy.get('[data-cy="prompts-list"]', { timeout: 20000 }).should('exist');

			cy.get('[data-cy="prompts-create"]').then(($after) => {
				expect(
					$after[0] === before ? 'untouched' : 'REPLACED — the whole page swapped',
					'a sub-swap must not replace anything outside its region'
				).to.eq('untouched');
			});
			// The typed text survived, which is the reason the form is outside the
			// region: replacing an input loses focus and cursor position.
			cy.get('[data-cy="prompts-search"]').should('have.value', 'zzz-no-such-prompt');
			stillAlive();
		});
	});

	it('a link off the surface still navigates', () => {
		cy.visit('/pages/workshop/agents');
		cy.get('[data-cy="page-heading"]').should('exist');
		mark();

		// `agents-create` points at the SPA, not at `/pages/`. The `data-swap`
		// VALUE on <main> is what confines the library; without it this link would
		// be fetched and whatever came back grafted into a server page.
		//
		// This one is unconditional. The Sprigs "Health" link would have read
		// better and renders only for a grafted Sprig with health, so on a fresh
		// container it is not there at all.
		cy.get('[data-cy="agents-create"]').click();

		// The assertion is that we LEFT the surface — not which route caught us,
		// since the SPA is free to redirect once it boots.
		cy.location('pathname').should('not.contain', '/pages/');
		cy.window().then((win) => {
			expect(
				(win as never as Record<string, unknown>)[SENTINEL] ? 'SWALLOWED BY A SWAP' : 'navigated',
				'a link that leaves /pages/ must be left alone'
			).to.eq('navigated');
		});
	});

	it('a signed-out reader is sent to sign in, not shown an empty box', () => {
		cy.visit('/pages/workshop/prompts');
		cy.get('#prompts-results').should('exist');

		// The cookie is what authenticates a server-rendered page. Dropping it mid
		// visit is exactly the expired-session case.
		cy.clearCookies();
		cy.get('[data-cy="prompts-search"]').type('anything{enter}');

		// The server redirects out of `/pages/`, the library reports the landing
		// address rather than the status, and follows it. The failure this replaces
		// is a region emptied of content with nothing said.
		cy.location('pathname', { timeout: 20000 }).should('eq', '/auth');
	});
});
