import { OLLAMA_API_BASE_URL } from '$lib/constants';

type OllamaConfig = {
	ENABLE_OLLAMA_API: boolean;
	OLLAMA_BASE_URLS: string[];
	OLLAMA_API_CONFIGS: object;
};

// DRY helper function to eliminate repetitive fetch/error patterns
async function api(url: string, token: string, method = 'GET', body?: any, context = '', useFormData = false) {
	try {
		console.log(`[OLLAMA] ${context}: Calling ${method} ${url}`);
		
		const headers: Record<string, string> = {
			Accept: 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		};
		
		if (!useFormData) {
			headers['Content-Type'] = 'application/json';
		}

		const res = await fetch(url, {
			method,
			headers,
			...(body && { body: useFormData ? body : JSON.stringify(body) })
		});
		
		console.log(`[OLLAMA] ${context}: Response status ${res.status} ${res.statusText}`);
		
		if (!res.ok) {
			const responseText = await res.text();
			console.error(`[OLLAMA] ${context}: Error response body:`, responseText);
			
			try {
				const errorJson = JSON.parse(responseText);
				throw errorJson;
			} catch (parseError) {
				console.error(`[OLLAMA] ${context}: Response is not valid JSON, got HTML/text instead:`, responseText.substring(0, 200) + '...');
				throw new Error(`Server returned HTML instead of JSON for ${context}. Status: ${res.status}. Response starts with: ${responseText.substring(0, 100)}...`);
			}
		}
		
		const responseText = await res.text();
		console.log(`[OLLAMA] ${context}: Response body:`, responseText.substring(0, 200) + (responseText.length > 200 ? '...' : ''));
		
		try {
			return JSON.parse(responseText);
		} catch (parseError) {
			console.error(`[OLLAMA] ${context}: Success response is not valid JSON:`, responseText.substring(0, 200) + '...');
			throw new Error(`Server returned HTML instead of JSON for ${context}. Expected JSON but got: ${responseText.substring(0, 100)}...`);
		}
	} catch (err: any) {
		console.error(`[OLLAMA] ${context}: Error details:`, err);
		throw err.detail || err.error?.message || err.message || err || 'Server connection failed';
	}
}

// Special helper for streaming responses
async function apiStream(url: string, token: string, body?: any, context = '') {
	try {
		const res = await fetch(url, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(body)
		});
		
		return res;
	} catch (err: any) {
		console.error(`[OLLAMA] ${context}:`, err);
		throw err.detail || err.error?.message || err || 'Server connection failed';
	}
}

export const verifyOllamaConnection = async (token: string = '', connection: any = {}) =>
	api(`${OLLAMA_API_BASE_URL}/verify`, token, 'POST', connection, 'verifyOllamaConnection');

export const getOllamaConfig = async (token: string = '') =>
	api(`${OLLAMA_API_BASE_URL}/config`, token, 'GET', null, 'getOllamaConfig');

export const updateOllamaConfig = async (token: string = '', config: OllamaConfig) =>
	api(`${OLLAMA_API_BASE_URL}/config/update`, token, 'POST', config, 'updateOllamaConfig');

export const getOllamaUrls = async (token: string = '') => {
	const res = await api(`${OLLAMA_API_BASE_URL}/urls`, token, 'GET', null, 'getOllamaUrls');
	return res.OLLAMA_BASE_URLS;
};

export const updateOllamaUrls = async (token: string = '', urls: string[]) => {
	const res = await api(`${OLLAMA_API_BASE_URL}/urls/update`, token, 'POST', { urls }, 'updateOllamaUrls');
	return res.OLLAMA_BASE_URLS;
};

export const getOllamaVersion = async (token: string, urlIdx?: number) => {
	const res = await api(`${OLLAMA_API_BASE_URL}/api/version${urlIdx ? `/${urlIdx}` : ''}`, token, 'GET', null, `getOllamaVersion(${urlIdx || 'default'})`);
	return res?.version ?? false;
};

export const getOllamaModels = async (token: string = '', urlIdx: null | number = null) => {
	const res = await api(`${OLLAMA_API_BASE_URL}/api/tags${urlIdx !== null ? `/${urlIdx}` : ''}`, token, 'GET', null, `getOllamaModels(${urlIdx || 'default'})`);
	return (res?.models ?? [])
		.map((model: any) => ({ id: model.model, name: model.name ?? model.model, ...model }))
		.sort((a: any, b: any) => a.name.localeCompare(b.name));
};

export const generatePrompt = async (token: string = '', model: string, conversation: string) => {
	if (conversation === '') {
		conversation = '[no existing conversation]';
	}

	return apiStream(`${OLLAMA_API_BASE_URL}/api/generate`, token, {
		model: model,
		prompt: `Conversation:
		${conversation}

		As USER in the conversation above, your task is to continue the conversation. Remember, Your responses should be crafted as if you're a human conversing in a natural, realistic manner, keeping in mind the context and flow of the dialogue. Please generate a fitting response to the last message in the conversation, or if there is no existing conversation, initiate one as a normal person would.
		
		Response:
		`
	}, `generatePrompt(${model})`);
};

export const generateEmbeddings = async (token: string = '', model: string, text: string) =>
	apiStream(`${OLLAMA_API_BASE_URL}/api/embeddings`, token, { model, prompt: text }, `generateEmbeddings(${model})`);

export const generateTextCompletion = async (token: string = '', model: string, text: string) =>
	apiStream(`${OLLAMA_API_BASE_URL}/api/generate`, token, { model, prompt: text, stream: true }, `generateTextCompletion(${model})`);

export const generateChatCompletion = async (token: string = '', body: object) => {
	const controller = new AbortController();
	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/chat`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	});
	return [res, controller];
};

export const unloadModel = async (token: string, tagName: string) =>
	apiStream(`${OLLAMA_API_BASE_URL}/api/unload`, token, { model: tagName }, `unloadModel(${tagName})`);

export const createModel = async (token: string, payload: object, urlIdx: string | null = null) =>
	apiStream(`${OLLAMA_API_BASE_URL}/api/create${urlIdx !== null ? `/${urlIdx}` : ''}`, token, payload, `createModel(${urlIdx || 'default'})`);

export const deleteModel = async (token: string, tagName: string, urlIdx: string | null = null) => {
	const res = await api(`${OLLAMA_API_BASE_URL}/api/delete${urlIdx !== null ? `/${urlIdx}` : ''}`, token, 'DELETE', { model: tagName }, `deleteModel(${tagName}, ${urlIdx || 'default'})`);
	return true;
};

export const pullModel = async (token: string, tagName: string, urlIdx: number | null = null) => {
	const controller = new AbortController();
	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/pull${urlIdx !== null ? `/${urlIdx}` : ''}`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ name: tagName })
	});
	return [res, controller];
};

export const downloadModel = async (token: string, download_url: string, urlIdx: string | null = null) =>
	apiStream(`${OLLAMA_API_BASE_URL}/models/download${urlIdx !== null ? `/${urlIdx}` : ''}`, token, { url: download_url }, `downloadModel(${urlIdx || 'default'})`);

export const uploadModel = async (token: string, file: File, urlIdx: string | null = null) => {
	const formData = new FormData();
	formData.append('file', file);
	return api(`${OLLAMA_API_BASE_URL}/models/upload${urlIdx !== null ? `/${urlIdx}` : ''}`, token, 'POST', formData, `uploadModel(${file.name}, ${urlIdx || 'default'})`, true);
};
