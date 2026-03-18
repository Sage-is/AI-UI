<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';

	const i18n = getContext('i18n');

	export let onNext: () => void = () => {};
	export let hasConnectionStep = false;
	export let hasUsersStep = false;
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	<div style="--size:1.4rem; --weight:600; --dark-c:#fff; --mb:0.4rem">
		{$i18n.t("Let's get you set up")}
	</div>
	<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.5rem">
		{$i18n.t("We'll walk you through a few quick steps to get {{name}} ready to use.", { name: $WEBUI_NAME })}
	</div>

	<div style="--d:flex; --fd:column; --g:0.8rem; --mb:1.5rem">
		{#if hasConnectionStep}
			<div style="--d:flex; --ai:center; --g:0.8rem">
				<div style="--w:2rem; --h:2rem; --radius:9999px; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --d:flex; --ai:center; --jc:center; --size:0.8rem; --weight:600; --shrink:0">
					1
				</div>
				<div>
					<div style="--size:0.8rem; --weight:500">{$i18n.t('Connect a Model Provider')}</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Add an OpenAI-compatible or Ollama connection')}
					</div>
				</div>
			</div>
		{/if}

		{#if hasUsersStep}
			<div style="--d:flex; --ai:center; --g:0.8rem">
				<div style="--w:2rem; --h:2rem; --radius:9999px; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --d:flex; --ai:center; --jc:center; --size:0.8rem; --weight:600; --shrink:0">
					{hasConnectionStep ? '2' : '1'}
				</div>
				<div>
					<div style="--size:0.8rem; --weight:500">{$i18n.t('Add Users')}</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Invite your team or choose to work alone')}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<button
		on:click={onNext}
		style="--ml:auto; --px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
	>
		{$i18n.t("Get Started")}
	</button>
</div>
