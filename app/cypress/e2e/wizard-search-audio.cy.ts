// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { openSurface } from '../support/surfaces';

// AI engine components — guard-rail for the one wizard panel that grafts.
//
// This panel used to graft `mock-embedding` and report "Document search is
// ready". The mock seeds its vectors from a sha256 of the input text, so uploads
// succeeded, queries returned results, and the results were noise — every
// surface reporting success while retrieval was meaningless. Both
// implementations now graft the in-housed cultivars instead, which is why this
// spec asserts what ended up ROOTED rather than that a button was clicked.
//
// Whisper is the component exercised here, because it grafts on its own.
// Embedding is a chain: `minilm-onnx-inhoused` refuses to start without
// chromadb, onnxruntime and numpy, which ride the vector-chroma overlay. That
// full chain is a multi-minute graft, and `sprigs-panel.cy.ts` already drives
// vector-chroma end to end — repeating it here would add several minutes per run
// for no signal this spec does not already get.

const auth = () => cy.window().then((win) => win.localStorage.getItem('token'));

const sprigState = (name: string) =>
	auth().then((token) =>
		cy
			.request({
				url: '/api/v1/retrieval/sprigs/catalog',
				headers: { Authorization: `Bearer ${token}` }
			})
			// State lives under `grafted`, not under `catalog` — the catalog is the
			// declaration and `grafted` is what is actually running. Reading the
			// wrong one returns undefined for everything, which looks like a clean
			// instance rather than a bad query.
			.then((res) => res.body?.grafted?.[name]?.state ?? null)
	);

const modelStatus = () =>
	auth().then((token) =>
		cy
			.request({
				url: '/api/v1/retrieval/models/status',
				headers: { Authorization: `Bearer ${token}` }
			})
			.then((res) => res.body?.models ?? {})
	);

/** Poll until the cultivar is running. Grafts pull an OCI artifact first. */
const expectRooted = (name: string, attempt = 0) => {
	sprigState(name).then((state) => {
		if (state === 'rooted' || state === 'delivered') return;
		if (attempt >= 90) {
			expect(state, `${name} is running`).to.be.oneOf(['rooted', 'delivered']);
			return;
		}
		cy.wait(2000);
		expectRooted(name, attempt + 1);
	});
};

describe('Setup wizard: AI engine components', () => {
	beforeEach(() => cy.loginAdmin());

	it('offers a control for each component', () => {
		openSurface('wizardSearchAudio');
		cy.get('[data-cy="search-audio-embedding"]').should('exist');
		cy.get('[data-cy="search-audio-whisper"]').should('exist');
		cy.get('[data-cy="search-audio-graft"]').should('exist');
		cy.get('[data-cy="search-audio-download"]').should('exist');
	});

	it('reflects the install status the server reports', () => {
		modelStatus().then((models: Record<string, string>) => {
			openSurface('wizardSearchAudio');
			cy.get('[data-cy="search-audio-panel"]')
				.should('have.attr', 'data-embedding-status', models.embedding ?? 'pending')
				.and('have.attr', 'data-whisper-status', models.whisper ?? 'pending');
		});
	});

	// The assertion the mock made impossible to write honestly: after grafting,
	// the thing that is running is the real cultivar, named.
	it('grafts the in-housed speech-to-text cultivar, not a mock', () => {
		openSurface('wizardSearchAudio');
		cy.get('[data-cy="search-audio-embedding"]').uncheck({ force: true });
		cy.get('[data-cy="search-audio-whisper"]').check({ force: true });
		cy.get('[data-cy="search-audio-graft"]').click();
		expectRooted('whisper-base-ggml');
		// And nothing grafted the mock on our behalf.
		sprigState('mock-embedding').should('not.eq', 'rooted');
	});
});
