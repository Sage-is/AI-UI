import { WEBUI_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

// Centralized API helper for groups module
const api = createApiHelper('Groups', WEBUI_API_BASE_URL);

export const createNewGroup = async (token: string, group: object) =>
	api('/groups/create', 'POST', group, token, 'createNewGroup');

export const getGroups = async (token: string = '') =>
	api('/groups/', 'GET', undefined, token, 'getGroups');

export const getGroupById = async (token: string, id: string) =>
	api(`/groups/id/${id}`, 'GET', undefined, token, `getGroupById(${id})`);

export const updateGroupById = async (token: string, id: string, group: object) =>
	api(`/groups/id/${id}/update`, 'POST', group, token, `updateGroupById(${id})`);

export const deleteGroupById = async (token: string, id: string) =>
	api(`/groups/id/${id}/delete`, 'DELETE', undefined, token, `deleteGroupById(${id})`);
