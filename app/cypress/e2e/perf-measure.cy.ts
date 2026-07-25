// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// PERF MEASUREMENT (not a gate): dump what a logged-in app load actually fetches,
// to settle the 23 MB question and size the eager-chunk win. Writes a summary to
// app/cypress/perf-resources.json and logs headline numbers. Self-seeds the admin
// and marks setup complete so the load isn't blocked (see the e2e-harness memo).
describe('perf measure — logged-in app load resources', () => {
	it('captures resource sizes on load', () => {
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
					body: {
						ui: { version, setupCompleted: true, workingAlone: true, showChangelog: false }
					}
				});
				cy.visit('/', {
					onBeforeLoad(win) {
						win.localStorage.setItem('token', token);
						win.localStorage.setItem('locale', 'en-US');
						win.localStorage.setItem('version', version);
					}
				});
				// Wait until the app is interactive, then let chunks settle.
				cy.get('#chat-input', { timeout: 30000 }).should('exist');
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
					const top = [...rows].sort((a, b) => b.decoded - a.decoded).slice(0, 25);
					const heavy = rows.filter((r) =>
						/ort-wasm|onnx|kokoro|transformers|pyodide|mediapipe|katex|mermaid|codemirror/i.test(
							r.url
						)
					);
					const summary = {
						count: rows.length,
						totalTransferMB: +(totalTransfer / 1048576).toFixed(2),
						totalDecodedMB: +(totalDecoded / 1048576).toFixed(2),
						top,
						heavy
					};
					cy.writeFile('cypress/perf-resources.json', summary);
					cy.log(
						`requests=${rows.length} transfer=${summary.totalTransferMB}MB decoded=${summary.totalDecodedMB}MB heavy=${heavy.length}`
					);
					expect(rows.length, 'captured resources').to.be.greaterThan(0);
				});
			});
		});
	});
});
