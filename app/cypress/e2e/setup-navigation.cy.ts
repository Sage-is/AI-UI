// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild } from '../support/surfaces';

// Navigation between the setup routes.
//
// No-build only, and not because the legacy side is exempt. It has
// nowhere to navigate. The wizard's sequence is Svelte state inside a modal;
// these are five addresses that a reader can land on cold. Without links each
// one is a cul-de-sac, which is what the manual review pass reported first.
//
// The order here is asserted against the pages themselves rather than restated,
// so adding a sixth panel to `_SETUP_ORDER` cannot leave this spec describing a
// sequence that no longer exists.

const ORDER = [
	'changelog',
	'welcome',
	'connection',
	'users',
	'features',
	'search-audio',
	'developer',
	'complete'
];

describe('Setup routes link to each other', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	it('numbers each panel and agrees on the total', () => {
		ORDER.forEach((panel, i) => {
			cy.visit(`/pages/admin/setup/${panel}`);
			cy.get('[data-cy="setup-step"]')
				.should('have.attr', 'data-step', String(i + 1))
				.and('have.attr', 'data-of', String(ORDER.length));
		});
	});

	it('offers no way back from the first panel and no way on from the last', () => {
		cy.visit(`/pages/admin/setup/${ORDER[0]}`);
		cy.get('[data-cy="setup-prev"]').should('not.exist');
		cy.get('[data-cy="setup-next"]').should('exist');

		cy.visit(`/pages/admin/setup/${ORDER[ORDER.length - 1]}`);
		cy.get('[data-cy="setup-next"]').should('not.exist');
		cy.get('[data-cy="setup-prev"]').should('exist');
	});

	it('walks forward through every panel and back again', () => {
		cy.visit(`/pages/admin/setup/${ORDER[0]}`);
		ORDER.slice(1).forEach((panel) => {
			cy.get('[data-cy="setup-next"]').click();
			cy.location('pathname').should('eq', `/pages/admin/setup/${panel}`);
		});
		ORDER.slice(0, -1)
			.reverse()
			.forEach((panel) => {
				cy.get('[data-cy="setup-prev"]').click();
				cy.location('pathname').should('eq', `/pages/admin/setup/${panel}`);
			});
	});
});
