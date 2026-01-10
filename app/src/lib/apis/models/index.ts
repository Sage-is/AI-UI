import { WEBUI_API_BASE_URL } from '$lib/constants';

// DRY helper function to eliminate repetitive fetch/error patterns
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
		console.error(`[MODELS] ${context}:`, err);
		throw err.detail || err;
	}
}

export const getModels = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/models/`, token, 'GET', null, 'getModels');

export const getBaseModels = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/models/base`, token, 'GET', null, 'getBaseModels');

export const createNewModel = async (token: string, model: object) =>
	api(`${WEBUI_API_BASE_URL}/models/create`, token, 'POST', model, 'createNewModel');

export const getModelById = async (token: string, id: string) => {
	const searchParams = new URLSearchParams();
	searchParams.append('id', id);
	return api(`${WEBUI_API_BASE_URL}/models/model?${searchParams.toString()}`, token, 'GET', null, `getModelById(${id})`);
};

export const toggleModelById = async (token: string, id: string) => {
	const searchParams = new URLSearchParams();
	searchParams.append('id', id);
	return api(`${WEBUI_API_BASE_URL}/models/model/toggle?${searchParams.toString()}`, token, 'POST', null, `toggleModelById(${id})`);
};

export const updateModelById = async (token: string, id: string, model: object) => {
	const searchParams = new URLSearchParams();
	searchParams.append('id', id);
	return api(`${WEBUI_API_BASE_URL}/models/model/update?${searchParams.toString()}`, token, 'POST', model, `updateModelById(${id})`);
};

export const deleteModelById = async (token: string, id: string) => {
	const searchParams = new URLSearchParams();
	searchParams.append('id', id);
	return api(`${WEBUI_API_BASE_URL}/models/model/delete?${searchParams.toString()}`, token, 'DELETE', null, `deleteModelById(${id})`);
};

export const deleteAllModels = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/models/delete/all`, token, 'DELETE', null, 'deleteAllModels');
