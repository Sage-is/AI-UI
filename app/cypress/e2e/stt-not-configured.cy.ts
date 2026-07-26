// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL: when no STT engine is configured (default STT_ENGINE=="") and this
// build ships no in-process faster-whisper, the transcription endpoint must
// return an ACTIONABLE message telling the admin to graft the Whisper (STT)
// Sprig™ — not a raw "No module named 'faster_whisper'" buried in a triple-
// wrapped 500/400 stack. Seeds the admin, POSTs a tiny valid WAV, and asserts
// the helpful 501. (Self-seeds + marks setup complete per the e2e-harness memo.)

// A minimal, valid 16 kHz mono 16-bit PCM WAV (silence) — small enough that the
// audio pipeline passes it straight through to the STT engine selection.
function makeWav(samples = 3200, rate = 16000): Blob {
	const bytesPerSample = 2;
	const dataSize = samples * bytesPerSample;
	const buf = new ArrayBuffer(44 + dataSize);
	const dv = new DataView(buf);
	const ws = (o: number, s: string) => {
		for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i));
	};
	ws(0, 'RIFF');
	dv.setUint32(4, 36 + dataSize, true);
	ws(8, 'WAVE');
	ws(12, 'fmt ');
	dv.setUint32(16, 16, true);
	dv.setUint16(20, 1, true); // PCM
	dv.setUint16(22, 1, true); // mono
	dv.setUint32(24, rate, true);
	dv.setUint32(28, rate * bytesPerSample, true);
	dv.setUint16(32, bytesPerSample, true);
	dv.setUint16(34, 16, true);
	ws(36, 'data');
	dv.setUint32(40, dataSize, true);
	return new Blob([buf], { type: 'audio/wav' });
}

describe('STT not configured — helpful graft message, not a raw ImportError', () => {
	it('returns an actionable "graft the Whisper Sprig" error for the mic flow', () => {
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
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: { Authorization: `Bearer ${token}` },
					body: { ui: { version, setupCompleted: true, workingAlone: true } }
				});

				// Same-origin fetch so multipart upload behaves like the mic flow.
				cy.visit('/', {
					onBeforeLoad(win) {
						win.localStorage.setItem('token', token);
						win.localStorage.setItem('version', version);
					}
				});
				cy.window().then((win) => {
					const fd = new win.FormData();
					fd.append('file', new win.File([makeWav()], 'guard.wav', { type: 'audio/wav' }));
					return win
						.fetch('/api/v1/audio/transcriptions', {
							method: 'POST',
							headers: { Authorization: `Bearer ${token}` },
							body: fd
						})
						.then((res: Response) => res.json().then((body: any) => ({ status: res.status, body })));
				}).then(({ status, body }) => {
					const detail = JSON.stringify(body?.detail ?? body);
					expect(status, 'STT-not-configured status').to.eq(501);
					expect(detail, 'names the Sprig to graft').to.match(/Sprig/i);
					expect(detail, 'points at Admin → Sprigs').to.match(/Admin\s*→\s*Sprigs/);
					expect(detail, 'no raw module error leaks through').to.not.match(/faster_whisper|No module/i);
				});
			});
		});
	});
});
