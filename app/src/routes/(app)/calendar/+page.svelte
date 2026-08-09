<script lang="ts">
	// BORN HOLLOW, 2026-08-09. There was never a Svelte calendar to hollow — this
	// route exists only to wrap the server-rendered `/pages/calendar` in the app
	// chrome, so a reader keeps the sidebar, the chat list and the navigation.
	//
	// That distinction is worth keeping. HOLLOWING is an existing route giving up
	// its content (`/home` did). This one had no content to give up, so it is a
	// chrome wrapper from the first commit — same mechanism, no migration.
	//
	// It carries the same warning as any hollow: the Svelte file outlives nothing,
	// but it is still a file kept alive around a server page, and it comes down
	// when the chat core is server-rendered and the sidebar no longer needs the
	// SPA. See `docs/decisions/2026-08-08-hollowing-a-svelte-route.md`.
	import { getContext } from 'svelte';
	import { hollow, PAGES_VARS } from '$lib/utils/pageHost';

	const i18n = getContext('i18n');

	let failed = '';
	let loading = true;
</script>

<div style="--maxw:56rem; --mx:auto; --px:1.5rem; --py:2rem">
	<!-- The month lives in the URL on the server page. `hollow` carries the query
	     through and swaps the previous/next links in place, so the address stays
	     `/calendar?month=…` and the sidebar survives a click. -->
	<div
		data-cy="calendar-host"
		use:hollow={{
			page: '/pages/calendar',
			base: '/calendar',
			onloading: (v) => (loading = v),
			onfailed: (v) => (failed = v)
		}}
		style={PAGES_VARS}
	></div>

	{#if loading}
		<p data-cy="calendar-loading" style="--c:var(--color-gray-400); --size:0.8125rem">
			{$i18n.t('Loading…')}
		</p>
	{/if}

	{#if failed}
		<p data-cy="calendar-failed" style="--c:var(--color-gray-500); --size:0.8125rem">
			{$i18n.t('Your calendar could not be loaded.')}
			<a href="/pages/calendar" style="--td:underline">{$i18n.t('Open it directly')}</a>
			<span style="--op:0.6"> ({failed})</span>
		</p>
	{/if}
</div>
