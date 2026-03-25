import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getUserPosition } from '$lib/utils';

async function api(url: string, token: string, method = 'GET', body?: any, context = '') {
	try {
		const res = await fetch(url, {
			method,
			credentials: 'include',
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
		console.error(`[Users API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const getUserGroups = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/users/groups`, token, 'GET', null, 'getUserGroups');

export const getUserDefaultPermissions = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/users/default/permissions`, token, 'GET', null, 'getUserDefaultPermissions');

export const updateUserDefaultPermissions = async (token: string, permissions: object) =>
	api(`${WEBUI_API_BASE_URL}/users/default/permissions`, token, 'POST', permissions, 'updateUserDefaultPermissions');

export const updateUserRole = async (token: string, id: string, role: string) =>
	api(`${WEBUI_API_BASE_URL}/users/update/role`, token, 'POST', { id, role }, 'updateUserRole');

export const getUsers = async (
	token: string,
	query?: string,
	orderBy?: string,
	direction?: string,
	page = 1
) => {
	const searchParams = new URLSearchParams();
	searchParams.set('page', `${page}`);
	if (query) searchParams.set('query', query);
	if (orderBy) searchParams.set('order_by', orderBy);
	if (direction) searchParams.set('direction', direction);

	return api(`${WEBUI_API_BASE_URL}/users/?${searchParams.toString()}`, token, 'GET', null, 'getUsers');
};

export const getAllUsers = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/users/all`, token, 'GET', null, 'getAllUsers');

export const getManagedUsers = async (
	token: string,
	query?: string,
	orderBy?: string,
	direction?: string,
	page = 1
) => {
	const searchParams = new URLSearchParams();
	searchParams.set('page', `${page}`);
	if (query) searchParams.set('query', query);
	if (orderBy) searchParams.set('order_by', orderBy);
	if (direction) searchParams.set('direction', direction);

	return api(`${WEBUI_API_BASE_URL}/users/managed?${searchParams.toString()}`, token, 'GET', null, 'getManagedUsers');
};

export const getUserSettings = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/users/user/settings`, token, 'GET', null, 'getUserSettings');

export const updateUserSettings = async (token: string, settings: object) =>
	api(`${WEBUI_API_BASE_URL}/users/user/settings/update`, token, 'POST', settings, 'updateUserSettings');

export const getUserById = async (token: string, userId: string) =>
	api(`${WEBUI_API_BASE_URL}/users/${userId}`, token, 'GET', null, 'getUserById');

export const getUserInfo = async (token: string) =>
	api(`${WEBUI_API_BASE_URL}/users/user/info`, token, 'GET', null, 'getUserInfo');

export const updateUserInfo = async (token: string, info: object) =>
	api(`${WEBUI_API_BASE_URL}/users/user/info/update`, token, 'POST', info, 'updateUserInfo');

export const getAndUpdateUserLocation = async (token: string) => {
	const location = await getUserPosition().catch((err) => {
		console.error(err);
		return null;
	});

	if (location) {
		await updateUserInfo(token, { location: location });
		return location;
	} else {
		console.info('Failed to get user location');
		return null;
	}
};

export const getUserActiveStatusById = async (token: string, userId: string) =>
	api(`${WEBUI_API_BASE_URL}/users/${userId}/active`, token, 'GET', null, 'getUserActiveStatusById');

export const deleteUserById = async (token: string, userId: string) =>
	api(`${WEBUI_API_BASE_URL}/users/${userId}`, token, 'DELETE', null, 'deleteUserById');

type UserUpdateForm = {
	role: string;
	profile_image_url: string;
	email: string;
	name: string;
	password: string;
};

export const updateUserById = async (token: string, userId: string, user: UserUpdateForm) =>
	api(`${WEBUI_API_BASE_URL}/users/${userId}/update`, token, 'POST', {
		profile_image_url: user.profile_image_url,
		role: user.role,
		email: user.email,
		name: user.name,
		password: user.password !== '' ? user.password : undefined
	}, 'updateUserById');
