import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { Banner } from '$lib/types';

async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		console.log(`[Config API] ${context}: Calling ${method} ${url}`);

		const res = await fetch(url, {
			method,
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			...(body && { body: JSON.stringify(body) })
		});

		console.log(`[Config API] ${context}: Response status ${res.status} ${res.statusText}`);
		console.log(`[Config API] ${context}: Response headers:`, Object.fromEntries(res.headers.entries()));

		if (!res.ok) {
			const responseText = await res.text();
			console.error(`[Config API] ${context}: Error response body:`, responseText);

			// Try to parse as JSON, but if it fails, throw the raw text
			try {
				const errorJson = JSON.parse(responseText);
				throw errorJson;
			} catch (parseError) {
				console.error(`[Config API] ${context}: Response is not valid JSON, got HTML/text instead:`, responseText.substring(0, 200) + '...');
				throw new Error(`Server returned HTML instead of JSON for ${context}. Status: ${res.status}. Response starts with: ${responseText.substring(0, 100)}...`);
			}
		}

		const responseText = await res.text();
		console.log(`[Config API] ${context}: Response body:`, responseText.substring(0, 200) + (responseText.length > 200 ? '...' : ''));

		try {
			return JSON.parse(responseText);
		} catch (parseError) {
			console.error(`[Config API] ${context}: Success response is not valid JSON:`, responseText.substring(0, 200) + '...');
			throw new Error(`Server returned HTML instead of JSON for ${context}. Expected JSON but got: ${responseText.substring(0, 100)}...`);
		}
	} catch (err: any) {
		console.error(`[Config API] ${context}: Error details:`, err);
		throw err.detail || err.message || err;
	}
}

export const importConfig = async (token: string, config: any) =>
	api(`${WEBUI_API_BASE_URL}/configs/import`, token, 'POST', {
		config: config
	}, 'importConfig');

export const exportConfig = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/configs/export`, token, 'GET', null, 'exportConfig');

export const getConnectionsConfig = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/configs/connections`, token, 'GET', null, 'getConnectionsConfig');

export const setConnectionsConfig = async (token: string, config: object) =>
	api(`${WEBUI_API_BASE_URL}/configs/connections`, token, 'POST', {
		...config
	}, 'setConnectionsConfig');

export const getToolServerConnections = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/configs/tool_servers`, token, 'GET', null, 'getToolServerConnections');

export const setToolServerConnections = async (token: string, connections: object) =>
	api(`${WEBUI_API_BASE_URL}/configs/tool_servers`, token, 'POST', {
		...connections
	}, 'setToolServerConnections');

export const verifyToolServerConnection = async (token: string, connection: object) =>
	api(`${WEBUI_API_BASE_URL}/configs/tool_servers/verify`, token, 'POST', {
		...connection
	}, 'verifyToolServerConnection');

export const getCodeExecutionConfig = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/configs/code_execution`, token, 'GET', null, 'getCodeExecutionConfig');

export const setCodeExecutionConfig = async (token: string, config: object) =>
	api(`${WEBUI_API_BASE_URL}/configs/code_execution`, token, 'POST', {
		...config
	}, 'setCodeExecutionConfig');

export const getModelsConfig = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/configs/models`, token, 'GET', null, 'getModelsConfig');

export const setModelsConfig = async (token: string, config: object) =>
	api(`${WEBUI_API_BASE_URL}/configs/models`, token, 'POST', {
		...config
	}, 'setModelsConfig');

export const setDefaultPromptSuggestions = async (token: string, promptSuggestions: string) =>
	api(`${WEBUI_API_BASE_URL}/configs/suggestions`, token, 'POST', {
		suggestions: promptSuggestions
	}, 'setDefaultPromptSuggestions');

export const getBanners = async (token: string): Promise<Banner[]> =>
	api(`${WEBUI_API_BASE_URL}/configs/banners`, token, 'GET', null, 'getBanners');

export const setBanners = async (token: string, banners: Banner[]) =>
	api(`${WEBUI_API_BASE_URL}/configs/banners`, token, 'POST', {
		banners: banners
	}, 'setBanners');

export const getUIConfig = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/configs/ui`, token, 'GET', null, 'getUIConfig');

export const setUIConfig = async (token: string, config: object) =>
	api(`${WEBUI_API_BASE_URL}/configs/ui`, token, 'POST', {
		...config
	}, 'setUIConfig');
