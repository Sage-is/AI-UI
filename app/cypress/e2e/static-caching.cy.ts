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
});
