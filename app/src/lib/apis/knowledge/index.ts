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
		console.error(`[KNOWLEDGE] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewKnowledge = async (
	token: string,
	name: string,
	description: string,
	accessControl: null | object
) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/create`, token, 'POST', {
		name: name,
		description: description,
		access_control: accessControl
	}, 'createNewKnowledge');

export const getKnowledgeBases = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/knowledge/`, token, 'GET', null, 'getKnowledgeBases');

export const getKnowledgeBaseList = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/knowledge/list`, token, 'GET', null, 'getKnowledgeBaseList');

export const getKnowledgeById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/${id}`, token, 'GET', null, `getKnowledgeById(${id})`);

type KnowledgeUpdateForm = {
	name?: string;
	description?: string;
	data?: object;
	access_control?: null | object;
};

export const updateKnowledgeById = async (token: string, id: string, form: KnowledgeUpdateForm) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/${id}/update`, token, 'POST', {
		name: form?.name ? form.name : undefined,
		description: form?.description ? form.description : undefined,
		data: form?.data ? form.data : undefined,
		access_control: form.access_control
	}, `updateKnowledgeById(${id})`);

export const addFileToKnowledgeById = async (token: string, id: string, fileId: string) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/${id}/file/add`, token, 'POST', {
		file_id: fileId
	}, `addFileToKnowledgeById(${id}, ${fileId})`);

export const updateFileFromKnowledgeById = async (token: string, id: string, fileId: string) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/${id}/file/update`, token, 'POST', {
		file_id: fileId
	}, `updateFileFromKnowledgeById(${id}, ${fileId})`);

export const removeFileFromKnowledgeById = async (token: string, id: string, fileId: string) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/${id}/file/remove`, token, 'POST', {
		file_id: fileId
	}, `removeFileFromKnowledgeById(${id}, ${fileId})`);

export const resetKnowledgeById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/${id}/reset`, token, 'POST', null, `resetKnowledgeById(${id})`);

export const deleteKnowledgeById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/${id}/delete`, token, 'DELETE', null, `deleteKnowledgeById(${id})`);

export const reindexKnowledgeFiles = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/knowledge/reindex`, token, 'POST', null, 'reindexKnowledgeFiles');
