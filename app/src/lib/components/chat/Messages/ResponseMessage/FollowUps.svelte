<script lang="ts">
		import { onMount, tick, getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	export let followUps: string[] = [];
	export let onClick: (followUp: string) => void = () => {};
</script>

<div style="--mt:1rem">
	<div style="--size:0.8rem; --weight:500">
		{$i18n.t('Follow up')}
	</div>

	<div style="--d:flex; --fd:column; --ta:left; --g:0.2rem; --mt:0.4rem">
		{#each followUps as followUp, idx (idx)}
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div
				style="--mr:0.5rem; --py:0.4rem; --bgc:transparent; --ta:left; --size:0.8rem; --d:flex; --ai:center; --g:0.5rem; --px:0.4rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --hvr-c:#000; --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --cur:pointer"
				on:click={() => onClick(followUp)}
				title={followUp}
				aria-label={followUp}
			>
				<Icon name="arrow-turn-down-right" className="size-3.5" />

				<div style="--line-clamp:1">
					{followUp}
				</div>
			</div>

			{#if idx < followUps.length - 1}
				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)" />
			{/if}
		{/each}
	</div>
</div>
