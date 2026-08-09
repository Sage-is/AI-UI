// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { openSetupPanel } from '../support/surfaces';

// Feature toggles. Guard-rail, written against the SvelteKit panel before any
// code moves, per docs/no-build-surface-convention.md.
//
// The whole contract is: what the server holds is what the form shows, and what
// you tick is what the server ends up holding. So every assertion goes through
// `/api/v1/auths/admin/config` rather than through the rendered checkbox, which
// means neither implementation can satisfy this by agreeing with itself.
//
// The case worth writing a test for is turning something OFF. An unchecked HTML
// checkbox posts nothing at all, so a server that reads only what arrived treats
// "off" as "unmentioned" and leaves the old value in place. That failure looks
// exactly like a save that worked until you reload, which is why "turns a
// feature off" is a separate test below and not folded into the round trip.

const FLAGS = {
	'features-community-sharing': 'ENABLE_COMMUNITY_SHARING',
	'features-message-rating': 'ENABLE_MESSAGE_RATING',
	'features-notes': 'ENABLE_NOTES',
	'features-spaces': 'ENABLE_SPACES',
	'features-user-webhooks': 'ENABLE_USER_WEBHOOKS'
} as const;

type Hook = keyof typeof FLAGS;

const readConfig = () =>
	cy.window().then((win) =>
		cy
			.request({
				url: '/api/v1/auths/admin/config',
				headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` }
			})
			.its('body')
	);

const writeConfig = (patch: Record<string, boolean>) =>
	cy.window().then((win) =>
		readConfig().then((cfg) =>
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/admin/config',
				headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` },
				body: { ...cfg, ...patch }
			})
		)
	);

/** Poll until the server holds `want`. cy.request does not retry on its own. */
const expectFlag = (flag: string, want: boolean, attempt = 0) => {
	readConfig().then((cfg: Record<string, unknown>) => {
		if (cfg[flag] === want) return;
		if (attempt >= 20) {
			expect(cfg[flag], `server holds ${flag}`).to.eq(want);
			return;
		}
		cy.wait(250);
		expectFlag(flag, want, attempt + 1);
	});
};

const ALL_OFF = Object.fromEntries(Object.values(FLAGS).map((f) => [f, false]));

describe('Setup wizard: feature toggles', () => {
	beforeEach(() => cy.loginAdmin());

	// Leave the instance as it was found. These are real platform flags. A
	// leftover ENABLE_SPACES changes what later specs see in the sidebar.
	afterEach(() => writeConfig(ALL_OFF));

	it('renders a control for every feature flag', () => {
		openSetupPanel('features');
		Object.keys(FLAGS).forEach((hook) => {
			cy.get(`[data-cy="features-panel"] [data-cy="${hook}"]`).should('exist');
		});
	});

	it('shows each toggle in the state the server holds', () => {
		writeConfig({ ...ALL_OFF, ENABLE_NOTES: true });
		openSetupPanel('features');
		cy.get('[data-cy="features-notes"]').should('be.checked');
		cy.get('[data-cy="features-spaces"]').should('not.be.checked');
	});

	it('turns a feature on and the server keeps it', () => {
		writeConfig(ALL_OFF);
		openSetupPanel('features');
		cy.get('[data-cy="features-spaces"]').check({ force: true });
		cy.get('[data-cy="features-save"]').click();
		expectFlag('ENABLE_SPACES', true);
	});

	// The one that catches the unchecked-box bug. An unticked checkbox sends
	// nothing, so a save that only reads the posted names cannot turn anything
	// off, and it passes every "turn it on" test while doing so.
	it('turns a feature off and the server keeps it off', () => {
		writeConfig({ ...ALL_OFF, ENABLE_SPACES: true });
		openSetupPanel('features');
		cy.get('[data-cy="features-spaces"]').should('be.checked').uncheck({ force: true });
		cy.get('[data-cy="features-save"]').click();
		expectFlag('ENABLE_SPACES', false);
	});

	it('leaves the other flags alone when one changes', () => {
		writeConfig({ ...ALL_OFF, ENABLE_MESSAGE_RATING: true });
		openSetupPanel('features');
		cy.get('[data-cy="features-notes"]').check({ force: true });
		cy.get('[data-cy="features-save"]').click();
		expectFlag('ENABLE_NOTES', true);
		expectFlag('ENABLE_MESSAGE_RATING', true);
	});

	// Not a feature flag. This proves the save did not post a five-key body and reset
	// everything else in AdminConfig to its model defaults.
	it('does not disturb admin config values it does not own', () => {
		readConfig().then((before: Record<string, unknown>) => {
			const witness = 'ENABLE_SIGNUP';
			expect(before, `${witness} exists to be a witness`).to.have.property(witness);
			openSetupPanel('features');
			cy.get('[data-cy="features-save"]').click();
			cy.wait(500);
			readConfig().then((after: Record<string, unknown>) => {
				expect(after[witness], `${witness} survived a features save`).to.eq(before[witness]);
			});
		});
	});
});
