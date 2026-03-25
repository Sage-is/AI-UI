import { WEBUI_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

// Create standardized API helper for tools with enhanced error reporting
const api = createApiHelper('TOOLS', WEBUI_API_BASE_URL, '/tools');

export const getTools = async (token: string = '') =>
	api('/', 'GET', undefined, token, 'getTools');
