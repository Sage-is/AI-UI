import { OPENAI_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

type OpenAIConfig = {
	ENABLE_OPENAI_API: boolean;
	OPENAI_API_BASE_URLS: string[];
	OPENAI_API_KEYS: string[];
	OPENAI_API_CONFIGS: object;
};

// DRY helper function to eliminate repetitive fetch/error patterns
async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		console.log(`[OPENAI] ${context}: Calling ${method} ${url}`);
		
		const res = await fetch(url, {
			method,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			},
			...(body && { body: JSON.stringify(body) })
		});
		
		console.log(`[OPENAI] ${context}: Response status ${res.status} ${res.statusText}`);
		
		if (!res.ok) {
			const responseText = await res.text();
			console.error(`[OPENAI] ${context}: Error response body:`, responseText);
			
			try {
				const errorJson = JSON.parse(responseText);
				throw errorJson;
			} catch (parseError) {
				console.error(`[OPENAI] ${context}: Response is not valid JSON, got HTML/text instead:`, responseText.substring(0, 200) + '...');
				throw new Error(`Server returned HTML instead of JSON for ${context}. Status: ${res.status}. Response starts with: ${responseText.substring(0, 100)}...`);
			}
		}
		
		const responseText = await res.text();
		console.log(`[OPENAI] ${context}: Response body:`, responseText.substring(0, 200) + (responseText.length > 200 ? '...' : ''));
		
		try {
			return JSON.parse(responseText);
		} catch (parseError) {
			console.error(`[OPENAI] ${context}: Success response is not valid JSON:`, responseText.substring(0, 200) + '...');
			throw new Error(`Server returned HTML instead of JSON for ${context}. Expected JSON but got: ${responseText.substring(0, 100)}...`);
		}
	} catch (err: any) {
		console.error(`[OPENAI] ${context}: Error details:`, err);
		throw err.detail || err.error?.message || err.message || err || 'Server connection failed';
	}
}

export const getOpenAIConfig = async (token: string = '') =>
	api(`${OPENAI_API_BASE_URL}/config`, token, 'GET', null, 'getOpenAIConfig');

export const updateOpenAIConfig = async (token: string = '', config: OpenAIConfig) =>
	api(`${OPENAI_API_BASE_URL}/config/update`, token, 'POST', config, 'updateOpenAIConfig');

export const getOpenAIUrls = async (token: string = '') => {
	const res = await api(`${OPENAI_API_BASE_URL}/urls`, token, 'GET', null, 'getOpenAIUrls');
	return res.OPENAI_API_BASE_URLS;
};

export const updateOpenAIUrls = async (token: string = '', urls: string[]) => {
	const res = await api(`${OPENAI_API_BASE_URL}/urls/update`, token, 'POST', { urls }, 'updateOpenAIUrls');
	return res.OPENAI_API_BASE_URLS;
};

export const getOpenAIKeys = async (token: string = '') => {
	const res = await api(`${OPENAI_API_BASE_URL}/keys`, token, 'GET', null, 'getOpenAIKeys');
	return res.OPENAI_API_KEYS;
};

export const updateOpenAIKeys = async (token: string = '', keys: string[]) => {
	const res = await api(`${OPENAI_API_BASE_URL}/keys/update`, token, 'POST', { keys }, 'updateOpenAIKeys');
	return res.OPENAI_API_KEYS;
};

export const getOpenAIModelsDirect = async (url: string, key: string) => {
	try {
		const res = await fetch(`${url}/models`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(key && { authorization: `Bearer ${key}` })
			}
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[OPENAI] getOpenAIModelsDirect(${url}):`, err);
		throw `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
	}
};

export const getOpenAIModels = async (token: string, urlIdx?: number) => {
	try {
		const res = await fetch(
			`${OPENAI_API_BASE_URL}/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`,
			{
				method: 'GET',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					...(token && { authorization: `Bearer ${token}` })
				}
			}
		);
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[OPENAI] getOpenAIModels(${urlIdx || 'default'}):`, err);
		throw `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
	}
};

export const verifyOpenAIConnection = async (
	token: string = '',
	connection: any = {},
	direct: boolean = false
) => {
	const { url, key, config } = connection;
	if (!url) {
		throw 'OpenAI: URL is required';
	}

	try {
		if (direct) {
			const res = await fetch(`${url}/models`, {
				method: 'GET',
				headers: {
					Accept: 'application/json',
					Authorization: `Bearer ${key}`,
					'Content-Type': 'application/json'
				}
			});
			
			if (!res.ok) throw await res.json();
			return res.json();
		} else {
			const res = await fetch(`${OPENAI_API_BASE_URL}/verify`, {
				method: 'POST',
				headers: {
					Accept: 'application/json',
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ url, key, config })
			});
			
			if (!res.ok) throw await res.json();
			return res.json();
		}
	} catch (err: any) {
		console.error(`[OPENAI] verifyOpenAIConnection(${direct ? 'direct' : 'proxy'}):`, err);
		throw `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
	}
};

export const chatCompletion = async (
	token: string = '',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`
): Promise<[Response | null, AbortController]> => {
	const controller = new AbortController();
	try {
		const res = await fetch(`${url}/chat/completions`, {
			signal: controller.signal,
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(body)
		});
		
		return [res, controller];
	} catch (err: any) {
		console.error(`[OPENAI] chatCompletion:`, err);
		throw err;
	}
};

export const generateOpenAIChatCompletion = async (
	token: string = '',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`
) => {
	try {
		const res = await fetch(`${url}/chat/completions`, {
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(body)
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[OPENAI] generateOpenAIChatCompletion:`, err);
		throw err?.detail ?? err;
	}
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model: string = 'tts-1'
) => {
	try {
		const res = await fetch(`${OPENAI_API_BASE_URL}/audio/speech`, {
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				model: model,
				input: text,
				voice: speaker
			})
		});
		
		return res;
	} catch (err: any) {
		console.error(`[OPENAI] synthesizeOpenAISpeech(${model}, ${speaker}):`, err);
		throw err;
	}
};
