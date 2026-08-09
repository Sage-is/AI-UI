// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// PERF MEASUREMENT (not a gate): what does a PLAIN-TEXT conversation load pull?
// This is where the markdown lazy-load win shows. Before the change,
// MarkdownTokens statically imported CodeBlock (mermaid + codemirror) and
// KatexRenderer (katex), so ANY rendered message — even plain prose — dragged
// those chunks in. After the change they load only when a math/code/diagram
// token actually renders. Heavy libs live in hash-named chunks (not URL-
// identifiable), so we compare TOTAL transferred/decoded bytes and request count
// for the same seeded plain chat across the BEFORE and AFTER images: the delta
// is the render libs no longer fetched. Writes app/cypress/perf-plain.json.

describe('perf — plain-text conversation heavy-lib load', () => {
	it('captures heavy render libs fetched for a plain chat', () => {
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signup',
			failOnStatusCode: false,
			body: { name: 'Admin User', email: 'admin@example.com', password: 'password' }
		});
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			failOnStatusCode: false,
			body: { email: 'admin@example.com', password: 'password' }
		}).then((login) => {
			expect(login.status, 'admin signin').to.eq(200);
			const token = login.body.token;
			cy.request('/api/config').then((cfg) => {
				const version = cfg.body.version;
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: { Authorization: `Bearer ${token}` },
					body: { ui: { version, setupCompleted: true, workingAlone: true, showChangelog: false } }
				});

				const userMsg = {
					id: 'u-1',
					parentId: null,
					childrenIds: ['a-1'],
					role: 'user',
					content: 'hi',
					models: ['guard'],
					timestamp: 1
				};
				const asstMsg = {
					id: 'a-1',
					parentId: 'u-1',
					childrenIds: [],
					role: 'assistant',
					content:
						'Just plain prose across a few sentences. No math, no code fences, no diagrams. Nothing that should pull a heavy render library.',
					model: 'guard',
					modelName: 'guard',
					done: true,
					timestamp: 2
				};
				const chat = {
					id: '',
					title: 'plain-perf',
					models: ['guard'],
					params: {},
					history: { messages: { 'u-1': userMsg, 'a-1': asstMsg }, currentId: 'a-1' },
					messages: [userMsg, asstMsg],
					tags: [],
					timestamp: 3
				};

				cy.request({
					method: 'POST',
					url: '/api/v1/chats/new',
					headers: { Authorization: `Bearer ${token}` },
					body: { chat }
				}).then((created) => {
					const chatId = created.body.id;
					cy.visit(`/c/${chatId}`, {
						onBeforeLoad(win) {
							win.localStorage.setItem('token', token);
							win.localStorage.setItem('locale', 'en-US');
							win.localStorage.setItem('version', version);
						}
					});
					// Ensure the plain message actually rendered, then let chunks settle.
					cy.contains('plain prose', { timeout: 30000 }).should('exist');
					// eslint-disable-next-line cypress/no-unnecessary-waiting
					cy.wait(3000);
					cy.window().then((win) => {
						const res = win.performance.getEntriesByType(
							'resource'
						) as PerformanceResourceTiming[];
						const rows = res.map((r) => ({
							url: r.name.replace(win.location.origin, ''),
							transfer: r.transferSize || 0,
							decoded: r.decodedBodySize || 0
						}));
						const totalTransfer = rows.reduce((a, r) => a + r.transfer, 0);
						const totalDecoded = rows.reduce((a, r) => a + r.decoded, 0);
						const top = [...rows].sort((a, b) => b.decoded - a.decoded).slice(0, 20);
						const summary = {
							count: rows.length,
							totalTransferMB: +(totalTransfer / 1048576).toFixed(2),
							totalDecodedMB: +(totalDecoded / 1048576).toFixed(2),
							top
						};
						cy.writeFile('cypress/perf-plain.json', summary);
						cy.log(
							`plain-convo requests=${rows.length} transfer=${summary.totalTransferMB}MB decoded=${summary.totalDecodedMB}MB`
						);
						expect(rows.length, 'captured resources').to.be.greaterThan(0);
					});
				});
			});
		});
	});
});
