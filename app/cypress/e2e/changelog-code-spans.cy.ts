// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild } from '../support/surfaces';

// Inline code in the release notes must stay inline code.
//
// Reported by Alexander against the live wizard: a note reading
//
//   Each recipe (`scripts/build-sprig-*.sh`) runs its sanity gate
//
// arrived as
//
//   Each recipe ( scripts/build-sprig-*.sh ) runs its sanity gate
//
// — no monospace, and stray spaces inside the brackets. The parser in `env.py`
// renders CHANGELOG.md to HTML and then flattens each entry with
// `get_text(separator=" ", strip=True)`, which drops the `<code>` element AND
// leaves a space where it was.
//
// Two assertions, because either one alone can pass while the bug is present:
// a page with SOME code spans could still have flattened this entry, and an
// entry with no stray spaces could still have lost its markup.

const PANEL = '/pages/admin/setup/changelog';

describe('Changelog: inline code survives the parser', () => {
	beforeEach(function () {
		// No-build only. The Svelte panel is deleted; this is the only renderer.
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	it('renders backticked spans as <code>, not as bare text', () => {
		cy.visit(PANEL);
		// A floor rather than an exact count: CHANGELOG.md gains entries every
		// release, and pinning the number would make this red on a release
		// rather than on a regression. Zero is the regression.
		cy.get('[data-cy="changelog-body"] code').should('have.length.at.least', 1);
	});

	it('does not pad the flattened span with spaces', () => {
		// The visible symptom, asserted on the rendered text rather than on the
		// markup: even if something re-introduced `<code>`, a stray space either
		// side would still read wrong to a human.
		cy.request(PANEL)
			.its('body')
			.then((html: string) => {
				const spans = [...html.matchAll(/<code[^>]*>([^<]+)<\/code>/g)].map((m) => m[1]);
				expect(spans, 'the page rendered inline code at all').to.have.length.at.least(1);
				spans.forEach((s) =>
					expect(s, `code span "${s}" carries no padding`).to.eq(s.trim())
				);
				// And the shape the report was about: an opening bracket
				// immediately followed by a code span, with nothing between.
				expect(html, 'brackets sit tight against the code they wrap').to.not.match(
					/\(\s+<code/
				);
			});
	});

	it('still strips the entry title from its own content', () => {
		// The parser splits "Title: content" on the first ": ". Rebuilding the
		// content from the raw HTML has to make the same split, or every list
		// entry would render its title twice.
		cy.request(PANEL)
			.its('body')
			.then((html: string) => {
				const pairs = [...html.matchAll(/<dt[^>]*>([^<]+)<\/dt>\s*<dd[^>]*>([\s\S]*?)<\/dd>/g)];
				expect(pairs, 'the changelog rendered term/description pairs').to.have.length.at.least(
					1
				);
				pairs.forEach(([, title, body]) => {
					const t = title.trim();
					if (!t) return;
					expect(
						body.trimStart().startsWith(t),
						`entry "${t}" does not repeat its title in the body`
					).to.eq(false);
				});
			});
	});
});
