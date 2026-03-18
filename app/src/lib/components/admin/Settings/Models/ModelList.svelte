<script lang="ts">
	import Sortable from 'sortablejs';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { models } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';

	export let modelIds = [];

	let sortable = null;
	let modelListElement = null;

	const positionChangeHandler = () => {
		const modelList = Array.from(modelListElement.children).map((child) =>
			child.id.replace('model-item-', '')
		);

		modelIds = modelList;
	};

	$: if (modelIds) {
		init();
	}

	const init = () => {
		if (sortable) {
			sortable.destroy();
		}

		if (modelListElement) {
			sortable = Sortable.create(modelListElement, {
				animation: 150,
				handle: '.item-handle',
				onUpdate: async (event) => {
					positionChangeHandler();
				}
			});
		}
	};
</script>

{#if modelIds.length > 0}
	<div style="--d:flex; --fd:column; --translatex:-0.2rem" bind:this={modelListElement}>
		{#each modelIds as modelId, modelIdx (modelId)}
			<div style="--d:flex; --g:0.5rem; --w:100%; --jc:space-between; --ai:center" id="model-item-{modelId}">
				<Tooltip content={modelId} placement="top-start">
					<div style="--d:flex; --ai:center; --g:0.2rem">
						<EllipsisVertical className="size-4 cursor-move item-handle" />

						<div style="--size:0.8rem; --fx:1 1 0%; --py:0.2rem; --radius:0.5rem">
							{#if $models.find((model) => model.id === modelId)}
								{$models.find((model) => model.id === modelId).name}
							{:else}
								{modelId}
							{/if}
						</div>
					</div>
				</Tooltip>
			</div>
		{/each}
	</div>
{:else}
	<div style="--c:var(--color-gray-500); --size:0.6rem; --ta:center; --py:0.5rem">
		{$i18n.t('No models found')}
	</div>
{/if}
