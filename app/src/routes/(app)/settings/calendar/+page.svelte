<script lang="ts">
	// BORN HOLLOW, 2026-08-09. There was never a Svelte page here — this route
	// exists only to wrap the server-rendered `/pages/settings/calendar` in the
	// app chrome.
	//
	// WHY IT EXISTS AT ALL. `/pages/settings/calendar` was reachable only as a
	// bare server page, and its "Back to the calendar" link pointed at another
	// bare server page — so a reader who clicked "Add a calendar" from the
	// dashboard left the app and had no route back into it. A one-way door.
	// Giving the surface an SPA address closes it, and costs these two files.
	//
	// See `docs/decisions/2026-08-08-hollowing-a-svelte-route.md` for the
	// mechanism and the two-mode rule.
	import { getContext } from 'svelte';
	import { hollow, PAGES_VARS } from '$lib/utils/pageHost';

	const i18n = getContext('i18n');

	let failed = '';
	let loading = true;
</script>

<div style="--maxw:56rem; --mx:auto; --px:1.5rem; --py:2rem">
	<div
		data-cy="settings-calendar-host"
		use:hollow={{
			page: '/pages/settings/calendar',
			base: '/settings/calendar',
			onloading: (v) => (loading = v),
			onfailed: (v) => (failed = v)
		}}
		style={PAGES_VARS}
	></div>

	{#if loading}
		<p data-cy="settings-calendar-loading" style="--c:var(--color-gray-400); --size:0.8125rem">
			{$i18n.t('Loading…')}
		</p>
	{/if}

	<!-- A failed fetch says so. The alternative is an empty box, which is the
	     failure nobody reports. -->
	{#if failed}
		<p data-cy="settings-calendar-failed" style="--c:var(--color-gray-500); --size:0.8125rem">
			{$i18n.t('Your calendars could not be loaded.')}
			<a href="/pages/settings/calendar" style="--td:underline">{$i18n.t('Open it directly')}</a>
			<span style="--op:0.6"> ({failed})</span>
		</p>
	{/if}
</div>
