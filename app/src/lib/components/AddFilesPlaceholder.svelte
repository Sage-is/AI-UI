<script>
	import { getContext } from 'svelte';

	export let title = '';
	export let content = '';
	const i18n = getContext('i18n');
</script>

<div style="--px:0.6rem">
	<div style="--ta:center; --size:3.75rem; --mb:0.6rem">📄</div>
	<div style="--ta:center; --dark-c:#fff; --size:1.2rem; --weight:600; --z:50">
		{#if title}
			{title}
		{:else}
			{$i18n.t('Add Files')}
		{/if}
	</div>

	<slot
		><div style="--px:0.5rem; --mt:0.5rem; --ta:center; --size:0.8rem; --dark-c:var(--color-gray-200); --w:100%">
			{#if content}
				{content}
			{:else}
				{$i18n.t('Drop any files here to upload')}
			{/if}
		</div>
	</slot>
</div>
