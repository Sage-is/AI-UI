<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	import Tooltip from '../Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Badge from '../Badge.svelte';
	import { showSearch, searchQuery } from '$lib/stores';
	const dispatch = createEventDispatcher();

	export let tags = [];
</script>

{#each tags as tag}
	<Tooltip content={tag.name}>
		<li
			style="--pos:relative; --px:0.4rem; --py:0.2px; --g:0.125rem; --d:flex; --jc:space-between; --h:fit-content; --w:fit-content; --ai:center; --radius:9999px; --bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --cur:pointer"
	class="group/tags max-h-fit"
		>
			<button
				style="--size:0.7rem; --weight:500; --as:center; --line-clamp:1; --w:fit-content; --cur:pointer; --bg:none; --b:none; --p:0; --c:inherit"
				type="button"
				on:click|stopPropagation={() => {
					searchQuery.set(`tag:${tag.name}`);
					showSearch.set(true);
				}}
			>
				{tag.name}
			</button>
			<div style="--pos:absolute; --v:hidden; --right:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover/tags:visible">
				<button
					style="--radius:9999px;  --bgc:#fff; --dark-bgc:var(--color-gray-700); --h:100%; --d:flex; --as:center; --cur:pointer"
					on:click={() => {
						dispatch('delete', tag.name);
					}}
					type="button"
					aria-label={$i18n.t('Remove this tag from list')}
				>
					<XMark className="size-3" strokeWidth="2.5" />
				</button>
			</div>
		</li>
	</Tooltip>
{/each}
