// Host a server-rendered `/pages/*` route inside a SvelteKit route.
//
// This is the mechanism behind HOLLOWING: a Svelte route keeps its address and
// the app chrome around it, gives up its own content, and renders the
// server-rendered page instead. See
// `docs/decisions/2026-08-08-hollowing-a-svelte-route.md`.
//
// `SetupDialog.svelte` has done this since the wizard cut over, showing a setup
// panel inside a `<dialog>`. Two callers is the point where a shared copy stops
// being premature — the same rule the swap prototype was held to. SetupDialog
// is NOT rewired onto this yet: it is guarded, load-bearing and working, so it
// adopts this when something else touches it rather than as drive-by surgery.
//
// THREE THINGS THIS GETS RIGHT, each because the obvious version is broken:
//
// 1. It extracts `<main>`, never the body. A `/pages/*` response is a whole
//    document — doctype, head, its own stylesheet links, `#toasts`. Injecting
//    the body grafts a second copy of the shell inside the first.
// 2. It snapshots `childNodes` before they are moved. The collection is LIVE,
//    so moving out of it while iterating skips every second node. This one is
//    silent: you get half a page and no error.
// 3. It sends the cookie. Server-rendered pages authenticate by cookie, because
//    they cannot read the localStorage token the SPA uses. `same-origin` is
//    what carries it.

import { pushState } from '$app/navigation';
import { page } from '$app/stores';

/** What a host needs to know after asking for a page. */
export type HostedPage =
	| { ok: true; nodes: Node[]; scripts: string[] }
	| { ok: false; reason: string; offSurface?: true };

const PAGES = '/pages/';

/** Every `src` already added to this document, so a second host does not refetch. */
const loaded = new Set<string>();

/**
 * Run the scripts a hosted page declared.
 *
 * A `<script>` that arrives through `DOMParser` NEVER executes — the spec says
 * so, and there is no error. The page renders, the script sits in the DOM inert,
 * and the enhancement it carried silently does not happen. Re-creating the
 * element is the only way to run it.
 *
 * `/pages/home` is the live example: it ships `home-greeting.js`, which corrects
 * the greeting to the reader's clock. Without this the hosted page would show
 * the server's guess forever and nothing would look broken.
 */
export function adoptScripts(srcs: string[]): void {
	for (const src of srcs) {
		if (loaded.has(src)) continue;
		loaded.add(src);
		const el = document.createElement('script');
		el.src = src;
		el.defer = true;
		document.head.appendChild(el);
	}
}

/**
 * Fetch a server-rendered page and return its `<main>` children.
 *
 * Returns a result rather than throwing, and rather than returning an empty
 * list on failure. A host that cannot tell "empty page" from "fetch failed"
 * renders an empty box either way, and an empty box is the failure mode nobody
 * reports — the same silent-degradation shape as a menu losing its positioning
 * when the CDN is blocked.
 */
export async function hostPage(url: string, init?: RequestInit): Promise<HostedPage> {
	let res: Response;
	try {
		res = await fetch(url, { credentials: 'same-origin', ...init });
	} catch (err) {
		return { ok: false, reason: `${err}` };
	}

	// Landing outside `/pages/` means the server redirected us elsewhere — a
	// signed-out reader is sent to sign in. That is not an error to render, it
	// is an instruction to follow, so it is reported separately.
	if (!new URL(res.url, location.href).pathname.startsWith(PAGES)) {
		return { ok: false, reason: 'off-surface', offSurface: true };
	}
	if (!res.ok) return { ok: false, reason: `${res.status} ${res.statusText}` };

	const doc = new DOMParser().parseFromString(await res.text(), 'text/html');
	const main = doc.querySelector('main');
	if (!main) return { ok: false, reason: 'no <main> in the response' };

	// Snapshot before the caller moves them. See note 2 above.
	return {
		ok: true,
		nodes: Array.from(main.childNodes),
		scripts: Array.from(
			doc.querySelectorAll('script[src]'),
			(s) => s.getAttribute('src') ?? ''
		).filter(Boolean)
	};
}

/** What a hollow needs to tell this module, and how it hears back. */
export type HollowOptions = {
	/** The server page to host, e.g. `/pages/calendar`. */
	page: string;
	/** The SPA address this route answers at, e.g. `/calendar`. */
	base: string;
	/** Called whenever the hollow starts or stops waiting. */
	onloading?: (loading: boolean) => void;
	/** Called with a reason when the page could not be hosted; `''` clears it. */
	onfailed?: (reason: string) => void;
};

/**
 * Host a server page inside a Svelte route, and keep it hosted.
 *
 * Used as an action, so a hollow is one attribute rather than a block of
 * lifecycle code repeated per route:
 *
 *   <div use:hollow={{ page: '/pages/calendar', base: '/calendar' }}></div>
 *
 * TWO JOBS, and the second is why this exists rather than a bare `onMount`.
 *
 * 1. `data-swap` marks the element a Startr Swap region, scoped to THIS page's
 *    own subtree. So `?month=` swaps in place and keeps the app chrome, while a
 *    link to another surface stays a real navigation — the SPA router's job,
 *    not ours. Before this, every in-page link walked the reader out to the
 *    bare server page and the sidebar vanished.
 *
 * 2. It takes the address bar off the library. Startr Swap would push the URL
 *    it fetched, `/pages/calendar?month=…`, and a raw `history.pushState` the
 *    SvelteKit router did not create desynchronises its history bookkeeping —
 *    a back button that silently stops working. Cancelling `swap:navigate` and
 *    calling SvelteKit's own shallow `pushState` keeps the router honest and
 *    shows the address people can share: `/calendar?month=…`.
 *
 * Back and forward then arrive as a `page` store update rather than a
 * `popstate`, which is also what re-hosts. That closes a bug the `onMount`
 * version had: `loaded` below is permanent for the document, so a second visit
 * re-injected the markup but skipped `adoptScripts`, and `home-greeting.js` —
 * an IIFE — never ran again. The greeting stayed at the server's guess and
 * nothing looked broken.
 */
export function hollow(node: HTMLElement, opts: HollowOptions) {
	let current = '';
	let dead = false;

	node.setAttribute('data-swap', opts.page);

	const load = async (search: string) => {
		const url = opts.page + search;
		if (url === current) return; // our own swap, arriving back through the store
		current = url;

		opts.onloading?.(true);
		const result = await hostPage(url);
		if (dead) return;
		opts.onloading?.(false);

		if (!result.ok) {
			// An off-surface redirect means the server sent us to sign in. The SPA
			// has its own guard for that, so saying nothing is right — a reader
			// mid-redirect should not be shown an error about it.
			if (!result.offSurface) opts.onfailed?.(result.reason);
			return;
		}
		opts.onfailed?.('');

		// `replaceChildren` rather than `innerHTML`: these are parsed nodes from a
		// document we fetched, and re-serialising them through a string would be a
		// second parse for nothing.
		node.replaceChildren(...result.nodes);
		// AFTER the markup lands, because a parsed <script> never runs and the
		// re-created one expects the elements it enhances to be present.
		adoptScripts(result.scripts);
	};

	const onNavigate = (e: Event) => {
		const next = new URL((e as CustomEvent<{ url: string }>).detail.url, location.href);
		e.preventDefault();
		// Claim it BEFORE pushing, so the store update this causes is recognised
		// as our own and does not refetch what is already on screen.
		current = opts.page + next.search;
		pushState(opts.base + next.search + next.hash, {});
	};

	node.addEventListener('swap:navigate', onNavigate);

	// THE STORE IS A SIGNAL, NOT THE ANSWER. Read the real address from
	// `location`, never from `$page.url`.
	//
	// A shallow `pushState` does not update `$page.url` the way an ordinary
	// navigation does, so the subscription fires carrying the address from BEFORE
	// the push. Trusting it meant every swap was chased by a fetch of the
	// un-parameterised page, which then replaced what had just been swapped in:
	// click Next twice on the calendar and the second click landed you back on
	// the current month. A single click hid it completely — the clobber arrives
	// after the new content, so anything looking straight after the click sees
	// the right answer.
	//
	// `location` cannot drift, because it IS what the push wrote.
	//
	// The address check also stops a fetch being started by the navigation that
	// LEAVES this route, which would land in a node already on its way out.
	// `trailingSlash` is 'ignore', so both spellings count as the same place.
	const here = (path: string) => path.replace(/\/$/, '') === opts.base.replace(/\/$/, '');
	const stop = page.subscribe(() => {
		if (here(location.pathname)) void load(location.search);
	});

	return {
		destroy() {
			dead = true;
			stop();
			node.removeEventListener('swap:navigate', onNavigate);
		}
	};
}

/**
 * The custom properties a `/pages/*` fragment expects and the SPA does not
 * define.
 *
 * Both live in `pages.css:35-36` and nowhere else. Set them on the host element
 * rather than adopting the whole stylesheet, which carries rules for `.btn`,
 * `dialog` and the page shell and would restyle the app around the hole.
 *
 * Keep this in step with `pages.css`. It is two lines of duplication, chosen
 * over a blast radius.
 */
export const PAGES_VARS =
	'--line: color-mix(in srgb, currentColor 18%, transparent);' +
	'--muted: color-mix(in srgb, currentColor 60%, transparent);';
