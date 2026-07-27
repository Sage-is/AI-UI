// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL for the base-models cache (ENABLE_BASE_MODELS_CACHE, default on).
//
// /api/models probes every configured provider. Uncached that costs ~740ms and
// it sits on the boot path for every user; cached it is ~5ms. The cache has no
// TTL, so the deal is: it must be FAST, and it must DROP when a provider
// connection changes, or deployments serve a stale model list until restart.
// Both halves are asserted here — a fast cache with broken invalidation is a
// worse bug than the slow path it replaced.
const ADMIN = { name: 'Admin User', email: 'admin@example.com', password: 'password' };

// Generous vs the measured ~5ms cached / ~740ms uncached, so this fails on
// behaviour rather than on a busy CI box.
const CACHED_MAX_MS = 250;

const timedModels = (token: string) => {
	const started = performance.now();
	return cy
		.request({ url: '/api/models', headers: { Authorization: `Bearer ${token}` } })
		.then((res) => {
			expect(res.status, '/api/models status').to.eq(200);
			return performance.now() - started;
		});
};

describe('base-models cache', () => {
	let token: string;

	before(() => {
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
			token = login.body.token;
		});
	});

	it('serves repeat /api/models from cache', () => {
		// Warmed at startup, so even the first call should already be cached.
		timedModels(token).then((first) => {
			timedModels(token).then((second) => {
				timedModels(token).then((third) => {
					cy.log(`models: ${first.toFixed(0)} / ${second.toFixed(0)} / ${third.toFixed(0)} ms`);
					const median = [first, second, third].sort((a, b) => a - b)[1];
					expect(median, 'median /api/models round-trip (ms)').to.be.lessThan(CACHED_MAX_MS);
				});
			});
		});
	});

	it('drops the cache when a provider connection changes', () => {
		// Read the current ollama config and write back the SAME values: no
		// functional change, no state leaked to later specs, but it still goes
		// through the update endpoint that must invalidate.
		cy.request({ url: '/ollama/config', headers: { Authorization: `Bearer ${token}` } }).then(
			(cfg) => {
				cy.request({
					method: 'POST',
					url: '/ollama/config/update',
					headers: { Authorization: `Bearer ${token}` },
					body: {
						ENABLE_OLLAMA_API: cfg.body.ENABLE_OLLAMA_API,
						OLLAMA_BASE_URLS: cfg.body.OLLAMA_BASE_URLS,
						OLLAMA_API_CONFIGS: cfg.body.OLLAMA_API_CONFIGS
					}
				});

				// Cache dropped => this one has to re-probe the providers, so it is
				// slow again. That slowness IS the evidence of invalidation.
				timedModels(token).then((afterChange) => {
					cy.log(`post-invalidation /api/models: ${afterChange.toFixed(0)} ms`);
					expect(
						afterChange,
						'provider re-probed after a connection change (ms)'
					).to.be.greaterThan(CACHED_MAX_MS);

					// ...and the cache refills, so the next one is fast again.
					timedModels(token).then((rewarmed) => {
						expect(rewarmed, 'cache refills after invalidation (ms)').to.be.lessThan(
							CACHED_MAX_MS
						);
					});
				});
			}
		);
	});
});
