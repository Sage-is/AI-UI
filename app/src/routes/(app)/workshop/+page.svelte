<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.workshop?.models) {
				goto('/workshop/models');
			} else if ($user?.permissions?.workshop?.knowledge) {
				goto('/workshop/knowledge');
			} else if ($user?.permissions?.workshop?.prompts) {
				goto('/workshop/prompts');
			} else if ($user?.permissions?.workshop?.tools) {
				goto('/workshop/tools');
			} else {
				goto('/');
			}
		} else {
			goto('/workshop/models');
		}
	});
</script>
