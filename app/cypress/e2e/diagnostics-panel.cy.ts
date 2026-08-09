// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Diagnostics: the guard-rail, written before the surface migrates.
//
// The plan's one rule spans every phase: a surface's spec is green before we
// cut and green after. This surface had no spec at all, so this is the "first
// gets one" half, and it is deliberately written against a contract the Svelte
// page and its server-rendered replacement can both satisfy.
//
// Everything below reads a data attribute, not a translated string or a class
// name. `data-status` rather than the badge's word means the spec survives a
// rewording and a locale change, and `data-section="boot_status"` rather than
// the heading "Boot status" means the same. That is what lets one spec judge
// two implementations instead of describing one of them.
import { surfacePath } from '../support/surfaces';

const PANEL = surfacePath('diagnostics');
const SECTIONS = ['endpoints', 'boot_status', 'static_assets', 'browser_headers'];
const STATUSES = ['ok', 'degraded', 'unreachable', 'unknown'];

describe(`Diagnostics (${PANEL})`, () => {
	beforeEach(() => {
		cy.loginAdmin();
		cy.visit(PANEL);
	});

	it('renders every diagnostic section', () => {
		cy.get('[data-cy="diag-section"]', { timeout: 30000 }).should('have.length.at.least', 1);
		SECTIONS.forEach((s) => cy.get(`[data-cy="diag-section"][data-section="${s}"]`).should('exist'));
	});

	it('every row carries a known status', () => {
		cy.get('[data-cy="diag-row"]', { timeout: 30000 }).should('have.length.at.least', 3);
		// A row whose status is absent or invented is the failure this catches:
		// the page would still look fine and the badge would say "Unknown"
		// whether the backend said so or the frontend lost it.
		cy.get('[data-cy="diag-row"]').each(($row) => {
			expect(STATUSES, `status of ${$row.attr('data-label')}`).to.include($row.attr('data-status'));
		});
	});

	it('rows are labelled with what they describe', () => {
		cy.get('[data-cy="diag-row"]', { timeout: 30000 }).each(($row) => {
			expect($row.attr('data-label'), 'every row names its subject').to.be.a('string').and.not.be
				.empty;
		});
	});

	it('boot status reports the checks the backend actually returned', () => {
		// Sourced from the API rather than hardcoded, so the spec cannot drift
		// from the backend the way a copied list would. Same discipline the
		// Sprigs spec uses for its post-graft note.
		cy.getCookie('token').then((c) =>
			cy
				.request({
					url: '/api/v1/diagnostics/health',
					headers: { Authorization: `Bearer ${c!.value}` }
				})
				.then((res) => {
					const keys = Object.keys(res.body?.boot_status ?? {});
					expect(keys, 'backend reports boot checks').to.have.length.at.least(1);
					keys.forEach((k) =>
						cy
							.get(`[data-cy="diag-section"][data-section="boot_status"] [data-label="${k}"]`)
							.should('exist')
					);
				})
		);
	});

	it('re-probing all endpoints leaves the page intact', () => {
		cy.get('[data-cy="diagnostics-refresh"]', { timeout: 30000 }).should('not.be.disabled').click();
		// The assertion is that a refresh is non-destructive: sections survive
		// and every row still carries a valid status. A refresh that empties the
		// page passes any "did it reload" check and fails this one.
		cy.get('[data-cy="diag-section"]', { timeout: 30000 }).should('have.length.at.least', 1);
		cy.get('[data-cy="diag-row"]').each(($row) => {
			expect(STATUSES).to.include($row.attr('data-status'));
		});
	});

	// The check that would otherwise be missing. Every assertion above passes just
	// as happily when a summary renders as `diagnostics.summary.unknown.ok`: the
	// row exists, its status is valid, its label is set. This one notices that the
	// page has stopped speaking English.
	//
	// It matters more for the server-rendered page than the Svelte one: there,
	// resolution happens in Python against a catalog shipped into the image, so
	// a missing COPY in the Dockerfile is exactly the failure that looks fine.
	it('summaries are sentences, not untranslated keys', () => {
		cy.get('[data-cy="diag-row"]', { timeout: 30000 }).should('have.length.at.least', 3);
		cy.get('body').then(($body) => {
			const raw = $body.text().match(/diagnostics\.summary\.[a-z_.]+/g) ?? [];
			expect(raw, 'no unresolved translation keys on the page').to.be.empty;
		});
	});

	// The button used to render and do nothing on the no-build page: markup with
	// no behaviour behind it. Every assertion in this file passed anyway, because
	// none of them opened it. A human caught that, not this spec.
	it('the offered fix actually contains remediation steps', () => {
		cy.get('body').then(($body) => {
			if ($body.find('[data-cy="diag-fix"]').length === 0) {
				cy.log('nothing unhealthy on this deployment, so there is no remedy to open');
				return;
			}
			cy.get('[data-cy="diag-fix"]').first().click();
			cy.get('[data-cy="diag-fix"]').first().within(() => {
				// Steps, not just a container: an empty panel is the bug.
				cy.get('li').should('have.length.at.least', 1);
			});
			// Remedies are translation keys in the registry, so an unresolved one
			// renders as `diagnostics.fix.<something>` and reads as gibberish to
			// the operator who most needs it.
			cy.get('[data-cy="diag-fix"]')
				.first()
				.invoke('text')
				.should('not.match', /diagnostics\.fix\./);
		});
	});

	it('an unhealthy row offers a way to fix it', () => {
		// Conditional on purpose. A clean deployment has no issues, and a spec
		// that demanded one would fail for the best possible reason. What must
		// hold is the implication: if something is wrong, the operator is
		// offered the fix rather than left to read a status word.
		cy.get('body').then(($body) => {
			const unhealthy = $body.find('[data-cy="diag-row"]').filter(
				(_, el) => (el.getAttribute('data-status') ?? 'ok') !== 'ok'
			);
			if (unhealthy.length === 0) {
				cy.log('no unhealthy rows on this deployment, so nothing should offer a fix');
				return;
			}
			cy.get('[data-cy="diag-issues"]').should('exist');
			cy.get('[data-cy="diag-fix"]').should('have.length.at.least', 1);
		});
	});
});
