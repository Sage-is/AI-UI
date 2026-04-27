/**
 * Provider-agnostic analytics shim for try.sage and the broader app.
 *
 * Why this shape:
 *   - One module, three providers (Matomo, Google Analytics 4, Plausible).
 *     We deliberately use each provider's official `<script>` snippet
 *     rather than wrapping a JS SDK. This avoids npm dependencies, keeps
 *     bundle size flat, and matches the user's "no library" preference.
 *     Each provider exposes a stable global (`_paq`, `gtag`, `plausible`)
 *     once its tracker is loaded; we just push to those globals.
 *
 *   - All providers are guarded by config presence. If a provider's
 *     config block is missing or empty, no script tag is injected and no
 *     network request fires — the functions are no-ops. This lets us
 *     ship the shim wired into the boot path without leaking traffic to
 *     anyone who has not opted in.
 *
 *   - `initAnalytics` is idempotent. The config store can re-emit after
 *     admin edits (or hot-reload during dev), and we should not
 *     double-inject script tags. Module-level booleans track
 *     per-provider initialization.
 *
 *   - `pageview` exists because SvelteKit does not fire native browser
 *     pageviews on client-side route transitions — only on the initial
 *     hard load. Without an explicit virtual-pageview call hooked into
 *     `afterNavigate`, every provider will under-count.
 *
 *   - Failures are silent. If a `<script>` tag fails to load (network
 *     error, ad-blocker), `track`/`pageview` skip that provider rather
 *     than throw — analytics must never break the app.
 *
 * Canonical try.sage event vocabulary. Other components import `track`
 * and emit these event names. Keep this list in sync with
 * docs/try-sage-analytics.md.
 *
 *   - try_sage.banner_impression       — banner first render in a session
 *   - try_sage.persona_switch          — props: { from, to }
 *   - try_sage.tutorial.step_view      — props: { step_id, index }
 *   - try_sage.tutorial.complete       — full tutorial finished
 *   - try_sage.tutorial.dismiss        — props: { step_id, dismissed_remaining }
 *   - try_sage.admin.extend            — admin clicked extend
 *   - try_sage.admin.reset             — admin clicked reset
 *   - try_sage.feature.first_use       — props: { feature: model_switch | chat_map | artifacts | agent_create }
 */

import { get } from 'svelte/store';
import { config } from '$lib/stores';

export type AnalyticsEvent = {
	name: string;
	props?: Record<string, string | number | boolean>;
};

// Per-provider init flags. Idempotency is enforced here: the script tag
// is injected at most once, even if `initAnalytics` is called every time
// the config store re-emits.
let matomoInited = false;
let gaInited = false;
let plausibleInited = false;

// SSR guard. The shim only runs in the browser; `window`/`document`
// access during SvelteKit's prerender pass would crash the build.
function isBrowser(): boolean {
	return typeof window !== 'undefined' && typeof document !== 'undefined';
}

/**
 * Inject a `<script>` tag into <head>. Returns the element so callers
 * can attach attributes (e.g. Plausible's `data-domain`). The `async`
 * flag keeps the tracker out of the critical render path.
 */
function injectScript(src: string, attrs: Record<string, string> = {}): HTMLScriptElement | null {
	if (!isBrowser()) return null;
	const s = document.createElement('script');
	s.src = src;
	s.async = true;
	for (const [k, v] of Object.entries(attrs)) {
		s.setAttribute(k, v);
	}
	// Failure is silent — `onerror` swallows the event so a missing
	// tracker (network blocked, DNS, ad-blocker) never throws.
	s.onerror = () => {
		/* noop */
	};
	document.head.appendChild(s);
	return s;
}

/**
 * Matomo bootstrap. Pushes the standard config commands to `_paq`
 * before injecting `matomo.js`. The tracker reads the queue once it
 * loads, so the order does not matter — only that everything ends up
 * on `_paq` eventually.
 */
function initMatomo(url: string, siteId: string): void {
	if (matomoInited || !isBrowser()) return;

	// `_paq` is Matomo's command queue. Create it if missing.
	const w = window as unknown as { _paq?: unknown[] };
	w._paq = w._paq || [];
	const paq = w._paq as unknown[];

	// Normalize trailing slash so `${url}/matomo.php` always resolves.
	const base = url.replace(/\/+$/, '');

	paq.push(['setSiteId', siteId]);
	paq.push(['setTrackerUrl', `${base}/matomo.php`]);
	paq.push(['enableLinkTracking']);

	injectScript(`${base}/matomo.js`);
	matomoInited = true;
}

/**
 * Google Analytics 4 bootstrap. Loads gtag.js for the given measurement
 * ID, then defines the `gtag` shim that buffers events into `dataLayer`
 * until the script finishes loading.
 */
function initGA(measurementId: string): void {
	if (gaInited || !isBrowser()) return;

	injectScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`);

	// Define `gtag` and seed the dataLayer. This is the canonical
	// snippet from Google's install instructions.
	const w = window as unknown as {
		dataLayer?: unknown[];
		gtag?: (...args: unknown[]) => void;
	};
	w.dataLayer = w.dataLayer || [];
	w.gtag =
		w.gtag ||
		function gtag(...args: unknown[]) {
			(w.dataLayer as unknown[]).push(args);
		};
	w.gtag('js', new Date());
	w.gtag('config', measurementId);

	gaInited = true;
}

/**
 * Plausible bootstrap. Plausible's tracker auto-attaches `window.plausible`
 * once loaded; we only need to inject the `<script>` with the right
 * `data-domain`. Custom `script_url` is supported for self-hosted
 * Plausible or proxy setups.
 */
function initPlausible(domain: string, scriptUrl?: string): void {
	if (plausibleInited || !isBrowser()) return;

	const src = scriptUrl || 'https://plausible.io/js/script.js';
	const s = injectScript(src, { 'data-domain': domain });
	if (s) s.defer = true;

	plausibleInited = true;
}

/**
 * Initialize analytics providers based on the current config. Idempotent —
 * safe to call multiple times. Reads `$config.analytics` and injects the
 * required <script> tags into <head> for any provider whose config is
 * non-empty. Wires `_paq` (Matomo), `gtag` (GA), and Plausible's data
 * attribute.
 */
export function initAnalytics(): void {
	if (!isBrowser()) return;

	const cfg = get(config);
	const a = cfg?.analytics;
	if (!a) return;

	if (a.matomo?.url && a.matomo?.site_id) {
		initMatomo(a.matomo.url, a.matomo.site_id);
	}
	if (a.ga?.measurement_id) {
		initGA(a.ga.measurement_id);
	}
	if (a.plausible?.domain) {
		initPlausible(a.plausible.domain, a.plausible.script_url);
	}
}

/**
 * Fire a tracked event to every enabled provider. Each dispatch is
 * wrapped in try/catch — a broken tracker must never bubble up to the
 * caller. Providers that are not initialized are silently skipped.
 */
export function track(event: AnalyticsEvent): void {
	if (!isBrowser()) return;

	const props = event.props ?? {};

	// Matomo: trackEvent uses category/action/name. We map our flat
	// dotted event names to a single category ("event") and pass the
	// full name as the action so the dashboard groups them naturally.
	if (matomoInited) {
		try {
			const w = window as unknown as { _paq?: unknown[] };
			const paq = w._paq;
			if (Array.isArray(paq)) {
				paq.push(['trackEvent', 'event', event.name, JSON.stringify(props)]);
			}
		} catch {
			/* swallow */
		}
	}

	// GA4: gtag('event', name, params). GA4 silently ignores unknown
	// param keys, so we forward props as-is.
	if (gaInited) {
		try {
			const w = window as unknown as { gtag?: (...args: unknown[]) => void };
			w.gtag?.('event', event.name, props);
		} catch {
			/* swallow */
		}
	}

	// Plausible: window.plausible(name, { props }). The global only
	// exists once the tracker has loaded; guard against the race.
	if (plausibleInited) {
		try {
			const w = window as unknown as {
				plausible?: (name: string, options?: { props?: Record<string, unknown> }) => void;
			};
			w.plausible?.(event.name, { props });
		} catch {
			/* swallow */
		}
	}
}

/**
 * Track a virtual pageview. SvelteKit does not fire native pageviews on
 * client-side route transitions, so we call this on `afterNavigate`.
 * `title` is optional — providers fall back to `document.title`.
 */
export function pageview(path: string, title?: string): void {
	if (!isBrowser()) return;

	const pageTitle = title ?? document.title;

	if (matomoInited) {
		try {
			const w = window as unknown as { _paq?: unknown[] };
			const paq = w._paq;
			if (Array.isArray(paq)) {
				// `setCustomUrl` + `setDocumentTitle` + `trackPageView` is
				// the documented pattern for SPA pageviews.
				paq.push(['setCustomUrl', path]);
				paq.push(['setDocumentTitle', pageTitle]);
				paq.push(['trackPageView']);
			}
		} catch {
			/* swallow */
		}
	}

	if (gaInited) {
		try {
			const w = window as unknown as { gtag?: (...args: unknown[]) => void };
			// GA4's recommended SPA pageview pattern.
			w.gtag?.('event', 'page_view', {
				page_path: path,
				page_title: pageTitle
			});
		} catch {
			/* swallow */
		}
	}

	if (plausibleInited) {
		try {
			const w = window as unknown as {
				plausible?: (name: string, options?: { u?: string }) => void;
			};
			// Plausible's manual pageview API: emit a "pageview" event
			// with the full URL so referrer/path attribution stays
			// consistent with the auto-tracker.
			w.plausible?.('pageview', { u: window.location.origin + path });
		} catch {
			/* swallow */
		}
	}
}
