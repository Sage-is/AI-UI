<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import { getContext } from 'svelte';
	export let show = false;
	export let model = null;
	export let feedbacks = [];
	export let onClose: () => void = () => {};
	const i18n = getContext('i18n');
	import XMark from '$lib/components/icons/XMark.svelte';

	const close = () => {
		show = false;
		onClose();
	};

	$: topTags = model ? getTopTagsForModel(model.id, feedbacks) : [];

	const getTopTagsForModel = (modelId: string, feedbacks: any[], topN = 5) => {
		const tagCounts = new Map();
		feedbacks
			.filter((fb) => fb.data.model_id === modelId)
			.forEach((fb) => {
				(fb.data.tags || []).forEach((tag) => {
					tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
				});
			});
		return Array.from(tagCounts.entries())
			.sort((a, b) => b[1] - a[1])
			.slice(0, topN)
			.map(([tag, count]) => ({ tag, count }));
	};
</script>

<Modal size="sm" bind:show>
	{#if model}
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center">
				{model.name}
			</div>
			<button style="--as:center" on:click={close} aria-label="Close">
				<XMark className={'size-5'} />
			</button>
		</div>
		<div style="--px:1.25rem; --pb:1rem; --dark-c:var(--color-gray-200)">
			<div style="--mb:0.5rem">
				{#if topTags.length}
					<div style="--d:flex; --fw:wrap; --g:0.25rem; --mt:0.25rem; --mx:-0.25rem">
						{#each topTags as tagInfo}
							<span style="--px:0.5rem; --py:0.125rem; --radius:9999px; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --size:0.75rem">
								{tagInfo.tag} <span style="--c:var(--color-gray-500); --weight:500">{tagInfo.count}</span>
							</span>
						{/each}
					</div>
				{:else}
					<span>-</span>
				{/if}
			</div>
			<div style="--d:flex; --jc:flex-end; --pt:0.5rem">
				<button
					style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
					type="button"
					on:click={close}
				>
					{$i18n.t('Close')}
				</button>
			</div>
		</div>
	{/if}
</Modal>
