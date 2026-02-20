<script lang="ts">
	import Fuse from 'fuse.js';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext } from 'svelte';
	import { settings, WEBUI_NAME } from '$lib/stores';
	import { WEBUI_VERSION } from '$lib/constants';

	const i18n = getContext('i18n');

	export let suggestionPrompts = [];
	export let className = '';
	export let listStyle = '';
	export let inputValue = '';
	export let onSelect = (e) => {};

	let sortedPrompts = [];

	const fuseOptions = {
		keys: ['content', 'title'],
		threshold: 0.5
	};

	let fuse;
	let filteredPrompts = [];

	// Initialize Fuse
	$: fuse = new Fuse(sortedPrompts, fuseOptions);

	// Update the filteredPrompts if inputValue changes
	// Only increase version if something wirklich geändert hat
	$: getFilteredPrompts(inputValue);

	// Helper function to check if arrays are the same
	// (based on unique IDs oder content)
	function arraysEqual(a, b) {
		if (a.length !== b.length) return false;
		for (let i = 0; i < a.length; i++) {
			if ((a[i].id ?? a[i].content) !== (b[i].id ?? b[i].content)) {
				return false;
			}
		}
		return true;
	}

	const getFilteredPrompts = (inputValue) => {
		if (inputValue.length > 500) {
			filteredPrompts = [];
		} else {
			const newFilteredPrompts =
				inputValue.trim() && fuse
					? fuse.search(inputValue.trim()).map((result) => result.item)
					: sortedPrompts;

			// Compare with the oldFilteredPrompts
			// If there's a difference, update array + version
			if (!arraysEqual(filteredPrompts, newFilteredPrompts)) {
				filteredPrompts = newFilteredPrompts;
			}
		}
	};

	$: if (suggestionPrompts) {
		sortedPrompts = [...(suggestionPrompts ?? [])].sort(() => Math.random() - 0.5);
		getFilteredPrompts(inputValue);
	}
</script>

<div style="--mb:0.25rem; --d:flex; --g:0.25rem; --size:0.75rem; --weight:500; --ai:center; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4)">
	{#if filteredPrompts.length > 0}
		<Bolt />
		{$i18n.t('Suggested')}
	{:else}
		<!-- Keine Vorschläge -->

		<div
			style="--d:flex; --w:100%; --as:flex-start; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4)"
	class="{$settings?.landingPageMode === 'chat'
				? ' -mt-1'
				: 'text-center items-center justify-center'}"
		>
			{$WEBUI_NAME} ‧ v{WEBUI_VERSION}
		</div>
	{/if}
</div>

<div style="--h:10rem; --w:100%">
	{#if filteredPrompts.length > 0}
		<div role="list" style="--maxh:10rem; --of:auto; --ai:flex-start; {listStyle}"
	class="scrollbar-none {className}">
			{#each filteredPrompts as prompt, idx (prompt.id || prompt.content)}
				<!-- svelte-ignore a11y-no-interactive-element-to-noninteractive-role -->
				<button
					role="listitem"
					class="waterfall group"
					style="--d:flex; --fd:column; --fx:1 1 0%; --fs:0; --w:100%; --jc:space-between; --px:0.75rem; --py:0.5rem; --radius:0.75rem; --bgc:transparent; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); animation-delay: {idx * 60}ms"
					on:click={() => onSelect({ type: 'prompt', data: prompt.content })}
				>
					<div style="--d:flex; --fd:column; --ta:left">
						{#if prompt.title && prompt.title[0] !== ''}
							<div
								style="--weight:500; --dark-c:var(--color-gray-300, #cdcdcd); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --line-clamp:1"
	class="dark:group-hover:text-gray-200"
							>
								{prompt.title[0]}
							</div>
							<div style="--size:0.75rem; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4); --weight:400; --line-clamp:1">
								{prompt.title[1]}
							</div>
						{:else}
							<div
								style="--weight:500; --dark-c:var(--color-gray-300, #cdcdcd); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --line-clamp:1"
	class="dark:group-hover:text-gray-200"
							>
								{prompt.content}
							</div>
							<div style="--size:0.75rem; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4); --weight:400; --line-clamp:1">
								{$i18n.t('Prompt')}
							</div>
						{/if}
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	/* Waterfall animation for the suggestions */
	@keyframes fadeInUp {
		0% {
			opacity: 0;
			transform: translateY(20px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.waterfall {
		opacity: 0;
		animation-name: fadeInUp;
		animation-duration: 200ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease;
	}
</style>
