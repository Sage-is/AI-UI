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
const STRUCTURE: Record<SurfaceName, { selector: string; display: string } | null> = {
	sprigs: { selector: '[data-cy="sprig-card"]', display: 'grid' },
	diagnostics: { selector: '[data-cy="diag-row"]', display: 'grid' },
	branding: null,
	wizardChangelog: null,
	wizardFeatures: null,
	wizardDeveloper: null,
	wizardComplete: null,
	wizardSearchAudio: null
};

// How many hooks proves the content survived. Five suits a whole admin page;
// a single wizard panel has fewer controls than that and always will, so
// holding it to the page number would make this gate fail for being small
// rather than for being broken.
const MIN_HOOKS: Partial<Record<SurfaceName, number>> = {
	wizardChangelog: 3,
	wizardFeatures: 6,
	wizardDeveloper: 3,
	wizardComplete: 3,
	wizardSearchAudio: 4
};

describe('No-build pages survive a startr.style outage', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
		// Regex, not a glob. See above.
		cy.intercept({ url: /startr\.style/ }, { forceNetworkError: true }).as('cdn');
	});

	(Object.keys(SURFACES) as SurfaceName[]).forEach((name) => {
		it(`${name}: stays usable without the framework`, () => {
			cy.visit(SURFACES[name].nobuild);

			// Content is server-rendered, so a missing stylesheet cannot cost us
			// any of it. If this drops, something moved into the framework that
			// should not have.
			cy.get('[data-cy]', { timeout: 30000 }).should(
				'have.length.at.least',
				MIN_HOOKS[name] ?? 5
			);

			// Only for surfaces that promise to KEEP their layout. A
			// props-styled surface has no such promise to check — see the note
			// on STRUCTURE — and asserting one anyway would be asserting
			// something we deliberately chose not to build.
			const structure = STRUCTURE[name];
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
