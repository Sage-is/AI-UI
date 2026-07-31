// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { openSetupPanel } from '../support/surfaces';

// The wizard's opening choice, guard-rail, written against the SvelteKit panel
// first.
//
// What this panel owes the reader: a control for every step, and a start button
// that takes you somewhere.

const STEPS = [
	'welcome-auth',
	'welcome-connection',
	'welcome-users',
	'welcome-features',
	'welcome-search-audio',
	'welcome-developer'
];

const auth = () => cy.window().then((win) => win.localStorage.getItem('token'));

const readUi = () =>
	auth().then((token) =>
		cy
			.request({
				url: '/api/v1/users/user/settings',
				headers: { Authorization: `Bearer ${token}` }
			})
			.then((res) => res.body?.ui ?? {})
	);

describe('Setup wizard: choosing steps', () => {
	beforeEach(() => cy.loginAdmin());

	it('offers a control for every step', () => {
		openSetupPanel('welcome');
		STEPS.forEach((hook) => {
			cy.get(`[data-cy="welcome-panel"] [data-cy="${hook}"]`).should('exist');
		});
		cy.get('[data-cy="welcome-start"]').should('exist');
	});

	it('leaves the choice behind when you start', () => {
		openSetupPanel('welcome');
		cy.get('[data-cy="welcome-features"]').check({ force: true });
		cy.get('[data-cy="welcome-start"]').click();
		// Somewhere else. Which panel depends on what was ticked, and the next
		// describe pins that down; here the only claim is that pressing start
		// leaves this panel.
		cy.get('[data-cy="welcome-panel"]').should('not.exist');
	});
});

// The migration's actual gain on this panel: the answer outlives the page. The
// deleted modal kept it in a component variable that died with the modal; the
// route writes `ui.selectedSteps`, which is what lets a panel at its own URL
// know whether it was meant to be part of this run.
//
// This is also what makes the dialog host possible. It holds no wizard state of
// its own — it fetches whichever panel the server sends it to next.
describe('Setup wizard: the chosen steps are durable', () => {
	beforeEach(() => cy.loginAdmin());

	it('records exactly what was ticked', () => {
		openSetupPanel('welcome');
		STEPS.forEach((hook) => cy.get(`[data-cy="${hook}"]`).uncheck({ force: true }));
		cy.get('[data-cy="welcome-features"]').check({ force: true });
		cy.get('[data-cy="welcome-developer"]').check({ force: true });
		cy.get('[data-cy="welcome-start"]').click();
		readUi().should((ui: Record<string, unknown>) => {
			expect(ui.selectedSteps, 'server stored the choice').to.deep.eq([
				'features',
				'developer'
			]);
		});
	});

	it('starts at the first chosen step that has a route', () => {
		openSetupPanel('welcome');
		STEPS.forEach((hook) => cy.get(`[data-cy="${hook}"]`).uncheck({ force: true }));
		cy.get('[data-cy="welcome-developer"]').check({ force: true });
		cy.get('[data-cy="welcome-start"]').click();
		cy.location('pathname').should('eq', '/pages/admin/setup/developer');
	});

	// This used to assert that choosing auth landed on the summary, because auth
	// had no route. It has one now, so that assertion was describing a gap rather
	// than a contract — the kind of test that quietly blocks the fix it was
	// written beside. What survives is the property worth keeping: every step the
	// panel offers must lead somewhere real.
	it('sends every step it offers to a route that exists', () => {
		const DESTINATIONS: Record<string, string> = {
			'welcome-auth': 'auth',
			'welcome-connection': 'connection',
			'welcome-users': 'users',
			'welcome-features': 'features',
			'welcome-search-audio': 'search-audio',
			'welcome-developer': 'developer'
		};
		Object.entries(DESTINATIONS).forEach(([hook, panel]) => {
			openSetupPanel('welcome');
			STEPS.forEach((h) => cy.get(`[data-cy="${h}"]`).uncheck({ force: true }));
			cy.get(`[data-cy="${hook}"]`).check({ force: true });
			cy.get('[data-cy="welcome-start"]').click();
			cy.location('pathname').should('eq', `/pages/admin/setup/${panel}`);
		});
	});

	// Choosing nothing is still a real answer, and it must not strand the reader.
	it('falls through to the summary when nothing is chosen', () => {
		openSetupPanel('welcome');
		STEPS.forEach((hook) => cy.get(`[data-cy="${hook}"]`).uncheck({ force: true }));
		cy.get('[data-cy="welcome-start"]').click();
		cy.location('pathname').should('eq', '/pages/admin/setup/complete');
	});

	it('remembers the choice when you come back', () => {
		openSetupPanel('welcome');
		STEPS.forEach((hook) => cy.get(`[data-cy="${hook}"]`).uncheck({ force: true }));
		cy.get('[data-cy="welcome-features"]').check({ force: true });
		cy.get('[data-cy="welcome-start"]').click();
		openSetupPanel('welcome');
		cy.get('[data-cy="welcome-features"]').should('be.checked');
		cy.get('[data-cy="welcome-auth"]').should('not.be.checked');
	});
});
