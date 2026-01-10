import { WEBUI_API_BASE_URL } from '$lib/constants';

// DRY API helper for functions module
async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		const res = await fetch(url, {
			method,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			...(body && { body: JSON.stringify(body) })
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[FUNCTIONS_API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewFunction = async (token: string, func: object) =>
	api(`${WEBUI_API_BASE_URL}/functions/create`, token, 'POST', func, 'createNewFunction');

export const getFunctions = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/functions/`, token, 'GET', null, 'getFunctions');

export const loadFunctionByUrl = async (token: string = '', url: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/load/url`, token, 'POST', { url }, 'loadFunctionByUrl');

export const exportFunctions = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/functions/export`, token, 'GET', null, 'exportFunctions');

export const getFunctionById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}`, token, 'GET', null, `getFunctionById(${id})`);

export const updateFunctionById = async (token: string, id: string, func: object) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/update`, token, 'POST', func, `updateFunctionById(${id})`);

export const deleteFunctionById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/delete`, token, 'DELETE', null, `deleteFunctionById(${id})`);

export const toggleFunctionById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/toggle`, token, 'POST', null, `toggleFunctionById(${id})`);

export const toggleGlobalById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/toggle/global`, token, 'POST', null, `toggleGlobalById(${id})`);

export const getFunctionValvesById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/valves`, token, 'GET', null, `getFunctionValvesById(${id})`);

export const getFunctionValvesSpecById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/valves/spec`, token, 'GET', null, `getFunctionValvesSpecById(${id})`);

export const updateFunctionValvesById = async (token: string, id: string, valves: object) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/valves/update`, token, 'POST', valves, `updateFunctionValvesById(${id})`);

export const getUserValvesById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/valves/user`, token, 'GET', null, `getUserValvesById(${id})`);

export const getUserValvesSpecById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/valves/user/spec`, token, 'GET', null, `getUserValvesSpecById(${id})`);

export const updateUserValvesById = async (token: string, id: string, valves: object) =>
	api(`${WEBUI_API_BASE_URL}/functions/id/${id}/valves/user/update`, token, 'POST', valves, `updateUserValvesById(${id})`);
