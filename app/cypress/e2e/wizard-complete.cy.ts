// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { openSetupPanel } from '../support/surfaces';

// The wizard's closing summary. Guard-rail, written against the SvelteKit
// panel first.
//
// This panel reports rather than configures, so what is checkable is that the
// numbers it reports are the server's numbers. They are read off data
// attributes rather than the sentences, which means a pluralisation change or a
// translation cannot turn this red, and a wrong count still can.
//
// Deliberately NOT asserted: the auth, connection and working-alone lines. The
// two implementations derive those from different questions. The modal asks
// whether the browser finished loading a model list and what the user clicked
// during this run; the page asks what the configuration and the stored settings
// say. Both are defensible and they disagree on a fresh instance, so pinning
// them here would either force one to imitate the other's accident or, worse,
// get relaxed until it checked nothing. Named in complete_panel.py and left to
// the human review pass.

const SUPPRESS = { setupCompleted: true, showChangelog: false, workingAlone: true };

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
			body: { ui: { ...SUPPRESS, ...ui } }
		})
	);

const nonAdminUsers = () =>
	auth().then((token) =>
		cy
			.request({ url: '/api/v1/users/', headers: { Authorization: `Bearer ${token}` } })
			.then((res) => {
				const rows = Array.isArray(res.body) ? res.body : (res.body?.users ?? []);
				return rows.filter((u: { role: string }) => u.role !== 'admin').length;
			})
	);

const FLAGS = [
	'ENABLE_COMMUNITY_SHARING',
	'ENABLE_MESSAGE_RATING',
	'ENABLE_NOTES',
	'ENABLE_SPACES',
	'ENABLE_USER_WEBHOOKS'
];

const enabledFeatures = () =>
	auth().then((token) =>
		cy
			.request({
				url: '/api/v1/auths/admin/config',
				headers: { Authorization: `Bearer ${token}` }
			})
			.then((res) => FLAGS.filter((f) => res.body[f]).length)
	);

const expectSetupCompleted = (attempt = 0) => {
	readUi().then((ui: Record<string, unknown>) => {
		if (ui.setupCompleted === true) return;
		if (attempt >= 20) {
			expect(ui.setupCompleted, 'server recorded setup as complete').to.eq(true);
			return;
		}
		cy.wait(250);
		expectSetupCompleted(attempt + 1);
	});
};

/**
 * Open the panel AND wait for it to finish gathering.
 *
 * The Svelte panel renders its summary inside an `{#if loading}` else-branch,
 * so the root element exists well before the four fetches behind it resolve.
 * Asserting on the root alone reads zeros and an empty list, which looks like
 * a correct empty instance, not a race. The features line is the settle signal
 * because it is the one line that always renders, even at a count of zero.
 */
const openComplete = () => {
	openSetupPanel('complete');
	cy.get('[data-check="features"]', { timeout: 30000 }).should('exist');
};

describe('Setup wizard: completion summary', () => {
	beforeEach(() => cy.loginAdmin());

	it('reports the number of non-admin users the server has', () => {
		nonAdminUsers().then((count) => {
			openComplete();
			cy.get('[data-cy="complete-panel"]').should('have.attr', 'data-users', String(count));
		});
	});

	it('reports the number of features the server has enabled', () => {
		enabledFeatures().then((count) => {
			openComplete();
			cy.get('[data-cy="complete-panel"]').should('have.attr', 'data-features', String(count));
		});
	});

	it('always shows the features line, even at zero', () => {
		openComplete();
		cy.get('[data-check="features"]').should('exist');
	});

	it('shows the users line only when there are non-admin users', () => {
		nonAdminUsers().then((count) => {
			openComplete();
			cy.get('[data-cy="complete-panel"]').then(($p) => {
				const line = $p.find('[data-check="users"]').length;
				expect(line > 0, `users line present with ${count} non-admin users`).to.eq(count > 0);
			});
		});
	});

	it('records setup as complete when you finish', () => {
		// Clear it first, or this passes whether or not the button did anything —
		// the harness marks setup complete at login.
		readUi().then((ui) => {
			writeUi({ ...ui, setupCompleted: false });
			openComplete();
			cy.get('[data-cy="complete-finish"]').click();
			expectSetupCompleted();
		});
	});

	afterEach(() => readUi().then((ui) => writeUi({ ...ui, setupCompleted: true })));
});
