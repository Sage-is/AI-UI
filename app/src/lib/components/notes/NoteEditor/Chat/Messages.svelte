<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Message from './Message.svelte';

	const i18n = getContext('i18n');

	export let messages = [];
	export let onInsert = (content: string) => {};
</script>

<div style="--g:0.75rem; --pb:3rem">
	{#each messages as message, idx}
		<Message
			{message}
			{idx}
			onInsert={() => {
				onInsert(message?.content ?? '');
			}}
			onEdit={() => {
				messages = messages.map((msg, messageIdx) => {
					if (messageIdx === idx) {
						return { ...msg, edit: true };
					}
					return msg;
				});
			}}
			onDelete={() => {
				messages = messages.filter((message, messageIdx) => messageIdx !== idx);
			}}
		/>
	{/each}
</div>
