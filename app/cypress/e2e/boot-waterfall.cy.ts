// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL for the boot fetch wave in src/routes/(app)/+layout.svelte.
//
// Two halves, and both matter:
//   1. Correctness — the stores those fetches feed still populate. A seeded banner
//      renders (banners store), the saved ui settings are honored (settings store),
//      and the app reaches interactive at all (loaded flag survives the refactor).
//   2. Teeth — the boot fetches that have no dependency on each other overlap in
//      time instead of forming a waterfall. RED against the pre-change image.
//
// The dependency that must SURVIVE is also asserted: user settings still resolve
// before /api/models goes out, because directConnections comes from settings.
//
// Self-seeds the admin and marks setup complete so no modal blocks the load
// (see the e2e-harness memo: signup hard-closes after the first admin).
const ADMIN = { name: 'Admin User', email: 'admin@example.com', password: 'password' };
const BANNER_TEXT = 'BOOT GUARD-RAIL BANNER';

type Entry = { url: string; start: number; end: number };

describe('boot fetch wave — (app) layout', () => {
	// The harness boots ONE container for the whole run, so a seeded banner would
	// otherwise sit on top of every later spec's landing page. Put it back.
	after(() => {
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			failOnStatusCode: false,
			body: { email: ADMIN.email, password: ADMIN.password }
		}).then((login) => {
			if (login.status !== 200) return;
			cy.request({
				method: 'POST',
				url: '/api/v1/configs/banners',
				headers: { Authorization: `Bearer ${login.body.token}` },
				failOnStatusCode: false,
				body: { banners: [] }
			});
		});
	});

	it('populates the boot stores and fetches the independent ones in parallel', () => {
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signup',
			failOnStatusCode: false,
			body: ADMIN
		});

		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			body: { email: ADMIN.email, password: ADMIN.password }
		}).then((login) => {
			expect(login.status, 'admin signin').to.eq(200);
			const token = login.body.token;
			const auth = { Authorization: `Bearer ${token}` };

			cy.request('/api/config').then((cfg) => {
				const version = cfg.body.version;

				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: auth,
					body: {
						ui: { version, setupCompleted: true, workingAlone: true, showChangelog: false }
					}
				});

				// Something observable for the banners store to carry.
				cy.request({
					method: 'POST',
					url: '/api/v1/configs/banners',
					headers: auth,
					body: {
						banners: [
							{
								id: 'boot-guard-rail',
								type: 'info',
								title: '',
								content: BANNER_TEXT,
								dismissible: false,
								timestamp: 0
							}
						]
					}
				});

				cy.visit('/', {
					onBeforeLoad(win) {
						win.localStorage.setItem('token', token);
						win.localStorage.setItem('locale', 'en-US');
						win.localStorage.setItem('version', version);
					}
				});

				// --- correctness ---------------------------------------------------
				// App reached interactive: the boot chain ran to `loaded = true`.
				cy.get('#chat-input', { timeout: 30000 }).should('exist');
				// settings store: setupCompleted honored, so the wizard never opened.
				cy.contains('Get Started').should('not.exist');
				// banners store: the seeded banner made it to the navbar.
				cy.contains(BANNER_TEXT, { timeout: 10000 }).should('be.visible');

				// --- teeth: the wave ------------------------------------------------
				cy.window().then((win) => {
					const res = win.performance.getEntriesByType(
						'resource'
					) as PerformanceResourceTiming[];

					// Earliest entry per endpoint — later refetches are not the boot wave.
					const first = (match: (path: string) => boolean): Entry | null => {
						const hits = res
							.filter((r) => match(new URL(r.name).pathname + new URL(r.name).search))
							.sort((a, b) => a.startTime - b.startTime);
						const r = hits[0];
						return r ? { url: r.name, start: r.startTime, end: r.responseEnd } : null;
					};

					const settings = first((p) => p === '/api/v1/users/user/settings');
					const models = first((p) => p.split('?')[0] === '/api/models');
					const banners = first((p) => p === '/api/v1/configs/banners');
					const tools = first((p) => p === '/api/v1/tools/');

					expect(settings, 'user settings request').to.not.be.null;
					expect(models, 'models request').to.not.be.null;
					expect(banners, 'banners request').to.not.be.null;
					expect(tools, 'tools request').to.not.be.null;

					const wave = [models, banners, tools] as Entry[];
					const lastStart = Math.max(...wave.map((e) => e.start));
					const firstEnd = Math.min(...wave.map((e) => e.end));

					// Written before the assertions so a RED run still leaves numbers behind.
					// The assertions live inside the .then() below because a synchronous
					// expect() here would abort the queue before writeFile ever ran.
					const round = (n: number) => +n.toFixed(1);
					cy.writeFile('cypress/boot-waterfall-timing.json', {
						settings: {
							start: round((settings as Entry).start),
							end: round((settings as Entry).end)
						},
						wave: wave.map((e) => ({
							path: new URL(e.url).pathname,
							start: round(e.start),
							end: round(e.end)
						})),
						waveSpanMs: round(Math.max(...wave.map((e) => e.end)) - Math.min(...wave.map((e) => e.start))),
						bootSpanMs: round(Math.max(...wave.map((e) => e.end)) - (settings as Entry).start),
						overlaps: lastStart < firstEnd
					}).then(() => {
						// All three in flight at the same instant => one wave, not a ladder.
						expect(
							lastStart,
							'independent boot fetches overlap (last start before first end)'
						).to.be.lessThan(firstEnd);

						// The one real dependency survives: settings feeds directConnections,
						// so it must still complete before /api/models is issued.
						expect(
							(settings as Entry).end,
							'user settings resolves before /api/models is issued'
						).to.be.at.most((models as Entry).start);
					});
				});
			});
		});
	});
});
