// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { surfacePath } from '../support/surfaces';

// The Agents surface — the guard-rail, written against the SvelteKit page
// before any code moves, per docs/no-build-surface-convention.md.
//
// This spec judges whichever implementation the run is pointed at, so it may
// only assert what BOTH must do. Three consequences worth stating, because each
// one is a place where a lazier spec would quietly stop checking something:
//
// 1. Search is asserted after a COMMIT (`{enter}`), not per keystroke. The
//    Svelte page filters on every input event against a client-side array; a
//    server-rendered page cannot without a round-trip per keystroke. Committing
//    is the weaker contract both can honour. The as-you-type difference is a
//    deliberate one for the human UX review, not a regression to hide here.
//
// 2. The toggle is asserted on the SERVER's `is_active`, not on the switch's
//    rendered state. A switch that looks flipped and saved nothing is exactly
//    the failure this migration has already shipped once, in the "Show me how
//    to fix this" button that rendered and did nothing.
//
// 3. Hide and Delete have a second, shift-key-only path in the legacy page
//    (`agents-hide` / `agents-delete` appear only while Shift is held). Those
//    are NOT asserted as a contract: the same two capabilities live in the row
//    menu, which is the path every user has, and a modifier-key affordance is a
//    UX decision the no-build page should be free to make differently. They
//    carry hooks anyway, so if a future implementation does render them the
//    parity gate will compare them.
//
// Everything below reads `data-cy` and API state rather than labels, so
// translating the page or retitling a control cannot turn this red.

type Agent = { id: string; name: string; tag?: string; description?: string };

const AGENTS: Agent[] = [
	{ id: 'cy-agent-alpha', name: 'Cypress Alpha', tag: 'cy-one', description: 'the alpha agent' },
	{ id: 'cy-agent-beta', name: 'Cypress Beta', tag: 'cy-two', description: 'the beta agent' },
	{ id: 'cy-agent-gamma', name: 'Cypress Gamma' }
];

const authed = (options: Partial<Cypress.RequestOptions>) =>
	cy.window().then((win) =>
		cy.request({
			...options,
			headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` }
		} as Cypress.RequestOptions)
	);

const createAgent = (agent: Agent) =>
	authed({
		method: 'POST',
		url: '/api/v1/models/create',
		body: {
			id: agent.id,
			name: agent.name,
			// Load-bearing, and the reason the first run of this spec found zero
			// rows: `Models.get_models()` filters `base_model_id != None`, so an
			// agent created without one is a BASE model and never reaches the
			// workshop list. Nothing dereferences the value to render a row, so
			// any id will do — but omitting it puts the fixture in the other list.
			base_model_id: 'cy-base-model',
			meta: {
				description: agent.description ?? null,
				...(agent.tag ? { tags: [{ name: agent.tag }] } : {})
			},
			params: {},
			is_active: true
		}
	});

// Agents are DATA, not config, so the support-level config guard does not cover
// them: whatever this spec creates would sit in every later spec's model list.
// It cleans up after itself for the same reason `stt-not-configured` sets its
// own engine — a spec that depends on the container being pristine, or on
// leaving it that way for someone else, is a spec that passes in one order.
const deleteAgent = (id: string) =>
	authed({
		method: 'DELETE',
		url: `/api/v1/models/model/delete?id=${encodeURIComponent(id)}`,
		failOnStatusCode: false
	});

const readAgent = (id: string) =>
	authed({
		method: 'GET',
		url: `/api/v1/models/model?id=${encodeURIComponent(id)}`
	}).its('body');

const rows = () => cy.get('[data-cy="agents-row"]');
const row = (id: string) => cy.get(`[data-cy="agents-row"][data-agent-id="${id}"]`);

describe('Workshop: Agents', () => {
	before(() => {
		cy.loginAdmin();
		// `cy.session` restores the session without leaving a page open, and the
		// token this reads lives in the app origin's localStorage — so something
		// has to be visited before any authed request can be built.
		cy.visit('/');
		AGENTS.forEach((a) => deleteAgent(a.id));
		AGENTS.forEach(createAgent);

		// The fixture verifies itself, because the first run of this spec failed
		// eight tests with "Expected to find [data-cy=agents-row], but never
		// found it" — a message that describes the page and says nothing about
		// WHY, when the actual state was that the seeded agents did not exist.
		// A fixture that can fail silently turns every downstream assertion into
		// a red herring, which is the same defect as a gate that passes on a
		// broken product. This names it at the source instead.
		authed({ method: 'GET', url: '/api/v1/models/' }).then((res) => {
			const ids = (res.body as Array<{ id: string }>).map((m) => m.id);
			AGENTS.forEach((a) =>
				expect(ids, `fixture: agent ${a.id} was created and is visible`).to.include(a.id)
			);
		});
	});

	after(() => {
		cy.loginAdmin();
		cy.visit('/');
		AGENTS.forEach((a) => deleteAgent(a.id));
	});

	beforeEach(() => {
		cy.loginAdmin();
		cy.visit(surfacePath('agents'));
		// The list is the surface. Waiting on it rather than on a fixed timeout
		// keeps every later assertion honest about what it is measuring.
		cy.get('[data-cy="agents-list"]', { timeout: 30000 }).should('exist');
	});

	it('renders one row per agent, and every seeded agent is there', () => {
		AGENTS.forEach((a) => row(a.id).should('exist'));
		rows().should('have.length.at.least', AGENTS.length);
	});

	it('offers a way to create an agent', () => {
		cy.get('[data-cy="agents-create"]').should('exist');
	});

	it('narrows the list to a search term, and restores it when cleared', () => {
		rows().its('length').as('total');

		cy.get('[data-cy="agents-search"]').type('Cypress Alpha{enter}');
		row('cy-agent-alpha').should('exist');
		row('cy-agent-beta').should('not.exist');

		cy.get('[data-cy="agents-search-clear"]').click();
		cy.get('@total').then((total) => rows().should('have.length', total));
	});

	it('narrows the list to a tag, and All brings the rest back', () => {
		// The tag row only renders when some agent carries a tag, which two of
		// the seeded three do.
		cy.get('[data-cy="agents-tag"]').contains('cy-one').click();
		row('cy-agent-alpha').should('exist');
		row('cy-agent-beta').should('not.exist');

		cy.get('[data-cy="agents-tag-all"]').click();
		row('cy-agent-beta').should('exist');
	});

	it('links each row to its own editor', () => {
		row('cy-agent-alpha')
			.find('[data-cy="agents-edit"]')
			.should('have.attr', 'href')
			.and('include', encodeURIComponent('cy-agent-alpha'));
	});

	it('links each row to a conversation with that agent', () => {
		row('cy-agent-alpha')
			.find('[data-cy="agents-open"]')
			.should('have.attr', 'href')
			.and('include', encodeURIComponent('cy-agent-alpha'));
	});

	it('toggling an agent changes is_active ON THE SERVER', () => {
		readAgent('cy-agent-alpha').its('is_active').should('eq', true);

		// `button, input` rather than a single selector, because the hook is on
		// the wrapper: the Svelte page's switch is a bits-ui `<button>`, and a
		// server-rendered page would post a form — a `<button>` or a checkbox
		// that submits. Both shapes are legitimate; naming one would make this
		// spec a vote for an implementation it is supposed to be neutral about.
		row('cy-agent-alpha').find('[data-cy="agents-toggle"]').find('button, input').first().click();

		// The rendered switch is not the assertion. A control that looks flipped
		// and persisted nothing passes an appearance check and fails the user.
		cy.then(() => readAgent('cy-agent-alpha').its('is_active').should('eq', false));
	});

	it('offers the row menu, with every action it carries today', () => {
		row('cy-agent-alpha').find('[data-cy="agents-menu"]').click();
		['hide', 'copy-link', 'clone', 'export', 'delete'].forEach((action) =>
			cy.get(`[data-cy="agents-menu-${action}"]`).should('exist')
		);
	});

	it('offers import and export to an admin', () => {
		cy.get('[data-cy="agents-import"]').should('exist');
		cy.get('[data-cy="agents-export"]').should('exist');
	});
});
