<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';

	export let align: 'start' | 'end' = 'start';
	export let onEdit = () => {};
	export let onExport = () => {};
	export let onDelete = () => {};

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			dispatch('close');
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:170px; --radius:0.5rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
			sideOffset={-2}
			side="bottom"
			{align}
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				on:click={() => {
					onEdit();
				}}
			>
				<Pencil strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Edit')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				on:click={() => {
					onExport();
				}}
			>
				<Download strokeWidth="2" />

				<div style="--d:flex; --ai:center">{$i18n.t('Export')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				on:click={() => {
					onDelete();
				}}
			>
				<GarbageBin strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
