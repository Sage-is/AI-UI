import { redirect } from '@sveltejs/kit';
import { getSessionUser } from '$lib/apis/auths';
import { getBackendConfig } from '$lib/apis';

export const ssr = false;
export const trailingSlash = 'ignore';

export const load = async ({ fetch, url }) => {
    let user = null;
    let config = null;

    // Always try to fetch config
    try {
        config = await getBackendConfig(fetch);
    } catch (e) {
        console.error('Failed to fetch backend config', e);
    }

    // Skip session check on auth/join pages to avoid unnecessary 403 errors
    if (!url.pathname.startsWith('/auth') && !url.pathname.startsWith('/join')) {
        try {
            user = await getSessionUser(fetch);
        } catch (error) {
            // User is not authenticated or session expired
            user = null;
        }
    }

    // Auth Guard: If not logged in and not on auth page/unprotected routes
    if (!user && !url.pathname.startsWith('/auth') && !url.pathname.startsWith('/join')) {
        throw redirect(303, '/auth');
    }

    // Auth Redirect: If logged in and on auth page, redirect to home
    if (user && url.pathname.startsWith('/auth')) {
        const redirectPath = url.searchParams.get('redirect') || '/';
        throw redirect(303, redirectPath);
    }

    return {
        user,
        config
    };
};
