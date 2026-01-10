import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getTimeRange } from '$lib/utils';

async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		const res = await fetch(url, {
			method,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			},
			...(body && { body: JSON.stringify(body) })
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[Chat API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewChat = async (token: string, chat: object, folderId: string | null) =>
	api(`${WEBUI_API_BASE_URL}/chats/new`, token, 'POST', {
		chat: chat,
		folder_id: folderId ?? null
	}, 'createNewChat');

export const importChat = async (
	token: string,
	chat: object,
	meta: object | null,
	pinned?: boolean,
	folderId?: string | null,
	createdAt: number | null = null,
	updatedAt: number | null = null
) =>
	api(`${WEBUI_API_BASE_URL}/chats/import`, token, 'POST', {
		chat: chat,
		meta: meta ?? {},
		pinned: pinned,
		folder_id: folderId,
		created_at: createdAt ?? null,
		updated_at: updatedAt ?? null
	}, 'importChat');

export const getChatList = async (token: string = '', page: number | null = null) => {
	const searchParams = new URLSearchParams();
	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await api(`${WEBUI_API_BASE_URL}/chats/?${searchParams.toString()}`, token, 'GET', null, 'getChatList');
	
	return res.map((chat: any) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getChatListByUserId = async (
	token: string = '',
	userId: string,
	page: number = 1,
	filter?: object
) => {
	const searchParams = new URLSearchParams();
	searchParams.append('page', `${page}`);

	if (filter) {
		Object.entries(filter).forEach(([key, value]) => {
			if (value !== undefined && value !== null) {
				searchParams.append(key, value.toString());
			}
		});
	}

	const res = await api(
		`${WEBUI_API_BASE_URL}/chats/list/user/${userId}?${searchParams.toString()}`,
		token,
		'GET',
		null,
		`getChatListByUserId(${userId})`
	);

	return res.map((chat: any) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getArchivedChatList = async (
	token: string = '',
	page: number = 1,
	filter?: object
) => {
	const searchParams = new URLSearchParams();
	searchParams.append('page', `${page}`);

	if (filter) {
		Object.entries(filter).forEach(([key, value]) => {
			if (value !== undefined && value !== null) {
				searchParams.append(key, value.toString());
			}
		});
	}

	const res = await api(
		`${WEBUI_API_BASE_URL}/chats/archived?${searchParams.toString()}`,
		token,
		'GET',
		null,
		'getArchivedChatList'
	);

	return res.map((chat: any) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getAllChats = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/all`, token, 'GET', null, 'getAllChats');

export const getChatListBySearchText = async (token: string, text: string, page: number = 1) => {
	const searchParams = new URLSearchParams();
	searchParams.append('text', text);
	searchParams.append('page', `${page}`);

	const res = await api(
		`${WEBUI_API_BASE_URL}/chats/search?${searchParams.toString()}`,
		token,
		'GET',
		null,
		`getChatListBySearchText(${text})`
	);

	return res.map((chat: any) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getChatsByFolderId = async (token: string, folderId: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/folder/${folderId}`, token, 'GET', null, `getChatsByFolderId(${folderId})`);

export const getAllArchivedChats = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/all/archived`, token, 'GET', null, 'getAllArchivedChats');

export const getAllUserChats = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/all/db`, token, 'GET', null, 'getAllUserChats');

export const getAllTags = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/all/tags`, token, 'GET', null, 'getAllTags');

export const getPinnedChatList = async (token: string = '') => {
	const res = await api(`${WEBUI_API_BASE_URL}/chats/pinned`, token, 'GET', null, 'getPinnedChatList');
	
	return res.map((chat: any) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getChatListByTagName = async (token: string = '', tagName: string) => {
	const res = await api(
		`${WEBUI_API_BASE_URL}/chats/tags`,
		token,
		'POST',
		{ name: tagName },
		`getChatListByTagName(${tagName})`
	);

	return res.map((chat: any) => ({
		...chat,
		time_range: getTimeRange(chat.updated_at)
	}));
};

export const getChatById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}`, token, 'GET', null, `getChatById(${id})`);

export const getChatByShareId = async (token: string, share_id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/share/${share_id}`, token, 'GET', null, `getChatByShareId(${share_id})`);

export const getChatPinnedStatusById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/pinned`, token, 'GET', null, `getChatPinnedStatusById(${id})`);

export const toggleChatPinnedStatusById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/pin`, token, 'POST', null, `toggleChatPinnedStatusById(${id})`);

export const cloneChatById = async (token: string, id: string, title?: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/clone`, token, 'POST', {
		...(title && { title: title })
	}, `cloneChatById(${id})`);

export const cloneSharedChatById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/clone/shared`, token, 'POST', null, `cloneSharedChatById(${id})`);

export const shareChatById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/share`, token, 'POST', null, `shareChatById(${id})`);

export const updateChatFolderIdById = async (token: string, id: string, folderId?: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/folder`, token, 'POST', {
		folder_id: folderId
	}, `updateChatFolderIdById(${id})`);

export const archiveChatById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/archive`, token, 'POST', null, `archiveChatById(${id})`);

export const deleteSharedChatById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/share`, token, 'DELETE', null, `deleteSharedChatById(${id})`);

export const updateChatById = async (token: string, id: string, chat: object) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}`, token, 'POST', {
		chat: chat
	}, `updateChatById(${id})`);

export const deleteChatById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}`, token, 'DELETE', null, `deleteChatById(${id})`);

export const getTagsById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, token, 'GET', null, `getTagsById(${id})`);

export const addTagById = async (token: string, id: string, tagName: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, token, 'POST', {
		name: tagName
	}, `addTagById(${id}, ${tagName})`);

export const deleteTagById = async (token: string, id: string, tagName: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/tags`, token, 'DELETE', {
		name: tagName
	}, `deleteTagById(${id}, ${tagName})`);
export const deleteTagsById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/${id}/tags/all`, token, 'DELETE', null, `deleteTagsById(${id})`);

export const deleteAllChats = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/`, token, 'DELETE', null, 'deleteAllChats');

export const archiveAllChats = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/chats/archive/all`, token, 'POST', null, 'archiveAllChats');
