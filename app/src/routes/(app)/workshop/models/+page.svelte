<script>
	import { onMount } from 'svelte';
	import { models } from '$lib/stores';
	import { loadModels } from '$lib/apis';
	import Models from '$lib/components/workshop/Models.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				models.set(await loadModels());
			})()
		]);
	});
</script>

{#if $models !== null}
	<Models />
{/if}
