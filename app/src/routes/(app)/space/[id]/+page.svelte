<script lang="ts">
	import { page } from '$app/stores';

	import Space from '$lib/components/channel/Space.svelte';
</script>

<Space id={$page.params.id} />
