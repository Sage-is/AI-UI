<script lang="ts">
	// Chrome only. The nav, the sidebar toggle and the scrolling body are shared
	// with the other dashboard surfaces — see DashboardShell.
	import DashboardShell from '$lib/components/layout/DashboardShell.svelte';
</script>

<DashboardShell title="Calendar">
	<slot />
</DashboardShell>
