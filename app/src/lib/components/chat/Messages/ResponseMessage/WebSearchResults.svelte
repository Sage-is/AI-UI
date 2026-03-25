<script lang="ts">
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	export let status = { urls: [], query: '' };
	let state = false;
</script>

<Collapsible bind:open={state} className="w-full space-y-1">
	<div
		style="--d:flex; --ai:center; --g:0.5rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --hvr-dark-c:var(--color-gray-300); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	>
		<slot />

		{#if state}
			<ChevronUp strokeWidth="3.5" className="size-3.5 " />
		{:else}
			<ChevronDown strokeWidth="3.5" className="size-3.5 " />
		{/if}
	</div>
	<div
		style="--size:0.8rem;  --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --radius:0.6rem; --mb:0.4rem"
		slot="content"
	>
		{#if status?.query}
			<a
				href="https://www.google.com/search?q={status.query}"
				target="_blank"
				style="--d:flex; --w:100%; --ai:center; --p:0.6rem; --px:1rem;  --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --jc:space-between; --weight:400; --c:var(--color-gray-800); --dark-c:var(--color-gray-300); --td:none"
	class="group/item"
			>
				<div style="--d:flex; --g:0.5rem; --ai:center">
					<Search />

					<div style="--line-clamp:1">
						{status.query}
					</div>
				</div>

				<div
					style="--ml:0.2rem; --c:#fff; --dark-c:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover/item:text-gray-600 dark:group-hover/item:text-white"
				>
					<!--  -->
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path
							fill-rule="evenodd"
							d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			</a>
		{/if}

		{#each status.urls as url, urlIdx}
			<a
				href={url}
				target="_blank"
				style="--d:flex; --w:100%; --ai:center; --p:0.6rem; --px:1rem; --jc:space-between; --weight:400; --c:var(--color-gray-800); --dark-c:var(--color-gray-300)"
	class="{urlIdx === status.urls.length - 1
					? ''
					: 'border-b border-gray-300/30 dark:border-gray-700/50'} group/item"
			>
				<div style="--line-clamp:1">
					{url}
				</div>

				<div
					style="--ml:0.2rem; --c:#fff; --dark-c:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover/item:text-gray-600 dark:group-hover/item:text-white"
				>
					<!--  -->
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path
							fill-rule="evenodd"
							d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			</a>
		{/each}
	</div>
</Collapsible>
