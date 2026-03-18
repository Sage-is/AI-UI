<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';

	export let content = '';
</script>

<div style="--d:flex; --my:0.5rem; --g:0.625rem;  --px:1rem; --py:0.6rem; --bc:rgb(220 38 38 / 0.1); --bgc:rgb(220 38 38 / 0.1); --radius:0.5rem">
	<div style="--as:flex-start; --mt:0.125rem">
		<Info className="size-5 text-red-700 dark:text-red-400" />
	</div>

	<div style="--as:center; --size:0.875rem">
		{typeof content === 'string' ? content : JSON.stringify(content)}
	</div>
</div>
