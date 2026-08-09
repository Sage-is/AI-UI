// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL for the markdown-render lazy-load (katex / highlight.js / mermaid /
// codemirror deferred out of the eager chunks). Its job is render-CORRECTNESS:
// prove that deferring these libraries did not break how math, code, and
// diagrams render. It seeds a chat with fixed markdown (no live model needed) and
// asserts the heavy renderers still mount:
//   - inline + block math  -> KaTeX output (.katex)
//   - a ```python fence     -> a code block (.copy-code-button)
//   - a ```mermaid fence    -> the mermaid element (pre.mermaid)
// A plain-text chat pulls none of them (negative control).
//
// This passes both BEFORE and AFTER the lazy-load refactor — that is the point:
// it fences the regression risk. The perf WIN (bytes moved off the eager chunk)
// is measured separately by perf-measure.cy.ts, not gated here.
//
// Self-seeds the admin and marks setup complete so the app isn't blocked — see
// the e2e-harness memo (signup hard-closes after the first admin; global
// before-hooks don't reliably yield a sign-in-able admin).

const MATH_CODE = [
	'Inline math $x^2 + y^2 = z^2$ in a sentence.',
	'',
	'Block math:',
	'',
	'$$E = mc^2$$',
	'',
	'A code fence:',
	'',
	'```python',
	'print("hello, lazy world")',
	'```',
	'',
	'A diagram:',
	'',
	'```mermaid',
	'graph TD; A-->B;',
	'```',
	''
].join('\n');

const PLAIN = 'Just plain prose. No math, no code, no diagrams. Nothing heavy to render here.';

function seedAdminAndVisit(assistantContent: string, assert: () => void) {
	// Idempotent admin bootstrap.
	cy.request({
		method: 'POST',
		url: '/api/v1/auths/signup',
		failOnStatusCode: false,
		body: { name: 'Admin User', email: 'admin@example.com', password: 'password' }
	});
	cy.request({
		method: 'POST',
		url: '/api/v1/auths/signin',
		failOnStatusCode: false,
		body: { email: 'admin@example.com', password: 'password' }
	}).then((login) => {
		expect(login.status, 'admin signin').to.eq(200);
		const token = login.body.token;

		cy.request('/api/config').then((cfg) => {
			const version = cfg.body.version;

			// Don't let the setup wizard block the render.
			cy.request({
				method: 'POST',
				url: '/api/v1/users/user/settings/update',
				headers: { Authorization: `Bearer ${token}` },
				body: {
					ui: { version, setupCompleted: true, workingAlone: true, showChangelog: false }
				}
			});

			const userMsg = {
				id: 'u-1',
				parentId: null,
				childrenIds: ['a-1'],
				role: 'user',
				content: 'render test',
				models: ['guard'],
				timestamp: 1
			};
			const asstMsg = {
				id: 'a-1',
				parentId: 'u-1',
				childrenIds: [],
				role: 'assistant',
				content: assistantContent,
				model: 'guard',
				modelName: 'guard',
				done: true,
				timestamp: 2
			};
			const chat = {
				id: '',
				title: 'render-guard',
				models: ['guard'],
				params: {},
				history: {
					messages: { 'u-1': userMsg, 'a-1': asstMsg },
					currentId: 'a-1'
				},
				messages: [userMsg, asstMsg],
				tags: [],
				timestamp: 3
			};

			cy.request({
				method: 'POST',
				url: '/api/v1/chats/new',
				headers: { Authorization: `Bearer ${token}` },
				body: { chat }
			}).then((created) => {
				expect(created.status, 'chat created').to.eq(200);
				const chatId = created.body.id;

				cy.visit(`/c/${chatId}`, {
					onBeforeLoad(win) {
						win.localStorage.setItem('token', token);
						win.localStorage.setItem('locale', 'en-US');
						win.localStorage.setItem('version', version);
					}
				});

				// NB: this fork does NOT use the upstream `.chat-assistant` wrapper
				// class on a history-loaded message. Gate on rendered content instead
				// (each assert below waits with its own timeout).
				assert();
			});
		});
	});
}

describe('markdown render lazy-load — math/code/diagram still render', () => {
	it('renders KaTeX, a code block, and a mermaid diagram from a seeded chat', () => {
		seedAdminAndVisit(MATH_CODE, () => {
			// KaTeX rendered (inline + block) — proves the lazily-loaded renderer mounted.
			cy.get('.katex', { timeout: 30000 }).should('have.length.greaterThan', 1);
			// A real code fence rendered its code-block chrome.
			cy.get('.copy-code-button', { timeout: 30000 }).should('exist');
			// The mermaid branch mounted its element (the lazy CodeBlock loaded mermaid).
			cy.get('pre.mermaid', { timeout: 30000 }).should('exist');
		});
	});

	it('renders none of the heavy renderers for a plain-text chat (control)', () => {
		seedAdminAndVisit(PLAIN, () => {
			// Wait for the assistant prose to render, then assert nothing heavy mounted.
			cy.contains('plain prose', { timeout: 30000 }).should('exist');
			cy.get('.katex').should('not.exist');
			cy.get('.copy-code-button').should('not.exist');
			cy.get('pre.mermaid').should('not.exist');
		});
	});
});
