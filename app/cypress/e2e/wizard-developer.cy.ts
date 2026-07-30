// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { openSurface } from '../support/surfaces';

// Developer mode — guard-rail, written against the SvelteKit panel first.
//
// The panel has two branches over one flag, and the e2e image runs with
// DEV_MODE unset, so what is exercised here is the production branch. The
// branch itself is asserted through `data-dev-mode` rather than by looking for
// English, so if the harness ever runs with DEV_MODE=true this reports which
// branch it saw instead of failing on missing copy.
//
// One value outlives the page: the mission signup, stored in the reader's own
// `ui` settings. As on the features panel, the case that matters is turning it
// OFF, because an unticked checkbox posts nothing at all.

// The harness suppresses the wizard's AUTO-trigger by writing setupCompleted
// and showChangelog into the reader's ui settings at login. Those keys are
// restated on every write here, because the settings endpoint REPLACES the
// whole ui blob rather than merging: one write built from a thin read drops
// them, the layout auto-opens the wizard on the next page load, and its modal
// then covers the very button these specs click. That failure looks like a
// flaky click and is actually a clobbered setting.
const SUPPRESS = { setupCompleted: true, showChangelog: false, workingAlone: true };

const readUi = () =>
	cy.window().then((win) =>
		cy
			.request({
				url: '/api/v1/users/user/settings',
				headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` }
			})
			.then((res) => res.body?.ui ?? {})
	);

const writeUi = (ui: Record<string, unknown>) =>
	cy.window().then((win) =>
		cy.request({
			method: 'POST',
			url: '/api/v1/users/user/settings/update',
			headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` },
			body: { ui: { ...SUPPRESS, ...ui } }
		})
	);

const setSignup = (value: boolean) => readUi().then((ui) => writeUi({ ...ui, devMissionSignup: value }));

const expectSignup = (want: boolean, attempt = 0) => {
	readUi().then((ui: Record<string, unknown>) => {
		if ((ui.devMissionSignup ?? false) === want) return;
		if (attempt >= 20) {
			expect(ui.devMissionSignup ?? false, 'server holds devMissionSignup').to.eq(want);
			return;
		}
		cy.wait(250);
		expectSignup(want, attempt + 1);
	});
};

describe('Setup wizard: developer mode', () => {
	beforeEach(() => cy.loginAdmin());

	it('reports which branch it rendered', () => {
		openSurface('wizardDeveloper');
		cy.get('[data-cy="developer-panel"]')
			.should('have.attr', 'data-dev-mode')
			.and('match', /^(true|false)$/);
	});

	it('offers the mission signup in the production branch', () => {
		openSurface('wizardDeveloper');
		cy.get('[data-cy="developer-panel"]').then(($p) => {
			if ($p.attr('data-dev-mode') === 'true') {
				cy.log('DEV_MODE branch — no signup control by design');
				return;
			}
			cy.get('[data-cy="developer-mission-signup"]').should('exist');
			cy.get('[data-cy="developer-save"]').should('exist');
		});
	});

	it('shows the signup in the state the server holds', () => {
		setSignup(true);
		openSurface('wizardDeveloper');
		cy.get('[data-cy="developer-mission-signup"]').should('be.checked');
	});

	it('signs up and the server keeps it', () => {
		setSignup(false);
		openSurface('wizardDeveloper');
		cy.get('[data-cy="developer-mission-signup"]').check({ force: true });
		cy.get('[data-cy="developer-save"]').click();
		expectSignup(true);
	});

	// The unticked-box case again — the one that a save reading only posted
	// names cannot pass.
	it('withdraws the signup and the server keeps it off', () => {
		setSignup(true);
		openSurface('wizardDeveloper');
		cy.get('[data-cy="developer-mission-signup"]').should('be.checked').uncheck({ force: true });
		cy.get('[data-cy="developer-save"]').click();
		expectSignup(false);
	});

	it('leaves the reader other ui settings alone', () => {
		readUi().then((before) => {
			openSurface('wizardDeveloper');
			cy.get('[data-cy="developer-save"]').click();
			cy.wait(500);
			readUi().then((after: Record<string, unknown>) => {
				expect(after.version, 'the changelog read marker survived').to.eq(before.version);
			});
		});
	});
});
