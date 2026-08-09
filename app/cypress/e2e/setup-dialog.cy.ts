// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { closeAnyModal } from '../support/surfaces';

// The dialog host. The only code the cut-over added, and therefore the only
// thing left that needs a gate of its own.
//
// Nine wizard panels are server-rendered routes with their own specs. What is
// new is `SetupDialog.svelte`: 200-odd lines that fetch one of those routes,
// lift the panel out of the response and show it in a native `<dialog>`. It
// replaced `ChangesAndSetupModal.svelte` and nine step components — 2,132 lines
// — so the nine wizard entries in the surface registry went with them. Comparing
// a route against itself would have passed for the wrong reason.
//
// This is what took their place, and it judges the four things the host can get
// wrong that no route spec would notice: the panel arriving at all, a link or a
// form being followed without a page load, a panel's script running, and the
// flow ending when the server says it has.
//
// Escape is NOT asserted. Closing on Escape is the element's own behaviour, and
// Cypress dispatches synthetic key events that a browser does not treat as the
// real thing — a test of it would pass or fail for reasons unrelated to this
// code. The close button, which IS ours, is asserted instead.

const GENERAL = '/admin/settings/general';

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

const writeUi = (ui: Record<string, unknown>) =>
	auth().then((token) =>
		cy.request({
			method: 'POST',
			url: '/api/v1/users/user/settings/update',
			headers: { Authorization: `Bearer ${token}` },
			body: { ui }
		})
	);

/**
 * Open the wizard the way an admin does, from general settings.
 *
 * The settle-then-clear dance is inherited from the retired registry callback
 * and the reason has not changed: two things open a modal on this page without
 * being asked — the wizard's own auto-trigger and the dev mission reminder — and
 * both mount after the layout has fetched config and settings. Clearing the
 * moment the DOM exists finds nothing and the modal appears immediately
 * afterwards, on top of the button about to be clicked.
 */
const openWizard = (trigger = 'run-setup-wizard') => {
	cy.visit(GENERAL);
	cy.get(`[data-cy="${trigger}"]`, { timeout: 30000 }).should('exist');
	cy.wait(1200);
	closeAnyModal();
	cy.get(`[data-cy="${trigger}"]`).click();
	cy.get('dialog[open]', { timeout: 30000 }).should('exist');
};

/**
 * Every data-cy value under a root.
 *
 * The ui-Sprig slot is skipped on both sides. It is a marketplace fragment the
 * page shell renders and the dialog deliberately drops, so counting it would
 * turn "an operator has a ui-Sprig grafted" into a failure of this gate.
 */
const hooksUnder = (root: ParentNode | null) => {
	const found = new Set<string>();
	root?.querySelectorAll('[data-cy]').forEach((el) => {
		if (el.closest('#sprig-ui-slot')) return;
		const v = el.getAttribute('data-cy');
		if (v) found.add(v);
	});
	return found;
};

describe('Setup dialog: the panel arrives', () => {
	beforeEach(() => cy.loginAdmin());

	it('opens on welcome without leaving the page it was triggered from', () => {
		openWizard();
		cy.get('dialog[open] [data-cy="welcome-panel"]').should('be.visible');
		// The whole point of a dialog over a route: the reader is still where
		// they were, so closing it puts them back rather than costing a
		// navigation.
		cy.location('pathname').should('eq', GENERAL);
	});

	it('opens on the changelog when that is what was asked for', () => {
		openWizard('see-whats-new');
		cy.get('dialog[open] [data-cy="changelog-panel"]').should('be.visible');
		cy.get('dialog[open] [data-cy="welcome-panel"]').should('not.exist');
	});

	it('closes when the close button is pressed', () => {
		openWizard();
		cy.get('dialog[open] [data-cy="setup-close"]').click();
		cy.get('dialog[open]').should('not.exist');
	});
});

// The extraction gate. This is what the retired parity entries were doing, kept
// once rather than nine times, because the extraction is one code path.
//
// It can fail: stop lifting the nav out of the response — it is a sibling of the
// panel root, not a child — and `setup-next`, `setup-prev` and `setup-step` go
// missing from this set while every panel spec stays green.
describe('Setup dialog: delivery loses nothing', () => {
	beforeEach(() => cy.loginAdmin());

	it('shows every control the route renders', () => {
		let fromRoute = new Set<string>();

		cy.visit('/pages/admin/setup/welcome');
		cy.get('[data-cy="welcome-panel"]', { timeout: 30000 }).should('exist');
		cy.document().then((doc) => {
			fromRoute = hooksUnder(doc.querySelector('main'));
			expect(fromRoute.size, 'the route rendered something to compare against').to.be.greaterThan(
				3
			);
		});

		openWizard();
		cy.get('dialog[open] [data-cy="welcome-panel"]').should('be.visible');
		cy.document().then((doc) => {
			const inDialog = hooksUnder(doc.querySelector('[data-cy="setup-content"]'));
			const missing = [...fromRoute].filter((h) => !inDialog.has(h)).sort();
			// On a string, not an array: Chai renders a failed array comparison as
			// "expected [ Array(3) ] to deeply equal []", which says something is
			// missing without saying what.
			expect(
				missing.join(', ') || 'nothing missing',
				'controls the route renders that the dialog dropped'
			).to.eq('nothing missing');
		});
	});
});

describe('Setup dialog: navigation happens in place', () => {
	beforeEach(() => cy.loginAdmin());

	it('follows a panel link without a page load', () => {
		openWizard();
		cy.get('dialog[open] [data-cy="setup-next"]').click();
		// Welcome's neighbour, per _SETUP_ORDER in pages/router.py.
		cy.get('dialog[open] [data-cy="auth-panel"]', { timeout: 30000 }).should('be.visible');
		cy.location('pathname').should('eq', GENERAL);
	});

	it('posts a form and shows what came back', () => {
		openWizard();
		// One step ticked, so the server's redirect target is known rather than
		// whatever the instance happened to default to.
		[
			'welcome-auth',
			'welcome-connection',
			'welcome-users',
			'welcome-features',
			'welcome-search-audio',
			'welcome-developer'
		].forEach((hook) => cy.get(`dialog[open] [data-cy="${hook}"]`).uncheck({ force: true }));
		cy.get('dialog[open] [data-cy="welcome-developer"]').check({ force: true });
		cy.get('dialog[open] [data-cy="welcome-start"]').click();
		// The post 303s and the fetch follows it, so arriving here proves both the
		// submit interception and the redirect being honoured.
		cy.get('dialog[open] [data-cy="developer-panel"]', { timeout: 30000 }).should('be.visible');
		cy.location('pathname').should('eq', GENERAL);
	});

	// A panel's script has to be run by hand: a `<script>` parsed out of a fetched
	// document never executes. The changelog is the only panel that asks for one,
	// and its starting state is the visible proof that it ran — without the pager,
	// the server renders the button in its END position with its END label.
	it('runs the script a panel asks for', () => {
		openWizard('see-whats-new');
		cy.get('dialog[open] [data-pager-row]', { timeout: 30000 }).should(
			'have.attr',
			'data-at-end',
			'false'
		);
		cy.get('dialog[open] [data-cy="changelog-continue"]').should('contain.text', 'Next page');
	});
});

// How a flow ends. Not a flag and not a close button: the server redirects out
// of `/pages/`, and the host reads that as "the errand is over". The same
// redirect gives a reader with no JavaScript a working ending — back in the app
// rather than staring at the summary they just dismissed.
describe('Setup dialog: the server decides when it is over', () => {
	beforeEach(() => cy.loginAdmin());

	it('closes when finishing setup sends the reader back to the app', () => {
		openWizard();
		// Nothing ticked falls through to the summary, which is where finish lives.
		[
			'welcome-auth',
			'welcome-connection',
			'welcome-users',
			'welcome-features',
			'welcome-search-audio',
			'welcome-developer'
		].forEach((hook) => cy.get(`dialog[open] [data-cy="${hook}"]`).uncheck({ force: true }));
		cy.get('dialog[open] [data-cy="welcome-start"]').click();
		cy.get('dialog[open] [data-cy="complete-finish"]', { timeout: 30000 }).click();

		cy.get('dialog[open]', { timeout: 30000 }).should('not.exist');
		// Closed, not navigated. The redirect was followed by the fetch, so the
		// browser never left the page the dialog opened over.
		cy.location('pathname').should('eq', GENERAL);
	});

	// The harness marks setup complete at login, and the run above cleared and
	// re-set it. Put it back so a later spec does not meet an auto-opening wizard.
	afterEach(() => readUi().then((ui) => writeUi({ ...ui, setupCompleted: true })));
});

// Release notes are not admin material. Every reader can open Settings, About,
// "See what's new", and before the wizard moved to the server that button opened
// a component with no role check at all. Pointing it at the admin tree would
// have turned a working control into a 403 for everybody who is not an admin,
// which is why `/pages/changelog` exists and why the host picks it by role.
describe('Setup dialog: the changelog is not admin-only', () => {
	const reader = {
		name: 'Changelog Reader',
		email: `changelog-reader-${Cypress.env('RUN_ID') ?? 'local'}@example.com`,
		password: 'changelog-reader-pw-1'
	};

	before(() => {
		cy.loginAdmin();
		// Through the panel's own route, which is the only way in: signup closes
		// after the first admin.
		cy.request({
			method: 'POST',
			url: '/pages/admin/setup/users/add',
			form: true,
			body: { name: reader.name, email: reader.email, password: reader.password, role: 'user' },
			failOnStatusCode: false
		});
	});

	it('serves the notes to a reader who is not an admin, and the admin route does not', () => {
		cy.login(reader.email, reader.password);
		cy.request({ url: '/pages/changelog', failOnStatusCode: false }).should((res) => {
			expect(res.status, '/pages/changelog is open to any signed-in reader').to.eq(200);
			expect(res.body, 'and it is the same panel').to.contain('data-cy="changelog-panel"');
		});
		cy.request({ url: '/pages/admin/setup/changelog', failOnStatusCode: false })
			.its('status')
			.should('eq', 403);
	});
});
