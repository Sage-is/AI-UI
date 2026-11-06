// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The admin notice for Docker Desktop and OrbStack (card "Admin notice when Sage
// runs on Docker Desktop or OrbStack"). `ai-ui` passes SAGE_RUNTIME into the
// container; /api/config hands it to admins. The spec sets it through an
// intercept, since a test box has no `ai-ui` behind it.

const KEY = 'sage.runtimeNotice.dismissed';

// The admin panel on `runtime`, once its nav has rendered, so an absent notice
// means absent and not "not drawn yet". `dismissed` seeds the browser's memory.
const adminOn = (runtime: string, dismissed?: string) => {
	cy.intercept('GET', '/api/config', (req) =>
		req.continue((res) => {
			res.body.sage_runtime = runtime;
		})
	).as('config');
	cy.visit('/admin', {
		onBeforeLoad: (win) =>
			dismissed ? win.localStorage.setItem(KEY, dismissed) : win.localStorage.removeItem(KEY)
	});
	cy.wait('@config');
	cy.get('nav.drag-region').should('be.visible');
};

describe('Admin runtime notice', () => {
	beforeEach(() => cy.loginAdmin());

	it('shows the migrate line on Docker Desktop, and stays dismissed', () => {
		adminOn('docker-desktop');
		cy.get('[data-cy=runtime-notice]')
			.should('contain', 'Docker Desktop')
			.and('contain', 'ai-ui migrate');
		cy.get('[data-cy=runtime-notice-dismiss]').click();
		cy.get('[data-cy=runtime-notice]').should('not.exist');
		cy.reload();
		cy.get('nav.drag-region').should('be.visible');
		cy.get('[data-cy=runtime-notice]').should('not.exist');
	});

	it('comes back after a move to another runtime', () => {
		adminOn('orbstack', 'docker-desktop');
		cy.get('[data-cy=runtime-notice]').should('contain', 'OrbStack');
	});

	it('says nothing on Colima', () => {
		adminOn('colima');
		cy.get('[data-cy=runtime-notice]').should('not.exist');
	});

	it('says nothing without ai-ui', () => {
		adminOn('');
		cy.get('[data-cy=runtime-notice]').should('not.exist');
	});
});
