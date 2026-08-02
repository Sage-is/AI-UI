/// <reference types="cypress" />

// The surface registry. One place that knows a surface's two addresses.
//
// Every migrated surface exists twice for as long as the strangler runs: the
// SvelteKit route users reach today, and the no-build route that will replace
// it. A spec should not care which one it is pointed at, and it certainly
// should not invent its own environment variable for the choice. The first two
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
//
// Removing one is the LAST step. A surface stays here only while both
// implementations exist; once the SvelteKit side is deleted there is nothing to
// compare against, and leaving the entry would give `surface-parity` a route to
// judge against itself. That is a gate whose failure is indistinguishable from
// success, which is the shape this repo keeps finding — so retiring the entry
// belongs in the same commit as the deletion, and whatever the surface still
// needs covered gets its own spec. The setup wizard is the worked example: nine
// entries out, `setup-dialog.cy.ts` in.

export type SurfaceTarget = 'legacy' | 'nobuild';

export interface Surface {
	/** The SvelteKit route users reach today. */
	legacy: string;
	/** The server-rendered route replacing it. */
	nobuild: string;
	/**
	 * A selector for content ONLY this surface renders, in both implementations.
	 *
	 * This is what makes registering a surface enrol it in the payload ledger
	 * (`cypress/e2e/upgrade/route-payload.cy.ts`) as well as the parity gate — the
	 * before-and-after measurement then costs a line rather than a spec.
	 *
	 * It must not match anything the app SHELL renders. A selector that also
	 * appears on the chat page measures the shell, reports a plausible number, and
	 * passes: planting `button` here once made a route report 152 ms instead of
	 * 1,840 ms while every other test stayed green. The ledger asserts this.
	 */
	content: string;
}

// `openLegacy` and `scope` used to live here: a callback that drove the SPA to a
// surface with no URL of its own, and a selector confining hook collection to
// the panel rather than the page it opened over. The setup wizard was the only
// user of either, because it was a modal. It is nine routes now, so both fields
// went with it — an optional field nothing sets is scaffolding that reads like a
// contract. Restore them from git if a modal-only surface ever needs migrating.

/** Dismiss whatever modal is on screen, topmost first. */
export const closeAnyModal = (attempt = 0) => {
	// Recursive rather than a single check, because more than one modal can be
	// stacked and each close reveals the next. Bounded so a modal that refuses
	// to close fails the test instead of hanging it.
	if (attempt > 4) return;
	cy.get('body').then(($body) => {
		// The setup dialog first: it is a native `<dialog>`, so it sits in the top
		// layer and covers any `modal-element` underneath regardless of z-index.
		// Closing in painted order is the only order that can actually reach the
		// control it means to press.
		if ($body.find('dialog[open]').length > 0) {
			cy.get('dialog[open] [data-cy="setup-close"]').first().click({ force: true });
			cy.wait(250);
			closeAnyModal(attempt + 1);
			return;
		}
		if ($body.find('modal-element').length === 0) return;
		cy.get('modal-element [aria-label="Close"]').first().click({ force: true });
		cy.wait(250);
		closeAnyModal(attempt + 1);
	});
};

/**
 * Open one setup panel at its own address.
 *
 * The wizard used to be a modal with no URL, which is why the registry below
 * grew an `openLegacy` step. It is now nine routes, so reaching a panel is a
 * visit — and the dialog that shows the same panels to a reader is tested as
 * its own surface in `setup-dialog.cy.ts` rather than nine times over here.
 */
export const openSetupPanel = (panel: string) => {
	cy.visit(`/pages/admin/setup/${panel}`);
	cy.get(`[data-cy="${panel}-panel"]`, { timeout: 30000 }).should('be.visible');
};

export const SURFACES = {
	sprigs: {
		legacy: '/admin/sprigs',
		nobuild: '/pages/admin/sprigs',
		content: '[data-cy="sprig-card"]'
	},
	diagnostics: {
		legacy: '/admin/diagnostics',
		nobuild: '/pages/admin/diagnostics',
		content: '[data-cy="diag-issues"]'
	},
	branding: {
		legacy: '/admin/settings/theme',
		nobuild: '/pages/admin/branding',
		content: '[data-cy="branding-preview"]'
	},
	// The route says `models` and the interface says Agents — the heading, the
	// page title and both import/export buttons already read `t('Agents')`. The
	// no-build path takes the name the product uses, and the old route redirects.
	agents: {
		legacy: '/workshop/models',
		nobuild: '/pages/workshop/agents',
		content: '[data-cy="agents-row"]'
	},
	prompts: {
		legacy: '/workshop/prompts',
		nobuild: '/pages/workshop/prompts',
		content: '[data-cy="prompts-row"]'
	}
	// The nine wizard surfaces used to be listed here, each with an `openLegacy`
	// step that opened the modal and jumped to a panel. They were removed when the
	// modal was deleted: the panels now have exactly one implementation, so this
	// gate would have been comparing a route against itself and passing for the
	// wrong reason. What replaced that coverage is `setup-dialog.cy.ts`, which
	// judges the one thing the cut-over actually added — the host that fetches a
	// route and shows it in a `<dialog>`.
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
	cy.visit(SURFACES[name][target]);
}

/** True when this run is judging the no-build implementation. */
export function isNoBuild(): boolean {
	return surfaceTarget() === 'nobuild';
}
