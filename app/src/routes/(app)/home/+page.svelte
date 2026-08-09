<script lang="ts">
	// HOLLOWED, 2026-08-08. This route keeps its address and the app chrome
	// around it, and hosts the server-rendered `/pages/home` instead of
	// rendering its own dashboard.
	//
	// WHY, and it is not a payload argument. `render_page` emits the ui-Sprig™
	// marketplace slot, and only `pages/` calls `render_page` — so a grafted
	// interface fragment could not reach the screen a person opens first. This
	// route could not simply be REPLACED either: it lives in the `(app)` group,
	// so a bare server-rendered page would cost the reader the sidebar, the chat
	// list and the navigation.
	//
	// Hollowing is the third mode: keep the frame, host the content. One
	// implementation of the dashboard, at the address people already use.
	// Reasoning and the two-mode rule:
	// `docs/decisions/2026-08-08-hollowing-a-svelte-route.md`.
	//
	// IT COSTS BYTES. This boots the SPA floor and then fetches a page on top —
	// strictly more than either alone. Hollowing buys reach and a single
	// implementation, never payload. The bytes come back when the hollow comes
	// down, which happens once the chat core is server-rendered and the sidebar
	// no longer needs the SPA.
	//
	// The 215-line dashboard this replaced lives on in `pages/templates/home.html`
	// and `pages/home_panel.py`. Recover it from git if the hollow is reversed.
	import { getContext } from 'svelte';
	import { hollow, PAGES_VARS } from '$lib/utils/pageHost';

	const i18n = getContext('i18n');

	let failed = '';
	let loading = true;
</script>

<div style="--maxw:56rem; --mx:auto; --px:1.5rem; --py:2rem">
	<!-- The hollow. `#sprig-ui-slot` arrives inside this, deliberately kept:
	     SetupDialog strips it because a wizard step is not a page, and a home
	     screen is. -->
	<div
		data-cy="home-host"
		use:hollow={{
			page: '/pages/home',
			base: '/home',
			onloading: (v) => (loading = v),
			onfailed: (v) => (failed = v)
		}}
		style={PAGES_VARS}
	></div>

	{#if loading}
		<p data-cy="home-loading" style="--c:var(--color-gray-400); --size:0.8125rem">
			{$i18n.t('Loading…')}
		</p>
	{/if}

	<!-- A failed fetch says so. The alternative is an empty box, which is the
	     failure nobody reports. -->
	{#if failed}
		<p data-cy="home-failed" style="--c:var(--color-gray-500); --size:0.8125rem">
			{$i18n.t('Your home page could not be loaded.')}
			<a href="/pages/home" style="--td:underline">{$i18n.t('Open it directly')}</a>
			<span style="--op:0.6"> ({failed})</span>
		</p>
	{/if}
</div>
