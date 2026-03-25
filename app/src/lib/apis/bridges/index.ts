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

export const getBridgeConnections = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/bridges/`, token, 'GET', null, 'getBridgeConnections');

export const createBridgeConnection = async (token: string, data: object) =>
	api(`${WEBUI_API_BASE_URL}/bridges/create`, token, 'POST', data, 'createBridgeConnection');

export const getBridgeConnection = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/bridges/${id}`, token, 'GET', null, 'getBridgeConnection');

export const updateBridgeConnection = async (token: string, id: string, data: object) =>
	api(
		`${WEBUI_API_BASE_URL}/bridges/${id}/update`,
		token,
		'POST',
		data,
		'updateBridgeConnection'
	);

export const deleteBridgeConnection = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/bridges/${id}/delete`, token, 'DELETE', null, 'deleteBridgeConnection');

export const toggleBridgeConnection = async (token: string, id: string) =>
	api(
		`${WEBUI_API_BASE_URL}/bridges/${id}/toggle`,
		token,
		'POST',
		{},
		'toggleBridgeConnection'
	);

export const restartBridgeConnection = async (token: string, id: string) =>
	api(
		`${WEBUI_API_BASE_URL}/bridges/${id}/restart`,
		token,
		'POST',
		{},
		'restartBridgeConnection'
	);

export const getBridgeStatuses = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/bridges/status/all`, token, 'GET', null, 'getBridgeStatuses');

export const getAvailablePlatforms = async (token: string) =>
	api(
		`${WEBUI_API_BASE_URL}/bridges/platforms/available`,
		token,
		'GET',
		null,
		'getAvailablePlatforms'
	);

export const getBridgeThreads = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/bridges/${id}/threads`, token, 'GET', null, 'getBridgeThreads');

export const getBridgeHealth = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/bridges/${id}/health`, token, 'GET', null, 'getBridgeHealth');
