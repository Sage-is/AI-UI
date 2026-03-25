<script lang="ts">
	import { copyToClipboard, unescapeHtml } from '$lib/utils';
	import { toast } from 'svelte-sonner';
	import { fade } from 'svelte/transition';

	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let token;
	export let done = true;
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
{#if done}
	<code
		style="--cur:pointer"
	class="codespan"
		on:click={() => {
			copyToClipboard(unescapeHtml(token.text));
			toast.success($i18n.t('Copied to clipboard'));
		}}>{unescapeHtml(token.text)}</code
	>
{:else}
	<code
		transition:fade={{ duration: 100 }}
		style="--cur:pointer"
	class="codespan"
		on:click={() => {
			copyToClipboard(unescapeHtml(token.text));
			toast.success($i18n.t('Copied to clipboard'));
		}}>{unescapeHtml(token.text)}</code
	>
{/if}
