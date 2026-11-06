// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL: every SensitiveInput on a page owns its id, and its screen-reader
// label points at that field. A literal id once made every label on a page with
// several keys (OAuth, Documents, Audio) announce and focus the first field
// (fixed 2026-11-05).
//
// Audio shows a key field only for a hosted engine, so the spec picks OpenAI for
// both speech directions to put two on the page. Nothing is saved.

describe('SensitiveInput ids', () => {
	beforeEach(() => {
		cy.loginAdmin();
	});

	it('gives each secret field its own id and label', () => {
		cy.visit('/admin/settings/audio');
		cy.get('select:has(option[value="openai"])', { timeout: 30000 })
			.should('have.length.at.least', 2)
			.each(($select) => {
				cy.wrap($select).select('openai');
			});

		cy.get('input[id^="sensitive-input-"]')
			.should('have.length.at.least', 2)
			.then(($inputs) => {
				const ids = [...$inputs].map((input) => input.id);
				expect(new Set(ids).size, 'distinct ids').to.eq(ids.length);
				ids.forEach((id) => {
					cy.get(`label[for="${id}"]`).should('have.length', 1);
				});
			});
	});
});
