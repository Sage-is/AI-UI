import { WEBUI_API_BASE_URL } from '$lib/constants';

type ChannelForm = {
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

// DRY API helper for channels module
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
		console.error(`[CHANNELS_API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewChannel = async (token: string = '', channel: ChannelForm) =>
	api(`${WEBUI_API_BASE_URL}/channels/create`, token, 'POST', channel, 'createNewChannel');

export const getChannels = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/channels/`, token, 'GET', null, 'getChannels');

export const getChannelById = async (token: string = '', channel_id: string) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}`, token, 'GET', null, `getChannelById(${channel_id})`);

export const updateChannelById = async (token: string = '', channel_id: string, channel: ChannelForm) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/update`, token, 'POST', channel, `updateChannelById(${channel_id})`);

export const deleteChannelById = async (token: string = '', channel_id: string) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/delete`, token, 'DELETE', null, `deleteChannelById(${channel_id})`);

export const getChannelMessages = async (token: string = '', channel_id: string, skip: number = 0, limit: number = 50) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages?skip=${skip}&limit=${limit}`, token, 'GET', null, `getChannelMessages(${channel_id})`);

export const getChannelThreadMessages = async (token: string = '', channel_id: string, message_id: string, skip: number = 0, limit: number = 50) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/thread?skip=${skip}&limit=${limit}`, token, 'GET', null, `getChannelThreadMessages(${channel_id}, ${message_id})`);

export const sendMessage = async (token: string = '', channel_id: string, message: MessageForm) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/post`, token, 'POST', message, `sendMessage(${channel_id})`);

export const updateMessage = async (token: string = '', channel_id: string, message_id: string, message: MessageForm) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/update`, token, 'POST', message, `updateMessage(${channel_id}, ${message_id})`);

export const addReaction = async (token: string = '', channel_id: string, message_id: string, name: string) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/reactions/add`, token, 'POST', { name }, `addReaction(${channel_id}, ${message_id})`);

export const removeReaction = async (token: string = '', channel_id: string, message_id: string, name: string) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/reactions/remove`, token, 'POST', { name }, `removeReaction(${channel_id}, ${message_id})`);

export const deleteMessage = async (token: string = '', channel_id: string, message_id: string) =>
	api(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/delete`, token, 'DELETE', null, `deleteMessage(${channel_id}, ${message_id})`);
