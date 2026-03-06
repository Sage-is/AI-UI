<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ArrowUpCircle from '$lib/components/icons/ArrowUpCircle.svelte';

	import { config } from '$lib/stores';
	import Link from '$lib/components/icons/Link.svelte';

	const i18n = getContext('i18n');

	export let user;
	export let model;

	export let exportHandler: Function;
	export let hideHandler: Function;
	export let copyLinkHandler: Function;

	export let onClose: Function;

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:170px; --radius:0.75rem; --px:0.25rem; --py:0.375rem;  --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:1"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				on:click={() => {
					hideHandler();
				}}
			>
				{#if model?.meta?.hidden ?? false}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88"
						/>
					</svg>
				{:else}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
						/>
					</svg>
				{/if}

				<div style="--d:flex; --ai:center">
					{#if model?.meta?.hidden ?? false}
						{$i18n.t('Show Model')}
					{:else}
						{$i18n.t('Hide Model')}
					{/if}
				</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				on:click={() => {
					copyLinkHandler();
				}}
			>
				<Link />

				<div style="--d:flex; --ai:center">{$i18n.t('Copy Link')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				on:click={() => {
					exportHandler();
				}}
			>
				<ArrowDownTray />

				<div style="--d:flex; --ai:center">{$i18n.t('Export')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
