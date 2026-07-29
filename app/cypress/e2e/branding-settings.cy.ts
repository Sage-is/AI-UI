// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild, surfacePath } from '../support/surfaces';

// Branding settings — the guard-rail, written against the SvelteKit page
// before any code moves, per docs/no-build-surface-convention.md.
//
// This spec judges whichever implementation the run is pointed at, so it may
// only assert things BOTH must do. That rules out one behaviour the Svelte
// page has today: its preview updates as you type, because the values are
// bound to a client-side model. A server-rendered form cannot do that without
// a round-trip per keystroke, so what is asserted here is the weaker contract
// both can honour — the preview reflects the SAVED branding. The live-typing
// difference is a deliberate one for the human UX review to judge, not a
// regression to hide inside a spec that quietly stopped checking it.
//
// Everything below reads `data-cy` and API state rather than labels, so
// retitling a field or translating the page cannot turn this red.

const FIELDS = [
	'branding-logo-url',
	'branding-logo-dark-url',
	'branding-favicon-url',
	'branding-title',
	'branding-subtitle'
] as const;

/** Branding as the server holds it — the only authority either page renders. */
const readBranding = () => cy.request('/api/v1/configs/branding').its('body');

const writeBranding = (body: Record<string, string>) =>
	cy.window().then((win) =>
		cy.request({
			method: 'POST',
			url: '/api/v1/configs/branding',
			headers: { Authorization: `Bearer ${win.localStorage.getItem('token')}` },
			body
		})
	);

const EMPTY = {
	logo_url: '',
	logo_dark_url: '',
	favicon_url: '',
	title: '',
	subtitle: '',
	primary_color: '',
	accent_color: ''
};

describe('Admin branding settings', () => {
	beforeEach(() => {
		cy.loginAdmin();
		cy.visit(surfacePath('branding'));
	});

	// Leave the instance as it was found. The support-level guard restores
	// branding after the whole spec anyway, but a test that depends on the
	// previous test's leftovers is a test that passes only in one order.
	afterEach(() => writeBranding(EMPTY));

	it('renders every branding field', () => {
		FIELDS.forEach((hook) => cy.get(`[data-cy="${hook}"]`, { timeout: 30000 }).should('exist'));
		// Colour is two controls bound to one value — a picker and a hex field.
		// Both are real controls an operator can reach, so both are contract.
		cy.get('[data-cy="branding-primary-color"]').should('exist');
		cy.get('[data-cy="branding-primary-color-text"]').should('exist');
		cy.get('[data-cy="branding-accent-color"]').should('exist');
		cy.get('[data-cy="branding-accent-color-text"]').should('exist');
		cy.get('[data-cy="branding-save"]').should('exist');
	});

	it('shows what the server currently holds, not an empty form', () => {
		writeBranding({ ...EMPTY, title: 'Seeded Title', subtitle: 'Seeded Subtitle' });
		cy.visit(surfacePath('branding'));
		cy.get('[data-cy="branding-title"]', { timeout: 30000 }).should(
			'have.value',
			'Seeded Title'
		);
		cy.get('[data-cy="branding-subtitle"]').should('have.value', 'Seeded Subtitle');
	});

	it('saves what was typed, and it survives a reload', () => {
		const title = 'Guard Rail Co';
		const subtitle = 'proof it persisted';

		cy.get('[data-cy="branding-title"]', { timeout: 30000 }).clear().type(title);
		cy.get('[data-cy="branding-subtitle"]').clear().type(subtitle);
		cy.get('[data-cy="branding-save"]').click();

		// Assert the SERVER changed, not that a toast appeared. A save button
		// that shows a success message without writing anything is the exact
		// failure this surface can have, and only the API can rule it out.
		readBranding().should((body: Record<string, string>) => {
			expect(body.title, 'title reached the server').to.eq(title);
			expect(body.subtitle, 'subtitle reached the server').to.eq(subtitle);
		});

		cy.visit(surfacePath('branding'));
		cy.get('[data-cy="branding-title"]', { timeout: 30000 }).should('have.value', title);
	});

	it('saves colours from the hex field', () => {
		// The hex text input, not the native colour picker: Cypress cannot drive
		// an OS colour dialog, and the two are bound to the same value, so this
		// covers the pair without pretending to click something it cannot.
		cy.get('[data-cy="branding-primary-color-text"]', { timeout: 30000 })
			.clear()
			.type('#123456');
		cy.get('[data-cy="branding-accent-color-text"]').clear().type('#abcdef');
		cy.get('[data-cy="branding-save"]').click();

		readBranding().should((body: Record<string, string>) => {
			expect(body.primary_color).to.eq('#123456');
			expect(body.accent_color).to.eq('#abcdef');
		});
	});

	it('keeps the colour picker in step with the hex field', () => {
		// The one behaviour on this surface with no other guard. On the Svelte
		// page both inputs bind to the same value; on the no-build page a small
		// island mirrors them, and an island nothing asserts is how the "Show me
		// how to fix this" button shipped rendering and doing nothing.
		//
		// Only this direction is testable — Cypress cannot open a native colour
		// dialog — so the picker-to-hex direction stays a human-pass item.
		cy.get('[data-cy="branding-primary-color-text"]', { timeout: 30000 })
			.clear()
			.type('#ff8800');
		cy.get('[data-cy="branding-primary-color"]').should('have.value', '#ff8800');

		// A half-typed value must NOT move the picker: assigning an invalid
		// colour silently resets the input to #000000, which would fight the
		// operator mid-word.
		cy.get('[data-cy="branding-accent-color-text"]').clear().type('#ab');
		cy.get('[data-cy="branding-accent-color"]').should('not.have.value', '#ab0000');
	});

	it('carries a picker change back into the hex field', () => {
		// The direction I first wrote off as human-only. It is not: no driver can
		// OPEN the OS colour dialog, but the dialog is the browser's code, not
		// ours. Our contract is "when the picker's value changes, the hex field
		// follows", and a synthetic input event exercises exactly that — the
		// island is delegated from the document and listens for `input`, and the
		// Svelte page's bind:value reacts to the same event.
		//
		// What stays genuinely out of reach for ANY WebDriver-family tool
		// (Selenium included) is proving the swatch opens a dialog at all. That
		// is browser behaviour, and it is not what breaks.
		cy.get('[data-cy="branding-primary-color"]', { timeout: 30000 })
			.invoke('val', '#22aa55')
			.trigger('input');
		cy.get('[data-cy="branding-primary-color-text"]').should('have.value', '#22aa55');

		// And it must survive the round trip, so this is a real contract and not
		// two fields agreeing in the browser and disagreeing on the server.
		cy.get('[data-cy="branding-save"]').click();
		readBranding().should((body: Record<string, string>) => {
			expect(body.primary_color, 'the picker value reached the server').to.eq('#22aa55');
		});
	});

	it('previews the saved branding', () => {
		writeBranding({ ...EMPTY, title: 'Previewed', subtitle: 'and shown', primary_color: '#123456' });
		cy.visit(surfacePath('branding'));

		// Scoped to the preview container rather than hooking each line of it.
		// The parity contract is interactive controls; preview text is output,
		// and asserting it through the container keeps the hook count honest.
		cy.get('[data-cy="branding-preview"]', { timeout: 30000 })
			.should('contain.text', 'Previewed')
			.and('contain.text', 'and shown');
		cy.get('[data-cy="branding-swatch-primary"]').should('exist');
		// Nothing set the accent, so its swatch must be absent. Asserting the
		// empty case is what stops a page that renders every swatch always from
		// passing the line above.
		cy.get('[data-cy="branding-swatch-accent"]').should('not.exist');
	});

	it('the no-build page runs with no SvelteKit bundle on it', function () {
		if (!isNoBuild()) this.skip();
		// The migration's standing rule: a migrated surface must pass its spec
		// with the compiled bundle absent from its route. Without this the spec
		// could be green against a page that quietly still boots the SPA.
		cy.get('[data-cy="branding-title"]', { timeout: 30000 }).should('exist');
		cy.get('script[src*="_app/immutable"]').should('not.exist');
	});
});
