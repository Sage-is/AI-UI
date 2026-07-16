// Upgrade gate, UI half — runs against a rootstock booted on a COPY of a
// production snapshot (scripts/smoke/upgrade-gate.sh KEEP=1), or any target:
//
//   KEEP=1 make upgrade_gate                                   # leaves it up
//   TARGET_URL=http://sage-upgrade:8080 \
//   CYPRESS_ADMIN_EMAIL=upgrade-gate@sage.is \
//   CYPRESS_ADMIN_PASSWORD=upgrade-gate-pw-1234 \
//   SPEC='cypress/e2e/upgrade/*.cy.ts' scripts/e2e/run-cypress.sh
//
// (TARGET_URL host is the container NAME on sage-network.) Point it at a
// staging clone to reuse the same assertions there. NEVER point it at
// production: it logs in and navigates as admin. Zero writes: this spec
// only reads.

const ADMIN_EMAIL = Cypress.env('ADMIN_EMAIL') || 'upgrade-gate@sage.is';
const ADMIN_PASSWORD = Cypress.env('ADMIN_PASSWORD') || 'upgrade-gate-pw-1234';

describe('upgrade: legacy production data on the new image', () => {
	it('login page renders and the injected admin signs in', () => {
		cy.visit('/auth');
		cy.get('input[type="email"], input[autocomplete="email"]', { timeout: 20000 })
			.first()
			.type(ADMIN_EMAIL);
		cy.get('input[type="password"]').first().type(ADMIN_PASSWORD, { log: false });
		cy.get('button[type="submit"]').first().click();
		cy.get('#chat-input', { timeout: 30000 }).should('exist');
	});

	it('theme stylesheet loads as real css (no SPA fallback)', () => {
		cy.request('/themes/active.css').then((res) => {
			expect(res.status).to.eq(200);
			expect(res.headers['content-type']).to.include('text/css');
			expect(res.body).not.to.include('<!doctype');
		});
	});

	it('admin sprigs panel renders the catalog over legacy data', () => {
		cy.visit('/admin/settings');
		cy.contains('button, a, div', /sprig/i, { timeout: 20000 }).click();
		cy.get('[data-cy="sprig-card"], section[id]', { timeout: 20000 }).should(
			'have.length.at.least',
			5
		);
	});
});
