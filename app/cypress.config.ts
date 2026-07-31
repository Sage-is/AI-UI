import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		baseUrl: 'http://localhost:8080',
		// Top-level specs only. Subdir suites are opt-in: cypress/e2e/upstream/
		// (inherited suites needing an Ollama backend) and cypress/e2e/heavy/
		// (big cultivar grafts — `make e2e_heavy`). NOTE: `--spec` cannot reach
		// them (Cypress intersects it with specPattern); the runner overrides
		// the pattern instead: SPEC='cypress/e2e/heavy/*.cy.ts' → --config
		// specPattern=... (see scripts/e2e/run-cypress.sh).
		specPattern: 'cypress/e2e/*.cy.{js,jsx,ts,tsx}',
		// Grafts pull artifacts and flip UI state asynchronously; one retry
		// absorbs timing flakes without hiding real regressions.
		retries: { runMode: 1, openMode: 0 },
		// NOT set here on purpose: `experimentalMemoryManagement` and
		// `numTestsKeptInMemory`. On 2026-07-31 a run failed its last three specs
		// with "Electron Renderer process just crashed" and no assertion, and
		// Cypress's own advice for that message is exactly those two options. They
		// were tried and changed NOTHING — the next run failed at the identical
		// spec, identical test, identical counts. Deterministic is the tell: a
		// memory ceiling wanders, and this did not. The Docker VM disk was 100%
		// full, so the renderer could not write video or screenshots; reclaiming
		// 17 GB fixed it. Check `docker run --rm --entrypoint sh alpine -c 'df -h /'`
		// before believing the message.
		// Desktop layout: below the desktop breakpoint the sidebar (and its
		// #chat-search login anchor) is not rendered at all.
		viewportWidth: 1440,
		viewportHeight: 900,
		setupNodeEvents(on) {
			on('before:browser:launch', (browser, launchOptions) => {
				if (browser.family === 'firefox') {
					// Inside the runner container Firefox cannot get its full
					// sandbox (root user; userns depends on the docker seccomp
					// profile) and shows the "security features may offer less
					// protection" banner. The runner passes --cap-add=SYS_ADMIN
					// to restore userns sandboxing where the kernel allows; this
					// pref acknowledges the residual, disposable-test-browser
					// risk instead of leaving a banner over the UI under test.
					launchOptions.preferences['security.sandbox.warn_unprivileged_namespaces'] =
						false;
				}
				return launchOptions;
			});
		}
	},
	video: true
});
