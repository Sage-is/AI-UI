import { IMAGES_API_BASE_URL } from '$lib/constants';
import { createApiHelper } from '../base';

// Centralized API helper for images module
const api = createApiHelper('Images', IMAGES_API_BASE_URL);

export const getConfig = async (token: string = '') =>
	api('/config', 'GET', undefined, token, 'getConfig');

export const updateConfig = async (token: string = '', config: object) =>
	api('/config/update', 'POST', config, token, 'updateConfig');

export const verifyConfigUrl = async (token: string = '') =>
	api('/config/url/verify', 'GET', undefined, token, 'verifyConfigUrl');

export const getImageGenerationConfig = async (token: string = '') =>
	api('/image/config', 'GET', undefined, token, 'getImageGenerationConfig');

export const updateImageGenerationConfig = async (token: string = '', config: object) =>
	api('/image/config/update', 'POST', config, token, 'updateImageGenerationConfig');

export const getImageGenerationModels = async (token: string = '') =>
	api('/models', 'GET', undefined, token, 'getImageGenerationModels');

export const imageGenerations = async (token: string = '', prompt: string) =>
	api('/generations', 'POST', { prompt }, token, 'imageGenerations');
