import { WEBUI_API_BASE_URL } from '$lib/constants';

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
		console.error(`[Memory API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const getMemories = (token: string) =>
	api(`${WEBUI_API_BASE_URL}/memories/`, token, 'GET', null, 'getMemories');

export const addNewMemory = (token: string, content: string) =>
	api(`${WEBUI_API_BASE_URL}/memories/add`, token, 'POST', { content }, 'addNewMemory');

export const updateMemoryById = (token: string, id: string, content: string) =>
	api(`${WEBUI_API_BASE_URL}/memories/${id}/update`, token, 'POST', { content }, `updateMemoryById(${id})`);

export const queryMemory = (token: string, content: string) =>
	api(`${WEBUI_API_BASE_URL}/memories/query`, token, 'POST', { content }, 'queryMemory');

export const deleteMemoryById = (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/memories/${id}`, token, 'DELETE', null, `deleteMemoryById(${id})`);

export const deleteMemoriesByUserId = (token: string) =>
	api(`${WEBUI_API_BASE_URL}/memories/delete/user`, token, 'DELETE', null, 'deleteMemoriesByUserId');
