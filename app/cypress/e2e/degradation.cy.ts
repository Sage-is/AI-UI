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
		// The toast must NAME the fix, not just fail. Since 2026-11-03 the composer
		// asks /retrieval/readiness first, so on a bare rootstock the upload never
		// starts: an admin is told at once and offered the fix as a button that runs
		// the wizard's install (lib/utils/documentReading.ts, upload-readiness.cy.ts).
		cy.contains('This box cannot read documents yet.', { timeout: 20000 }).should('exist');
		cy.contains('button', 'Turn on document reading').should('exist');
	});

	it('sprigs panel shows everything Sprouted (nothing silently grafted)', () => {
		cy.visit('/admin/sprigs');
		cy.get('[data-cy="sprig-card"]', { timeout: 20000 }).should('have.length.at.least', 5);
		cy.get('[data-cy="sprig-state"][data-state="rooted"]').should('not.exist');
	});
});
