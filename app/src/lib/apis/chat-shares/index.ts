import { WEBUI_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

const api = createApiHelper('ChatShares', WEBUI_API_BASE_URL);

export const shareChatWithTargets = async (
	token: string,
	chatId: string,
	targets: Array<{ type: string; id: string; mode: string }>
) => api(`/chats/${chatId}/share/targets`, 'POST', { targets }, token, 'shareChatWithTargets');

export const getChatShareTargets = async (token: string, chatId: string) =>
	api(`/chats/${chatId}/share/targets`, 'GET', undefined, token, 'getChatShareTargets');

export const removeChatShareTarget = async (token: string, chatId: string, shareId: string) =>
	api(
		`/chats/${chatId}/share/targets/${shareId}`,
		'DELETE',
		undefined,
		token,
		'removeChatShareTarget'
	);

export const getChatsSharedWithMe = async (token: string) =>
	api('/chats/shared-with-me', 'GET', undefined, token, 'getChatsSharedWithMe');

export const getChatsSharedByMe = async (token: string) =>
	api('/chats/shared-by-me', 'GET', undefined, token, 'getChatsSharedByMe');
