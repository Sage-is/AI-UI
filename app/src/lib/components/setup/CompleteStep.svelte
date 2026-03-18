<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';

	const i18n = getContext('i18n');

	export let onFinish: () => void = () => {};
	export let connectionAdded = false;
	export let usersAdded = false;
	export let workingAlone = false;
</script>

<div style="--px:1.2rem; --pt:1.5rem; --pb:1.5rem; --ta:center">
	<div style="--size:2rem; --mb:0.6rem">
		&#10003;
	</div>
	<div style="--size:1.4rem; --weight:600; --dark-c:#fff; --mb:0.4rem">
		{$i18n.t("You're all set!")}
	</div>
	<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.5rem">
		{$i18n.t('{{name}} is ready to use.', { name: $WEBUI_NAME })}
	</div>

	<div style="--d:flex; --fd:column; --g:0.5rem; --mb:1.5rem; --ta:left; --mx:auto; --w:fit-content">
		{#if connectionAdded}
			<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
				<span style="--c:var(--color-green-600)">&#10003;</span>
				<span>{$i18n.t('Model connection configured')}</span>
			</div>
		{/if}

		{#if usersAdded}
			<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
				<span style="--c:var(--color-green-600)">&#10003;</span>
				<span>{$i18n.t('Users added')}</span>
			</div>
		{/if}

		{#if workingAlone}
			<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
				<span style="--c:var(--color-green-600)">&#10003;</span>
				<span>{$i18n.t('Working alone mode enabled')}</span>
			</div>
		{/if}

		{#if !connectionAdded && !usersAdded && !workingAlone}
			<div style="--size:0.75rem; --c:var(--color-gray-400)">
				{$i18n.t('You can configure connections and users anytime from Settings.')}
			</div>
		{/if}
	</div>

	<button
		on:click={onFinish}
		style="--px:1.2rem; --py:0.5rem; --size:0.9rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
	>
		{$i18n.t("Let's Go!")}
	</button>
</div>
