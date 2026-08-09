// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL for the admin models refresh control.
//
// What it is for. The backend holds BASE_MODELS with no TTL, so a provider that
// was unreachable when the list was built stays invisible until something
// invalidates the cache. Changing a connection does that; a provider quietly
// coming back does not. This button is the control for that case, and it is the
// only caller in the app that asks for `refresh=true` deliberately.
//
// What it asserts. MOTION, not presence. A refresh button that renders, spins
// and sends nothing looks identical to a working one in a screenshot and in any
// spec that only reads the DOM. So every assertion below turns on a REQUEST
// leaving the browser with the refresh flag set, observed through an intercept.
// The button being there is a precondition, never the claim.
//
// It reads `data-cy`, never a class name and never a phrase, for the same reason
// the sprigs panel does: when this page is strangled onto the server-rendered
// stack the control becomes one htmx attribute, and this file should judge that
// implementation without being rewritten. At that point register `models` in
// cypress/support/surfaces.ts and swap PAGE for `surfacePath('models')` — not
// before, because a surface with one implementation would have the parity gate
// comparing a route against itself.

const PAGE = '/admin/settings/models';

// Any /api/models call carrying the flag. The mount fires one of these too, so
// every test below waits for that one FIRST and then judges the next — a spec
// that waited once could be satisfied by the page load and would pass with the
// button unwired, which is precisely the failure this file exists to catch.
const REFRESH_CALL = '**/api/models?*refresh=true*';

describe('admin models refresh', () => {
	beforeEach(() => {
		cy.loginAdmin();
	});

	it('the click sends a refresh, not just a spinner', () => {
		cy.intercept('GET', REFRESH_CALL).as('modelsRefresh');
		cy.visit(PAGE);

		// The mount's own refresh. Consuming it here is what makes the second
		// wait below evidence of the CLICK rather than of the page load.
		cy.wait('@modelsRefresh', { timeout: 30000 });

		cy.get('[data-cy="models-refresh"]', { timeout: 30000 }).should('be.enabled').click();

		cy.wait('@modelsRefresh', { timeout: 30000 }).then((interception) => {
			expect(interception.response?.statusCode, 'refresh round-trip').to.eq(200);
			// The flag is the whole point: without it the backend serves the same
			// cached list back and the button is decoration.
			expect(new URL(interception.request.url).searchParams.get('refresh')).to.eq('true');
		});

		// The list is still rendered afterwards. A refresh that empties the page
		// is worse than no refresh.
		cy.get('[data-cy="models-refresh"]', { timeout: 30000 }).should('be.enabled');
	});

	it('refuses a second click while one is in flight', () => {
		// Held open on purpose. Without the delay the request completes inside
		// the click and the disabled window is too short to observe, so the
		// assertion would pass against a button that never disables at all.
		cy.intercept('GET', REFRESH_CALL, (req) => {
			req.on('response', (res) => res.setDelay(1500));
		}).as('slowRefresh');

		cy.visit(PAGE);
		cy.wait('@slowRefresh', { timeout: 30000 });

		cy.get('[data-cy="models-refresh"]', { timeout: 30000 }).should('be.enabled').click();
		cy.get('[data-cy="models-refresh"]').should('be.disabled');

		cy.wait('@slowRefresh', { timeout: 30000 });
		cy.get('[data-cy="models-refresh"]', { timeout: 30000 }).should('be.enabled');
	});
});
