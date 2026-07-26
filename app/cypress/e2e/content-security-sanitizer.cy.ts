// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL (security): the shared DOMPurify sanitizer must strip hyperscript's
// three attribute forms — `_`, `script`, `data-script` — from ALL sanitized
// content. They're interpreted and CSP-invisible, and DOMPurify's default
// ALLOW_DATA_ATTR lets `data-script` through. hyperscript isn't loaded in the
// app yet; this is defense-in-depth before it's adopted for no-build surfaces.
//
// Exercised through a real @html sanitize path: an admin banner
// (Banner.svelte -> DOMPurify.sanitize(content)) rendered in the chat navbar.
// The probe element keeps its id (allowed) so we can find it and assert the
// hyperscript attributes are gone.

const PROBE =
	'<b id="hs-probe" data-script="pwn" _="on click alert(1)" script="alert(2)">probe</b>';

describe('content security — sanitizer strips hyperscript attribute forms', () => {
	it('drops _ / script / data-script from a rendered (sanitized) banner', () => {
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signup',
			failOnStatusCode: false,
			body: { name: 'Admin User', email: 'admin@example.com', password: 'password' }
		});
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			failOnStatusCode: false,
			body: { email: 'admin@example.com', password: 'password' }
		}).then((login) => {
			expect(login.status, 'admin signin').to.eq(200);
			const token = login.body.token;
			const auth = { Authorization: `Bearer ${token}` };

			cy.request('/api/config').then((cfg) => {
				const version = cfg.body.version;
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: auth,
					body: { ui: { version, setupCompleted: true, workingAlone: true } }
				});

				cy.request({
					method: 'POST',
					url: '/api/v1/configs/banners',
					headers: auth,
					body: {
						banners: [
							{
								id: 'hs',
								type: 'info',
								title: '',
								content: PROBE,
								dismissible: false,
								timestamp: 0
							}
						]
					}
				}).then((r) => {
					expect(r.status, 'banner set').to.eq(200);

					cy.visit('/', {
						onBeforeLoad(win) {
							win.localStorage.setItem('token', token);
							win.localStorage.setItem('version', version);
						}
					});

					// The banner rendered its (sanitized) probe element.
					cy.get('#hs-probe', { timeout: 30000 }).should('exist');
					// …with every hyperscript attribute form stripped.
					cy.get('#hs-probe').should('not.have.attr', 'data-script');
					cy.get('#hs-probe').should('not.have.attr', '_');
					cy.get('#hs-probe').should('not.have.attr', 'script');
				});
			});
		});
	});
});
