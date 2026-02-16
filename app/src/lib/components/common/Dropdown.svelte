<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';

	export let show = false;
	export let side = 'bottom';
	export let align = 'start';
	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:130px; --radius:0.5rem; --px:0.25rem; --py:0.375rem; --b:1px solid; --bc:var(--color-gray-900, #171717); --z:50; --bgc:var(--color-gray-850, #262626); --c:#fff"
			sideOffset={8}
			{side}
			{align}
			transition={flyAndScale}
		>
			<DropdownMenu.Item style="--d:flex; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500">
				<div style="--d:flex; --ai:center">Profile</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item style="--d:flex; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500">
				<div style="--d:flex; --ai:center">Profile</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item style="--d:flex; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500">
				<div style="--d:flex; --ai:center">Profile</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
