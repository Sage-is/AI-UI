// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild } from '../support/surfaces';

// Server-side locale for the no-build pages.
//
// This was the standing blocker on any route taking over from the SPA. The wizard
// carries 210 translation keys and roughly a quarter are translated. The image
// shipped one catalog, so it could only ever answer in English.
//
// Three properties, each one a thing that has gone wrong somewhere before.
//
// The language rides in `?lang=`, never a cookie. A response varying by cookie
// owes `Vary: Cookie`. The auth cookie shares that header, so every session
// becomes its own cache entry, and a mis-set `Vary` hands one admin's page to
// another. The absence of `Vary: Cookie` is asserted, not assumed.
//
// `?lang=` also names a directory. `pages/i18n.py` builds
// `locales/<locale>/translation.json`, so an unchecked value walks the filesystem.
//
// And English must survive. 1,511 of the 1,538 `en-US` entries are stored as `""`,
// because the key IS the English text. A translator missing the SPA's
// `returnEmptyString: false` guard blanks the English UI. That reads as a CSS bug.

const PANEL = '/pages/admin/setup/features';

// Present in every catalog, and short enough to be unambiguous in the HTML.
const EN = 'Save';
const ES = 'Guardar';

describe('Pages: locale', () => {
	beforeEach(function () {
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	it('renders Spanish when the URL asks for it', () => {
		cy.request(`${PANEL}?lang=es-ES`).then((res) => {
			expect(res.body, 'the Spanish string is rendered').to.contain(ES);
		});
	});

	it('renders English by default, not a blank where a string should be', () => {
		cy.request(PANEL).then((res) => {
			expect(res.body, 'English falls back to the key, not to ""').to.contain(EN);
		});
	});

	it('negotiates from Accept-Language when the URL does not say', () => {
		cy.request({ url: PANEL, headers: { 'Accept-Language': 'es-ES,es;q=0.9' } }).then((res) => {
			expect(res.body, 'the header picked the language').to.contain(ES);
		});
	});

	it('reaches a shipped catalog for a region we do not ship', () => {
		// es-MX has no catalog. Falling all the way to English would be worse than
		// answering in the Spanish we do have.
		cy.request({ url: PANEL, headers: { 'Accept-Language': 'es-MX' } }).then((res) => {
			expect(res.body, 'a regional variant reaches its shipped sibling').to.contain(ES);
		});
	});

	// The cacheability guarantee. Assert the header, because "we decided not to
	// use a cookie" is not something a future edit can be trusted to remember.
	it('never varies by cookie, and varies by Accept-Language only when it had to', () => {
		cy.request({ url: PANEL, headers: { 'Accept-Language': 'es-ES' } }).then((res) => {
			const vary = String(res.headers.vary ?? '');
			expect(vary.toLowerCase(), 'a cookie must never key the cache').to.not.contain('cookie');
			expect(vary, 'a negotiated response says so').to.contain('Accept-Language');
		});

		cy.request(`${PANEL}?lang=es-ES`).then((res) => {
			const vary = String(res.headers.vary ?? '');
			expect(vary.toLowerCase(), 'a cookie must never key the cache').to.not.contain('cookie');
			// The URL alone identifies this representation, so nothing varies and
			// the response is cacheable on its address.
			expect(vary.toLowerCase(), 'an explicit ?lang= needs no Vary').to.not.contain(
				'accept-language'
			);
		});
	});

	// A reader who picks a language and presses Next must not land in English.
	it('carries the language through every link it renders', () => {
		cy.visit(`${PANEL}?lang=es-ES`);
		cy.get('[data-cy="setup-next"]').should('have.attr', 'href').and('contain', 'lang=es-ES');
		cy.get('[data-cy="setup-prev"]').should('have.attr', 'href').and('contain', 'lang=es-ES');
		cy.get('[data-cy="features-panel"] form')
			.should('have.attr', 'action')
			.and('contain', 'lang=es-ES');
	});

	// This one discriminates, and the others below it do not — say so rather than
	// letting the count look like coverage.
	//
	// `../locales/es-ES` resolves back onto a REAL catalog file. Remove the
	// membership check in `_catalog` and this request renders Spanish; with the
	// check it renders English. Every other traversal string points at a path
	// where no `translation.json` happens to exist, so those pass whether the
	// guard is there or not. They are kept because the layout that makes them
	// harmless today is an accident, not a design.
	it('refuses a traversal that would otherwise reach a real catalog', () => {
		cy.request({ url: `${PANEL}?lang=${encodeURIComponent('../locales/es-ES')}` }).then((res) => {
			expect(res.body, 'a traversal must not load the catalog it points at').to.not.contain(ES);
			expect(res.body, 'it renders the default instead').to.contain(EN);
		});
	});

	it('falls back for any other locale that escapes the catalog directory', () => {
		cy.request(PANEL).then((plain) => {
			['../../../etc', 'en-US/..', '..%2F..%2Fetc', '/etc/passwd'].forEach((attempt) => {
				cy.request({
					url: `${PANEL}?lang=${encodeURIComponent(attempt)}`,
					failOnStatusCode: false
				}).then((res) => {
					expect(res.status, `${attempt} is handled, not fatal`).to.eq(200);
					expect(res.body, `${attempt} rendered the default, not another file`).to.eq(
						plain.body
					);
				});
			});
		});
	});
});
