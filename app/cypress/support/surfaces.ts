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
}

export const SURFACES = {
	sprigs: { legacy: '/admin/sprigs', nobuild: '/pages/admin/sprigs' },
	diagnostics: { legacy: '/admin/diagnostics', nobuild: '/pages/admin/diagnostics' },
	branding: { legacy: '/admin/settings/theme', nobuild: '/pages/admin/branding' }
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

/** True when this run is judging the no-build implementation. */
export function isNoBuild(): boolean {
	return surfaceTarget() === 'nobuild';
}
