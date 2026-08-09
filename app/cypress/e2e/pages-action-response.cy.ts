// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// A row action must answer with a DOCUMENT, not a fragment.
//
// WHY THIS EXISTS. On 2026-08-03 Alexander clicked Disable on an agent and the
// page lost every style. The cause: `/pages/workshop/agents/{verb}/{id}` returned
// the bare panel — no `<html>`, no `<head>`, no stylesheet link. These surfaces
// have no swapper, so the form does an ordinary POST and the browser NAVIGATES
// to whatever comes back; it rendered the fragment as the whole document. Every
// action on that surface — toggle, hide, clone, delete — had shipped that way.
//
// **Not one gate noticed.** `workshop-agents.cy.ts` asserted `is_active` flipped
// on the server, which it did. `surface-parity.cy.ts` counted `data-cy` hooks,
// which were all present. `route-payload.cy.ts` measured the GET. Every one of
// them was looking at something true while the page a person saw was broken —
// the same shape as the button that rendered and did nothing, and the timing
// that could not fail.
//
// A fragment IS the right answer for a surface whose response gets swapped into
// a live document: `/admin/sprigs` returns one and htmx puts it where it
// belongs. So this cannot be a blanket rule, and the table below names the
// surfaces that NAVIGATE. Adding a swapper to one of them means moving it out
// of this list deliberately, which is a decision rather than a silent drift.
//
// It asserts on the RESPONSE rather than on the DOM after a click, on purpose.
// A page with a swapper never navigates, so a DOM assertion would pass without
// ever exercising the path that broke. The response is the contract.

type Action = { surface: string; url: string; note: string };

/** Surfaces whose POST responses are NAVIGATED TO, so must be whole documents. */
const NAVIGATING: Action[] = [
	{
		surface: 'agents',
		url: '/pages/workshop/agents/toggle/',
		note: 'toggle needs an agent id appended'
	},
	{
		surface: 'prompts',
		url: '/pages/workshop/prompts/clone/',
		note: 'clone needs a command appended'
	}
];

const isDocument = (body: string) =>
	/<html[\s>]/i.test(body) && /<head[\s>]/i.test(body) && /rel=["']?stylesheet/i.test(body);

describe('a row action answers with a whole document', () => {
	beforeEach(() => {
		cy.loginAdmin();
		cy.visit('/');
	});

	it('agents: toggling returns a styled document, not a bare panel', () => {
		const id = 'cy-doc-agent';
		cy.window().then((win) => {
			const token = win.localStorage.getItem('token');
			// Seed rather than assume. A fresh container has no agents, and the
			// first run of this spec failed on "an agent to act on" — a message
			// that at least said WHY, which is the whole reason fixtures assert
			// themselves in this suite.
			//
			// `base_model_id` is load-bearing: `Models.get_models()` filters
			// `base_model_id != None`, so an agent created without one is a BASE
			// model and never reaches the workshop list.
			cy.request({
				method: 'POST',
				url: '/api/v1/models/create',
				headers: { Authorization: `Bearer ${token}` },
				failOnStatusCode: false,
				body: {
					id,
					name: 'Doc Probe',
					base_model_id: 'cy-base-model',
					meta: { description: null },
					params: {},
					is_active: true
				}
			});
			cy.request({
				url: '/api/v1/models/',
				headers: { Authorization: `Bearer ${token}` }
			}).then((list) => {
				const rows = list.body as { id: string }[];
				expect(
					rows.map((r) => r.id).join(', ') || 'NONE',
					'the seeded agent reached the workshop list'
				).to.contain(id);
				cy.request({ method: 'POST', url: `${NAVIGATING[0].url}${id}` }).then((res) => {
					expect(res.status).to.eq(200);
					// Assert on a STRING so the failure says what is missing rather
					// than "expected false to be true".
					expect(
						isDocument(res.body as string)
							? 'a document'
							: 'A BARE FRAGMENT — no <html>, <head> or stylesheet',
						'the browser NAVIGATES to this response, so it must be a whole page'
					).to.eq('a document');
				});
				cy.request({
					method: 'DELETE',
					url: `/api/v1/models/model/delete?id=${id}`,
					headers: { Authorization: `Bearer ${token}` },
					failOnStatusCode: false
				});
			});
		});
	});

	it('prompts: cloning returns a styled document, not a bare panel', () => {
		const command = 'cy-doc-probe';
		cy.window().then((win) => {
			const token = win.localStorage.getItem('token');
			cy.request({
				method: 'POST',
				url: '/api/v1/prompts/create',
				headers: { Authorization: `Bearer ${token}` },
				// The leading slash matters — see workshop-prompts.cy.ts and the
				// board: a prompt stored without it can never be found again.
				body: { command: `/${command}`, title: 'Doc Probe', content: 'x' },
				failOnStatusCode: false
			});
			cy.request({ method: 'POST', url: `${NAVIGATING[1].url}${command}` }).then((res) => {
				expect(res.status).to.eq(200);
				expect(
					isDocument(res.body as string)
						? 'a document'
						: 'A BARE FRAGMENT — no <html>, <head> or stylesheet',
					'the browser NAVIGATES to this response, so it must be a whole page'
				).to.eq('a document');
			});
			// Clean up both the probe and the clone it created.
			[command, `${command}-clone`].forEach((c) =>
				cy.request({
					method: 'DELETE',
					url: `/api/v1/prompts/command/${c}/delete`,
					headers: { Authorization: `Bearer ${token}` },
					failOnStatusCode: false
				})
			);
		});
	});
});
