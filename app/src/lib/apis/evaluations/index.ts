import { WEBUI_API_BASE_URL } from '$lib/constants';

async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		const res = await fetch(url, {
			method,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			},
			...(method !== 'GET' && body && { body: JSON.stringify(body) })
		});
		
		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[Evaluations API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const getConfig = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/evaluations/config`, token, 'GET', null, 'getConfig');

export const updateConfig = async (token: string, config: object) =>
	api(`${WEBUI_API_BASE_URL}/evaluations/config`, token, 'POST', config, 'updateConfig');

export const getAllFeedbacks = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/evaluations/feedbacks/all`, token, 'GET', null, 'getAllFeedbacks');

export const exportAllFeedbacks = async (token: string = '') =>
	api(`${WEBUI_API_BASE_URL}/evaluations/feedbacks/all/export`, token, 'GET', null, 'exportAllFeedbacks');

export const createNewFeedback = async (token: string, feedback: object) =>
	api(`${WEBUI_API_BASE_URL}/evaluations/feedback`, token, 'POST', feedback, 'createNewFeedback');

export const getFeedbackById = async (token: string, feedbackId: string) =>
	api(`${WEBUI_API_BASE_URL}/evaluations/feedback/${feedbackId}`, token, 'GET', null, 'getFeedbackById');

export const updateFeedbackById = async (token: string, feedbackId: string, feedback: object) =>
	api(`${WEBUI_API_BASE_URL}/evaluations/feedback/${feedbackId}`, token, 'POST', feedback, 'updateFeedbackById');

export const deleteFeedbackById = async (token: string, feedbackId: string) =>
	api(`${WEBUI_API_BASE_URL}/evaluations/feedback/${feedbackId}`, token, 'DELETE', null, 'deleteFeedbackById');
