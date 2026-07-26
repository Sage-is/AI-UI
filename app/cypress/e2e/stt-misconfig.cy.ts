// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// GUARD-RAIL: a misconfigured external STT engine (here: pointed at an
// unreachable local server) must fail with a CLEAN, single message — not the
// old triple-wrapped "400: [ERROR: 500: Error transcribing chunk: ...]" stack
// that buried the real reason. Seeds the admin, sets STT_ENGINE=openai at a
// dead URL, POSTs a tiny WAV, and asserts the clean 502.

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
	dv.setUint16(20, 1, true);
	dv.setUint16(22, 1, true);
	dv.setUint32(24, rate, true);
	dv.setUint32(28, rate * bytesPerSample, true);
	dv.setUint16(32, bytesPerSample, true);
	dv.setUint16(34, 16, true);
	ws(36, 'data');
	dv.setUint32(40, dataSize, true);
	return new Blob([buf], { type: 'audio/wav' });
}

describe('STT misconfigured external engine — clean error, not a triple-wrapped stack', () => {
	it('returns a single clean 502 when the STT server is unreachable', () => {
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
			const auth = { Authorization: `Bearer ${token}` };

			cy.request('/api/config').then((cfg) => {
				const version = cfg.body.version;
				cy.request({
					method: 'POST',
					url: '/api/v1/users/user/settings/update',
					headers: auth,
					body: { ui: { version, setupCompleted: true, workingAlone: true } }
				});

				// Point STT at an unreachable local "openai" server.
				cy.request({ url: '/api/v1/audio/config', headers: auth }).then((conf) => {
					const body = conf.body;
					body.stt.ENGINE = 'openai';
					body.stt.OPENAI_API_BASE_URL = 'http://127.0.0.1:59999/v1';
					body.stt.OPENAI_API_KEY = 'x';
					cy.request({
						method: 'POST',
						url: '/api/v1/audio/config/update',
						headers: auth,
						body
					}).then((upd) => {
						expect(upd.status, 'audio config saved').to.eq(200);

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
									headers: auth,
									body: fd
								})
								.then((res: Response) =>
									res.json().then((b: any) => ({ status: res.status, body: b }))
								);
						}).then(({ status, body }) => {
							const detail = JSON.stringify(body?.detail ?? body);
							expect(status, 'clean upstream-error status').to.eq(502);
							expect(detail, 'no triple-wrapped chunk stack').to.not.match(
								/Error transcribing chunk/i
							);
							expect(detail, 'no nested [ERROR: ...] wrapper').to.not.contain('[ERROR:');
						});
					});
				});
			});
		});
	});
});
