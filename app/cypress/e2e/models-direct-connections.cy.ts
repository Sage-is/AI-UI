// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL: with direct connections on, every page asks for the model list the
// way the app boot does. 36 calls passed the session token where getModels takes
// the browser's connections, so the connections landed in `base` and the request
// went to /api/models/base: the wrong list for an admin, a 401 for everyone else,
// and the browser's own models never merged (found 2026-08-07, fixed 2026-11-05
// with one loadModels helper).
//
// The workshop models page is one of the 36. Its own request must reach
// /api/models, and nothing on the page may ask for /api/models/base.
//
// The connection names its model, so the merge makes no network call. The admin's
// settings are put back afterwards; the connections config is restored by the
// guard in support/e2e.ts.

const ADMIN = { email: 'admin@example.com', password: 'password' };
const DIRECT = {
	OPENAI_API_BASE_URLS: ['http://127.0.0.1:9/v1'],
	OPENAI_API_KEYS: [''],
	OPENAI_API_CONFIGS: { '0': { enable: true, model_ids: ['direct-fixture-model'] } }
};

describe('model list with direct connections on', () => {
	let token = '';
	let saved: Record<string, any> = {};
	const auth = () => ({ Authorization: `Bearer ${token}` });

	before(() => {
		cy.request({ method: 'POST', url: '/api/v1/auths/signin', body: ADMIN }).then((login) => {
			token = login.body.token;
			cy.request({ url: '/api/v1/users/user/settings', headers: auth() }).then((res) => {
				saved = res.body ?? {};
			});
		});
	});

	after(() => {
		cy.request({
			method: 'POST',
			url: '/api/v1/users/user/settings/update',
			headers: auth(),
			body: saved
		});
	});

	it('asks /api/models, never /api/models/base', () => {
		cy.request({
			method: 'POST',
			url: '/api/v1/users/user/settings/update',
			headers: auth(),
			body: { ...saved, ui: { ...(saved.ui ?? {}), directConnections: DIRECT } }
		});
		cy.request({ url: '/api/v1/configs/connections', headers: auth() }).then((res) => {
			cy.request({
				method: 'POST',
				url: '/api/v1/configs/connections',
				headers: auth(),
				body: { ...res.body, ENABLE_DIRECT_CONNECTIONS: true }
			});
		});

		cy.intercept('GET', '**/api/models/base*').as('base');
		cy.intercept('GET', /\/api\/models(\?|$)/).as('list');
		cy.loginAdmin();
		cy.visit('/workshop/models');

		// The app boot asks first, then the page's own mount.
		cy.wait('@list', { timeout: 30000 });
		cy.wait('@list', { timeout: 30000 });
		cy.get('@base.all').should('have.length', 0);
	});
});
