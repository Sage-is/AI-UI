import { WEBUI_API_BASE_URL } from '$lib/constants';

type PromptItem = {
	command: string;
	title: string;
	content: string;
	access_control?: null | object;
};

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
		console.error(`[PROMPTS] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewPrompt = async (token: string, prompt: PromptItem) =>
	api(`${WEBUI_API_BASE_URL}/prompts/create`, token, 'POST', {
		...prompt,
		command: `/${prompt.command}`
	}, `createNewPrompt(${prompt.command})`);

export const getPrompts = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/prompts/`, token, 'GET', null, 'getPrompts');

export const getPromptList = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/prompts/list`, token, 'GET', null, 'getPromptList');

export const getPromptByCommand = async (token: string, command: string) =>
	api(`${WEBUI_API_BASE_URL}/prompts/command/${command}`, token, 'GET', null, `getPromptByCommand(${command})`);

export const updatePromptByCommand = async (token: string, prompt: PromptItem) =>
	api(`${WEBUI_API_BASE_URL}/prompts/command/${prompt.command}/update`, token, 'POST', {
		...prompt,
		command: `/${prompt.command}`
	}, `updatePromptByCommand(${prompt.command})`);

export const deletePromptByCommand = async (token: string, command: string) => {
	// Preserve command preprocessing logic
	const cleanCommand = command.charAt(0) === '/' ? command.slice(1) : command;
	return api(`${WEBUI_API_BASE_URL}/prompts/command/${cleanCommand}/delete`, token, 'DELETE', null, `deletePromptByCommand(${cleanCommand})`);
};
