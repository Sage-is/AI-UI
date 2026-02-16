<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowUpCircle from '$lib/components/icons/ArrowUpCircle.svelte';
	import BarsArrowUp from '$lib/components/icons/BarsArrowUp.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';

	const i18n = getContext('i18n');

	export let onClose: Function = () => {};

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
	align="end"
>
	<Tooltip content={$i18n.t('Add Content')}>
		<button
			style="--p:0.375rem; --radius:0.75rem; --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem; --d:flex; --ai:center; --g:0.25rem"
			on:click={(e) => {
				e.stopPropagation();
				show = true;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				style="--w:1rem; --h:1rem"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:11rem; --radius:0.75rem; --p:0.25rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --shadow:1"
			sideOffset={4}
			side="bottom"
			align="end"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					dispatch('upload', { type: 'files' });
				}}
			>
				<ArrowUpCircle strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Upload files')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					dispatch('upload', { type: 'directory' });
				}}
			>
				<FolderOpen strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Upload directory')}</div>
			</DropdownMenu.Item>

			<Tooltip
				content={$i18n.t(
					'This option will delete all existing files in the collection and replace them with newly uploaded files.'
				)}
				className="w-full"
			>
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
					on:click={() => {
						dispatch('sync', { type: 'directory' });
					}}
				>
					<ArrowPath strokeWidth="2" />
					<div style="--d:flex; --ai:center">{$i18n.t('Sync directory')}</div>
				</DropdownMenu.Item>
			</Tooltip>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					dispatch('upload', { type: 'text' });
				}}
			>
				<BarsArrowUp strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Add text content')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
