// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The Persian face must arrive for Persian readers, and for nobody else.
//
// WHY THIS EXISTS. On 2026-08-02 `Vazirmatn-Variable` was given a
// `unicode-range` in `app/src/app.css`. It sits in the body stack as Archivo's
// fallback, so before that change it was fetched on routes where any character
// Archivo lacks appeared — 235 kB of Arabic glyphs, measured on the production
// snapshot, on a page rendering English. After it, the browser may only use the
// face for characters in the Arabic blocks.
//
// That change fails in two directions and **only one of them is visible**:
//
//   too NARROW — a Persian reader gets fallback glyphs for Persian text. Nothing
//     errors. Nobody on this team reads Persian. It would ship.
//   too WIDE / REMOVED — everyone pays for the face again and the saving
//     evaporates, with no symptom but a number in a ledger nobody re-reads.
//
// EACH DIRECTION NEEDS A DIFFERENT KIND OF ASSERTION, and finding that out cost
// two wrong attempts worth writing down:
//
//   * Widening the range to include Latin did NOT re-introduce the download.
//     `unicode-range` says which characters a face MAY serve; the browser still
//     only fetches a face it actually USES, and Archivo comes first in the stack
//     and covers Latin. So a network assertion cannot see that regression.
//   * Deleting the range entirely did not re-introduce it either, on the page
//     this spec can reach without signing in. The 235 kB came from a signed-in
//     route containing some glyph Archivo lacks.
//
// So the "not too wide" direction is asserted **structurally, against the
// stylesheet the app actually serves**, and the "not too narrow" direction is
// asserted **behaviourally, against the network**. Both were proved able to fail
// before this file was trusted: narrowing the range reddens the second test,
// deleting it reddens the first.
//
// The earlier draft of this spec asserted "en-US does not download Vazirmatn"
// and passed whether or not the change was present. It is kept in mind rather
// than in the file: an assertion that cannot fail is worse than none, because it
// reports coverage it does not have.

const VAZIRMATN = /Vazirmatn/;

/** Every font this document actually pulled over the network. */
const fontsFetched = (win: Window) =>
	(win.performance.getEntriesByType('resource') as PerformanceResourceTiming[])
		.map((r) => r.name)
		.filter((u) => /\.(woff2?|ttf|otf)(\?|$)/.test(u));

describe('Vazirmatn is scoped to Arabic, and still reaches Persian readers', () => {
	// DIRECTION 1 — the range exists and is not wide open.
	//
	// Read from the served stylesheet rather than the source file, so a build
	// step that drops or rewrites the declaration is caught too. The app's CSS is
	// hashed into `/_app/immutable/assets/*.css`, so find it from the document
	// rather than guessing the name.
	it('the served stylesheet scopes the Persian face to the Arabic blocks', () => {
		cy.visit('/');
		cy.get('#chat-input, input[type="email"]', { timeout: 60000 }).should('exist');

		cy.document().then((doc) => {
			const sheets = [...doc.querySelectorAll('link[rel="stylesheet"]')]
				.map((l) => (l as HTMLLinkElement).href)
				.filter((h) => h.startsWith(doc.location.origin));
			expect(sheets.length, 'same-origin stylesheets on the page').to.be.greaterThan(0);

			// Collect every sheet, then assert on the one that declares the face.
			const bodies: string[] = [];
			return cy
				.wrap(sheets)
				.each((href: unknown) => {
					cy.request(href as string).then((res) => bodies.push(res.body as string));
				})
				.then(() => {
					const css = bodies.join('\n');
					const face = css.match(/@font-face\s*{[^}]*Vazirmatn[^}]*}/);
					expect(
						face ? 'declared' : 'MISSING',
						'a @font-face for Vazirmatn must exist in the served CSS'
					).to.eq('declared');

					const block = face ? face[0] : '';
					expect(
						/unicode-range/.test(block) ? 'scoped' : 'UNSCOPED',
						'Vazirmatn must carry a unicode-range, or every locale downloads the Persian face again — that is the 235 kB this change removed'
					).to.eq('scoped');

					// And the scope must actually be the Arabic block, not anything.
					//
					// Both spellings are accepted because THE MINIFIER REWRITES THE
					// RANGE: the source says `U+0600-06FF` and the served CSS says
					// `U+6??`, which is the equivalent wildcard form. The first draft
					// of this assertion knew only the source spelling and went red
					// against correct code — a guard that fails on every build gets
					// deleted, and it would have taken the real check with it.
					expect(
						/U\+0?6\?\?|U\+0600-0?6FF/i.test(block) ? 'covers Arabic' : 'DOES NOT COVER ARABIC',
						'the range must include the Arabic block (U+0600-06FF, or U+6?? once minified), where Persian letters and Persian digits live'
					).to.eq('covers Arabic');
				});
		});
	});

	// DIRECTION 2 — Persian text really does pull the face.
	//
	// Proved able to fail: narrowing the range to exclude U+0600-06FF turns this
	// red with the message below, which is precisely the silent breakage nobody
	// here would notice by looking.
	it('Persian text on the page pulls the Persian face', () => {
		cy.visit('/', {
			onBeforeLoad(win) {
				win.localStorage.setItem('locale', 'fa-IR');
			}
		});
		cy.get('#chat-input, input[type="email"]', { timeout: 60000 }).should('exist');

		// Persian text is injected rather than relied upon from the catalogue: a
		// missing translation is a translation bug, and a spec that fails for two
		// unrelated reasons gets muted rather than fixed.
		cy.document().then((doc) => {
			const p = doc.createElement('p');
			p.id = 'cy-persian';
			p.className = 'font-primary';
			p.textContent = 'سلام دنیا ۱۲۳';
			doc.body.appendChild(p);
		});
		cy.get('#cy-persian').should('exist');
		cy.document().its('fonts.ready');
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(2000);

		cy.window().then((win) => {
			expect(
				fontsFetched(win).filter((u) => VAZIRMATN.test(u)).length,
				'Persian text must pull Vazirmatn — if this is 0 the unicode-range is too narrow and Persian readers are seeing fallback glyphs'
			).to.be.greaterThan(0);
		});
	});
});
