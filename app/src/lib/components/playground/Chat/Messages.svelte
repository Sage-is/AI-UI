<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Message from './Message.svelte';

	const i18n = getContext('i18n');

	export let messages = [];
</script>

<div style="--py:0.75rem; --g:0.75rem">
	{#each messages as message, idx}
		<Message
			{message}
			{idx}
			onDelete={() => {
				messages = messages.filter((message, messageIdx) => messageIdx !== idx);
			}}
		/>
	{/each}
</div>
