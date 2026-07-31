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
// Per-surface: does this surface promise to KEEP its layout without the
// framework, or only to stay usable?
//
// The two list surfaces style their generated rows from pages.css, so their
// grid survives and is worth asserting. Branding is authored with startr.style
// props (a deliberate call — the framework is first-party and editing one
// string beats maintaining a parallel stylesheet), which means its layout is
// the framework's by definition and CANNOT survive its absence. Asserting a
// grid there would be asserting something we chose not to build.
//
// So branding is `null` here, and what the rest of this spec checks still
// applies to it: every control renders, and nothing overflows the viewport.
// Be honest about the difference rather than quietly dropping the surface —
// what it no longer proves is that branding looks right during an outage. What
// it still proves is that branding remains USABLE during one, which is the
// property that actually matters to an operator on an air-gapped Rootstock.
interface Outage {
	name: string;
	url: string;
	/** How many hooks proves the content survived. */
	minHooks: number;
	structure: { selector: string; display: string } | null;
}

// The nine setup panels are checked from their own addresses rather than from
// the surface registry. They used to be listed there, alongside a callback that
// opened the modal they lived in; the modal is deleted and the entries went with
// it, but these are the surfaces MOST worth checking here — every one of them is
// authored in startr.style props, so an outage is exactly the condition they are
// least prepared for. Naming the routes keeps that coverage.
//
// Hook counts are per panel and deliberately below what a whole admin page
// renders: a wizard step has fewer controls than a page and always will, so
// holding it to the page number would make this gate fail for being small
// rather than for being broken.
const SETUP: ReadonlyArray<readonly [string, number]> = [
	['changelog', 3],
	['welcome', 7],
	['auth', 10],
	['connection', 5],
	['users', 7],
	['features', 6],
	['search-audio', 4],
	['developer', 3],
	['complete', 3]
];

const STRUCTURE: Record<SurfaceName, { selector: string; display: string } | null> = {
	sprigs: { selector: '[data-cy="sprig-card"]', display: 'grid' },
	diagnostics: { selector: '[data-cy="diag-row"]', display: 'grid' },
	branding: null
};

const TARGETS: Outage[] = [
	...(Object.keys(SURFACES) as SurfaceName[]).map((name) => ({
		name,
		url: SURFACES[name].nobuild,
		minHooks: 5,
		structure: STRUCTURE[name]
	})),
	...SETUP.map(([panel, minHooks]) => ({
		name: `setup/${panel}`,
		url: `/pages/admin/setup/${panel}`,
		minHooks,
		structure: null
	}))
];

describe('No-build pages survive a startr.style outage', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
		// Regex, not a glob. See above.
		cy.intercept({ url: /startr\.style/ }, { forceNetworkError: true }).as('cdn');
	});

	TARGETS.forEach(({ name, url, minHooks, structure }) => {
		it(`${name}: stays usable without the framework`, () => {
			cy.visit(url);

			// Content is server-rendered, so a missing stylesheet cannot cost us
			// any of it. If this drops, something moved into the framework that
			// should not have.
			cy.get('[data-cy]', { timeout: 30000 }).should('have.length.at.least', minHooks);

			// Only for surfaces that promise to KEEP their layout. A
			// props-styled surface has no such promise to check — see the note
			// on STRUCTURE — and asserting one anyway would be asserting
			// something we deliberately chose not to build.
			if (structure) {
				cy.get(structure.selector).first().should('have.css', 'display', structure.display);
			}

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
