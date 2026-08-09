// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// The try.sage welcome page, server-rendered at `/` for anonymous visitors.
//
// Two suites, gated on how the container was started:
//
//   Flag OFF (the default harness): the routes must not exist. `/` is the SPA
//   index, and `/welcome` falls through to the SPA catch-all. This is the half
//   that protects every non-trial deploy, and it runs on `make e2e` untouched.
//
//   Flag ON  (ENABLE_TRY_SAGE=true SPEC=try-sage-welcome.cy.ts make e2e): the
//   welcome renders in the first response, and — the reason this surface moved
//   at all — the page SCROLLS on a phone. The Svelte version pinned a fixed
//   100vh layer and flex-centered its overflow off both ends, which is
//   Reviewer T's bottom-of-page cutoff. The teeth: on a 375×667 viewport the
//   footer must be reachable by scrolling, and the document must actually
//   scroll rather than clip.
const PHONE = { width: 375, height: 667 };

const trySageOn = () =>
	cy
		.request('/api/config')
		.then((res) => Boolean(res.body?.features?.enable_try_sage));

describe('try.sage welcome surface', () => {
	it('flag off: `/` stays the SPA and the welcome route does not exist', function () {
		trySageOn().then((on) => {
			if (on) this.skip();
			cy.clearCookies();
			cy.request('/').then((res) => {
				expect(res.status).to.eq(200);
				expect(res.body, 'the SPA shell, not the welcome page').to.not.contain(
					'data-cy="try-sage-welcome"'
				);
			});
			cy.request('/welcome').then((res) => {
				// The SPA catch-all answers unmatched paths with the shell.
				expect(res.body).to.not.contain('data-cy="try-sage-welcome"');
			});
		});
	});

	it('flag on: an anonymous `/` is the welcome page in the first response', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			cy.clearCookies();
			cy.request('/').then((res) => {
				expect(res.status).to.eq(200);
				expect(res.body).to.contain('data-cy="try-sage-welcome"');
				// Invite-only contract: no sign-in form, no signup escape hatch.
				expect(res.body).to.not.contain('type="password"');
			});
		});
	});

	// Social graph tags. The failure this guards against is not "the tags are
	// missing" — it is the tags being PRESENT and wrong, which nothing on the
	// page reveals: a crawler fetches og:image, gets a 404, and renders a bare
	// card. Nobody sees that until a link is already pasted somewhere public.
	//
	// The assertion is written as an invariant that holds in BOTH config
	// branches, because `WEBUI_URL` is optional and the template omits the whole
	// block when it is unset (a share card pointing at localhost is worse than
	// no share card). Either there are no tags, or every URL in them is
	// absolute AND og:image really resolves to an image.
	it('flag on: social tags are absent or absolutely correct, never half-right', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			cy.clearCookies();
			cy.request('/').then((res) => {
				const html: string = res.body;
				const og = [...html.matchAll(/<meta property="og:([\w:]+)" content="([^"]*)"/g)];
				const tw = [...html.matchAll(/<meta name="twitter:([\w:]+)" content="([^"]*)"/g)];

				// The description is unconditional — it does not need a base URL.
				expect(html, 'description is always emitted').to.match(
					/<meta name="description" content="[^"]+"/
				);

				if (og.length === 0) {
					// WEBUI_URL unset. Nothing may be half-emitted.
					expect(tw, 'no twitter tags without og tags').to.have.length(0);
					expect(html).to.not.contain('rel="canonical"');
					return;
				}

				const byName = Object.fromEntries(og.map((m) => [m[1], m[2]]));
				expect(byName, 'og:image is declared').to.have.property('image');
				expect(byName.type).to.eq('website');
				expect(
					tw.find((m) => m[1] === 'card')?.[2],
					'a 1200x630 card needs summary_large_image, not summary'
				).to.eq('summary_large_image');

				// Every URL-bearing tag must be absolute. A relative og:image is
				// the single most common way this ships broken.
				for (const key of ['url', 'image']) {
					expect(byName[key], `og:${key} is absolute`).to.match(/^https?:\/\//);
				}

				// The teeth: fetch what we told the crawler to fetch.
				cy.request(byName.image).then((img) => {
					expect(img.status, 'og:image resolves').to.eq(200);
					expect(
						img.headers['content-type'] as string,
						'og:image is an image'
					).to.match(/^image\//);
				});

				// Declared dimensions must match the card the crawler crops to.
				expect(byName['image:width']).to.eq('1200');
				expect(byName['image:height']).to.eq('630');
			});
		});
	});

	it('flag off: the SPA shell stays unbranded', function () {
		trySageOn().then((on) => {
			if (on) this.skip();
			// Scope decision, 2026-08-03: social tags live on the server-rendered
			// page and NOT in `app/src/app.html`, which is one file serving every
			// deployment. A self-hosted instance must not advertise itself as
			// Sage.is when someone pastes its URL.
			cy.request('/').then((res) => {
				expect(res.body, 'no og tags in the shared SPA shell').to.not.contain(
					'property="og:'
				);
			});
		});
	});

	it('flag on: the page scrolls on a phone and the footer is reachable', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			cy.clearCookies();
			cy.viewport(PHONE.width, PHONE.height);
			cy.visit('/');
			cy.get('[data-cy="try-sage-welcome"]').should('exist');

			// The cutoff's exact shape: content below the first screen must be
			// reachable. Scroll to the bottom and the footer must be visible —
			// under the old fixed-layer layout it sat behind the browser chrome
			// or off the unreachable end of a centered overflow.
			cy.scrollTo('bottom');
			cy.get('[data-cy="try-sage-footer"]').should('be.visible');

			// And the document really scrolled — the page is taller than the
			// viewport on a phone, so a scrollTop of 0 after scrollTo means a
			// clipped layout swallowed the scroll.
			cy.window().then((win) => {
				const doc = win.document.scrollingElement as Element;
				expect(doc.scrollHeight, 'content taller than one phone screen').to.be.greaterThan(
					PHONE.height
				);
				expect(doc.scrollTop, 'the scroll actually happened').to.be.greaterThan(0);
			});
		});
	});

	// The chrome, and its MOTION. Both were dropped in the port and neither was
	// caught, because the spec asserted structure: the page rendered, the
	// hooks existed, and the suite was green while a human saw a static page
	// with no backdrop. Real waits, not a stubbed clock — this repo has already
	// shipped one animation that a driver reported working and a person could
	// see was broken.
	it('flag on: the backdrop and the heading both rotate', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			cy.clearCookies();
			cy.visit('/welcome');

			// Every backdrop image is present, exactly one showing.
			cy.get('[data-slide]').should('have.length', 4);
			cy.get('[data-slide].on').should('have.length', 1);
			// All three phrases are IN the document — the first response is the
			// whole page, so a reader who never runs the script still gets one.
			cy.get('[data-marquee-item]').should('have.length', 3);
			cy.get('[data-marquee-item].on').should('have.length', 1);

			cy.get('[data-marquee-item].on')
				.invoke('text')
				.then((firstPhrase) => {
					cy.get('[data-slide].on')
						.invoke('attr', 'style')
						.then((firstImage) => {
							// One tick of the five-second cycle, plus margin.
							cy.wait(6000);
							cy.get('[data-marquee-item].on')
								.invoke('text')
								.should('not.eq', firstPhrase);
							cy.get('[data-slide].on')
								.invoke('attr', 'style')
								.should('not.eq', firstImage);
						});
				});
		});
	});

	it('flag on: bare /auth goes to the welcome; an explicit ?next= gets the form', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			cy.clearCookies();
			// The sign-in intent the pages auth bridge emits: form, not welcome.
			cy.visit('/auth?next=/pages');
			cy.get('input[autocomplete="email"]').should('be.visible');
			// A lost anonymous visitor: no form exists for them.
			cy.visit('/auth');
			cy.location('pathname').should('eq', '/welcome');
			cy.get('[data-cy="try-sage-welcome"]').should('exist');
		});
	});

	it('flag on: a signed-in reader still gets the SPA at `/`', function () {
		trySageOn().then((on) => {
			if (!on) this.skip();
			// API sign-in, not cy.loginAdmin(): that command drives the /auth
			// FORM, and trial mode redirects an anonymous /auth to `/` — the
			// form does not exist, which is the invite-only contract working.
			// The signin response sets the `token` cookie; the jar carries it.
			cy.clearCookies();
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/signup',
				body: { name: 'admin', email: 'admin@example.com', password: 'password' },
				failOnStatusCode: false // 200 created, 400/403 already there
			});
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/signin',
				body: { email: 'admin@example.com', password: 'password' }
			});
			cy.getCookie('token').should('exist');
			cy.request('/').then((res) => {
				expect(res.status).to.eq(200);
				expect(res.body, 'the SPA shell for the signed-in').to.not.contain(
					'data-cy="try-sage-welcome"'
				);
			});
		});
	});
});
