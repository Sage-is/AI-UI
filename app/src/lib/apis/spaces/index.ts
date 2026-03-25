import { WEBUI_API_BASE_URL } from '$lib/constants';

type SpaceForm = {
	name: string;
	data?: object;
	meta?: object;
	access_control?: object;
};

type MessageForm = {
	parent_id?: string;
	content: string;
	data?: object;
	meta?: object;
};

// DRY API helper for spaces module
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
		console.error(`[SPACES_API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewSpace = async (token: string = '', space: SpaceForm) =>
	api(`${WEBUI_API_BASE_URL}/spaces/create`, token, 'POST', space, 'createNewSpace');

export const getSpaces = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/spaces/`, token, 'GET', null, 'getSpaces');

export const getSpaceById = async (token: string = '', space_id: string) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}`, token, 'GET', null, `getSpaceById(${space_id})`);

export const updateSpaceById = async (token: string = '', space_id: string, space: SpaceForm) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/update`, token, 'POST', space, `updateSpaceById(${space_id})`);

export const deleteSpaceById = async (token: string = '', space_id: string) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/delete`, token, 'DELETE', null, `deleteSpaceById(${space_id})`);

export const getSpaceMessages = async (token: string = '', space_id: string, skip: number = 0, limit: number = 50) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/messages?skip=${skip}&limit=${limit}`, token, 'GET', null, `getSpaceMessages(${space_id})`);

export const getSpaceThreadMessages = async (token: string = '', space_id: string, message_id: string, skip: number = 0, limit: number = 50) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/messages/${message_id}/thread?skip=${skip}&limit=${limit}`, token, 'GET', null, `getSpaceThreadMessages(${space_id}, ${message_id})`);

export const sendMessage = async (token: string = '', space_id: string, message: MessageForm) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/messages/post`, token, 'POST', message, `sendMessage(${space_id})`);

export const updateMessage = async (token: string = '', space_id: string, message_id: string, message: MessageForm) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/messages/${message_id}/update`, token, 'POST', message, `updateMessage(${space_id}, ${message_id})`);

export const addReaction = async (token: string = '', space_id: string, message_id: string, name: string) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/messages/${message_id}/reactions/add`, token, 'POST', { name }, `addReaction(${space_id}, ${message_id})`);

export const removeReaction = async (token: string = '', space_id: string, message_id: string, name: string) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/messages/${message_id}/reactions/remove`, token, 'POST', { name }, `removeReaction(${space_id}, ${message_id})`);

export const deleteMessage = async (token: string = '', space_id: string, message_id: string) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/messages/${message_id}/delete`, token, 'DELETE', null, `deleteMessage(${space_id}, ${message_id})`);

export const getSpaceParticipants = async (token: string = '', space_id: string) =>
	api(`${WEBUI_API_BASE_URL}/spaces/${space_id}/participants`, token, 'GET', null, `getSpaceParticipants(${space_id})`);
