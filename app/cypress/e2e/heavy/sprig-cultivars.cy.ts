// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../../support/index.d.ts" />

// HEAVY cultivar grafts — the big catalog entries the default gates skip on
// purpose: bge-large-en-v1.5 (~600MB+ OCI artifact, cls-pooling onnx-transformer)
// top-grafted by minilm-onnx-inhoused (384-dim, OCI). Excluded from `make e2e`
// by specPattern (top-level only, like upstream/); run on demand with
// `make e2e_heavy`. Requires only the local sprig registry on the docker
// network — ZERO internet egress (all-MiniLM-onnx, the last live-pull entry,
// was retired 2026-07-05).
//
// Also the only coverage of two Poka-Yoke paths nothing else exercises:
// restart-free onnx graft straight after vector-chroma delivery (the
// invalidate_caches pre-check fix, for BOTH onnx backends), and the 1024→384
// top-graft width-change warning ("must be reindexed").
describe('Heavy Sprig cultivars', () => {
	beforeEach(() => {
		cy.loginAdmin();
		cy.visit('/admin/sprigs');
	});

	it('delivers vector-chroma (ML runtime prerequisite)', () => {
		cy.get('[data-sprig="vector-chroma"]', { timeout: 20000 }).then(($card) => {
			// Idempotent: a previous spec/run may have delivered it already.
			if ($card.find('[data-cy="sprig-state"][data-state="delivered"]').length > 0) return;
			cy.wrap($card).find('[data-cy="sprig-graft"]').click();
			cy.wrap($card)
				.find('[data-cy="sprig-state"]', { timeout: 180000 })
				.should('have.attr', 'data-state', 'delivered');
		});
	});

	it('grafts bge-large-en-v1.5 restart-free after the overlay delivery', () => {
		// The whole point: NO container restart between vector-chroma delivery and
		// this graft — the supervisor invalidates import caches in its pre-check.
		cy.get('[data-sprig="bge-large-en-v1.5"]', { timeout: 20000 }).within(() => {
			cy.get('[data-cy="sprig-graft"]').click();
			// OCI pull + extract + 1024-dim onnx model load; catalog allows 120s.
			cy.get('[data-cy="sprig-state"]', { timeout: 240000 }).should(
				'have.attr',
				'data-state',
				'rooted'
			);
		});
	});

	it('minilm-onnx-inhoused top-grafts over bge with a width warning', () => {
		cy.get('[data-sprig="minilm-onnx-inhoused"]', { timeout: 20000 }).within(() => {
			cy.get('[data-cy="sprig-graft"]').click();
			// OCI pull from the local registry + chroma-cache seed (~80MB, offline).
			cy.get('[data-cy="sprig-state"]', { timeout: 120000 }).should(
				'have.attr',
				'data-state',
				'rooted'
			);
		});
		// Poka-Yoke contract: swapping 1024-dim → 384-dim must WARN the operator
		// that old-width knowledge bases need a reindex before they answer again.
		cy.contains('must be reindexed', { timeout: 10000 }).should('exist');
		// Top-graft contract: only one embedding cultivar rooted at a time — the
		// bge card must have fallen back out of 'rooted'.
		cy.get('[data-sprig="bge-large-en-v1.5"] [data-cy="sprig-state"]').should(
			($el) => expect($el.attr('data-state')).to.not.equal('rooted')
		);
	});
});
