import { WEBUI_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

const api = createApiHelper('MagicLinks', WEBUI_API_BASE_URL);

export const createMagicLink = async (token: string, data: object) =>
	api('/magic-links/create', 'POST', data, token, 'createMagicLink');

export const getMagicLinks = async (token: string) =>
	api('/magic-links/', 'GET', undefined, token, 'getMagicLinks');

export const getMagicLinkById = async (token: string, id: string) =>
	api(`/magic-links/${id}`, 'GET', undefined, token, `getMagicLinkById(${id})`);

export const deactivateMagicLink = async (token: string, id: string) =>
	api(`/magic-links/${id}/deactivate`, 'POST', undefined, token, `deactivateMagicLink(${id})`);

export const deleteMagicLink = async (token: string, id: string) =>
	api(`/magic-links/${id}`, 'DELETE', undefined, token, `deleteMagicLink(${id})`);

export const redeemMagicLink = async (linkToken: string, name?: string) =>
	api('/magic-links/redeem', 'POST', { token: linkToken, name }, '', 'redeemMagicLink');
