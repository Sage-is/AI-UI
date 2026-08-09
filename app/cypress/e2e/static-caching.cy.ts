// Guard-rail (Phase Q perf): SvelteKit content-hashes assets under
// /_app/immutable/, so a new deploy changes the filename — they are safe to
// cache forever. Serving them with `Cache-Control: immutable` ends the
// per-asset revalidation round-trips that inflate repeat-visit load.
//
// Measure-twice: against the pre-change image these assets carry no long-lived
// Cache-Control (this FAILS); after the fix they carry
// `public, max-age=31536000, immutable` (PASSES).
describe('Static assets — immutable caching (Phase Q perf guard-rail)', () => {
	it('serves _app/immutable assets with a long immutable Cache-Control', () => {
		// The SPA shell references content-hashed assets; grab one.
		cy.request('/').then((index) => {
			const match = String(index.body).match(/\/_app\/immutable\/[^"'()\s]+/);
			expect(match, 'index.html references an _app/immutable asset').to.not.be.null;
			const asset = (match as RegExpMatchArray)[0];
			cy.request(asset).then((res) => {
				const cc = String(res.headers['cache-control'] || '');
				expect(cc, `Cache-Control for ${asset}`).to.contain('immutable');
				expect(cc, `max-age for ${asset}`).to.contain('max-age=31536000');
			});
		});
	});

	// /static/* is NOT content-hashed, so it gets a bounded cache instead of an
	// immutable one: STATIC_DIR is re-synced from the build at startup, so a
	// deploy is what changes these, and a week is the worst-case staleness.
	// Without any Cache-Control the browser spends a revalidation round-trip per
	// asset on every repeat visit.
	it('serves /static assets with a bounded Cache-Control, not immutable', () => {
		cy.request('/static/favicon.ico').then((res) => {
			const cc = String(res.headers['cache-control'] || '');
			expect(cc, 'Cache-Control for /static/favicon.ico').to.contain('max-age=604800');
			expect(cc, '/static must not be immutable — these filenames are reused').to.not.contain(
				'immutable'
			);
		});
	});

	// The SPA shell must stay revalidated or a deploy never reaches the browser.
	it('does not cache the SPA shell', () => {
		cy.request('/').then((res) => {
			const cc = String(res.headers['cache-control'] || '');
			expect(cc, 'index.html must not carry a long max-age').to.not.match(/max-age=[1-9]\d{3,}/);
		});
	});
});
