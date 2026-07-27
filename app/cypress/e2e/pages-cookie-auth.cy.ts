// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The cookie bridge — server-rendered pages authenticating without localStorage.
//
// The plan treats this as a prerequisite for every fragment phase, on the
// grounds that a server-rendered route cannot read the token the SPA keeps in
// localStorage. Measured, the backend was already most of the way there:
// get_current_user falls back to the `token` cookie and every sign-in path
// already sets it httponly. What this spec guards is the part that was
// genuinely missing — that a PAGE fails differently from an API.
//
// It asserts on HTTP status and Location, not on rendered copy, so it stays
// true when the page is redesigned.
const PAGE = '/pages/admin/sprigs';

describe('Pages: cookie auth bridge', () => {
	it('sends a signed-out visitor to sign in, not to a JSON error', () => {
		cy.clearCookies();
		cy.request({ url: PAGE, followRedirect: false, failOnStatusCode: false }).then((res) => {
			expect(res.status, 'redirect rather than 401/403').to.eq(307);
			// `next` must come back as a PATH. An absolute URL here would make the
			// sign-in page an open redirect, which is why the handler never echoes
			// anything but request.url.path.
			const location = res.headers.location as string;
			expect(location).to.eq(`/auth?next=${PAGE}`);
			expect(location, 'never an absolute URL').to.not.match(/^https?:\/\//);
		});
	});

	it('serves the page to an admin carrying only the auth cookie', () => {
		cy.loginAdmin();
		// Strip the header path entirely: no Authorization, no localStorage read.
		// If this passes, identity came from the cookie and nothing else.
		cy.getCookie('token').should('exist');
		cy.request({ url: PAGE, failOnStatusCode: false }).then((res) => {
			expect(res.status).to.eq(200);
			expect(res.body).to.contain('Sprigs');
		});
	});

	// The branch most likely to ship wrong, because it is four lines and nobody
	// clicks it: a signed-in NON-admin. It must be 403, not a redirect —
	// bouncing them to /auth would loop them straight back here, since they are
	// already signed in.
	//
	// The user is created and deleted inside this test. The harness boots one
	// container for the whole run, so a leftover account would be a state leak
	// of exactly the kind the support-file guard exists to stop; that guard
	// watches admin CONFIG, not the user table, so this cleans up after itself.
	it('refuses a signed-in non-admin with 403, not a redirect loop', () => {
		cy.loginAdmin();
		const member = { name: 'Page Auth Member', email: 'page-auth-member@example.com', password: 'password1234' };

		cy.getCookie('token').then((adminCookie) => {
			const asAdmin = { Authorization: `Bearer ${adminCookie!.value}` };
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/add',
				headers: asAdmin,
				body: { ...member, role: 'user' }
			}).then((added) => {
				const memberId = added.body.id;
				cy.clearCookies();
				cy.request({
					method: 'POST',
					url: '/api/v1/auths/signin',
					body: { email: member.email, password: member.password }
				}).then(() => {
					cy.request({ url: PAGE, followRedirect: false, failOnStatusCode: false }).then((res) => {
						expect(res.status, 'forbidden, not redirected').to.eq(403);
					});
					cy.clearCookies();
					cy.request({ method: 'DELETE', url: `/api/v1/users/${memberId}`, headers: asAdmin });
				});
			});
		});
	});

	it('the auth cookie is httponly, so a script cannot read it', () => {
		cy.loginAdmin();
		// The reason this bridge is worth having: a cookie the page can use and
		// injected script cannot. If this ever flips, the bridge stops being an
		// improvement on localStorage and becomes a second copy of the same risk.
		cy.getCookie('token').should('have.property', 'httpOnly', true);
	});
});
