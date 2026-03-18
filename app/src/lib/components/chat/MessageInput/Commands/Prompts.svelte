<script lang="ts">
	import { prompts, settings, user } from '$lib/stores';
	import {
		extractCurlyBraceWords,
		getUserPosition,
		getFormattedDate,
		getFormattedTime,
		getCurrentDateTime,
		getUserTimezone,
		getWeekday
	} from '$lib/utils';
	import { tick, getContext, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let command = '';
	export let onSelect = (e) => {};

	let selectedPromptIdx = 0;
	let filteredPrompts = [];

	$: filteredPrompts = $prompts
		.filter((p) => p.command.toLowerCase().includes(command.toLowerCase()))
		.sort((a, b) => a.title.localeCompare(b.title));

	$: if (command) {
		selectedPromptIdx = 0;
	}

	export const selectUp = () => {
		selectedPromptIdx = Math.max(0, selectedPromptIdx - 1);
	};

	export const selectDown = () => {
		selectedPromptIdx = Math.min(selectedPromptIdx + 1, filteredPrompts.length - 1);
	};

	let container;
	let adjustHeightDebounce;

	const adjustHeight = () => {
		if (container) {
			if (adjustHeightDebounce) {
				clearTimeout(adjustHeightDebounce);
			}

			adjustHeightDebounce = setTimeout(() => {
				if (!container) return;

				// Ensure the container is visible before adjusting height
				const rect = container.getBoundingClientRect();
				container.style.maxHeight = Math.max(Math.min(240, rect.bottom - 80), 100) + 'px';
			}, 100);
		}
	};

	const confirmPrompt = async (command) => {
		onSelect({ type: 'prompt', data: command });
	};

	onMount(() => {
		window.addEventListener('resize', adjustHeight);
		adjustHeight();
	});

	onDestroy(() => {
		window.removeEventListener('resize', adjustHeight);
	});
</script>

{#if filteredPrompts.length > 0}
	<div
		id="commands-container"
		style="--px:0.5rem; --mb:0.5rem; --ta:left; --w:100%; --pos:absolute; --bottom:0; --left:0; --right:0; --z:10"
	>
		<div style="--d:flex; --w:100%; --radius:0.6rem;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)">
			<div style="--d:flex; --fd:column; --w:100%; --radius:0.6rem; --bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-c:var(--color-gray-100)">
				<div
					style="--m:0.25rem; --ofy:auto; --p:0.25rem; --g:0.125rem; --maxh:15rem"
	class="scrollbar-hidden"
					id="command-options-container"
					bind:this={container}
				>
					{#each filteredPrompts as promptItem, promptIdx}
						<button
							style="--px:0.6rem; --py:0.375rem; --radius:0.6rem; --w:100%; --ta:left"
	class="{promptIdx === selectedPromptIdx
								? '  bg-gray-50 dark:bg-gray-850 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								confirmPrompt(promptItem);
							}}
							on:mousemove={() => {
								selectedPromptIdx = promptIdx;
							}}
							on:focus={() => {}}
						>
							<div style="--weight:500; --c:#000; --dark-c:var(--color-gray-100)">
								{promptItem.command}
							</div>

							<div style="--size:0.6rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-100)">
								{promptItem.title}
							</div>
						</button>
					{/each}
				</div>

				<div
					style="--px:0.5rem; --pt:0.125rem; --pb:0.25rem; --size:0.6rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-100); --bgc:#fff; --dark-bgc:var(--color-gray-900); --bblr:0.6rem; --bbrr:0.6rem; --d:flex; --ai:center; --g:0.25rem"
				>
					<div>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							style="--w:0.6rem; --h:0.6rem"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
							/>
						</svg>
					</div>

					<div style="--line-clamp:1">
						{$i18n.t(
							'Tip: Update multiple variable slots consecutively by pressing the tab key in the chat input after each replacement.'
						)}
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
