import { WEBUI_API_BASE_URL } from '$lib/constants';
import { createApiHelper, createApiBlobHelper, createDownloadHelper } from '../base';

// Create standardized API helpers for utils with enhanced error reporting
const api = createApiHelper('UTILS', WEBUI_API_BASE_URL, '/utils');
const apiBlob = createApiBlobHelper('UTILS', WEBUI_API_BASE_URL, '/utils');
const downloadFile = createDownloadHelper('UTILS', WEBUI_API_BASE_URL, '/utils');

export const getGravatarUrl = async (token: string, email: string) => {
	const res = await api(`/gravatar?email=${email}`, 'GET', undefined, token, `getGravatarUrl(${email})`);
	return res.json();
};

export const executeCode = async (token: string, code: string) => {
	const res = await api('/code/execute', 'POST', { code }, token, 'executeCode');
	return res.json();
};

export const formatPythonCode = async (token: string, code: string) => {
	const res = await api('/code/format', 'POST', { code }, token, 'formatPythonCode');
	return res.json();
};

export const downloadChatAsPDF = async (token: string, title: string, messages: object[]) => 
	apiBlob('/pdf', 'POST', { title, messages }, token, `downloadChatAsPDF("${title}")`);

export const getHTMLFromMarkdown = async (token: string, md: string) => {
	const res = await api('/markdown', 'POST', { md }, token, 'getHTMLFromMarkdown');
	const json = await res.json();
	return json.html;
};

export const downloadDatabase = async (token: string) => 
	downloadFile('/db/download', 'webui.db', token, 'downloadDatabase');

export const downloadLiteLLMConfig = async (token: string) => 
	downloadFile('/litellm/config', 'config.yaml', token, 'downloadLiteLLMConfig');
