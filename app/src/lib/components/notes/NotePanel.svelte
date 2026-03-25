<script lang="ts">
	import { onDestroy, onMount, tick } from 'svelte';
	import { Pane, PaneResizer } from 'paneforge';

	import Drawer from '../common/Drawer.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';

	export let show = false;
	export let pane = null;

	export let containerId = 'note-container';

	let mediaQuery;
	let largeScreen = false;

	let minSize = 0;

	const handleMediaQuery = async (e) => {
		if (e.matches) {
			largeScreen = true;
		} else {
			largeScreen = false;
			pane = null;
		}
	};

	onMount(() => {
		// listen to resize 1000px
		mediaQuery = window.matchMedia('(min-width: 1000px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		// Select the container element you want to observe
		const container = document.getElementById(containerId);

		// initialize the minSize based on the container width
		minSize = Math.floor((400 / container.clientWidth) * 100);

		// Create a new ResizeObserver instance
		const resizeObserver = new ResizeObserver((entries) => {
			for (let entry of entries) {
				const width = entry.contentRect.width;
				// calculate the percentage of 200px
				const percentage = (400 / width) * 100;
				// set the minSize to the percentage, must be an integer
				minSize = Math.floor(percentage);

				if (show) {
					if (pane && pane.isExpanded() && pane.getSize() < minSize) {
						pane.resize(minSize);
					}
				}
			}
		});

		// Start observing the container's size changes
		resizeObserver.observe(container);
	});

	onDestroy(() => {
		mediaQuery.removeEventListener('change', handleMediaQuery);
	});
</script>

{#if !largeScreen}
	{#if show}
		<Drawer
			{show}
			onClose={() => {
				show = false;
			}}
		>
			<div style="--px:0.8rem; --py:0.625rem; --h:100vh; --d:flex; --fd:column"
	class="max-h-dvh">
				<slot />
			</div>
		</Drawer>
	{/if}
{:else if show}
	<PaneResizer
		style="--pos:relative; --d:flex; --w:0.5rem; --ai:center; --jc:center; --bgc:#fff; --dark-shadow:4; --dark-bgc:var(--color-gray-850); --bl:1px solid; --bc:var(--color-gray-50); --dark-bc:var(--color-gray-850)"
	class="bg-background group"
	>
		<div style="--z:10; --d:flex; --h:1.75rem; --w:1.2rem; --ai:center; --jc:center"
	class="rounded-xs">
			<EllipsisVertical className="size-4 invisible group-hover:visible" />
		</div>
	</PaneResizer>

	<Pane
		bind:pane
		defaultSize={Math.max(20, minSize)}
		{minSize}
		onCollapse={() => {
			show = false;
		}}
		collapsible={true}
		style="--z:10"
	>
		{#if show}
			<div style="--d:flex; --maxh:100%; --minh:100%">
				<div
					style="--w:100%; --pl:0.4rem; --pr:0.625rem; --pt:0.5rem; --bgc:#fff; --dark-shadow:4; --dark-bgc:var(--color-gray-850); --z:40; --pe:auto; --ofy:auto; --d:flex; --fd:column"
	class="scrollbar-hidden"
				>
					<slot />
				</div>
			</div>
		{/if}
	</Pane>
{/if}
