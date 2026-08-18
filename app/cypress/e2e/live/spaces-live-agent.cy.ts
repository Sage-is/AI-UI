// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../../support/index.d.ts" />

// Live-agent Spaces e2e: a member @mentions a real pull-bot agent and an
// actual model reply lands in the space. Requires BOT_URL/BOT_KEY env (an
// OpenAI-compatible endpoint hosting the pullbot.Sage-Agent model); without
// them the whole spec skips cleanly. Connection registration happens in
// before() via the openai config surface — the RESTORED_CONFIG poka-yoke
// auto-restores it, so the key never persists past the run.
import { adminUser } from '../../support/e2e';

const BOT_URL: string | undefined = Cypress.env('BOT_URL');
const BOT_KEY: string | undefined = Cypress.env('BOT_KEY');

const memberUser = {
	name: 'Space Member',
	email: 'space-member@sage.is',
	password: 'space-member-pw-123'
};

const SPACE_NAME = 'e2e-space';
const AGENT_MODEL_ID = 'pullbot.Sage-Agent';
const AGENT_MENTION = '@Sage-Agent what is 2 plus 2';

const describeLive = BOT_URL && BOT_KEY ? describe : describe.skip;

describeLive('Shared space — live agent reply', () => {
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
			const auth = { Authorization: `Bearer ${token}` };

			// Enable Spaces. GET returns exactly the AdminConfig field set POST
			// accepts, so post the FULL body back with ENABLE_SPACES flipped.
			// The poka-yoke RESTORED_CONFIG guard in support/e2e auto-restores
			// it — do NOT restore manually here.
			cy.request({
				method: 'GET',
				url: '/api/v1/auths/admin/config',
				headers: auth
			}).then((cfg) => {
				cy.request({
					method: 'POST',
					url: '/api/v1/auths/admin/config',
					headers: auth,
					body: { ...cfg.body, ENABLE_SPACES: true }
				});
			});

			// Register the bot as an OpenAI connection. RESTORED_CONFIG
			// 'openai' surface auto-restores — key never persists.
			cy.request({
				method: 'GET',
				url: '/openai/config',
				headers: auth
			}).then((cfg) => {
				const urls: string[] = cfg.body.OPENAI_API_BASE_URLS ?? [];
				const keys: string[] = cfg.body.OPENAI_API_KEYS ?? [];
				const configs: Record<string, unknown> = cfg.body.OPENAI_API_CONFIGS ?? {};
				let idx = urls.indexOf(BOT_URL as string);
				if (idx === -1) {
					urls.push(BOT_URL as string);
					keys.push(BOT_KEY as string);
					idx = urls.length - 1;
				} else {
					keys[idx] = BOT_KEY as string;
				}
				configs[String(idx)] = {
					enable: true,
					prefix_id: 'pullbot',
					tags: [],
					model_ids: [],
					connection_type: 'external'
				};
				cy.request({
					method: 'POST',
					url: '/openai/config/update',
					headers: auth,
					body: {
						...cfg.body,
						ENABLE_OPENAI_API: true,
						OPENAI_API_BASE_URLS: urls,
						OPENAI_API_KEYS: keys,
						OPENAI_API_CONFIGS: configs
					}
				});
			});

			// Create the member. 400 = already exists on a re-run against a warm DB.
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/add',
				headers: auth,
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
						headers: auth
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
				// connect — room membership is computed at join. The agent is
				// attached to the space in data.agents.
				cy.request({
					method: 'POST',
					url: '/api/v1/spaces/create',
					headers: auth,
					body: {
						name: SPACE_NAME,
						description: '',
						data: {
							agents: [
								{
									model_id: AGENT_MODEL_ID,
									name: 'Sage-Agent',
									profile_image_url: '/static/icons/favicon.png'
								}
							]
						},
						access_control: {
							read: { user_ids: [memberId], group_ids: [] },
							write: { user_ids: [memberId], group_ids: [] }
						}
					}
				}).then((space) => {
					expect(space.status, 'space create').to.eq(200);
					spaceId = space.body.id;
				});
			});
		});
	});

	it('member @mentions the agent and an agent reply arrives', () => {
		cy.login(memberUser.email, memberUser.password);
		cy.visit('/space/' + spaceId);
		// Type the mention LITERALLY — never pick from the dropdown
		// (#commands-container); the space agent router matches the text.
		cy.get('#space-container .ProseMirror', { timeout: 20000 })
			.click()
			.type(AGENT_MENTION);
		cy.get('#send-message-button').click();
		// Space.svelte does NO optimistic add — a render proves socket delivery.
		cy.get('#messages-container')
			.contains(AGENT_MENTION, { timeout: 15000 })
			.should('exist');

		// Poll the messages API for the agent's reply. Recursive cy.request
		// poll: 3s interval, 60s cap. Extra messages are fine — we only care
		// that SOME message is an agent reply from our model.
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			body: { email: memberUser.email, password: memberUser.password }
		}).then((login) => {
			expect(login.status, 'member signin').to.eq(200);
			const token = login.body.token;

			const pollForAgentReply = (attemptsLeft: number): Cypress.Chainable<string> => {
				return cy
					.request({
						method: 'GET',
						url: `/api/v1/spaces/${spaceId}/messages`,
						headers: { Authorization: `Bearer ${token}` }
					})
					.then((res) => {
						expect(res.status, 'space messages').to.eq(200);
						const reply = (res.body as Array<{
							user_id: string;
							content: string;
							data?: { agent?: { model_id?: string } };
						}>).find(
							(m) =>
								m.user_id === '__agent__' &&
								m.data?.agent?.model_id === AGENT_MODEL_ID
						);
						if (reply) {
							return reply.content;
						}
						if (attemptsLeft <= 0) {
							throw new Error(
								`agent reply never arrived within 60s — no message with user_id '__agent__' and data.agent.model_id '${AGENT_MODEL_ID}'`
							);
						}
						cy.wait(3000);
						return pollForAgentReply(attemptsLeft - 1);
					});
			};

			pollForAgentReply(20).then((content) => {
				cy.get('#messages-container')
					.contains(content, { timeout: 15000 })
					.should('exist');
			});
		});
	});
});
