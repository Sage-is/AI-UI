// The community hub: where a model, prompt, chat or feedback set is shared, and
// where an installed model or prompt comes from. Every share and install path
// goes through here, so the hub's address, the origin check and the handshake
// word live in one place. Card "Community-share leak + dead wiring"; decisions 8
// (the address) and 9 (the word) in docs/community-hub.md, settled 2026-11-03.
import { get } from 'svelte/store';
import { config } from '$lib/stores';

// What the opened page posts back once it can take a message.
export const HUB_HANDSHAKE = 'loaded';
const DEFAULT_HUB_URL = 'https://community.sage.is';

/** The hub's address, COMMUNITY_HUB_URL on the server, with no trailing slash. */
export const hubUrl = (): string =>
	(get(config)?.features?.community_hub_url || DEFAULT_HUB_URL).replace(/\/+$/, '');

const sharingOn = (): boolean => Boolean(get(config)?.features?.enable_community_sharing);

/**
 * Open `path` on the hub and post `item` once that page says it is ready. The
 * item travels by postMessage to the hub's exact origin, never in the URL, where
 * logs and history keep it, and never to '*'. Only the tab opened here is heard.
 */
export const shareToHub = (path: string, item: unknown): void => {
	if (!sharingOn()) return;
	const origin = new URL(hubUrl()).origin;
	const tab = window.open(`${hubUrl()}${path}`, '_blank');
	if (!tab) return;
	const onMessage = (event: MessageEvent) => {
		if (event.source !== tab || event.origin !== origin || event.data !== HUB_HANDSHAKE) return;
		window.removeEventListener('message', onMessage);
		tab.postMessage(JSON.stringify(item), origin);
	};
	window.addEventListener('message', onMessage);
};

/**
 * The install side: when the hub opened this page, say it is ready and hand the
 * item the hub posts to `onItem`. Nothing listens while sharing is off, and only
 * the opener at the hub's origin is heard. Returns the cleanup for onDestroy.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- parsed JSON; the form it fills is reviewed before saving
export const receiveFromHub = (onItem: (item: any) => void): (() => void) => {
	const opener = window.opener;
	if (!sharingOn() || !opener) return () => {};
	const origin = new URL(hubUrl()).origin;
	const onMessage = (event: MessageEvent) => {
		if (event.source !== opener || event.origin !== origin) return;
		try {
			onItem(JSON.parse(event.data));
		} catch {
			// Not JSON, so not an item.
		}
	};
	window.addEventListener('message', onMessage);
	opener.postMessage(HUB_HANDSHAKE, origin);
	return () => window.removeEventListener('message', onMessage);
};
