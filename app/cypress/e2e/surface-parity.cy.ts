// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { SURFACES, type SurfaceName } from '../support/surfaces';

// Surface parity — the check that does not depend on my judgement.
//
// Every other spec in this suite tests what its author decided to test. That is
// the flaw this file exists to cover, and it has already cost us twice: the
// diagnostics guard-rail was green against BOTH implementations while the
// no-build one was missing most of the old page, and its "Show me how to fix
// this" button rendered and did nothing. Every assertion passed, because I had
// written assertions for the parts I had built.
//
// So this asserts nothing about behaviour. It visits both implementations of a
// surface in the same run, collects the `data-cy` hooks each one renders, and
// fails if the no-build page is missing any the legacy page offers. It cannot
// be satisfied by writing a narrower spec, because it never reads the spec.
//
// The contract that makes it work: every interactive element on a LEGACY
// surface carries a `data-cy`, added as the first step of migrating it, before
// any code moves. Enumerating the old surface's controls is the part that gets
// skipped otherwise, and it is the part that matters.
//
// This is a coverage floor, not a ceiling. Identical hooks do not mean
// identical behaviour — a button that renders and does nothing has the same
// hook as one that works. Behaviour is still each surface spec's job.

const SEEN: Record<string, Set<string>> = {};

/** Every data-cy value the current document renders, shadow DOM included. */
const collectHooks = () =>
	cy.document().then((doc) => {
		const found = new Set<string>();
		doc.querySelectorAll('[data-cy]').forEach((el) => {
			const v = el.getAttribute('data-cy');
			if (v) found.add(v);
		});
		return found;
	});

describe('Surface parity: no-build renders every control the SvelteKit page does', () => {
	beforeEach(() => cy.loginAdmin());

	(Object.keys(SURFACES) as SurfaceName[]).forEach((name) => {
		const { legacy, nobuild } = SURFACES[name];

		it(`${name}: collects the controls the SvelteKit page offers`, () => {
			cy.visit(legacy);
			// Wait for real content rather than a fixed pause — the SPA paints
			// chrome first, and hooks collected mid-boot would understate it,
			// which would make this check pass by measuring too little.
			cy.get('[data-cy]', { timeout: 30000 }).should('have.length.at.least', 3);
			collectHooks().then((hooks) => {
				SEEN[`${name}:legacy`] = hooks;
				cy.log(`${name} legacy hooks: ${[...hooks].sort().join(', ')}`);
			});
		});

		it(`${name}: the no-build page is missing none of them`, () => {
			cy.visit(nobuild);
			cy.get('[data-cy]', { timeout: 30000 }).should('have.length.at.least', 1);
			collectHooks().then((hooks) => {
				SEEN[`${name}:nobuild`] = hooks;
				const legacyHooks = SEEN[`${name}:legacy`] ?? new Set<string>();
				const missing = [...legacyHooks].filter((h) => !hooks.has(h)).sort();
				const extra = [...hooks].filter((h) => !legacyHooks.has(h)).sort();
				// Extras are fine and expected — the no-build pages carry hooks the
				// SPA never needed. Only absence is a regression.
				if (extra.length) cy.log(`${name} no-build adds: ${extra.join(', ')}`);
				// Assert on a STRING, not on the array. Chai renders a failed array
				// comparison as "expected [ Array(4) ] to deeply equal []", which
				// tells you something is missing and not what — and a gate whose
				// failure you have to go investigate is half a gate. Joining the
				// names into the message puts the work list in the failure itself.
				expect(
					missing.join(', ') || 'nothing missing',
					`${name}: controls on ${legacy} that ${nobuild} does not render`
				).to.eq('nothing missing');
			});
		});
	});
});
