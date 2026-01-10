import { WEBUI_API_BASE_URL } from '$lib/constants';

type FolderForm = {
	name: string;
	data?: Record<string, any>;
};

type FolderItems = {
	chat_ids: string[];
	file_ids: string[];
};

// DRY API helper for folders module
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
		console.error(`[FOLDERS_API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewFolder = async (token: string, folderForm: FolderForm) =>
	api(`${WEBUI_API_BASE_URL}/folders/`, token, 'POST', folderForm, 'createNewFolder');

export const getFolders = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/folders/`, token, 'GET', null, 'getFolders');

export const getFolderById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/folders/${id}`, token, 'GET', null, `getFolderById(${id})`);

export const updateFolderById = async (token: string, id: string, folderForm: FolderForm) =>
	api(`${WEBUI_API_BASE_URL}/folders/${id}/update`, token, 'POST', folderForm, `updateFolderById(${id})`);

export const updateFolderIsExpandedById = async (token: string, id: string, isExpanded: boolean) =>
	api(`${WEBUI_API_BASE_URL}/folders/${id}/update/expanded`, token, 'POST', { is_expanded: isExpanded }, `updateFolderIsExpandedById(${id})`);

export const updateFolderParentIdById = async (token: string, id: string, parentId?: string) =>
	api(`${WEBUI_API_BASE_URL}/folders/${id}/update/parent`, token, 'POST', { parent_id: parentId }, `updateFolderParentIdById(${id})`);

export const updateFolderItemsById = async (token: string, id: string, items: FolderItems) =>
	api(`${WEBUI_API_BASE_URL}/folders/${id}/update/items`, token, 'POST', { items }, `updateFolderItemsById(${id})`);

export const deleteFolderById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/folders/${id}`, token, 'DELETE', null, `deleteFolderById(${id})`);
