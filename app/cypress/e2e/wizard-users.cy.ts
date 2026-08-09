// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { openSetupPanel } from '../support/surfaces';

// Add users. Guard-rail, written against the SvelteKit panel first.
//
// Every assertion goes through /api/v1/users/ rather than through the rendered
// list, so neither implementation can satisfy this by agreeing with itself.
//
// The role picker is the interesting part. It offers `facilitator`, and the CSV
// importer used to validate against ['admin', 'user', 'pending'], so a role you
// could choose by hand was refused from a file. Both sides now accept it. That
// is asserted here rather than left to the changelog, because the two lists
// living apart is exactly how they drifted in the first place.

const auth = () => cy.window().then((win) => win.localStorage.getItem('token'));

const people = () =>
	auth().then((token) =>
		cy
			.request({ url: '/api/v1/users/', headers: { Authorization: `Bearer ${token}` } })
			.then((res) => {
				const rows = Array.isArray(res.body) ? res.body : (res.body?.users ?? []);
				return rows as Array<{ email: string; role: string }>;
			})
	);

const expectUser = (email: string, role: string, attempt = 0) => {
	people().then((rows) => {
		const found = rows.find((u) => u.email === email);
		if (found && found.role === role) return;
		if (attempt >= 20) {
			expect(found && found.role, `${email} exists with role ${role}`).to.eq(role);
			return;
		}
		cy.wait(250);
		expectUser(email, role, attempt + 1);
	});
};

// A fresh address per run. The e2e container is reused across specs in a run,
// so a fixed address would pass once and then collide with itself.
const unique = (prefix: string) => `${prefix}-${Date.now()}@example.test`;

describe('Setup wizard: users', () => {
	beforeEach(() => cy.loginAdmin());

	it('offers a field for each part of a user, and a role picker', () => {
		openSetupPanel('users');
		['name', 'email', 'password', 'role'].forEach((field) => {
			cy.get(`[data-cy="users-${field}"]`).should('exist');
		});
		cy.get('[data-cy="users-add"]').should('exist');
		cy.get('[data-cy="users-working-alone"]').should('exist');
	});

	it('offers facilitator as a role', () => {
		openSetupPanel('users');
		cy.get('[data-cy="users-role"] option[value="facilitator"]').should('exist');
	});

	it('adds a user the server then reports', () => {
		const email = unique('added');
		openSetupPanel('users');
		cy.get('[data-cy="users-name"]').type('Added Person');
		cy.get('[data-cy="users-email"]').type(email);
		cy.get('[data-cy="users-password"]').type('hunter2hunter');
		cy.get('[data-cy="users-role"]').select('user');
		cy.get('[data-cy="users-add"]').click();
		expectUser(email, 'user');
	});

	it('records working alone', () => {
		openSetupPanel('users');
		cy.get('[data-cy="users-working-alone"]').click();
		auth().then((token) =>
			cy
				.request({
					url: '/api/v1/users/user/settings',
					headers: { Authorization: `Bearer ${token}` }
				})
				.then((res) => {
					expect(res.body?.ui?.workingAlone, 'workingAlone recorded').to.eq(true);
				})
		);
	});
});

// CSV import. The deleted modal parsed the file in the browser with FileReader
// and posted one row at a time; the route uploads it and parses it once, which
// is what makes it drivable by attaching a file to a form.
describe('Setup wizard: CSV import', () => {
	beforeEach(() => cy.loginAdmin());

	it('imports a facilitator, which the old allowlist refused', () => {
		const email = unique('facil');
		const csv = `Name,Email,Password,Role\nFacil Person,${email},hunter2hunter,facilitator\n`;
		openSetupPanel('users');
		cy.get('[data-cy="users-csv"]').selectFile(
			{ contents: Cypress.Buffer.from(csv), fileName: 'users.csv', mimeType: 'text/csv' },
			{ force: true }
		);
		cy.get('[data-cy="users-import"]').click();
		expectUser(email, 'facilitator');
	});

	// split(',') mangles this; csv.DictReader does not.
	it('keeps a comma inside a quoted field', () => {
		const email = unique('quoted');
		const csv = `Name,Email,Password,Role\n"Doe, Jane",${email},hunter2hunter,user\n`;
		openSetupPanel('users');
		cy.get('[data-cy="users-csv"]').selectFile(
			{ contents: Cypress.Buffer.from(csv), fileName: 'users.csv', mimeType: 'text/csv' },
			{ force: true }
		);
		cy.get('[data-cy="users-import"]').click();
		expectUser(email, 'user');
		people().then((rows) => {
			const found = rows.find((u) => u.email === email) as unknown as { name: string };
			expect(found.name, 'the comma survived the parse').to.eq('Doe, Jane');
		});
	});

	it('reports a bad row by its line number and imports the rest', () => {
		const good = unique('good');
		const csv =
			`Name,Email,Password,Role\n` +
			`Good Person,${good},hunter2hunter,user\n` +
			`Bad Role,${unique('bad')},hunter2hunter,wizard\n`;
		openSetupPanel('users');
		cy.get('[data-cy="users-csv"]').selectFile(
			{ contents: Cypress.Buffer.from(csv), fileName: 'users.csv', mimeType: 'text/csv' },
			{ force: true }
		);
		cy.get('[data-cy="users-import"]').click();
		cy.get('[data-cy="users-result"]')
			.should('contain.text', 'Imported 1 user')
			.and('contain.text', 'line 3');
		expectUser(good, 'user');
	});
});
