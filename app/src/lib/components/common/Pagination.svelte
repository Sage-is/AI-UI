<script lang="ts">
	import { Pagination } from 'bits-ui';
	import { createEventDispatcher } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';


	export let page = 0;
	export let count = 0;
	export let perPage = 20;
</script>

<div style="--d:flex; --jc:center">
	<Pagination.Root bind:page {count} {perPage} let:pages>
		<div style="--my:0.5rem; --d:flex; --ai:center">
			<Pagination.PrevButton
				style="--mr:25px; --d:inline-flex; --w:2rem; --h:2rem; --ai:center; --jc:center; --radius:9px; --bgc:transparent; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850)"
	class="active:scale-98 disabled:cursor-not-allowed disabled:text-gray-400 dark:disabled:text-gray-700 hover:disabled:bg-transparent dark:hover:disabled:bg-transparent"
			>
				<Icon name="chevron-left" className="size-4" strokeWidth="2" />
			</Pagination.PrevButton>
			<div style="--d:flex; --ai:center; --g:0.625rem">
				{#each pages as page (page.key)}
					{#if page.type === 'ellipsis'}
						<div style="--size:0.8rem; --weight:500"
	class="text-foreground-alt">...</div>
					{:else}
						<Pagination.Page
							{page}
							style="--d:inline-flex; --w:2rem; --h:2rem; --ai:center; --jc:center; --radius:9px; --bgc:transparent; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --size:0.8rem; --weight:500; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="hover:bg-dark-10 active:scale-98 disabled:cursor-not-allowed disabled:opacity-50 hover:disabled:bg-transparent data-selected:bg-gray-50 data-selected:text-gray-700 data-selected:hover:bg-gray-100 dark:data-selected:bg-gray-850 dark:data-selected:text-gray-50 dark:data-selected:hover:bg-gray-800"
						>
							{page.value}
						</Pagination.Page>
					{/if}
				{/each}
			</div>
			<Pagination.NextButton
				style="--ml:25px; --d:inline-flex; --w:2rem; --h:2rem; --ai:center; --jc:center; --radius:9px; --bgc:transparent; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850)"
	class="active:scale-98 disabled:cursor-not-allowed disabled:text-gray-400 dark:disabled:text-gray-700 hover:disabled:bg-transparent dark:hover:disabled:bg-transparent"
			>
				<Icon name="chevron-right" className="size-4" strokeWidth="2" />
			</Pagination.NextButton>
		</div>
	</Pagination.Root>
</div>
