import { WEBUI_API_BASE_URL } from '$lib/constants';

// DRY API helper for files module
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
		console.error(`[FILES_API] ${context}:`, err);
		throw err.detail || err;
	}
}

// Special helper for FormData uploads (no Content-Type header)
async function apiFormData(url: string, token: string, method = 'POST', formData?: FormData, context = '') {
	try {
		const res = await fetch(url, {
			method,
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			},
			...(formData && { body: formData })
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[FILES_API] ${context}:`, err);
		throw err.detail || err;
	}
}

// Special helper for blob responses
async function apiBlobResponse(url: string, context = '') {
	try {
		const res = await fetch(url, {
			method: 'GET',
			headers: {
				Accept: 'application/json'
			},
			credentials: 'include'
		});
		
		if (!res.ok) throw await res.json();
		return await res.blob();
	} catch (err: any) {
		console.error(`[FILES_API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const uploadFile = async (token: string, file: File, metadata?: object | null) => {
	const data = new FormData();
	data.append('file', file);
	if (metadata) {
		data.append('metadata', JSON.stringify(metadata));
	}
	return apiFormData(`${WEBUI_API_BASE_URL}/files/`, token, 'POST', data, 'uploadFile');
};

export const uploadDir = async (token: string) =>
	apiFormData(`${WEBUI_API_BASE_URL}/files/upload/dir`, token, 'POST', undefined, 'uploadDir');

export const getFiles = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/files/`, token, 'GET', null, 'getFiles');

export const getFileById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/files/${id}`, token, 'GET', null, `getFileById(${id})`);

export const updateFileDataContentById = async (token: string, id: string, content: string) =>
	api(`${WEBUI_API_BASE_URL}/files/${id}/data/content/update`, token, 'POST', { content }, `updateFileDataContentById(${id})`);

export const getFileContentById = async (id: string) =>
	apiBlobResponse(`${WEBUI_API_BASE_URL}/files/${id}/content`, `getFileContentById(${id})`);

export const deleteFileById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/files/${id}`, token, 'DELETE', null, `deleteFileById(${id})`);

export const deleteAllFiles = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/files/all`, token, 'DELETE', null, 'deleteAllFiles');
