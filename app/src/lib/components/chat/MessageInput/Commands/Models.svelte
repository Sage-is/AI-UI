<script lang="ts">
	import Fuse from 'fuse.js';

	import { createEventDispatcher, onDestroy, onMount } from 'svelte';
	import { tick, getContext } from 'svelte';

	import { models } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding, type Branding } from '$lib/apis/configs';

	const i18n = getContext('i18n');

	export let command = '';
	export let onSelect = (e) => {};

	let branding: Branding | null = null;
	let selectedIdx = 0;
	let filteredItems = [];

	let fuse = new Fuse(
		$models
			.filter((model) => !model?.info?.meta?.hidden)
			.map((model) => {
				const _item = {
					...model,
					modelName: model?.name,
					tags: model?.info?.meta?.tags?.map((tag) => tag.name).join(' '),
					desc: model?.info?.meta?.description
				};
				return _item;
			}),
		{
			keys: ['value', 'tags', 'modelName'],
			threshold: 0.3
		}
	);

	$: filteredItems = command.slice(1)
		? fuse.search(command).map((e) => {
				return e.item;
			})
		: $models.filter((model) => !model?.info?.meta?.hidden);

	$: if (command) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
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
				container.style.maxHeight = Math.max(Math.min(240, rect.bottom - 100), 100) + 'px';
			}, 100);
		}
	};

	const confirmSelect = async (model) => {
		onSelect({ type: 'model', data: model });
	};

	onMount(async () => {
		window.addEventListener('resize', adjustHeight);
		adjustHeight();

		// Fetch branding for fallback logo
		try {
			branding = await getBranding();
		} catch (e) {
			console.error('Failed to load branding:', e);
		}

		await tick();
		const chatInputElement = document.getElementById('chat-input');
		await tick();
		chatInputElement?.focus();
		await tick();
	});

	onDestroy(() => {
		window.removeEventListener('resize', adjustHeight);
	});
</script>

{#if filteredItems.length > 0}
	<div
		id="commands-container"
		style="--px:0.5rem; --mb:0.5rem; --ta:left; --w:100%; --pos:absolute; --bottom:0; --left:0; --right:0; --z:10"
	>
		<div style="--d:flex; --w:100%; --radius:0.6rem;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)">
			<div style="--d:flex; --fd:column; --w:100%; --radius:0.6rem; --bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-c:var(--color-gray-100)">
				<div
					style="--m:0.25rem; --ofy:auto; --p:0.25rem; --btrr:0.5rem; --bbrr:0.5rem; --g:0.125rem; --maxh:15rem"
	class="scrollbar-hidden"
					id="command-options-container"
					bind:this={container}
				>
					{#each filteredItems as model, modelIdx}
						<button
							style="--px:0.6rem; --py:0.375rem; --radius:0.6rem; --w:100%; --ta:left"
	class="{modelIdx === selectedIdx
								? 'bg-gray-50 dark:bg-gray-850 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								confirmSelect(model);
							}}
							on:mousemove={() => {
								selectedIdx = modelIdx;
							}}
							on:focus={() => {}}
						>
							<div style="--d:flex; --weight:500; --c:#000; --dark-c:var(--color-gray-100); --line-clamp:1">
								<img
									src={model?.info?.meta?.profile_image_url ??
										branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
									alt={model?.name ?? model.id}
									style="--radius:9999px; --w:1.5rem; --h:1.5rem; --ai:center; --mr:0.5rem"
								/>
								{model.name}
							</div>
						</button>
					{/each}
				</div>
			</div>
		</div>
	</div>
{/if}
