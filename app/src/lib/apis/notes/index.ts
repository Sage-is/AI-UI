import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getTimeRange } from '$lib/utils';

type NoteItem = {
	title: string;
	data: object;
	meta?: null | object;
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
		console.error(`[NOTES] ${context}:`, err);
		throw err.detail || err;
	}
}

export const createNewNote = async (token: string, note: NoteItem) =>
	api(`${WEBUI_API_BASE_URL}/notes/create`, token, 'POST', note, 'createNewNote');

export const getNotes = async (token: string = '', raw: boolean = false) => {
	const res = await api(`${WEBUI_API_BASE_URL}/notes/`, token, 'GET', null, 'getNotes');
	
	if (raw) {
		return res; // Return raw response if requested
	}

	if (!Array.isArray(res)) {
		return {}; // or throw new Error("Notes response is not an array")
	}

	// Build the grouped object
	const grouped: Record<string, any[]> = {};
	for (const note of res) {
		const timeRange = getTimeRange(note.updated_at / 1000000000);
		if (!grouped[timeRange]) {
			grouped[timeRange] = [];
		}
		grouped[timeRange].push({
			...note,
			timeRange
		});
	}

	return grouped;
};

export const getNoteList = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/notes/list`, token, 'GET', null, 'getNoteList');

export const getNoteById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/notes/${id}`, token, 'GET', null, `getNoteById(${id})`);

export const updateNoteById = async (token: string, id: string, note: NoteItem) =>
	api(`${WEBUI_API_BASE_URL}/notes/${id}/update`, token, 'POST', note, `updateNoteById(${id})`);

export const deleteNoteById = async (token: string, id: string) =>
	api(`${WEBUI_API_BASE_URL}/notes/${id}/delete`, token, 'DELETE', null, `deleteNoteById(${id})`);
