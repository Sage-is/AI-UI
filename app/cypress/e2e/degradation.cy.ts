// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The degradation UX contract (Poka-Yoke): on a bare rootstock, a capability
// that is not grafted must fail with a HUMAN-READABLE message that names the
// Sprig™ — in the UI, not just in an API response. If someone breaks the
// graceful-503 chain (or swallows the toast), this suite goes red.
describe('Bare-rootstock degradation UX', () => {
	beforeEach(() => {
		cy.loginAdmin();
	});

	it('chat file upload surfaces a clean Sprig-naming error toast', () => {
		cy.visit('/');
		cy.get('#chat-input', { timeout: 20000 }).should('exist');
		// Attach a document through the real (hidden) file input — this fires
		// /api/v1/retrieval/process/file, which 503s pre-graft.
		cy.get('[data-cy="chat-file-input"]').selectFile(
			{
				contents: Cypress.Buffer.from('sage rootstock degradation probe'),
				fileName: 'probe.txt',
				mimeType: 'text/plain'
			},
			{ force: true }
		);
		// The toast must NAME the fix, not just fail. Accept either capability
		// owner depending on which guard fires first (vector vs loaders).
		cy.contains(/Sprig|vector|rag-loaders/i, { timeout: 20000 }).should('exist');
	});

	it('sprigs panel shows everything Sprouted (nothing silently grafted)', () => {
		cy.visit('/admin/sprigs');
		cy.get('[data-cy="sprig-card"]', { timeout: 20000 }).should('have.length.at.least', 5);
		cy.get('[data-cy="sprig-state"][data-state="rooted"]').should('not.exist');
	});
});
