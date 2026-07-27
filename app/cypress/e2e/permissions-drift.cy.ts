// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL for the permission tree. The backend describes user permissions
// in TWO places: the env-derived DEFAULT_USER_PERMISSIONS table (what
// has_permission() enforces) and the Pydantic models in routers/users.py (what
// the admin panel renders). Nothing kept them in agreement.
//
// This asserts the observable contract rather than the internal tables: what
// /users/default/permissions ADVERTISES to the admin must equal what
// /users/permissions ENFORCES. A key present in one and absent from the other
// is the bug — an absent key reads as falsy, so the panel says a feature is on
// while every non-admin silently loses it.
const ADMIN = { name: 'Admin User', email: 'admin@example.com', password: 'password' };

type PermTree = Record<string, Record<string, boolean>>;

describe('permission tree — advertised vs enforced', () => {
	let advertised: PermTree;
	let enforced: PermTree;

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
			const auth = { Authorization: `Bearer ${login.body.token}` };
			cy.request({ url: '/api/v1/users/default/permissions', headers: auth }).then((res) => {
				advertised = res.body;
			});
			cy.request({ url: '/api/v1/users/permissions', headers: auth }).then((res) => {
				enforced = res.body;
			});
		});
	});

	// One-directional on purpose. Everything ADVERTISED must be ENFORCED — that
	// is the policy lie we care about, and it is the direction web_search broke.
	// The reverse is not a defect: a database upgraded from an older release
	// still carries retired keys (a v1.1.1 snapshot keeps a `workspace` group
	// from before this fork renamed it `workshop`), which nothing reads. Testing
	// equality would fail on every upgraded deployment for no reason.
	it('enforces every permission key it advertises', () => {
		const missing: string[] = [];
		Object.keys(advertised).forEach((group) => {
			Object.keys(advertised[group] ?? {}).forEach((key) => {
				if (!(key in (enforced[group] ?? {}))) {
					missing.push(`${group}.${key} advertised but not enforced`);
				}
			});
		});
		expect(missing.join('; '), 'advertised keys with no enforcement').to.eq('');
	});

	it('advertises the same values it enforces', () => {
		const drift: string[] = [];
		Object.keys(advertised).forEach((group) => {
			Object.entries(advertised[group] ?? {}).forEach(([key, value]) => {
				const actual = (enforced[group] ?? {})[key];
				if (key in (enforced[group] ?? {}) && actual !== value) {
					drift.push(`${group}.${key}: panel=${value} enforced=${actual}`);
				}
			});
		});
		expect(drift.join('; '), 'advertised/enforced value drift').to.eq('');
	});

	// Regression pin for the specific key that started this: web_search lived
	// only in the Pydantic model, so the panel showed it on while every
	// non-admin lost the button (MessageInput gates on the permission).
	it('enforces features.web_search rather than leaving it absent', () => {
		expect(enforced.features, 'features group is enforced').to.be.an('object');
		expect(enforced.features, 'features.web_search is a real enforced key').to.have.property(
			'web_search'
		);
	});
});
