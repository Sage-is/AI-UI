// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Sprigs™ panel lifecycle — the operator-facing half of the Bonsai™
// architecture. Walks the actual buttons an admin clicks: catalog render,
// graft (mock cultivar: no artifact pull, fast), prune, and a deliver-sprig
// graft whose post_graft_note must surface as a visible warning toast
// (vector-chroma: requires the local sprig registry on the docker network).
describe('Sprigs panel', () => {
	beforeEach(() => {
		cy.loginAdmin();
		cy.visit('/admin/sprigs');
	});

	it('runs in a secure context (TLS sidecar) so gated APIs are testable', () => {
		// clipboard, crypto.subtle, service workers, getUserMedia all require
		// this — over plain http on a non-localhost origin they silently vanish.
		cy.window().its('isSecureContext').should('be.true');
	});

	it('renders the catalog with state badges', () => {
		cy.get('[data-cy="sprig-card"]', { timeout: 20000 }).should('have.length.at.least', 5);
		cy.get('[data-sprig="mock-embedding"]').should('exist');
		cy.get('[data-sprig="vector-chroma"]').should('exist');
	});

	// MUST run while the rootstock is still bare (before vector-chroma delivers):
	// an onnx cultivar's dep pre-check fails fast, and the Poka-Yoke UX contract
	// is that the operator sees the backend's actual fix pointer ("graft
	// vector-chroma first"), not a generic "Failed to graft".
	it('failed graft surfaces the backend reason, not a generic error', () => {
		cy.get('[data-sprig="multilingual-e5-large"]', { timeout: 20000 }).within(() => {
			cy.get('[data-cy="sprig-graft"]').click();
		});
		// The fix-pointer phrase exists ONLY in the backend's error detail — the
		// bare string "vector-chroma" would also match that sprig's catalog card.
		cy.contains('Graft vector-chroma first', { timeout: 30000 }).should('exist');
	});

	it('grafts the mock embedding cultivar and shows it rooted', () => {
		cy.get('[data-sprig="mock-embedding"]', { timeout: 20000 }).within(() => {
			cy.get('[data-cy="sprig-graft"]').click();
			cy.get('[data-cy="sprig-state"]', { timeout: 60000 }).should(
				'have.attr',
				'data-state',
				'rooted'
			);
		});
	});

	it('prunes the grafted cultivar back to Sprouted', () => {
		// grafted in the previous test (same container); if not, graft first
		cy.get('[data-sprig="mock-embedding"]', { timeout: 20000 }).then(($card) => {
			if ($card.find('[data-cy="sprig-prune"]').length === 0) {
				cy.wrap($card).find('[data-cy="sprig-graft"]').click();
				cy.wrap($card)
					.find('[data-cy="sprig-state"]', { timeout: 60000 })
					.should('have.attr', 'data-state', 'rooted');
			}
		});
		cy.get('[data-sprig="mock-embedding"]').within(() => {
			cy.get('[data-cy="sprig-prune"]').click();
			cy.get('[data-cy="sprig-state"]', { timeout: 30000 }).should(
				'have.attr',
				'data-state',
				'sprouted'
			);
		});
	});

	it('deliver-sprig graft surfaces the post-graft warning toast', () => {
		cy.get('[data-sprig="vector-chroma"]', { timeout: 20000 }).within(() => {
			cy.get('[data-cy="sprig-graft"]').click();
			cy.get('[data-cy="sprig-state"]', { timeout: 180000 }).should(
				'have.attr',
				'data-state',
				'delivered'
			);
		});
		// The Poka-Yoke UX contract: the operator is TOLD what to do next.
		cy.contains('Restart the Rootstock', { timeout: 10000 }).should('exist');
	});

	// Regression: the header counter must include 'delivered' sprigs, matching the
	// cards' own grafted test — it used to count only 'rooted', so a delivered
	// vector-chroma showed "0 of N grafted" under a card badged "Delivered".
	it('grafted counter counts delivered sprigs', () => {
		// State from the previous test: mock pruned (sprouted), vector-chroma delivered.
		cy.get('[data-sprig="vector-chroma"] [data-cy="sprig-state"]', { timeout: 20000 }).should(
			'have.attr',
			'data-state',
			'delivered'
		);
		cy.get('[data-cy="sprigs-grafted-count"]')
			.invoke('text')
			.should('match', /^\s*[1-9]\d* of \d+ grafted\s*$/);
	});
});
