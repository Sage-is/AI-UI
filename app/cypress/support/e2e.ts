/// <reference types="cypress" />
// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

export const adminUser = {
	name: 'Admin User',
	email: 'admin@example.com',
	password: 'password'
};

const login = (email: string, password: string) => {
	return cy.session(
		email,
		() => {
			// Make sure to test against us english to have stable tests,
			// regardless on local language preferences
			localStorage.setItem('locale', 'en-US');
			// Pre-seed the changelog version so the "What's New" modal never
			// opens (deterministic — no copy-dependent dismiss click).
			cy.request('/api/config').then((res) => {
				localStorage.setItem('version', res.body.version);
			});
			// Visit auth page
			cy.visit('/auth');
			// Fill out the form
			cy.get('input[autocomplete="email"]').type(email);
			cy.get('input[type="password"]').type(password);
			// Submit the form
			cy.get('button[type="submit"]').click();
			// Logged-in anchor that exists regardless of sidebar state
			// (#chat-search only renders with the sidebar open).
			cy.get('#chat-input', { timeout: 20000 }).should('exist');
			// Mark setup complete + changelog seen in SERVER-side user settings —
			// the ChangesAndSetupModal triggers off $settings.version /
			// $settings.setupCompleted (not localStorage), and would otherwise
			// cover the UI on every restored-session visit.
			cy.window().then((win) => {
				const token = win.localStorage.getItem('token');
				cy.request('/api/config').then((cfg) => {
					cy.request({
						method: 'POST',
						url: '/api/v1/users/user/settings/update',
						headers: { Authorization: `Bearer ${token}` },
						body: {
							ui: {
								version: cfg.body.version,
								setupCompleted: true,
								workingAlone: true,
								showChangelog: false
							}
						}
					});
				});
			});
		},
		{
			validate: () => {
				cy.request({
					method: 'GET',
					url: '/api/v1/auths/',
					headers: {
						Authorization: 'Bearer ' + localStorage.getItem('token')
					}
				});
			}
		}
	);
};

const register = (name: string, email: string, password: string) => {
	return cy
		.request({
			method: 'POST',
			url: '/api/v1/auths/signup',
			body: {
				name: name,
				email: email,
				password: password
			},
			failOnStatusCode: false
		})
		.then((response) => {
			// 200 = created; 400 = already exists; 403 = signup closed (this fork
			// hard-closes public signup once an admin exists — the subsequent
			// loginAdmin is the real arbiter of whether the account works).
			expect(response.status).to.be.oneOf([200, 400, 403]);
		});
};

const registerAdmin = () => {
	return register(adminUser.name, adminUser.email, adminUser.password);
};

const loginAdmin = () => {
	return login(adminUser.email, adminUser.password);
};

Cypress.Commands.add('login', (email, password) => login(email, password));
Cypress.Commands.add('register', (name, email, password) => register(name, email, password));
Cypress.Commands.add('registerAdmin', () => registerAdmin());
Cypress.Commands.add('loginAdmin', () => loginAdmin());

before(() => {
	cy.registerAdmin();
});
