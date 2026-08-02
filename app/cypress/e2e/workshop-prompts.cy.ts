// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { surfacePath } from '../support/surfaces';

// The Prompts surface — the guard-rail, written against the SvelteKit page
// before any code moves, per docs/no-build-surface-convention.md.
//
// This spec judges whichever implementation the run is pointed at, so it may
// only assert what BOTH must do. Three consequences, each a place where a lazier
// spec would quietly stop checking something:
//
// 1. Search is asserted after a COMMIT (`{enter}`), not per keystroke. The
//    Svelte page filters on every input event against a client-side array; a
//    server-rendered page cannot without a round-trip per keystroke. Committing
//    is the weaker contract both can honour, and pressing enter is harmless on
//    the side that has already filtered. The as-you-type difference is a
//    deliberate UX question for the human review, not a regression to hide.
//
// 2. Delete is asserted on the SERVER, not on the row disappearing. A control
//    that looks like it worked and persisted nothing is exactly the failure this
//    migration has already shipped once, in a "Show me how to fix this" button
//    that rendered and did nothing. The confirm step is handled tolerantly
//    because the two implementations reach it differently — the Svelte page
//    opens a dialog, a server-rendered page posts a form — and which of those a
//    surface uses is an implementation choice, while "the prompt is gone
//    afterwards" is the contract.
//
// 3. The owner line is asserted as TEXT, never as an avatar. `/api/v1/prompts/list`
//    returns `PromptUserResponse`, which nests the whole `UserResponse` — on the
//    production snapshot that is 115 kB of base64 across 8 prompts whose own
//    content totals 7 kB. The row renders `prompt.user.name` and nothing else,
//    so a faithful port would ship 95% waste. Prune, don't port.
//
// Everything below reads `data-cy` and API state rather than labels, so
// translating the page or retitling a control cannot turn this red.

type Prompt = { command: string; title: string; content: string };

const PROMPTS: Prompt[] = [
	{ command: 'cy-prompt-alpha', title: 'Cypress Alpha', content: 'the alpha prompt body' },
	{ command: 'cy-prompt-beta', title: 'Cypress Beta', content: 'the beta prompt body' },
	{ command: 'cy-prompt-gamma', title: 'Cypress Gamma', content: 'the gamma prompt body' }
];

const authed = (options: Partial<Cypress.RequestOptions>) =>
	cy.window().then((win) =>
		cy.request({
			...options,
			headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` }
		} as Cypress.RequestOptions)
	);

/**
 * Seed a prompt the way the product's own form does — WITH a leading slash.
 *
 * This is not cosmetic. `insert_new_prompt` stores the command verbatim, while
 * `get`, `update` and `delete` all look it up as `f"/{command}"`
 * (`routers/prompts.py:99,126,161`). So a prompt stored without the slash can
 * never be fetched, edited or deleted again. Seeding without it made this spec
 * fail with the app throwing NOT_FOUND, which read like a spec bug and is not
 * one — see the board entry. The fixture matches the product; the defect is
 * filed separately rather than papered over here.
 */
const createPrompt = (p: Prompt) =>
	authed({
		method: 'POST',
		url: '/api/v1/prompts/create',
		body: { command: `/${p.command}`, title: p.title, content: p.content },
		failOnStatusCode: false
	});

const deletePrompt = (command: string) =>
	authed({
		method: 'DELETE',
		url: `/api/v1/prompts/command/${command}/delete`,
		failOnStatusCode: false
	});

/** The list as the SERVER sees it — the only opinion that counts for state. */
const serverCommands = () =>
	cy.window().then((win) =>
		cy
			.request({
				url: '/api/v1/prompts/list',
				headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` }
			})
			// The API stores commands with a leading slash; the fixture creates them
			// without. Normalising here rather than in each assertion keeps that
			// detail in one place instead of four.
			.then((res) => (res.body as { command: string }[]).map((p) => p.command.replace(/^\//, '')))
	);

const rows = () => cy.get('[data-cy="prompts-row"]');
const row = (command: string) => cy.get('[data-cy="prompts-row"]').filter(`:contains(${command})`);

describe('Workshop: Prompts', () => {
	before(() => {
		cy.loginAdmin();
		cy.visit('/');
		PROMPTS.forEach((p) => createPrompt(p));

		// Self-verifying fixture. The Agents spec learned this the hard way: eight
		// tests failed with "Expected to find [data-cy=...] but never found it",
		// a message describing the page and saying nothing about WHY, when the
		// real state was that the seeded rows did not exist. Assert the seed.
		serverCommands().then((commands) => {
			PROMPTS.forEach((p) =>
				expect(commands, `seeded prompt ${p.command} exists on the server`).to.include(p.command)
			);
		});
	});

	after(() => {
		cy.loginAdmin();
		cy.visit('/');
		PROMPTS.forEach((p) => deletePrompt(p.command));
	});

	beforeEach(() => {
		cy.loginAdmin();
		cy.visit(surfacePath('prompts'));
		// The list is the surface. Waiting on it rather than on a fixed timeout
		// keeps every later assertion honest about what it is measuring.
		cy.get('[data-cy="prompts-list"]', { timeout: 30000 }).should('exist');
	});

	it('renders one row per prompt, and every seeded prompt is there', () => {
		PROMPTS.forEach((p) => row(p.command).should('exist'));
		rows().should('have.length.at.least', PROMPTS.length);
	});

	it('offers a way to create a prompt', () => {
		cy.get('[data-cy="prompts-create"]').should('exist').and('have.attr', 'href');
	});

	it('narrows the list to a search term, and restores it when cleared', () => {
		rows().its('length').as('total');

		cy.get('[data-cy="prompts-search"]').type('Cypress Alpha{enter}');
		row('cy-prompt-alpha').should('exist');
		row('cy-prompt-beta').should('not.exist');

		cy.get('[data-cy="prompts-search-clear"]').click();
		cy.get('@total').then((total) => rows().should('have.length', total));
	});

	it('links each row to its own editor', () => {
		row('cy-prompt-alpha')
			.find('[data-cy="prompts-edit"]')
			.should('have.attr', 'href')
			.and('include', 'cy-prompt-alpha');
	});

	it('gives the title its own link to the editor', () => {
		row('cy-prompt-alpha')
			.find('[data-cy="prompts-title"]')
			.should('have.attr', 'href')
			.and('include', 'cy-prompt-alpha');
	});

	it('names the owner as text, not as a picture', () => {
		// The contract is that a reader can see who owns a prompt. It is asserted
		// as text on purpose: the list endpoint nests the owner's whole record
		// including a base64 avatar, and rendering that avatar would be a faithful
		// port of the defect rather than a migration.
		row('cy-prompt-alpha').should('contain.text', 'By ');
		row('cy-prompt-alpha').find('img').should('not.exist');
	});

	it('offers the row menu, with every action it carries today', () => {
		row('cy-prompt-alpha').find('[data-cy="prompts-menu"]').click();
		['share', 'clone', 'export', 'delete'].forEach((action) =>
			cy.get(`[data-cy="prompts-menu-${action}"]`).should('exist')
		);
	});

	it('offers import and export to an admin', () => {
		cy.get('[data-cy="prompts-import"]').should('exist');
		cy.get('[data-cy="prompts-export"]').should('exist');
	});

	it('deleting a prompt removes it ON THE SERVER', () => {
		// This test is NOT retry-safe by nature: it destroys its own subject, so a
		// second attempt would delete an already-deleted prompt and the app would
		// throw a 404 as an unhandled rejection — which is exactly what the first
		// run of this spec reported, with the retry's error masking whatever went
		// wrong on attempt one. Re-seed instead of assuming, so each attempt starts
		// from the same state and the failure it reports is its own.
		createPrompt({
			command: 'cy-prompt-gamma',
			title: 'Cypress Gamma',
			content: 'the gamma prompt body'
		});
		cy.reload();
		cy.get('[data-cy="prompts-list"]', { timeout: 30000 }).should('exist');
		serverCommands().should('include', 'cy-prompt-gamma');

		row('cy-prompt-gamma').find('[data-cy="prompts-menu"]').click();
		cy.get('[data-cy="prompts-menu-delete"]').filter(':visible').first().click();

		// Confirm ONLY if a confirmation appears. The Svelte page opens a dialog;
		// a server-rendered page may post the form straight through. Requiring one
		// shape would make this spec a vote for an implementation it is meant to
		// judge neutrally; requiring neither would let a no-op delete pass.
		//
		// It WAITS for the dialog rather than looking once. Looking once is what
		// the first draft did, and a Svelte dialog opens on a state change a tick
		// later — so the check ran against a document that did not have it yet,
		// skipped the confirm, and the test failed on "the prompt is still there"
		// with no hint that the confirm had never been clicked. Bounded, and it
		// costs nothing on an implementation that has no dialog at all.
		cy.document().then(
			(doc) =>
				new Cypress.Promise<void>((resolve) => {
					const deadline = Date.now() + 4000;
					const tick = () => {
						if (doc.querySelector('[data-cy="confirm-dialog-confirm"]') || Date.now() > deadline) {
							resolve();
						} else {
							setTimeout(tick, 100);
						}
					};
					tick();
				})
		);
		cy.get('body').then(($body) => {
			const confirm = $body.find('[data-cy="confirm-dialog-confirm"]');
			if (confirm.length) cy.wrap(confirm.first()).click({ force: true });
		});

		// The row vanishing is not the assertion. The server is.
		cy.then(() => serverCommands().should('not.include', 'cy-prompt-gamma'));
	});
});
