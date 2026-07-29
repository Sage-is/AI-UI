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

// ── Poka-Yoke: a spec may not leak server config into the specs after it ──
//
// The harness boots ONE container for the whole run, so anything a spec writes
// to server config silently changes the world for everything that follows.
// That has already bitten twice: stt-misconfig left STT_ENGINE=openai behind
// and stt-not-configured then asserted 502 where it expects 501 (it passes in
// isolation — that is the tell), and a banner seeded by boot-waterfall sat on
// top of every later spec's page.
//
// Fixing those one at a time relies on every future spec author remembering.
// This restores instead: snapshot the admin-mutable config surface before a
// spec runs, compare after, and put back only what actually changed. Specs
// that touch nothing (the common case) trigger zero writes, so the guard
// cannot itself become a source of drift. A leak is logged by NAME so the
// culprit is visible rather than whichever spec runs next and fails.
type ConfigSurface = {
	name: string;
	read: string;
	write: string;
	// Some endpoints read a bare value but write it wrapped.
	wrap?: (body: unknown) => unknown;
};

const RESTORED_CONFIG: ConfigSurface[] = [
	{ name: 'audio', read: '/api/v1/audio/config', write: '/api/v1/audio/config/update' },
	{
		name: 'banners',
		read: '/api/v1/configs/banners',
		write: '/api/v1/configs/banners',
		wrap: (banners) => ({ banners })
	},
	// Branding is the loudest surface on this list: it sets the app title, the
	// logo and the --primary/--secondary the whole interface cascades from, so
	// a spec that leaves test branding behind does not merely change a config
	// value — it repaints every page every later spec looks at.
	{ name: 'branding', read: '/api/v1/configs/branding', write: '/api/v1/configs/branding' },
	{ name: 'ollama', read: '/ollama/config', write: '/ollama/config/update' },
	{ name: 'openai', read: '/openai/config', write: '/openai/config/update' },
	{
		name: 'user-permissions',
		read: '/api/v1/users/default/permissions',
		write: '/api/v1/users/default/permissions'
	}
];

let configSnapshot: Record<string, string> = {};
let adminToken: string | null = null;

const readSurface = (surface: ConfigSurface) =>
	cy
		.request({
			url: surface.read,
			headers: { Authorization: `Bearer ${adminToken}` },
			failOnStatusCode: false
		})
		.then((res) => (res.status === 200 ? res.body : null));

before(() => {
	cy.registerAdmin();

	// Sign in directly rather than via cy.session: this runs before any spec's
	// own setup, and a failure here must not fail the spec — the guard is
	// best-effort, never the reason a run goes red.
	cy.request({
		method: 'POST',
		url: '/api/v1/auths/signin',
		failOnStatusCode: false,
		body: { email: adminUser.email, password: adminUser.password }
	}).then((res) => {
		adminToken = res.status === 200 ? res.body.token : null;
		if (!adminToken) return;

		configSnapshot = {};
		RESTORED_CONFIG.forEach((surface) => {
			readSurface(surface).then((body) => {
				if (body !== null) configSnapshot[surface.name] = JSON.stringify(body);
			});
		});
	});
});

after(() => {
	if (!adminToken) return;

	RESTORED_CONFIG.forEach((surface) => {
		const before = configSnapshot[surface.name];
		if (before === undefined) return;

		readSurface(surface).then((body) => {
			if (body === null || JSON.stringify(body) === before) return;

			const original = JSON.parse(before);
			cy.log(`**poka-yoke**: this spec modified \`${surface.name}\` config — restoring`);
			cy.request({
				method: 'POST',
				url: surface.write,
				headers: { Authorization: `Bearer ${adminToken}` },
				failOnStatusCode: false,
				body: surface.wrap ? surface.wrap(original) : original
			});
		});
	});
});
