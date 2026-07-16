// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// User management through the actual admin panel. Public signup hard-closes
// after the first admin in this fork, so the Add User modal IS the real
// onboarding path for operators — worth a robot walking it.
const newUser = {
	name: 'Panel-Made User',
	email: 'panel-user@sage.is',
	password: 'panel-user-pw-123'
};

describe('Admin user management', () => {
	beforeEach(() => {
		cy.loginAdmin();
		// /admin/users redirects to /overview — visit the settled route directly
		// (clicking mid-redirect loses the modal state to a component remount).
		cy.visit('/admin/users/overview');
	});

	it('creates a user through the Add User modal', () => {
		// Wait for the table to actually render before touching the toolbar.
		cy.contains('td, div', 'admin@example.com', { timeout: 20000 }).should('exist');
		cy.get('[data-cy="add-user"]').click();
		cy.get('[data-cy="add-user-name"]').type(newUser.name);
		cy.get('[data-cy="add-user-email"]').type(newUser.email);
		cy.get('[data-cy="add-user-password"]').type(newUser.password);
		cy.get('[data-cy="add-user-submit"]').click();
		// The new user appears in the list
		cy.contains(newUser.email, { timeout: 15000 }).should('exist');
	});

	it('the panel-made user can sign in and reach the chat', () => {
		// cy.login (support) drives the real /auth form and anchors on #chat-input;
		// non-admin users skip the setup wizard entirely (layout gates on role).
		cy.login(newUser.email, newUser.password);
		cy.visit('/');
		cy.get('#chat-input', { timeout: 20000 }).should('exist');
	});

	it('the new user is NOT an admin (bounced from admin routes)', () => {
		cy.login(newUser.email, newUser.password);
		cy.visit('/admin/users');
		// Non-admins get redirected off admin routes; once the app settles
		// (chat input rendered), the admin users table must not exist.
		cy.get('#chat-input', { timeout: 20000 }).should('exist');
		cy.get('[data-cy="add-user"]').should('not.exist');
	});
});
