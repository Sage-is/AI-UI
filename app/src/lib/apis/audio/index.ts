import { AUDIO_API_BASE_URL } from '$lib/constants';

async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		const res = await fetch(url, {
			method,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { Authorization: `Bearer ${token}` })
			},
			...(method !== 'GET' && body && { body: JSON.stringify(body) })
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[Audio API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const getAudioConfig = async (token: string) =>
	api(`${AUDIO_API_BASE_URL}/config`, token, 'GET', null, 'getAudioConfig');

type OpenAIConfigForm = {
	url: string;
	key: string;
	model: string;
	speaker: string;
};

export const updateAudioConfig = async (token: string, payload: OpenAIConfigForm) =>
	api(`${AUDIO_API_BASE_URL}/config/update`, token, 'POST', payload, 'updateAudioConfig');

export const transcribeAudio = async (token: string, file: File, language?: string) => {
	try {
		const data = new FormData();
		data.append('file', file);
		if (language) {
			data.append('language', language);
		}

		const res = await fetch(`${AUDIO_API_BASE_URL}/transcriptions`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			},
			body: data
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error('[Audio API] transcribeAudio:', err);
		throw err.detail || err;
	}
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model?: string
) => {
	try {
		const res = await fetch(`${AUDIO_API_BASE_URL}/speech`, {
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				input: text,
				voice: speaker,
				...(model && { model })
			})
		});
		
		if (!res.ok) throw await res.json();
		return res; // Return raw response, not JSON
	} catch (err: any) {
		console.error('[Audio API] synthesizeOpenAISpeech:', err);
		throw err.detail || err;
	}
};

interface AvailableModelsResponse {
	models: { name: string; id: string }[] | { id: string }[];
}

export const getModels = async (token: string = ''): Promise<AvailableModelsResponse> =>
	api(`${AUDIO_API_BASE_URL}/models`, token, 'GET', null, 'getModels');

export const getVoices = async (token: string = '') =>
	api(`${AUDIO_API_BASE_URL}/voices`, token, 'GET', null, 'getVoices');
