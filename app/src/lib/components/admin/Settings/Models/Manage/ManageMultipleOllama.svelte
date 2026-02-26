<script>
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import ManageOllama from './ManageOllama.svelte';

	export let ollamaConfig = null;

	let selectedUrlIdx = 0;
</script>

{#if ollamaConfig}
	<div style="--fx:1 1 0%; --mb:0.625rem; --pr:0.375rem; --radius:0.5rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850)">
		<select
			style="--w:100%; --py:0.5rem; --px:1rem; --size:0.875rem; --oe:none; --bgc:transparent"
			bind:value={selectedUrlIdx}
			placeholder={$i18n.t('Select an Ollama instance')}
		>
			{#each ollamaConfig.OLLAMA_BASE_URLS as url, idx}
				<option value={idx}>{url}</option>
			{/each}
		</select>
	</div>

	<ManageOllama urlIdx={selectedUrlIdx} />
{/if}
