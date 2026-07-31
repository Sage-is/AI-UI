<script lang="ts">
	// The setup wizard, as a native dialog around server-rendered routes.
	//
	// This replaces `ChangesAndSetupModal.svelte` and the nine step components it
	// mounted — 2,132 lines of Svelte for nine panels that now exist as ordinary
	// pages under `/pages/admin/setup/`. Nothing here renders a panel. It fetches
	// one, lifts it out of the response and shows it, which is why the whole host
	// fits in one file: every panel's markup, validation, defaults and save path
	// live on the server, in one language, tested by the specs that already point
	// at those routes.
	//
	// A native `<dialog>` rather than `Modal.svelte`, because the element already
	// does what that component hand-rolls: Escape to close, focus trapped inside,
	// everything behind it inert, and a `::backdrop` that needs no fixed-position
	// overlay. Those are four behaviours we no longer maintain.
	//
	// EXTRACTED, NOT FRAMED. The panel is lifted into this document rather than
	// shown in an iframe, so the wizard specs keep reaching their `data-cy` hooks
	// with a plain `cy.get`, and so an operator's Content-Security-Policy has no
	// say in whether the wizard works. The cost is that the two documents share a
	// stylesheet: startr.style is already loaded by `app.html`, and the nine setup
	// panels carry no CSS classes at all — every one of them is inline props —
	// so what `pages.css` still owns for them is `--line` and the three pager
	// rules, both reproduced in the scoped block below. That was measured, not
	// assumed; a panel that grows a class will need this revisited.
	//
	// WHAT THE SERVER DECIDES. Where the flow ends is a redirect, not a flag: a
	// response that lands outside `/pages/` means the errand is over, and this
	// closes. `/pages/changelog/seen` and `/pages/admin/setup/complete/finish`
	// both redirect to `/`, so a reader with no JavaScript gets the same ending —
	// back in the app — rather than a dead end.

	import { getContext } from 'svelte';

	import Icon from '$lib/components/Icon.svelte';
	import { getUserSettings } from '$lib/apis/users';
	import { config, settings, setupTriggerReason, user } from '$lib/stores';
	import type { SetupTriggerReason } from '$lib/stores';

	const i18n = getContext<any>('i18n');

	export let show = false;

	const PAGES = '/pages/';
	const SETUP = '/pages/admin/setup/';

	let dialog: HTMLDialogElement;
	let content: HTMLDivElement;
	let opened = false;
	let failed = '';

	/** Scripts a panel asked for. Loaded once each and left in place. */
	const loaded = new Set<string>();

	// Kept from the modal verbatim, including the reasoning: the changelog branch
	// also lives here, and a trial-mode reader still benefits from release notes
	// when the version bumps. Suppressing only the wizard branch keeps the
	// changelog alive while stopping the setup wizard opening itself in a
	// workshop. `manualTrigger` lets the TrialMode admin tab re-open it anyway —
	// the operator opting in beats the gate.
	function needsWizard(reason: SetupTriggerReason): boolean {
		if ($config?.try_sage?.enabled && !reason.manualTrigger) return false;
		return reason.needsModels || reason.needsUsers || reason.manualTrigger;
	}

	/**
	 * Which route this opens on.
	 *
	 * A reader who is not an admin only ever gets the release notes, and gets
	 * them from the route that does not require an admin. Settings, About,
	 * "See what's new" is a control everybody has, and before the wizard moved to
	 * the server it opened a component with no role check at all — pointing it at
	 * the admin tree would have turned that button into a 403.
	 */
	function startUrl(reason: SetupTriggerReason): string {
		// The language the reader is already using, so the panel arrives in it.
		// `?lang=` rather than a cookie keeps each rendering cacheable on its own
		// address; every link and form inside the panel carries it onward.
		const lang = $i18n?.language ? `?lang=${encodeURIComponent($i18n.language)}` : '';
		if ($user?.role !== 'admin') return `${PAGES}changelog${lang}`;
		if (reason.hasChangelog) return `${SETUP}changelog${lang}`;
		return `${SETUP}${needsWizard(reason) ? 'welcome' : 'changelog'}${lang}`;
	}

	/** Run the scripts a panel declared. A parsed `<script>` never executes. */
	function adoptScripts(doc: Document) {
		doc.querySelectorAll('script[src]').forEach((tag) => {
			const src = tag.getAttribute('src');
			if (!src || loaded.has(src)) return;
			loaded.add(src);
			const el = document.createElement('script');
			el.src = src;
			el.defer = true;
			// Announce again on load. The script arrives after the panel it belongs
			// to, so the swap signal below has already fired and been missed — and
			// for the changelog pager that signal is what puts its button in the
			// starting position.
			el.addEventListener('load', announce);
			document.head.appendChild(el);
		});
	}

	/** Tell any panel script that the DOM under it just changed. */
	function announce() {
		document.dispatchEvent(new CustomEvent('pages:panel'));
	}

	async function load(url: string, init?: RequestInit) {
		let res: Response;
		try {
			res = await fetch(url, { credentials: 'same-origin', ...init });
		} catch (err) {
			failed = `${err}`;
			return;
		}

		// Off the pages surface: the server says the errand is finished. Checked
		// before `res.ok`, because this is the success path, not a failure.
		if (!new URL(res.url, location.href).pathname.startsWith(PAGES)) {
			close();
			return;
		}
		if (!res.ok) {
			failed = `${res.status} ${res.statusText}`;
			return;
		}

		const doc = new DOMParser().parseFromString(await res.text(), 'text/html');
		const main = doc.querySelector('main');
		if (!main) {
			failed = $i18n.t('That page could not be displayed here.');
			return;
		}
		// The ui-Sprig marketplace slot belongs to a page, not to a wizard step.
		main.querySelector('#sprig-ui-slot')?.remove();

		failed = '';
		// Snapshot before moving: `childNodes` is live, and moving out of it while
		// iterating skips every second node.
		content.replaceChildren(...Array.from(main.childNodes));
		adoptScripts(doc);
		announce();
	}

	function openDialog() {
		opened = true;
		failed = '';
		// Shown before the fetch, not after. A reader who presses the button gets
		// the dialog immediately and watches the panel land in it; opening only
		// once the response is in means the button does nothing at all for a round
		// trip, which on a slow connection reads as a broken control.
		if (!dialog.open) dialog.showModal();
		load(startUrl($setupTriggerReason));
	}

	function close() {
		if (dialog?.open) dialog.close();
		// Not left to the `close` event. That event is queued as a task rather than
		// fired inline, and the element unmounts as soon as `show` goes false, so
		// waiting for it would drop the settings refresh below on the floor.
		// `closed` guards on `opened`, so the event arriving afterwards is a no-op.
		closed();
	}

	async function closed() {
		if (!opened) return;
		opened = false;
		show = false;
		// The server owns `setupCompleted` and the changelog read marker now, so
		// this re-reads them rather than writing what it assumes was stored. The
		// modal set both locally and posted them, which is two sources of truth
		// for one fact.
		const fresh = await getUserSettings('').catch(() => null);
		if (fresh?.ui) settings.set(fresh.ui);
	}

	function onClick(event: MouseEvent) {
		const target = event.target as Element | null;
		const link = target?.closest?.('a[href]') as HTMLAnchorElement | null;
		if (!link) return;
		const url = new URL(link.href, location.href);
		// Anything pointing off this surface is a real link and keeps working.
		if (url.origin !== location.origin || !url.pathname.startsWith(PAGES)) return;
		event.preventDefault();
		load(url.pathname + url.search);
	}

	function onSubmit(event: SubmitEvent) {
		const form = event.target as HTMLFormElement;
		if (!(form instanceof HTMLFormElement)) return;
		event.preventDefault();
		// `formaction` is how the search-audio panel puts two different actions on
		// one form, so the button that was pressed decides where this goes.
		const submitter = event.submitter as HTMLElement | null;
		const action =
			submitter?.getAttribute('formaction') ?? form.getAttribute('action') ?? location.pathname;
		const method = (
			submitter?.getAttribute('formmethod') ??
			form.getAttribute('method') ??
			'post'
		).toUpperCase();
		// The submitter is passed so its own name and value are included, exactly
		// as a real submit would.
		const data = new FormData(form, submitter as never);
		if (method === 'GET') {
			load(`${action}?${new URLSearchParams(data as never)}`);
			return;
		}
		load(action, { method, body: data });
	}

	/**
	 * Delegate clicks and submits from the injected panel.
	 *
	 * An action rather than `onMount`, because the dialog is only in the DOM while
	 * it is open — `onMount` runs once, when there is nothing to attach to. In
	 * code rather than `on:` directives, because this is delegation on a plain
	 * container, which the a11y lint reads as a click handler on a div, and
	 * because the submit path needs the raw event for `submitter`.
	 */
	function delegate(node: HTMLElement) {
		node.addEventListener('click', onClick);
		node.addEventListener('submit', onSubmit);
		return {
			destroy() {
				node.removeEventListener('click', onClick);
				node.removeEventListener('submit', onSubmit);
			}
		};
	}

	$: if (dialog && content && show && !opened) openDialog();
	$: if (dialog && !show && opened) close();
</script>

<!-- Only in the DOM while it is open.
	 A `<dialog>` left mounted and closed still renders its children, which put
	 `setup-dialog`, `setup-close` and `setup-content` on EVERY page of the app —
	 caught by the surface-parity gate, which found three controls on the SvelteKit
	 side that no server-rendered page had. The deleted modal was conditional for
	 the same reason and this matches it. -->
{#if show}
	<!-- `--m:auto` is NOT redundant. The UA stylesheet centres a modal dialog with
		 `inset: 0` and `margin: auto`, so this should be free — and measured in a
		 real browser it is not: without it the dialog sits at 0,0 with 557px of
		 slack on the right. With it, 278/278 and 54/54 on a 1440x900 viewport.
		 Something in the loaded sheets defeats the UA margin; whatever it is, do
		 not delete this on the theory that the element handles it. -->
	<dialog
		bind:this={dialog}
		data-cy="setup-dialog"
		aria-label={$i18n.t('Setup')}
		on:close={closed}
		style="--m:auto; --w:min(46rem, 92vw); --maxh:88vh; --p:1rem; --br:1rem; --b:0; --bg:var(--white); --dark-bg:var(--color-gray-900); --c:var(--color-gray-800); --dark-c:var(--color-gray-100)"
	>
		<div style="--d:flex; --jc:flex-end">
			<button
				data-cy="setup-close"
				aria-label={$i18n.t('Close')}
				on:click={() => close()}
				style="--cur:pointer"
			>
				<Icon name="x-mark" strokeWidth="2" className={'size-5'} />
			</button>
		</div>

		{#if failed}
			<p data-cy="setup-error" style="--size:.85rem; --op:.75">
				{failed}
			</p>
		{/if}

		<div bind:this={content} use:delegate data-cy="setup-content"></div>
	</dialog>
{/if}

<style>
	/* What the panels still need from pages.css, and nothing more.
	   The nine setup panels carry no CSS classes — they are inline props end to
	   end — so loading that whole stylesheet into the app document would import
	   its `:root { color-scheme: light dark }` and hand every form control in the
	   app to the OS theme instead of the app's. These are the two rules the
	   panels actually use, scoped to the dialog.

	   `color-scheme` is also why the element above sets its own text colour: at a
	   route the panels inherit readable text from that `:root` rule, and here
	   there is nothing to inherit it from. */
	dialog {
		--line: color-mix(in srgb, currentColor 18%, transparent);
		overflow-y: auto;
	}

	dialog::backdrop {
		background: rgb(0 0 0 / 0.6);
	}

	/* The changelog pager. The button's side depends on runtime state, which an
	   inline prop cannot express — see changelog-pager.js. */
	dialog :global([data-pager-row]) {
		display: flex;
		width: 100%;
	}

	dialog :global([data-pager-row] > button) {
		margin-left: auto;
	}

	dialog :global([data-pager-row][data-at-end='false'] > button) {
		margin-left: 0;
	}
</style>
