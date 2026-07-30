// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild, openSurface } from '../support/surfaces';

// The changelog panel — guard-rail, written against the SvelteKit modal before
// any code moves, per docs/no-build-surface-convention.md.
//
// First wizard surface, and the first surface anywhere in this migration whose
// legacy side has no URL. `openSurface` handles that: on the legacy target it
// loads admin general settings and clicks "See what's new", which is what puts
// the modal on this panel. On the no-build target it just loads the route. A
// spec should not know which of those happened.
//
// What this may assert is limited to what BOTH implementations must do, and one
// difference is worth naming rather than hiding. In the modal, "Continue"
// closes the modal; at a route there is nothing to close. So what is checked is
// the durable half both share — the server records that this version's changelog
// has been read. That is the part an operator would notice going missing,
// because it is what stops the changelog reappearing on every page load.
//
// Everything reads data attributes and API state, never rendered English, so
// translating the panel cannot turn this red.

/** The changelog as the server holds it — the only authority either side renders. */
const serverChangelog = () => cy.request('/api/changelog').its('body');

const appVersion = () => cy.request('/api/config').its('body.version');

// The harness suppresses the wizard's AUTO-trigger by writing setupCompleted
// and showChangelog into the reader's ui settings at login. Those keys are
// restated on every write here, because the settings endpoint REPLACES the
// whole ui blob rather than merging: one write built from a thin read drops
// them, the layout auto-opens the wizard on the next page load, and its modal
// then covers the very button these specs click. That failure looks like a
// flaky click and is actually a clobbered setting.
const SUPPRESS = { setupCompleted: true, showChangelog: false, workingAlone: true };

const readUiSettings = () =>
	cy.window().then((win) =>
		cy
			.request({
				method: 'GET',
				url: '/api/v1/users/user/settings',
				headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` }
			})
			.then((res) => res.body?.ui ?? {})
	);

const writeUiSettings = (ui: Record<string, unknown>) =>
	cy.window().then((win) =>
		cy.request({
			method: 'POST',
			url: '/api/v1/users/user/settings/update',
			headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` },
			body: { ui: { ...SUPPRESS, ...ui } }
		})
	);

/**
 * Wait for the server to record the read, without caring who told it.
 *
 * `cy.request` does not retry, and the two implementations report the read by
 * different routes — the SPA through its settings store, the no-build page
 * through a form post — so intercepting a specific URL would tie this spec to
 * one of them. Polling the resulting STATE is the assertion both can satisfy.
 */
const expectRecorded = (version: string, attempt = 0) => {
	readUiSettings().then((ui: Record<string, unknown>) => {
		if (ui.version === version) return;
		if (attempt >= 20) {
			// Out of retries: assert so the failure names both values.
			expect(ui.version, 'server recorded the changelog as read').to.eq(version);
			return;
		}
		cy.wait(250);
		expectRecorded(version, attempt + 1);
	});
};

describe('Setup wizard: changelog panel', () => {
	beforeEach(() => {
		cy.loginAdmin();
		openSurface('wizardChangelog');
	});

	// Put the read marker back. `cy.loginAdmin` is a cached session, so it will
	// not re-run its setup for later specs in this run — a test that died after
	// clearing the marker would leave the wizard auto-opening over every page
	// the rest of the suite tries to click. That is the shared-container leak
	// this suite has already been bitten by three times.
	afterEach(() => {
		cy.request('/api/config')
			.its('body.version')
			.then((version: string) =>
				readUiSettings().then((ui) => writeUiSettings({ ...ui, version, setupCompleted: true }))
			);
	});

	it('lists every version the server publishes', () => {
		serverChangelog().then((changelog: Record<string, unknown>) => {
			const versions = Object.keys(changelog);
			// A changelog with no versions would make every assertion below pass
			// by checking nothing, which is the failure shape this suite keeps
			// finding. Refuse to run rather than report green on an empty list.
			expect(versions.length, 'server publishes at least one version').to.be.greaterThan(0);
			versions.forEach((v) => {
				cy.get(`[data-cy="changelog-panel"] [data-version="${v}"]`).should('exist');
			});
		});
	});

	it('shows each version with its release date', () => {
		serverChangelog().then((changelog: Record<string, { date: string }>) => {
			Object.entries(changelog).forEach(([version, data]) => {
				cy.get(`[data-version="${version}"]`).should('contain.text', data.date);
			});
		});
	});

	it('labels each change section the server publishes', () => {
		// Derived from the server, not from a list written here. A hardcoded set
		// of section names would have to be edited every time CHANGELOG.md grows
		// one — and the first draft of this test did exactly that, then failed on
		// the "docs" section that already exists.
		serverChangelog().then((changelog: Record<string, Record<string, unknown>>) => {
			const [version, data] = Object.entries(changelog)[0];
			const expected = Object.keys(data).filter((k) => k !== 'date');
			expect(expected.length, 'the newest release has at least one section').to.be.greaterThan(
				0
			);
			cy.get(`[data-version="${version}"] [data-section]`).then(($els) => {
				const rendered = [...$els].map((el) => el.getAttribute('data-section'));
				expect(rendered.sort()).to.deep.eq(expected.sort());
			});
		});
	});

	it('renders the title and body of every entry', () => {
		serverChangelog().then((changelog: Record<string, Record<string, any>>) => {
			// One version is enough to prove entries render; asserting every
			// entry of every release makes the spec grow with the CHANGELOG and
			// slows every run for no extra signal.
			const [version, data] = Object.entries(changelog)[0];
			Object.entries(data)
				.filter(([section]) => section !== 'date')
				.forEach(([, entries]) => {
					(entries as Array<{ title: string; content: string }>).forEach((entry) => {
						cy.get(`[data-version="${version}"]`)
							.should('contain.text', entry.title)
							.and('contain.text', entry.content);
					});
				});
		});
	});

	it('shows the version this instance is running', () => {
		appVersion().then((version: string) => {
			cy.get('[data-app-version]').should('have.attr', 'data-app-version', version);
		});
	});

	it('records the changelog as read when you continue', () => {
		// The harness marks it read at login, so asserting it without clearing
		// first would pass whether or not the button did anything.
		readUiSettings().then((ui) => {
			writeUiSettings({ ...ui, version: 'not-the-current-version' });
			openSurface('wizardChangelog');
			// The no-build button pages the notes before it advances, so get to
			// the end first. Best-effort and forced, because on the legacy target
			// this element is an inner div whose centre sits off-screen inside
			// its own scroll container — Cypress refuses to trigger on it, and
			// the legacy button submits on any click regardless.
			cy.get('[data-cy="changelog-body"]').then(($el) => {
				$el[0].scrollTop = $el[0].scrollHeight;
			});
			cy.get('[data-cy="changelog-body"]').trigger('scroll', { force: true });
			cy.get('[data-cy="changelog-continue"]').click();
			appVersion().then((version: string) => expectRecorded(version));
		});
	});
});

// The pager is no-build only: the legacy panel has no script and its Continue
// submits on the first click. Asserted separately rather than folded into the
// shared guard-rail, because a spec that judges both may only assert what both
// do — and this is a capability only one of them has.
describe('Setup wizard: changelog pager', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
		openSurface('wizardChangelog');
	});

	it('starts as a pager, not an advance', () => {
		cy.get('[data-pager-row]').should('have.attr', 'data-at-end', 'false');
		cy.get('[data-cy="changelog-continue"]').should('contain.text', 'Next page');
	});

	it('pages down instead of leaving the notes', () => {
		cy.get('[data-cy="changelog-body"]')
			.invoke('prop', 'scrollTop')
			.then((before: number) => {
				cy.get('[data-cy="changelog-continue"]').click();
				cy.get('[data-cy="changelog-body"]')
					.invoke('prop', 'scrollTop')
					.should('be.greaterThan', before);
				// Still here. Advancing on the first click is the behaviour this
				// replaced.
				cy.location('pathname').should('eq', '/pages/admin/setup/changelog');
			});
	});

	// Measure the BUTTON, not the row's CSS.
	//
	// The first version of this test asserted that justify-content flipped from
	// flex-start to flex-end. It passed, and the button did not move a pixel —
	// the row had no width, so it shrink-wrapped to the button and there was no
	// free space for justify-content to distribute. A computed style is not a
	// position, and only one of them is what a reader sees.
	it('moves to the other side once the notes run out', () => {
		cy.get('[data-cy="changelog-continue"]').then(($button) => {
			const before = $button[0].getBoundingClientRect().left;

			cy.get('[data-cy="changelog-body"]').then(($el) => {
				$el[0].scrollTop = $el[0].scrollHeight;
			});
			cy.get('[data-cy="changelog-body"]').trigger('scroll', { force: true });
			cy.get('[data-pager-row]').should('have.attr', 'data-at-end', 'true');
			cy.get('[data-cy="changelog-continue"]').should('contain.text', 'Continue');

			// Travelled most of the way across its own row, not nudged. Retried,
			// because the move is a 350ms transition rather than a jump.
			cy.get('[data-pager-row]').then(($row) => {
				const width = $row[0].clientWidth;
				cy.get('[data-cy="changelog-continue"]').should(($moved) => {
					const after = $moved[0].getBoundingClientRect().left;
					expect(after - before, 'button travelled across the row').to.be.greaterThan(
						width / 2
					);
				});
			});
		});
	});

	it('advances to the next panel from the end', () => {
		cy.get('[data-cy="changelog-body"]').then(($el) => {
			$el[0].scrollTop = $el[0].scrollHeight;
		});
		cy.get('[data-cy="changelog-body"]').trigger('scroll');
		cy.get('[data-cy="changelog-continue"]').click();
		cy.location('pathname').should('eq', '/pages/admin/setup/features');
	});
});
