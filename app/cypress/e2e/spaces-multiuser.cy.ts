// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// First Spaces e2e: a non-owner member uses a shared space. Covers the whole
// path — admin enables Spaces, grants read+write to a plain user at create
// time, that user posts through the real socket round-trip, and the admin sees
// the message back. Spaces are the multiuser surface of this fork, so the
// ownership/membership split is exactly what deserves a robot walk.
import { adminUser } from '../support/e2e';

const memberUser = {
	name: 'Space Member',
	email: 'space-member@sage.is',
	password: 'space-member-pw-123'
};

const SPACE_NAME = 'e2e-space';

describe('Shared space — non-owner member', () => {
	let spaceId: string;

	before(() => {
		cy.registerAdmin();

		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			failOnStatusCode: false,
			body: { email: adminUser.email, password: adminUser.password }
		}).then((login) => {
			expect(login.status, 'admin signin').to.eq(200);
			const token = login.body.token;
			const adminId = login.body.id;

			// Enable Spaces. GET returns exactly the AdminConfig field set POST
			// accepts, so post the FULL body back with ENABLE_SPACES flipped.
			// The poka-yoke RESTORED_CONFIG guard in support/e2e auto-restores
			// it — do NOT restore manually here.
			cy.request({
				method: 'GET',
				url: '/api/v1/auths/admin/config',
				headers: { Authorization: `Bearer ${token}` }
			}).then((cfg) => {
				cy.request({
					method: 'POST',
					url: '/api/v1/auths/admin/config',
					headers: { Authorization: `Bearer ${token}` },
					body: { ...cfg.body, ENABLE_SPACES: true }
				});
			});

			// Create the member. 400 = already exists on a re-run against a warm DB.
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/add',
				headers: { Authorization: `Bearer ${token}` },
				failOnStatusCode: false,
				body: { ...memberUser, role: 'user' }
			}).then((add) => {
				expect(add.status).to.be.oneOf([200, 400]);
				if (add.status === 200) {
					return add.body.id;
				}
				// Re-run: look the member up by email via the admin users list.
				return cy
					.request({
						method: 'GET',
						url: '/api/v1/users/',
						headers: { Authorization: `Bearer ${token}` }
					})
					.then((list) => {
						expect(list.status, 'users list').to.eq(200);
						const found = list.body.users.find(
							(u: { email: string }) => u.email === memberUser.email
						);
						expect(found, 'member present in user list').to.exist;
						return found.id;
					});
			}).then((memberId: string) => {
				// Grant membership AT CREATE, before the member's first socket
				// connect — room membership is computed at join. The ADMIN goes in
				// the lists too: admins bypass the access gate, but the mention
				// dropdown lists exactly access_control.read.user_ids (the
				// participants endpoint), so an unlisted admin is unmentionable.
				cy.request({
					method: 'POST',
					url: '/api/v1/spaces/create',
					headers: { Authorization: `Bearer ${token}` },
					body: {
						name: SPACE_NAME,
						description: '',
						data: {},
						access_control: {
							read: { user_ids: [adminId, memberId], group_ids: [] },
							write: { user_ids: [adminId, memberId], group_ids: [] }
						}
					}
				}).then((space) => {
					expect(space.status, 'space create').to.eq(200);
					spaceId = space.body.id;
				});
			});
		});
	});

	it('admin can open the space', () => {
		cy.loginAdmin();
		cy.visit('/space/' + spaceId);
		cy.get('#space-container', { timeout: 20000 }).should('exist');
		cy.get('#messages-container').should('exist');
	});

	it('member can open the shared space', () => {
		cy.login(memberUser.email, memberUser.password);
		cy.visit('/space/' + spaceId);
		cy.get('#space-container', { timeout: 20000 }).should('exist');
	});

	it('member posts and the message renders via the socket round-trip', () => {
		cy.login(memberUser.email, memberUser.password);
		cy.visit('/space/' + spaceId);
		cy.get('#space-container .ProseMirror', { timeout: 20000 })
			.click()
			.type('hello from the member');
		cy.get('#send-message-button').click();
		// Space.svelte does NO optimistic add — a render proves socket delivery.
		cy.get('#messages-container')
			.contains('hello from the member', { timeout: 15000 })
			.should('exist');
	});

	it('mention dropdown opens on @ and is selectable by CLICK', () => {
		cy.login(memberUser.email, memberUser.password);
		cy.visit('/space/' + spaceId);
		cy.get('#space-container .ProseMirror', { timeout: 20000 }).click().type('@');
		cy.get('#commands-container', { timeout: 10000 }).should('exist');
		// Keyboard nav is a KNOWN LIVE BUG: MessageInput.svelte queries the
		// nonexistent #mentions-container while the real id is
		// #commands-container — never arrow-key/Enter here, only click.
		cy.get('#commands-container button')
			.contains('Admin User')
			.click();
		cy.get('#space-container .ProseMirror').contains('Admin').should('exist');
	});

	it('admin sees the member message', () => {
		cy.loginAdmin();
		cy.visit('/space/' + spaceId);
		cy.get('#messages-container', { timeout: 20000 })
			.contains('hello from the member', { timeout: 15000 })
			.should('exist');
	});
});
