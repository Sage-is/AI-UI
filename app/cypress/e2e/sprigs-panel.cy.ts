// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Sprigs™ panel lifecycle — the operator-facing half of the Bonsai™
// architecture. Walks the actual buttons an admin clicks: catalog render,
// graft (mock cultivar: no artifact pull, fast), prune, and a deliver-sprig
// graft whose post_graft_note must surface as a visible warning toast
// (vector-chroma: requires the local sprig registry on the docker network).
// One spec, two implementations. `/admin/sprigs` is the SvelteKit panel;
// `/pages/admin/sprigs` is the no-build page that replaces it. The migration
// rule is that this spec is green against BOTH — that is the proof users lost
// nothing, and it is why every assertion below reads a data-cy attribute or a
// message the backend itself supplies, never a class name or a phrase one
// implementation happens to use.
//
//   SPRIGS_PANEL=/pages/admin/sprigs   (Cypress env, so: CYPRESS_SPRIGS_PANEL=…)
const PANEL = Cypress.env('SPRIGS_PANEL') || '/admin/sprigs';

describe(`Sprigs panel (${PANEL})`, () => {
	beforeEach(() => {
		cy.loginAdmin();
		cy.visit(PANEL);
	});

	it('runs in a secure context (TLS sidecar) so gated APIs are testable', () => {
		// clipboard, crypto.subtle, service workers, getUserMedia all require
		// this — over plain http on a non-localhost origin they silently vanish.
		cy.window().its('isSecureContext').should('be.true');
	});

	// Without this, the spec could pass against the SPA while believing it was
	// testing the no-build page — a green run that proves nothing, which is the
	// failure mode the streaming spike taught us to design against. It also
	// encodes the plan's rule for every later surface: a migrated route passes
	// its spec with the SvelteKit bundle absent.
	it('the no-build page ships no SvelteKit bundle', function () {
		if (PANEL === '/admin/sprigs') this.skip();
		cy.document().then((doc) => {
			const srcs = [...doc.querySelectorAll('script[src]')].map((s) => s.getAttribute('src') ?? '');
			expect(srcs.filter((s) => s.includes('_app/immutable')), 'SvelteKit chunks').to.be.empty;
			expect(srcs.some((s) => s.includes('/pages/_assets/vendor/htmx.min.js')), 'htmx is all that runs')
				.to.be.true;
		});
	});

	// The first-paint claim, made falsifiable. The island could not do this: it
	// shipped chrome and then fetched, so the catalog was absent from the HTML
	// the server sent. Asserting on the RESPONSE BODY rather than the rendered
	// page is the whole point — a browser would fill either one in.
	it('the panel is in the HTML the server sends, not fetched afterwards', function () {
		if (PANEL === '/admin/sprigs') this.skip();
		cy.request(PANEL).then((res) => {
			expect(res.body, 'catalog rendered server-side').to.contain('data-sprig="mock-embedding"');
			expect(res.body).to.contain('data-cy="sprigs-grafted-count"');
		});
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

	// retries:0 on purpose. This test grafts, so a retry does not re-run it — it
	// runs a DIFFERENT test against already-delivered state, where the Graft
	// button is a Prune button. That second failure ("sprig-graft never found")
	// then masks the first, real one. Once burned: the real failure here was a
	// missing toast, and the retry's error sent the diagnosis chasing an
	// ordering bug that did not exist.
	it('deliver-sprig graft surfaces the post-graft warning toast', { retries: 0 }, () => {
		// Ask the backend what it will say, instead of hardcoding a copy of the
		// copy. This assertion used to look for "Restart the Rootstock" — a phrase
		// the product stopped emitting when grafting became restart-free — so a
		// genuine UX improvement showed up as a failing graft test. Sourcing the
		// text from the catalog means rewording the note can never break this,
		// while the contract it guards (the operator is TOLD what happens next)
		// is still enforced.
		cy.window()
			.then((win) =>
				cy.request({
					url: '/api/v1/retrieval/sprigs/catalog',
					headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` }
				})
			)
			.then((res) => {
				const note = res.body?.catalog?.['vector-chroma']?.post_graft_note;
				expect(note, 'vector-chroma declares a post_graft_note').to.be.a('string').and.not.be
					.empty;

				cy.get('[data-sprig="vector-chroma"]', { timeout: 20000 }).within(() => {
					cy.get('[data-cy="sprig-graft"]').click();
					cy.get('[data-cy="sprig-state"]', { timeout: 180000 }).should(
						'have.attr',
						'data-state',
						'delivered'
					);
				});
				// The Poka-Yoke UX contract: the operator is TOLD what happens next.
				cy.contains(note, { timeout: 10000 }).should('exist');
			});
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
