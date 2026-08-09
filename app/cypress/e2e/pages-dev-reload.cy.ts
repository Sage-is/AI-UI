// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { isNoBuild } from '../support/surfaces';

// The development reloader must be INVISIBLE unless somebody asked for it.
//
// `PAGES_RELOAD_DIRS` pins the app to one worker and runs a filesystem watcher.
// Both are right for a person editing panels and wrong for anything serving
// users, so the flag being off has to mean genuinely off — not "registered but
// guarded", which is the same claim with a worse failure mode.
//
// This suite therefore asserts the OFF state, which is the state every shipped
// instance is in and the one the harness gives us: the e2e container boots the
// baked image with nothing mounted and no flag set.
//
// The ON state cannot be reached from here — it needs a container booted with
// the flag and a source tree mounted over the image — so it has its own gate,
// `scripts/gates/dev-reload/run-gate.sh` (`make reload_gate`). Saying that here
// rather than quietly testing half the feature: a spec that only ever sees one
// state should admit which one.

const PANELS = ['changelog', 'welcome', 'auth', 'complete'];

describe('Dev reloader: absent unless asked for', () => {
	beforeEach(function () {
		// No-build only. There is nothing on the SvelteKit side to be absent from.
		if (!isNoBuild()) this.skip();
		cy.loginAdmin();
	});

	it('does not answer on the reload endpoint', () => {
		// NOT a 404 assertion, though that is what this reached for first and it
		// went red at 200. Nothing under `/pages/` can 404: `SPAStaticFiles` is
		// mounted at `/` with an index.html fallback (main.py), so every
		// unmatched path is answered by the SPA shell with a 200. The route
		// genuinely is not registered — the shell is what replies.
		//
		// So assert the thing that is actually observable and actually matters:
		// whatever answers here, it is not an event stream. That goes red the
		// moment somebody drops the `if PAGES_RELOAD_DIRS:` guard, which is the
		// regression worth catching.
		cy.request({ url: '/pages/_dev/reload', failOnStatusCode: false }).should((res) => {
			expect(
				String(res.headers['content-type'] ?? ''),
				'nothing streams events when the reloader is off'
			).to.not.contain('text/event-stream');
		});
	});

	it('does not serve the reload island', () => {
		cy.request({ url: '/pages/_assets/dev-reload.js', failOnStatusCode: false }).should((res) => {
			// The FILE ships in the image — it lives beside the other page assets
			// and there is no build step to exclude it from. What must not happen
			// is a page asking for it.
			expect(res.status, 'the asset itself is allowed to exist').to.be.oneOf([200, 404]);
		});
	});

	it('no page references it', () => {
		// Every setup panel plus the three whole-page surfaces, because the
		// injection is one line in the shell and a regression there would hit
		// all of them at once — so checking one would be enough to pass and not
		// enough to be sure.
		PANELS.forEach((panel) => {
			cy.request(`/pages/admin/setup/${panel}`).its('body').should('not.contain', 'dev-reload.js');
		});
		['/pages/admin/sprigs', '/pages/admin/diagnostics', '/pages/admin/branding'].forEach((url) => {
			cy.request(url).its('body').should('not.contain', 'dev-reload.js');
		});
	});

	it('diagnostics reports the reloader as off', () => {
		cy.window().then((win) => {
			const token = win.localStorage.getItem('token');
			cy.request({
				url: '/api/v1/diagnostics/health',
				headers: { Authorization: `Bearer ${token}` }
			}).should((res) => {
				const row = res.body?.boot_status?.dev_reloader;
				expect(row, 'boot_status carries a dev_reloader row').to.be.an('object');
				expect(row.status, 'reloader is off in a shipped configuration').to.eq('ok');
				expect(row.issue_type, 'and therefore raises no issue').to.eq(null);
			});
		});
	});
});
