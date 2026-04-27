/**
 * try.sage personas store hydration helpers.
 *
 * Lives outside the API client (`$lib/apis/sage-runtime`) so the API
 * client stays a thin transport layer. This module owns the store-side
 * concerns: when to fetch, when to invalidate, how to recover from a
 * 404 (try mode disabled).
 */

import { get } from 'svelte/store';
import { tryPersonas, config } from '$lib/stores';
import { getPersonas } from '$lib/apis/sage-runtime';

/**
 * Fetch the persona list and write it to the store. Caller passes the
 * auth token; anonymous callers should not invoke this — the endpoint
 * still works without auth when try mode is on, but a missing token
 * keeps the API helper consistent with everything else in the codebase.
 *
 * Silent on 404: a 404 means try mode is off and the personas store
 * should stay null. Other errors surface to the caller.
 */
export async function loadPersonas(token: string): Promise<void> {
	// Skip the network round-trip when try mode is known to be off.
	const cfg = get(config);
	if (cfg && cfg.features?.enable_try_sage === false) {
		tryPersonas.set(null);
		return;
	}

	try {
		const list = await getPersonas(token);
		tryPersonas.set(list);
	} catch (err: any) {
		// 404 → try mode is off on the backend. Treat as "no personas".
		if (err?.status === 404 || err?.detail?.includes?.('Not Found')) {
			tryPersonas.set(null);
			return;
		}
		throw err;
	}
}

/**
 * Force a re-fetch on the next access. Called after admin extend/reset
 * so the banner and switcher pick up rotated magic-link URLs.
 */
export function invalidatePersonas(): void {
	tryPersonas.set(null);
}
