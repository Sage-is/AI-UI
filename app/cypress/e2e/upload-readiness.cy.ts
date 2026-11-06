// An upload is refused at once when the box cannot read documents (card "An
// upload starts before anyone checks that the box can read it", 2026-11-03).
// The readiness answer is intercepted, so the spec runs on any box; the knowledge
// page and the chat composer share the check (lib/utils/documentReading.ts).

const NOT_READY = { ready: false, missing: ['document loaders'] };

// A fresh knowledge base, open and loaded: a file picked before the page has
// its knowledge base hits a null on any version, which proves nothing here.
const knowledgePage = () => {
	const name = `readiness-${Date.now()}`;
	return cy
		.request('POST', '/api/v1/auths/signin', {
			email: Cypress.env('ADMIN_EMAIL') || 'admin@example.com',
			password: Cypress.env('ADMIN_PASSWORD') || 'password'
		})
		.then(({ body: { token } }) =>
			cy
				.request({
					method: 'POST',
					url: '/api/v1/knowledge/create',
					headers: { Authorization: `Bearer ${token}` },
					body: { name, description: 'spec', access_control: null }
				})
				.then(({ body: { id } }) => {
					cy.intercept('GET', `/api/v1/knowledge/${id}`).as('knowledge');
					cy.visit(`/workshop/knowledge/${id}`, {
						onBeforeLoad: (win) => win.localStorage.setItem('token', token)
					});
					cy.wait('@knowledge');
				})
		);
};

const attach = () =>
	cy
		.get('#files-input')
		.selectFile(
			{ contents: Cypress.Buffer.from('hello'), fileName: 'note.txt', mimeType: 'text/plain' },
			{ force: true }
		);

describe('Upload readiness', () => {
	let upload: sinon.SinonSpy;

	beforeEach(() => {
		upload = cy.spy().as('upload');
		cy.loginAdmin();
		// The upload is answered here, so the spy firing proves the request left; the
		// page handles the stub's error and the spec stores nothing.
		cy.intercept({ method: 'POST', pathname: '/api/v1/files/' }, (req) => {
			upload();
			req.reply({ statusCode: 500, body: { detail: 'spec stub' } });
		});
	});

	it('refuses an upload at once and offers an admin the fix', () => {
		cy.intercept('GET', '/api/v1/retrieval/readiness', NOT_READY).as('readiness');
		knowledgePage();
		attach();
		cy.wait('@readiness');
		cy.contains('This box cannot read documents yet.').should('be.visible');
		cy.contains('button', 'Turn on document reading').should('be.visible');
		cy.get('@upload').should('not.have.been.called');
	});

	it("runs the wizard's install from the button and says when it is done", () => {
		let calls = 0;
		cy.intercept('GET', '/api/v1/retrieval/readiness', (req) =>
			req.reply(calls++ === 0 ? NOT_READY : { ready: true, missing: [] })
		);
		cy.intercept('POST', '/api/v1/retrieval/models/download', { status: true }).as('install');
		cy.intercept('GET', '/api/v1/retrieval/models/status', { status: true, models: {} });
		knowledgePage();
		attach();
		cy.contains('button', 'Turn on document reading').click();
		cy.wait('@install')
			.its('request.body')
			.should('deep.equal', { components: ['embedding'] });
		cy.contains('Document reading is on. Add your file again.', { timeout: 10000 }).should(
			'be.visible'
		);
	});

	it('tells a member whom to ask', () => {
		cy.intercept('GET', '/api/v1/retrieval/readiness', NOT_READY);
		cy.intercept('GET', '/api/v1/auths/', (req) =>
			req.continue((res) => {
				res.body.role = 'user';
			})
		);
		knowledgePage();
		attach();
		cy.contains('Ask your admin to turn on document reading.').should('be.visible');
		cy.contains('button', 'Turn on document reading').should('not.exist');
	});

	it('lets the upload through when the box can read', () => {
		cy.intercept('GET', '/api/v1/retrieval/readiness', { ready: true, missing: [] });
		knowledgePage();
		attach();
		cy.get('@upload').should('have.been.called');
	});
});
