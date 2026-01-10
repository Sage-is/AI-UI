import { WEBUI_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

// Create standardized API helper for tools with enhanced error reporting
const api = createApiHelper('TOOLS', WEBUI_API_BASE_URL, '/tools');

export const createNewTool = async (token: string, tool: object) => 
	api('/create', 'POST', tool, token, 'createNewTool');

export const loadToolByUrl = async (token: string = '', url: string) => 
	api('/load/url', 'POST', { url }, token, `loadToolByUrl(${url})`);

export const getTools = async (token: string = '') => 
	api('/', 'GET', undefined, token, 'getTools');

export const getToolList = async (token: string = '') => 
	api('/list', 'GET', undefined, token, 'getToolList');

export const exportTools = async (token: string = '') => 
	api('/export', 'GET', undefined, token, 'exportTools');

export const getToolById = async (token: string, id: string) => 
	api(`/id/${id}`, 'GET', undefined, token, `getToolById(${id})`);

export const updateToolById = async (token: string, id: string, tool: object) => 
	api(`/id/${id}/update`, 'POST', tool, token, `updateToolById(${id})`);

export const deleteToolById = async (token: string, id: string) => 
	api(`/id/${id}/delete`, 'DELETE', undefined, token, `deleteToolById(${id})`);

export const getToolValvesById = async (token: string, id: string) => 
	api(`/id/${id}/valves`, 'GET', undefined, token, `getToolValvesById(${id})`);

export const getToolValvesSpecById = async (token: string, id: string) => 
	api(`/id/${id}/valves/spec`, 'GET', undefined, token, `getToolValvesSpecById(${id})`);

export const updateToolValvesById = async (token: string, id: string, valves: object) => 
	api(`/id/${id}/valves/update`, 'POST', valves, token, `updateToolValvesById(${id})`);

export const getUserValvesById = async (token: string, id: string) => 
	api(`/id/${id}/valves/user`, 'GET', undefined, token, `getUserValvesById(${id})`);

export const getUserValvesSpecById = async (token: string, id: string) => 
	api(`/id/${id}/valves/user/spec`, 'GET', undefined, token, `getUserValvesSpecById(${id})`);

export const updateUserValvesById = async (token: string, id: string, valves: object) => 
	api(`/id/${id}/valves/user/update`, 'POST', valves, token, `updateUserValvesById(${id})`);
