// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL: code typed into a fenced block in the composer is readable.
// startr.style colours `code` with var(--background) and `pre` #d0d0d0, near white
// on the fence's gray-50 block, so the text all but vanished (fixed 2026-11-05).
// The judge is the WCAG contrast ratio of the computed colours, not a class name.

// Tailwind 4 computes colours as oklch(), so each one goes through a canvas
// to come back as sRGB bytes; alpha 0 means no background of its own.
const rgba = (doc: Document, css: string) => {
	const ctx = doc.createElement('canvas').getContext('2d') as CanvasRenderingContext2D;
	ctx.fillStyle = css;
	ctx.fillRect(0, 0, 1, 1);
	return Array.from(ctx.getImageData(0, 0, 1, 1).data);
};

const luminance = ([r, g, b]: number[]) => {
	const [lr, lg, lb] = [r, g, b].map((v) => {
		const c = v / 255;
		return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
	});
	return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
};

const contrast = (a: number[], b: number[]) => {
	const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
	return (hi + 0.05) / (lo + 0.05);
};

describe('composer code fence', () => {
	it('shows fenced code at a readable contrast', () => {
		cy.request({
			method: 'POST',
			url: '/api/v1/auths/signin',
			body: { email: 'admin@example.com', password: 'password' }
		}).then((login) => {
			const token = login.body.token;
			cy.request('/api/config').then((cfg) => {
				const version = cfg.body.version;
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: { Authorization: `Bearer ${token}` },
					body: { ui: { version, setupCompleted: true, workingAlone: true } }
				});
				cy.visit('/', {
					onBeforeLoad(win) {
						win.localStorage.setItem('token', token);
						win.localStorage.setItem('version', version);
					}
				});
			});
		});

		// The composer takes text once the page has settled; prove it first.
		cy.get('#chat-input', { timeout: 30000 }).click().type('ready');
		cy.get('#chat-input').should('contain.text', 'ready');
		// Open the fence through the editor itself. Typed backticks and a space
		// open one in a person's browser, but under Cypress the input rule leaves
		// an empty paragraph; this spec judges the colours, not the input rule.
		cy.get('#chat-input').then(($el) => {
			const editor = ($el[0] as any).editor;
			expect(editor, 'the tiptap editor on the composer').to.exist;
			editor.chain().focus().clearContent().setCodeBlock().insertContent('hello fence').run();
		});
		cy.get('#chat-input pre code')
			.should('contain.text', 'hello fence')
			.then(($code) => {
				const code = $code[0];
				const doc = code.ownerDocument;
				const view = doc.defaultView as Window;
				const pre = code.closest('pre') as HTMLElement;
				const text = rgba(doc, view.getComputedStyle(code).color);
				const ground = [code, pre]
					.map((el) => rgba(doc, view.getComputedStyle(el).backgroundColor))
					.find((c) => c[3] > 0) as number[];
				expect(contrast(text, ground), `${text} on ${ground}`).to.be.greaterThan(4.5);
			});
	});
});
