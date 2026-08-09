// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL (smoke): the Audio settings panel must render its STT + TTS engine
// controls without crashing. This is the cheap insurance behind the Kokoro
// lazy-load / double-load refactor in Audio.svelte — if that component throws on
// mount, this catches it. Deliberately does NOT select browser-kokoro (that
// would pull the ~82 MB model); it only asserts the option is present.

describe('Audio settings panel — renders STT + TTS controls', () => {
	it('opens Settings → Audio and shows the engine selectors', () => {
		// Seed + sign in the admin so the app is past setup and the modal is reachable.
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
			cy.request('/api/config').then((cfg) => {
				const version = cfg.body.version;
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: { Authorization: `Bearer ${token}` },
					body: { ui: { version, setupCompleted: true, workingAlone: true } }
				});

				cy.visit('/', {
					onBeforeLoad(win) {
						win.localStorage.setItem('token', token);
						win.localStorage.setItem('version', version);
					}
				});

				// App interactive, then open Settings (Ctrl + .) and go to Audio.
				cy.get('#chat-input', { timeout: 30000 }).should('exist');
				cy.get('body').type('{ctrl}.');
				cy.get('[aria-controls="tab-audio"]', { timeout: 15000 }).should('exist').click();

				// The Audio panel and both engine sections render.
				cy.get('#tab-audio', { timeout: 15000 }).should('exist');
				cy.contains('Speech-to-Text Engine').should('be.visible');
				cy.contains('Text-to-Speech Engine').should('be.visible');

				// The browser-Kokoro TTS option is present — but we do NOT select it
				// (selecting it would download the model). Just prove it's wired.
				cy.get('#tab-audio select').should('have.length.greaterThan', 0);
				cy.get('#tab-audio option[value="browser-kokoro"]').should('exist');
			});
		});
	});
});
