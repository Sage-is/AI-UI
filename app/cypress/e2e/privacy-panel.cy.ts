// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Privacy rules panel — the no-build admin page. What an admin clicks: the
// switches and detectors render, the test bench shows what a hosted model
// would see and what comes back, a literal rule saves and takes effect, and a
// purge without the confirmation is refused. Every assertion reads a data-cy
// attribute or a message the backend itself supplies.

const PANEL = '/pages/admin/privacy';

describe(`Privacy panel (${PANEL})`, () => {
	beforeEach(() => {
		cy.loginAdmin();
		cy.visit(PANEL);
	});

	it('renders the switches, the detectors, the rules and the map', () => {
		cy.get('#privacy-panel').should('exist');
		cy.get('[data-cy=privacy-enabled]').should('exist');
		cy.get('[data-cy=privacy-detector-email]').should('be.checked');
		cy.get('[data-cy=privacy-rules] [data-cy=privacy-rule-row]').its('length').should('be.gte', 1);
		cy.get('[data-cy=privacy-map]').should('exist');
	});

	it('the test bench shows what the model would see and what comes back', () => {
		cy.get('[data-cy=bench-text]').clear().type('Ring (416) 555-0100 or bob@corp.example');
		cy.get('[data-cy=bench-run]').click();
		cy.get('[data-cy=bench-out]')
			.should('contain', '(416) 555-')
			.and('not.contain', '0100')
			.and('contain', '@example.invalid')
			.and('not.contain', 'bob@corp.example');
		cy.get('[data-cy=bench-back]').should('contain', '(416) 555-0100').and('contain', 'bob@corp.example');
		cy.get('[data-cy=bench-roundtrip]').should('contain', 'identical');
	});

	it('saves a literal rule and the bench honours it', () => {
		cy.get('[data-cy=privacy-rule-row]')
			.last()
			.within(() => {
				cy.get('[data-cy=rule-name]').clear().type('surname (spec)');
				cy.get('[data-cy=rule-pattern]').clear().type('Silva');
				cy.get('[data-cy=rule-category]').clear().type('surname');
			});
		cy.get('[data-cy=privacy-save]').click();
		cy.get('[data-cy=panel-message]').should('contain', 'Saved');
		cy.get('[data-cy=bench-text]').clear().type('Faye Silva called');
		cy.get('[data-cy=bench-run]').click();
		cy.get('[data-cy=bench-out]').should('contain', 'Faye').and('not.contain', 'Silva');
	});

	it('refuses a purge without the confirmation', () => {
		cy.get('[data-cy=purge-run]').click();
		cy.get('[data-cy=panel-message]').should('contain', 'confirmation');
	});

	// The round trip needs a provider. A recording mock (scripts/privacy/
	// mock_provider.py) registered as a flagged connection provides one on a
	// dev instance; the gate's fresh instance has none, so these skip there.
	const MOCK_MODEL = Cypress.env('PRIVACY_MOCK_MODEL');
	const MOCK_CAPTURE = Cypress.env('PRIVACY_MOCK_CAPTURE');

	it('a flagged connection sees only fakes and the reply comes back real', function () {
		if (!MOCK_MODEL || !MOCK_CAPTURE) this.skip();
		const text = 'Call Faye at (613) 555-0187 or faye.silva@example.com about K1A 0B1.';
		cy.window().then((win) => {
			const token = win.localStorage.getItem('token');
			cy.request({
				method: 'POST',
				url: '/api/chat/completions',
				headers: { Authorization: `Bearer ${token}` },
				body: { model: MOCK_MODEL, stream: false, messages: [{ role: 'user', content: text }] }
			}).then(({ body }) => {
				expect(body.choices[0].message.content).to.contain(text);
			});
			cy.request(MOCK_CAPTURE).then(({ body }) => {
				const sent = body.messages.find((m: { role: string }) => m.role === 'user').content;
				expect(sent).to.not.contain('0187');
				expect(sent).to.not.contain('faye.silva@example.com');
				expect(sent).to.not.contain('K1A 0B1');
				expect(sent).to.match(/\(613\) 555-\d{4}/);
			});
		});
	});

	it('reveals a pair with an audit line, forgets it, then purges with the confirmation', function () {
		if (!MOCK_MODEL) this.skip();
		cy.visit(PANEL);
		cy.get('[data-cy=map-row]').its('length').should('be.gte', 1);
		cy.get('[data-cy=map-reveal]').first().click();
		cy.get('[data-cy=map-real]').should('exist');
		cy.get('[data-cy=privacy-audit]').should('contain', 'reveal');
		cy.get('[data-cy=map-forget]').first().click();
		cy.get('[data-cy=panel-message]').should('contain', 'Forgotten');
		cy.get('[data-cy=purge-confirm]').check();
		cy.get('[data-cy=purge-run]').click();
		cy.get('[data-cy=panel-message]').should('contain', 'Purged');
		cy.get('[data-cy=map-row]').should('not.exist');
		cy.get('[data-cy=privacy-audit]').should('contain', 'purge');
	});
});
