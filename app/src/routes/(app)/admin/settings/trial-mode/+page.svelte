<script>
	// Same shape as the other admin/settings/[tab]/+page.svelte routes —
	// the parent <Settings> component reads $page.url.pathname and dispatches
	// to the matching tab. WHY a dedicated route rather than the [tab] catch:
	// the tab registry is allow-listed; "trial-mode" needs an explicit entry.
	import Settings from '$lib/components/admin/Settings.svelte';
</script>

<Settings />
