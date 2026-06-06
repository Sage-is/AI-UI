import { WEBUI_API_BASE_URL } from '$lib/constants';

async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		const res = await fetch(url, {
			method,
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			...(body && { body: JSON.stringify(body) })
		});

		if (!res.ok) {
			const responseText = await res.text();
			try {
				const errorJson = JSON.parse(responseText);
				throw errorJson;
			} catch (parseError) {
				if (parseError instanceof SyntaxError) {
					throw new Error(`Server error for ${context}: ${res.status}`);
				}
				throw parseError;
			}
		}

		const responseText = await res.text();
		try {
			return JSON.parse(responseText);
		} catch (parseError) {
			throw new Error(`Invalid JSON response for ${context}`);
		}
	} catch (err: any) {
		throw err.detail || err.message || err;
	}
}

export const getDiagnosticsHealth = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/diagnostics/health`, token, 'GET', null, 'getDiagnosticsHealth');

export const probeEndpoint = async (token: string, url: string, capability: string) =>
	api(
		`${WEBUI_API_BASE_URL}/diagnostics/probe`,
		token,
		'POST',
		{ url, capability },
		'probeEndpoint'
	);
