// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The ui-Sprig™ contract — Phase 1 of the frontend migration, and the surface
// the marketplace cannot launch without.
//
// A ui-Sprig ships hypermedia: a self-contained fragment, validated fail-closed
// at graft, rendered into the page shell's slot. Script is refused unless an
// admin grants it to that Sprig by name, and pruning revokes the grant.
//
// This walks the whole lifecycle against a real artifact pulled from the local
// registry — graft, serve, render, prune, reset — because the parts that go
// wrong in a marketplace are the transitions, not the happy state.
const SPRIG = 'ui-workshop-welcome';
const PAGE = '/pages/admin/sprigs';
const CATALOG = '/api/v1/retrieval/sprigs/catalog';

const auth = () => cy.getCookie('token').then((c) => ({ Authorization: `Bearer ${c!.value}` }));

describe('ui-Sprig contract', () => {
	beforeEach(() => cy.loginAdmin());

	after(() => {
		// The harness boots one container for the whole run, so a grafted
		// fragment left behind would render into every later page. The shared
		// support-file guard watches admin CONFIG, not the sprig volume, so this
		// suite cleans up after itself.
		cy.loginAdmin();
		auth().then((headers) => {
			cy.request({
				method: 'POST',
				url: '/api/v1/retrieval/sprigs/prune',
				headers,
				body: { name: SPRIG },
				failOnStatusCode: false
			});
		});
	});

	it('nothing is served, and the slot is empty, before anything is grafted', () => {
		cy.request('/ui/active.html').then((res) => {
			expect(res.body.trim(), 'no fragment').to.eq('');
		});
		cy.request(PAGE).then((res) => {
			expect(res.body).to.not.contain('sprig-ui-slot');
		});
	});

	it('the catalog offers it as a ui capability, with no scripting granted', () => {
		auth().then((headers) => {
			cy.request({ url: CATALOG, headers }).then((res) => {
				expect(res.body.catalog[SPRIG], 'catalogued').to.exist;
				expect(res.body.catalog[SPRIG].capability).to.eq('ui');
				// A permission nobody can see is a permission nobody revokes, so
				// the panel is told about it whether or not it is set.
				expect(res.body.ui_scripting_grant, 'granted to nobody by default').to.eq('');
			});
		});
	});

	it('grafts, serves the fragment, and renders it into the page slot', () => {
		auth().then((headers) => {
			cy.request({
				method: 'POST',
				url: '/api/v1/retrieval/sprigs/graft',
				headers,
				body: { name: SPRIG, capability: 'ui' },
				timeout: 120000
			}).then((res) => {
				expect(res.body.status).to.be.true;
				expect(res.body.delivered).to.be.true;
			});

			cy.request('/ui/active.html').then((res) => {
				expect(res.body).to.contain('sprig-welcome');
				expect(res.body).to.contain('Welcome to the workshop');
			});

			// The slot is server-rendered, so the fragment must arrive WITH the
			// page — no second request, no slot-shaped hole to fill in later.
			cy.request(PAGE).then((res) => {
				expect(res.body).to.contain('id="sprig-ui-slot"');
				expect(res.body).to.contain(`data-sprig-ui="${SPRIG}"`);
				expect(res.body).to.contain('Welcome to the workshop');
			});

			cy.request({ url: CATALOG, headers }).then((res) => {
				expect(res.body.active_ui).to.eq(SPRIG);
			});
		});
	});

	it('a scripting grant belongs to one Sprig by name and cannot be inherited', () => {
		auth().then((headers) => {
			cy.request({
				method: 'POST',
				url: '/api/v1/retrieval/sprigs/ui/scripting',
				headers,
				body: { name: SPRIG, allow: true }
			}).then((res) => {
				expect(res.body.ui_scripting_grant).to.eq(SPRIG);
			});

			// A grant is only meaningful for something that could become the
			// active fragment, so the catalog allowlist gates it the same way
			// graft does. Without this an admin could arm a name that does not
			// exist yet and have it take effect the day it does.
			cy.request({
				method: 'POST',
				url: '/api/v1/retrieval/sprigs/ui/scripting',
				headers,
				body: { name: 'theme-workshop-bio', allow: true },
				failOnStatusCode: false
			}).then((res) => {
				expect(res.status, 'not a ui-Sprig').to.eq(400);
			});

			cy.request({ url: CATALOG, headers }).then((res) => {
				expect(res.body.ui_scripting_grant, 'the refused grant changed nothing').to.eq(SPRIG);
			});
		});
	});

	it('pruning clears the fragment AND revokes the grant', () => {
		auth().then((headers) => {
			cy.request({
				method: 'POST',
				url: '/api/v1/retrieval/sprigs/prune',
				headers,
				body: { name: SPRIG }
			}).then((res) => {
				expect(res.body.ui_reset, 'the active pointer was cleared').to.be.true;
				// The grant must not survive what it was granted to. A name left
				// behind would silently re-arm if this Sprig were grafted again.
				expect(res.body.scripting_grant_revoked, 'grant revoked').to.be.true;
			});

			cy.request('/ui/active.html').then((res) => {
				expect(res.body.trim()).to.eq('');
			});
			cy.request(PAGE).then((res) => {
				expect(res.body).to.not.contain('sprig-ui-slot');
			});
			cy.request({ url: CATALOG, headers }).then((res) => {
				expect(res.body.active_ui).to.eq('');
				expect(res.body.ui_scripting_grant).to.eq('');
			});
		});
	});
});
