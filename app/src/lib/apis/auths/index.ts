import { WEBUI_API_BASE_URL } from '$lib/constants';

async function api(url: string, method = 'GET', body?: any, context = '', customFetch = fetch) {
	try {
		const res = await customFetch(url, {
			method,
			credentials: 'include',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json'
			},
			...(method !== 'GET' && body && { body: JSON.stringify(body) })
		});

		if (!res.ok) throw await res.json();
		return res.json();
	} catch (err: any) {
		console.error(`[Auth API] ${context}:`, err);
		throw err.detail || err;
	}
}

export const getAdminDetails = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/admin/details`, 'GET', null, 'getAdminDetails');

export const getAdminConfig = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/admin/config`, 'GET', null, 'getAdminConfig');

export const updateAdminConfig = async (body: object) =>
	api(`${WEBUI_API_BASE_URL}/auths/admin/config`, 'POST', body, 'updateAdminConfig');

export const getSessionUser = async (customFetch = fetch) =>
	api(`${WEBUI_API_BASE_URL}/auths/`, 'GET', null, 'getSessionUser', customFetch);

export const ldapUserSignIn = async (user: string, password: string) =>
	api(`${WEBUI_API_BASE_URL}/auths/ldap`, 'POST', { user, password }, 'ldapUserSignIn');

export const getLdapConfig = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, 'GET', null, 'getLdapConfig');

export const updateLdapConfig = async (enable_ldap: boolean) =>
	api(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, 'POST', { enable_ldap }, 'updateLdapConfig');

export const getLdapServer = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, 'GET', null, 'getLdapServer');

export const updateLdapServer = async (body: object) =>
	api(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, 'POST', body, 'updateLdapServer');

export const userSignIn = async (email: string, password: string) =>
	api(`${WEBUI_API_BASE_URL}/auths/signin`, 'POST', { email, password }, 'userSignIn');

export const userSignUp = async (
	name: string,
	email: string,
	password: string,
	profile_image_url: string
) =>
	api(`${WEBUI_API_BASE_URL}/auths/signup`, 'POST', { name, email, password, profile_image_url }, 'userSignUp');

export const userSignOut = async () => {
	const result = await api(`${WEBUI_API_BASE_URL}/auths/signout`, 'GET', null, 'userSignOut');
	sessionStorage.clear();
	localStorage.removeItem('token');
	return result;
};

export const addUser = async (
	token: string,
	name: string,
	email: string,
	password: string,
	role: string = 'pending',
	profile_image_url: null | string = null
) =>
	api(`${WEBUI_API_BASE_URL}/auths/add`, 'POST', {
		name,
		email,
		password,
		role,
		...(profile_image_url && { profile_image_url })
	}, 'addUser');

export const updateUserProfile = async (name: string, profileImageUrl: string) =>
	api(`${WEBUI_API_BASE_URL}/auths/update/profile`, 'POST', {
		name,
		profile_image_url: profileImageUrl
	}, 'updateUserProfile');

export const updateUserPassword = async (password: string, newPassword: string) =>
	api(`${WEBUI_API_BASE_URL}/auths/update/password`, 'POST', {
		password,
		new_password: newPassword
	}, 'updateUserPassword');

export const claimAccount = async (email: string, password: string) =>
	api(`${WEBUI_API_BASE_URL}/auths/claim`, 'POST', { email, password }, 'claimAccount');

export const getSignUpEnabledStatus = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/signup/enabled`, 'GET', null, 'getSignUpEnabledStatus');

export const getDefaultUserRole = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, 'GET', null, 'getDefaultUserRole');

export const updateDefaultUserRole = async (role: string) =>
	api(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, 'POST', { role }, 'updateDefaultUserRole');

export const toggleSignUpEnabledStatus = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/signup/enabled/toggle`, 'GET', null, 'toggleSignUpEnabledStatus');

export const getJWTExpiresDuration = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/token/expires`, 'GET', null, 'getJWTExpiresDuration');

export const updateJWTExpiresDuration = async (duration: string) =>
	api(`${WEBUI_API_BASE_URL}/auths/token/expires/update`, 'POST', { duration }, 'updateJWTExpiresDuration');

export const createAPIKey = async () => {
	const res = await api(`${WEBUI_API_BASE_URL}/auths/api_key`, 'POST', null, 'createAPIKey');
	return res.api_key;
};

export const getAPIKey = async () => {
	const res = await api(`${WEBUI_API_BASE_URL}/auths/api_key`, 'GET', null, 'getAPIKey');
	return res.api_key;
};

export const deleteAPIKey = async () =>
	api(`${WEBUI_API_BASE_URL}/auths/api_key`, 'DELETE', null, 'deleteAPIKey');
