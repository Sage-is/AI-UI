<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';

	export let onClose: Function = () => {};
	export let devices: any;

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
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:180px; --radius:0.5rem; --px:0.2rem; --py:0.4rem;  --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --z:9999; --bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-c:#fff"
	class="shadow-xs"
			sideOffset={6}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			{#each devices as device}
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
					on:click={() => {
						dispatch('change', device.deviceId);
					}}
				>
					<div style="--d:flex; --ai:center">
						<div style="--line-clamp:1">
							{device?.label ?? 'Camera'}
						</div>
					</div>
				</DropdownMenu.Item>
			{/each}
		</DropdownMenu.Content>
	</div>
</Dropdown>
