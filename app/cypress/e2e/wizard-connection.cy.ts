// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { openSetupPanel } from '../support/surfaces';

// Model providers. Guard-rail, written against the SvelteKit panel first.
//
// The contract this panel owes: a URL field and a verify button per
// provider, and a
// verify that fails does NOT persist. That second half is the one worth having.
// A step whose whole job is "prove this endpoint answers before you keep it"
// fails silently if a bad URL gets saved anyway, and the instance then looks
// configured while answering nothing.
//
// The e2e rootstock has no reachable provider, so the unreachable case is the
// one that can be driven end to end here. A passing verify needs a live
// endpoint and belongs to the manual pass.

const auth = () => cy.window().then((win) => win.localStorage.getItem('token'));

const ollamaUrls = () =>
	auth().then((token) =>
		cy
			.request({ url: '/ollama/config', headers: { Authorization: `Bearer ${token}` } })
			.then((res) => res.body?.OLLAMA_BASE_URLS ?? [])
	);

const BAD = 'http://nope.invalid:11434';

describe('Setup wizard: model connections', () => {
	beforeEach(() => cy.loginAdmin());

	it('offers a URL and a verify button for each provider', () => {
		openSetupPanel('connection');
		['openai', 'ollama'].forEach((provider) => {
			cy.get(`[data-cy="connection-${provider}-url"]`).should('exist');
			cy.get(`[data-cy="connection-${provider}-verify"]`).should('exist');
		});
		cy.get('[data-cy="connection-openai-key"]').should('exist');
	});

	// The assertion the step exists for.
	it('does not persist a URL that fails to verify', () => {
		ollamaUrls().then((before: string[]) => {
			openSetupPanel('connection');
			cy.get('[data-cy="connection-ollama-url"]').clear().type(BAD);
			cy.get('[data-cy="connection-ollama-verify"]').click();
			// Give the save time to land if it was going to.
			cy.wait(2000);
			ollamaUrls().should((after: string[]) => {
				expect(after, 'an unverifiable URL was not stored').to.not.include(BAD);
				expect(after, 'the existing configuration survived').to.deep.eq(before);
			});
		});
	});
});

// The same exposure, on the provider key. The deleted modal read the stored key
// into its password field on mount. The route refuses to render it at all.
describe('Setup wizard: the API key is never rendered back', () => {
	beforeEach(() => cy.loginAdmin());

	it('renders the key field empty, whatever is stored', () => {
		openSetupPanel('connection');
		cy.get('[data-cy="connection-openai-key"]').should('have.value', '');
	});

	// Not just the field, the whole document. A value echoed anywhere in the
	// HTML reaches the disk cache and the back button.
	it('keeps the stored key out of the page source', () => {
		auth().then((token) =>
			cy
				.request({ url: '/openai/config', headers: { Authorization: `Bearer ${token}` } })
				.then((res) => {
					const key = (res.body?.OPENAI_API_KEYS ?? [])[0];
					if (!key) {
						cy.log('no key stored on this instance — nothing to leak');
						return;
					}
					cy.request('/pages/admin/setup/connection').then((page) => {
						expect(page.body, 'the stored key does not appear in the HTML').to.not.contain(
							key
						);
					});
				})
		);
	});

	it('says a key is stored without showing it', () => {
		openSetupPanel('connection');
		cy.get('[data-cy="connection-openai-key"]')
			.should('have.attr', 'placeholder')
			.and('match', /sk-\.\.\.|a key is stored/);
	});
});
