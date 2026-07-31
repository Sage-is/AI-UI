// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild, openSurface } from '../support/surfaces';

// Sign-in providers. Guard-rail, written against the SvelteKit panel first.
//
// The contract both implementations owe: a client ID and a secret per provider,
// and the sign-up toggles. That much is shape, and the parity gate covers most
// of it.
//
// The assertion worth having is the one below it — pressing Save without
// touching anything must change nothing. This panel writes two whole-object
// models, `OAuthConfig` and `AdminConfig`, and it renders neither in full: the
// three secrets come back blank by design, and `AdminConfig` carries sixteen
// fields of which the panel shows one. Both are read-merge-write, and both fail
// the same way — silently, into config, discovered later by an admin who cannot
// sign in. A no-op Save is the cheapest thing that catches either.
//
// Every mutation here is restored in `after`. The e2e rootstock is one shared
// container for the whole run, so a spec that leaves auth config altered is a
// spec that breaks whichever file happens to run next. That has bitten this
// suite before.

const auth = () => cy.window().then((win) => win.localStorage.getItem('token'));

const readOAuth = () =>
	auth().then((token) =>
		cy
			.request({
				url: '/api/v1/auths/admin/config/oauth',
				headers: { Authorization: `Bearer ${token}` }
			})
			.then((res) => res.body)
	);

const writeOAuth = (body: Record<string, unknown>) =>
	auth().then((token) =>
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/admin/config/oauth',
			headers: { Authorization: `Bearer ${token}` },
			body
		})
	);

const readAdmin = () =>
	auth().then((token) =>
		cy
			.request({
				url: '/api/v1/auths/admin/config',
				headers: { Authorization: `Bearer ${token}` }
			})
			.then((res) => res.body)
	);

const PROVIDERS = ['google', 'github'];

describe('Setup wizard: authentication', () => {
	beforeEach(() => cy.loginAdmin());

	it('offers a client ID and a secret for each provider', () => {
		openSurface('wizardAuth');
		PROVIDERS.forEach((provider) => {
			cy.get(`[data-cy="auth-${provider}-client-id"]`).should('exist');
			cy.get(`[data-cy="auth-${provider}-client-secret"]`).should('exist');
		});
	});

	it('offers the sign-up controls and a way to save', () => {
		openSurface('wizardAuth');
		cy.get('[data-cy="auth-enable-signup"]').should('exist');
		cy.get('[data-cy="auth-oauth-merge-accounts-by-email"]').should('exist');
		cy.get('[data-cy="auth-enable-magic-link-login"]').should('exist');
		cy.get('[data-cy="auth-save"]').should('exist');
	});
});

// No-build only. The modal reads all three secrets into its inputs on mount, so
// they are in the DOM by construction; asserting otherwise of the modal would be
// asserting it had already been migrated.
describe('Setup wizard: auth secrets are never rendered back', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	it('renders every secret field empty', () => {
		openSurface('wizardAuth');
		PROVIDERS.forEach((provider) =>
			cy.get(`[data-cy="auth-${provider}-client-secret"]`).should('have.value', '')
		);
		cy.get('[data-cy="auth-magic-link-smtp-password"]').should('have.value', '');
	});

	// Not the field, the whole document. A value echoed anywhere in the HTML
	// reaches the disk cache and the back button.
	it('keeps stored secrets out of the page source', () => {
		readOAuth().then((cfg) => {
			const secrets = [
				cfg.GOOGLE_CLIENT_SECRET,
				cfg.GITHUB_CLIENT_SECRET,
				cfg.MAGIC_LINK_SMTP_PASSWORD
			].filter(Boolean);
			if (!secrets.length) {
				cy.log('no secrets stored on this instance — nothing to leak');
				return;
			}
			cy.request('/pages/admin/setup/auth').then((page) => {
				secrets.forEach((secret: string) =>
					expect(page.body, 'a stored secret appears in the HTML').to.not.contain(secret)
				);
			});
		});
	});

	it('says a secret is stored without showing it', () => {
		openSurface('wizardAuth');
		cy.get('[data-cy="auth-google-client-secret"]')
			.should('have.attr', 'data-stored')
			.and('match', /true|false/);
	});
});

// The assertion this file exists for.
describe('Setup wizard: saving auth without edits changes nothing', () => {
	// Not named `before`/`after` — those are Mocha's own hook functions, and a
	// local of the same name shadows them for the whole suite. The failure is a
	// bare "before is not a function" at load time, with no test named.
	let storedOAuth: Record<string, unknown>;
	let storedAdmin: Record<string, unknown>;

	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	// A secret the panel will render blank, so pressing Save is a real test of
	// "blank keeps what is stored" rather than a test of an empty field staying
	// empty. Magic-link SMTP is inert unless the feature is enabled, so seeding it
	// registers no provider and changes no login page.
	const SEEDED = 'seeded-smtp-password-do-not-keep';

	before(() => {
		cy.loginAdmin();
		readOAuth().then((cfg) => {
			storedOAuth = cfg;
			writeOAuth({ ...cfg, MAGIC_LINK_SMTP_PASSWORD: SEEDED });
		});
		readAdmin().then((cfg) => {
			storedAdmin = cfg;
		});
	});

	after(() => {
		cy.loginAdmin();
		if (storedOAuth) writeOAuth(storedOAuth);
	});

	it('keeps the stored secret when the field is submitted blank', () => {
		openSurface('wizardAuth');
		cy.get('[data-cy="auth-magic-link-smtp-password"]').should('have.value', '');
		cy.get('[data-cy="auth-save"]').click();
		cy.get('[data-cy="auth-saved"]', { timeout: 30000 }).should('exist');
		readOAuth().should((cfg) => {
			expect(cfg.MAGIC_LINK_SMTP_PASSWORD, 'the stored secret survived a blank submit').to.eq(
				SEEDED
			);
		});
	});

	it('leaves every admin-config field it does not show alone', () => {
		openSurface('wizardAuth');
		cy.get('[data-cy="auth-save"]').click();
		cy.get('[data-cy="auth-saved"]', { timeout: 30000 }).should('exist');
		readAdmin().should((cfg) => {
			// ENABLE_SIGNUP is the one field this panel owns, so it is allowed to
			// differ in principle; nothing here changed it, so it must not.
			expect(cfg, 'the whole admin config survived a no-op save').to.deep.eq(storedAdmin);
		});
	});
});

// The other half of a settings form: it must be able to turn something OFF.
// An unchecked checkbox posts nothing, so a handler that reads only what arrived
// treats "cleared it" as "did not mention it" and the box springs back on.
describe('Setup wizard: an auth toggle can be turned off', () => {
	let storedOAuth: Record<string, unknown>;

	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	before(() => {
		cy.loginAdmin();
		readOAuth().then((cfg) => {
			storedOAuth = cfg;
			writeOAuth({ ...cfg, OAUTH_MERGE_ACCOUNTS_BY_EMAIL: true });
		});
	});

	after(() => {
		cy.loginAdmin();
		if (storedOAuth) writeOAuth(storedOAuth);
	});

	it('clears merge-accounts-by-email and it stays cleared', () => {
		openSurface('wizardAuth');
		cy.get('[data-cy="auth-oauth-merge-accounts-by-email"]').should('be.checked').uncheck();
		cy.get('[data-cy="auth-save"]').click();
		cy.get('[data-cy="auth-saved"]', { timeout: 30000 }).should('exist');
		readOAuth().should((cfg) => {
			expect(cfg.OAUTH_MERGE_ACCOUNTS_BY_EMAIL, 'the cleared box stayed cleared').to.eq(false);
		});
	});
});
