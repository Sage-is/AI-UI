<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
			import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';

	import { config } from '$lib/stores';

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
			style="--w:100%; --maxw:170px; --radius:0.6rem; --px:0.2rem; --py:0.4rem;  --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:1"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					hideHandler();
				}}
			>
				{#if model?.meta?.hidden ?? false}
					<Icon name="eye-slash" className="size-4" />
				{:else}
					<Icon name="eye" className="size-4" />
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
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					copyLinkHandler();
				}}
			>
				<Icon name="link" />

				<div style="--d:flex; --ai:center">{$i18n.t('Copy Link')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					exportHandler();
				}}
			>
				<Icon name="arrow-down-tray" />

				<div style="--d:flex; --ai:center">{$i18n.t('Export')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
