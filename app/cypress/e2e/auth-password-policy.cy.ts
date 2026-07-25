// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Guard-rail (Phase Q): the 8-character password minimum must be enforced
// SERVER-side, not only in the browser. A direct API call previously bypassed
// the client check. Proven on the always-open /update/password path (this fork
// hard-closes public signup once an admin exists, so signup can't be reused).
//
// Self-seeding: the spec registers the admin itself (idempotent) rather than
// relying on the global before hook, which does not reliably leave a
// sign-in-able admin in an isolated run. See the ai-ui-e2e-harness memo.
//
// Measure-twice: against the pre-change image /update/password returns 200 (a
// short new password is accepted — the bug), so this FAILS; after the fix it
// returns 400 and PASSES. The refusal leaves the admin password unchanged, so
// it is safe to re-run.
describe('Auth — server-side password policy (Phase Q guard-rail)', () => {
	const ADMIN = { name: 'Admin User', email: 'admin@example.com', password: 'password' };

	it('rejects a too-short new password at /update/password (server-side)', () => {
		// Ensure an admin exists: 200 = created (first user), 400/403 = already there.
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signup',
			failOnStatusCode: false,
			body: { name: ADMIN.name, email: ADMIN.email, password: ADMIN.password }
		});
		// Sign in as the admin to get a bearer token.
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			failOnStatusCode: false,
			body: { email: ADMIN.email, password: ADMIN.password }
		}).then((login) => {
			expect(login.status, 'admin signin').to.eq(200);
			const token = login.body.token;
			// A new password shorter than 8 chars must be refused with 400. The
			// correct current password is supplied so the request reaches the length
			// check rather than failing auth first.
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/update/password',
				failOnStatusCode: false,
				headers: { Authorization: `Bearer ${token}` },
				body: { password: ADMIN.password, new_password: 'short7!' }
			}).then((res) => {
				expect(res.status, 'server rejects a <8-char new password').to.eq(400);
			});
		});
	});
});
