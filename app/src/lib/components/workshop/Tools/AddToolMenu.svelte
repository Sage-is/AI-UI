<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Github from '$lib/components/icons/Github.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import Link from '$lib/components/icons/Link.svelte';

	const i18n = getContext('i18n');

	export let createHandler: Function;
	export let importFromLinkHandler: Function;

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
>
	<Tooltip content={$i18n.t('Create')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:190px; --size:0.8rem; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
	class="font-primary"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<button
				style="--d:flex; --radius:0.4rem; --py:0.4rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={async () => {
					createHandler();
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<PencilSolid />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('New Tool')}</div>
			</button>

			<button
				style="--d:flex; --radius:0.4rem; --py:0.4rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={async () => {
					importFromLinkHandler();
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<Link />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Import From Link')}</div>
			</button>
		</DropdownMenu.Content>
	</div>
</Dropdown>
