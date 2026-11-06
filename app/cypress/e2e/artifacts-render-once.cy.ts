// An HTML reply renders once in the artifact panel (2026-11-03). The panel took
// every ```html block, then read the whole reply again for bare <html>, <style>
// and <script> tags, the ones inside the block included, and wrapped a full
// document in a second one. The page came out doubled under a malformed shell.
// Each case seeds a chat whose reply holds the HTML, opens it, and reads the
// iframe's srcdoc.

const count = (text: string, re: RegExp) => (text.match(re) || []).length;

const FULL_DOCUMENT = [
	'Here is your page:',
	'',
	'```html',
	'<!DOCTYPE html>',
	'<html lang="en">',
	'<head><style>h1 { color: red; }</style></head>',
	'<body><h1 id="t">Hello</h1><script>document.title = "ran";</script></body>',
	'</html>',
	'```'
].join('\n');

const BARE_HTML = ['```html', '<html>', '<body><p>Only once</p></body>', '</html>', '```'].join(
	'\n'
);

const FRAGMENT_AND_CSS = [
	'```html',
	'<p id="x">fragment</p>',
	'```',
	'',
	'```css',
	'p { color: blue; }',
	'```'
].join('\n');

function openArtifact(reply: string) {
	cy.request({
		method: 'POST',
		url: '/api/v1/auths/signup',
		failOnStatusCode: false,
		body: { name: 'Admin User', email: 'admin@example.com', password: 'password' }
	});
	cy.request('POST', '/api/v1/auths/signin', {
		email: Cypress.env('ADMIN_EMAIL') || 'admin@example.com',
		password: Cypress.env('ADMIN_PASSWORD') || 'password'
	}).then(({ body: { token } }) => {
		cy.request('/api/config').then(({ body: { version } }) => {
			const headers = { Authorization: `Bearer ${token}` };
			cy.request({
				method: 'POST',
				url: '/api/v1/users/user/settings/update',
				headers,
				body: { ui: { version, setupCompleted: true, workingAlone: true, showChangelog: false } }
			});
			const user = {
				id: 'u-1',
				parentId: null,
				childrenIds: ['a-1'],
				role: 'user',
				content: 'a page',
				timestamp: 1
			};
			const answer = {
				id: 'a-1',
				parentId: 'u-1',
				childrenIds: [],
				role: 'assistant',
				content: reply,
				done: true,
				timestamp: 2
			};
			const chat = {
				title: 'artifact-once',
				models: ['guard'],
				history: { messages: { 'u-1': user, 'a-1': answer }, currentId: 'a-1' },
				messages: [user, answer]
			};
			cy.request({ method: 'POST', url: '/api/v1/chats/new', headers, body: { chat } }).then(
				({ body: { id } }) => {
					cy.visit(`/c/${id}`, {
						onBeforeLoad: (win) => {
							win.localStorage.setItem('token', token);
							win.localStorage.setItem('version', version);
						}
					});
				}
			);
		});
	});
	return cy.get('iframe[title="Content"]', { timeout: 30000 }).invoke('attr', 'srcdoc');
}

describe('Artifact panel renders an HTML reply once', () => {
	beforeEach(() => cy.viewport(1400, 900)); // the panel opens on its own only off mobile

	it('shows a full document as it is, with its style and script once', () => {
		openArtifact(FULL_DOCUMENT).then((doc) => {
			expect(count(doc, /<html/gi), '<html> tags').to.eq(1);
			expect(count(doc, /color: red/g), 'its style').to.eq(1);
			expect(count(doc, /document\.title = "ran"/g), 'its script').to.eq(1);
		});
	});

	it('takes a bare <html> inside a code block once', () => {
		openArtifact(BARE_HTML).then((doc) => {
			expect(count(doc, /Only once/g), 'the page body').to.eq(1);
		});
	});

	it('still wraps a fragment with its separate css block (control)', () => {
		openArtifact(FRAGMENT_AND_CSS).then((doc) => {
			expect(count(doc, /<html/gi), 'one wrapper').to.eq(1);
			expect(count(doc, /fragment/g), 'the fragment').to.eq(1);
			expect(count(doc, /color: blue/g), 'its css').to.eq(1);
		});
	});
});
