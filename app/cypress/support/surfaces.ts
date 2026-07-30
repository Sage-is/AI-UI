/// <reference types="cypress" />

// The surface registry — one place that knows a surface's two addresses.
//
// Every migrated surface exists twice for as long as the strangler runs: the
// SvelteKit route users reach today, and the no-build route that will replace
// it. A spec should not care which one it is pointed at, and it certainly
// should not invent its own environment variable for the choice — the first two
// specs did exactly that (CYPRESS_SPRIGS_PANEL, CYPRESS_DIAGNOSTICS_PANEL), so
// running "both" meant remembering two different names and running each spec
// twice by hand.
//
// Here, a spec asks for a surface by NAME and the runner decides which
// implementation it gets. `make e2e_both` runs the whole suite twice, once per
// target, so "green against both" is what the gate means rather than what
// somebody remembered to check.
//
// Adding a surface here is the first step of migrating it, before any code
// moves. That ordering is the point: it forces the question "what does the old
// one actually do?" while the old one is still the only one there is.

export type SurfaceTarget = 'legacy' | 'nobuild';

export interface Surface {
	/** The SvelteKit route users reach today. */
	legacy: string;
	/** The server-rendered route replacing it. */
	nobuild: string;
	/**
	 * How to drive the SPA to this surface after loading `legacy`, for a surface
	 * that has no URL of its own.
	 *
	 * The setup wizard is a modal — `(app)/+layout.svelte` mounts it and a store
	 * decides whether it shows, so there is no address to visit. Without this,
	 * the whole wizard would migrate with no parity gate at all, which is the one
	 * check that does not depend on the spec author's judgement.
	 *
	 * A callback rather than a selector, because reaching a panel part-way into
	 * a wizard is not one click. Features sits behind Welcome, and the steps
	 * before it must be deselected to get there — with `.uncheck()`, not
	 * `.click()`, since WelcomeStep's boxes start checked or unchecked depending
	 * on whether the instance already has models and users. A click would toggle
	 * whatever it found and land on a different panel on a different instance.
	 */
	openLegacy?: () => void;
	/**
	 * Confine hook collection to this selector, on BOTH sides.
	 *
	 * Only meaningful alongside `openLegacy`, and required by it: a modal opens
	 * on top of a page that is still in the DOM, so collecting the whole document
	 * would sweep up the host page's controls and then demand the no-build route
	 * render them too. The surface is the panel, not the page it opened over.
	 */
	scope?: string;
}

/**
 * Open the setup wizard from admin general settings, then jump to one panel.
 *
 * Two hazards this exists to absorb, both found the hard way.
 *
 * A modal can already be open when we arrive, and it covers the trigger button.
 * Two separate things open one: the wizard's own auto-trigger, and the dev
 * mission reminder, which `(app)/+layout.svelte` shows whenever the reader has
 * `devMissionSignup` set — which is precisely what the developer-panel spec
 * turns on. Both are correct product behaviour, so the gate closes what it
 * finds rather than pretending neither happens.
 *
 * And the jump is by progress dot rather than through Welcome's own step
 * selection, because selecting a step and pressing Get Started lands on the
 * WRONG panel — `handleWelcomeStart` skips against a stale `panels` value. That
 * bug is filed in TODO.md; driving the gates through it would make every wizard
 * spec depend on a defect.
 */
const closeAnyModal = (attempt = 0) => {
	// Recursive rather than a single check, because more than one modal can be
	// stacked and each close reveals the next. Bounded so a modal that refuses
	// to close fails the test instead of hanging it.
	if (attempt > 4) return;
	cy.get('body').then(($body) => {
		if ($body.find('modal-element').length === 0) return;
		cy.get('modal-element [aria-label="Close"]').first().click({ force: true });
		cy.wait(250);
		closeAnyModal(attempt + 1);
	});
};

const openWizardPanel = (welcomeHook: string, panel: string) => () => {
	// Settle before closing. Both auto-opening modals mount after the layout has
	// fetched config and settings, so a close that runs the moment the DOM
	// exists finds nothing and the modal appears immediately afterwards, on top
	// of the button we are about to click. Wait for the trigger to render, give
	// the async modals their turn, THEN clear whatever showed up.
	cy.get('[data-cy="run-setup-wizard"]', { timeout: 30000 }).should('exist');
	cy.wait(1200);
	closeAnyModal();
	cy.get('[data-cy="run-setup-wizard"]').click();
	cy.get(`[data-cy="${welcomeHook}"]`, { timeout: 30000 }).check({ force: true });
	cy.get('[data-cy="welcome-start"]').click();
	cy.get(`[aria-label="${panel}"]`, { timeout: 30000 }).click();
};

export const SURFACES = {
	sprigs: { legacy: '/admin/sprigs', nobuild: '/pages/admin/sprigs' },
	diagnostics: { legacy: '/admin/diagnostics', nobuild: '/pages/admin/diagnostics' },
	branding: { legacy: '/admin/settings/theme', nobuild: '/pages/admin/branding' },
	// The changelog branch of the setup modal. `openLegacy` is the "See what's
	// new" button on admin general settings, which sets hasChangelog and opens
	// the modal on this panel.
	wizardChangelog: {
		legacy: '/admin/settings/general',
		openLegacy: () => {
			cy.get('[data-cy="see-whats-new"]', { timeout: 30000 }).should('exist');
			cy.wait(1200);
			closeAnyModal();
			cy.get('[data-cy="see-whats-new"]').click();
		},
		nobuild: '/pages/admin/setup/changelog',
		scope: '[data-cy="changelog-panel"]'
	},
	wizardFeatures: {
		legacy: '/admin/settings/general',
		openLegacy: openWizardPanel('welcome-features', 'features'),
		nobuild: '/pages/admin/setup/features',
		scope: '[data-cy="features-panel"]'
	},
	wizardDeveloper: {
		legacy: '/admin/settings/general',
		openLegacy: openWizardPanel('welcome-developer', 'developer'),
		nobuild: '/pages/admin/setup/developer',
		scope: '[data-cy="developer-panel"]'
	},
	// Complete is not one of the selectable steps, so its progress dot is never
	// dimmed and any welcome selection reaches it.
	wizardComplete: {
		legacy: '/admin/settings/general',
		openLegacy: openWizardPanel('welcome-features', 'complete'),
		nobuild: '/pages/admin/setup/complete',
		scope: '[data-cy="complete-panel"]'
	},
	wizardSearchAudio: {
		legacy: '/admin/settings/general',
		openLegacy: openWizardPanel('welcome-search-audio', 'search_audio'),
		nobuild: '/pages/admin/setup/search-audio',
		scope: '[data-cy="search-audio-panel"]'
	}
} satisfies Record<string, Surface>;

export type SurfaceName = keyof typeof SURFACES;

/** Which implementation this run is judging. Defaults to the one users reach. */
export function surfaceTarget(): SurfaceTarget {
	return (Cypress.env('SURFACE_TARGET') as SurfaceTarget) || 'legacy';
}

/** The path for a surface under the current target. */
export function surfacePath(name: SurfaceName): string {
	return SURFACES[name][surfaceTarget()];
}

/**
 * Load one side of a surface and wait until it is actually there.
 *
 * Every spec should reach a surface through this rather than calling `cy.visit`
 * itself, so the open step cannot be remembered in one place and forgotten in
 * another. A guard-rail spec that skipped it would fail on an empty page and
 * get "fixed" with a longer timeout.
 */
export function openSurface(name: SurfaceName, target: SurfaceTarget = surfaceTarget()) {
	const surface: Surface = SURFACES[name];
	cy.visit(surface[target]);
	if (target === 'legacy' && surface.openLegacy) surface.openLegacy();
	// Anchor on the surface's own root when it declares one. The modal animates
	// in, so a spec that started asserting the moment the click returned would
	// race the panel it is judging.
	if (surface.scope) cy.get(surface.scope, { timeout: 30000 }).should('be.visible');
}

/** True when this run is judging the no-build implementation. */
export function isNoBuild(): boolean {
	return surfaceTarget() === 'nobuild';
}
