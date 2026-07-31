// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild } from '../support/surfaces';

// Navigation between the setup routes.
//
// No-build only, and not because the legacy side is exempt. It has nowhere to
// navigate. The wizard's sequence is Svelte state inside a modal; these are
// addresses a reader can land on cold. Without links each one is a cul-de-sac,
// which is what the manual review pass reported first.
//
// The order is DISCOVERED by walking `setup-next`, not restated here. An earlier
// version of this file claimed exactly that in a comment while keeping a
// hardcoded `ORDER` array below it, and adding the auth panel to `_SETUP_ORDER`
// broke two of its three tests — the comment described an intent the code did not
// implement.
//
// A spec that derives everything from the thing it tests can pass by measuring
// nothing, so FLOOR, FIRST and LAST are asserted independently. Those three are
// the contract; the panels between them are free to change.

const FIRST = 'changelog';
const LAST = 'complete';
const FLOOR = 9;

const path = (panel: string) => `/pages/admin/setup/${panel}`;
const panelOf = (pathname: string) => pathname.replace('/pages/admin/setup/', '');

/**
 * Follow `setup-next` from the first panel, collecting the panel at each stop.
 *
 * Recursive rather than a fixed loop, because the length is what we are trying
 * to find out. Bounded well above FLOOR so a nav that links to itself fails the
 * test instead of hanging it.
 */
const walkForward = (seen: string[] = []): Cypress.Chainable<string[]> =>
	cy.location('pathname').then((p) => {
		const next = [...seen, panelOf(p)];
		if (next.length > 40) throw new Error(`setup nav did not terminate: ${next.join(' -> ')}`);
		return cy.get('body').then(($body) => {
			if ($body.find('[data-cy="setup-next"]').length === 0) return cy.wrap(next);
			cy.get('[data-cy="setup-next"]').click();
			return walkForward(next);
		});
	});

describe('Setup routes link to each other', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	it('offers no way back from the first panel and no way on from the last', () => {
		cy.visit(path(FIRST));
		cy.get('[data-cy="setup-prev"]').should('not.exist');
		cy.get('[data-cy="setup-next"]').should('exist');

		cy.visit(path(LAST));
		cy.get('[data-cy="setup-next"]').should('not.exist');
		cy.get('[data-cy="setup-prev"]').should('exist');
	});

	it('walks forward through every panel and back again', () => {
		cy.visit(path(FIRST));
		walkForward().then((order) => {
			expect(order, 'the walk reached every panel').to.have.length.of.at.least(FLOOR);
			expect(order[0], 'the walk starts at the first panel').to.eq(FIRST);
			expect(order[order.length - 1], 'the walk ends at the last panel').to.eq(LAST);
			expect(new Set(order).size, 'no panel appears twice').to.eq(order.length);

			// Back along the same path. Walking out and not being able to walk
			// home is the failure an operator hits, and it is invisible to a
			// forward-only check.
			order
				.slice(0, -1)
				.reverse()
				.forEach((panel) => {
					cy.get('[data-cy="setup-prev"]').click();
					cy.location('pathname').should('eq', path(panel));
				});
		});
	});

	// Numbering is checked against the walk rather than against a restated list,
	// so a panel added to `_SETUP_ORDER` is covered the moment it is linked.
	it('numbers each panel and agrees on the total', () => {
		cy.visit(path(FIRST));
		walkForward().then((order) => {
			order.forEach((panel, i) => {
				cy.visit(path(panel));
				cy.get('[data-cy="setup-step"]')
					.should('have.attr', 'data-step', String(i + 1))
					.and('have.attr', 'data-of', String(order.length));
			});
		});
	});
});
