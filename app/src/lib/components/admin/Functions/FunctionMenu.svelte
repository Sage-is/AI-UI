<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
		import Tooltip from '$lib/components/common/Tooltip.svelte';
				import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let func;

	export let editHandler: Function;
	export let shareHandler: Function;
	export let cloneHandler: Function;
	export let exportHandler: Function;
	export let deleteHandler: Function;
	export let toggleGlobalHandler: Function;

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
			style="--w:100%; --maxw:180px; --radius:0.6rem; --px:0.2rem; --py:0.4rem;  --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:1"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			{#if ['filter', 'action'].includes(func.type)}
				<div
					style="--d:flex; --g:0.5rem; --jc:space-between; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointerrounded-md"
				>
					<div style="--d:flex; --g:0.5rem; --ai:center">
						<Icon name="globe-alt" />

						<div style="--d:flex; --ai:center">{$i18n.t('Global')}</div>
					</div>

					<div>
						<Switch on:change={toggleGlobalHandler} bind:state={func.is_global} />
					</div>
				</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.2rem" />
			{/if}

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					editHandler();
				}}
			>
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
						d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
					/>
				</svg>

				<div style="--d:flex; --ai:center">{$i18n.t('Edit')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					shareHandler();
				}}
			>
				<Icon name="share" />
				<div style="--d:flex; --ai:center">{$i18n.t('Share')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					cloneHandler();
				}}
			>
				<Icon name="document-duplicate" />

				<div style="--d:flex; --ai:center">{$i18n.t('Clone')}</div>
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

			<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.2rem" />

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					deleteHandler();
				}}
			>
				<Icon name="garbage-bin" strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
