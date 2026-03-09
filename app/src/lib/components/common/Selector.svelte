<script lang="ts">
	import { Select } from 'bits-ui';

	import { flyAndScale } from '$lib/utils/transitions';

	import { createEventDispatcher } from 'svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Check from '../icons/Check.svelte';
	import Search from '../icons/Search.svelte';

	const dispatch = createEventDispatcher();

	export let value = '';
	export let placeholder = 'Select a model';
	export let searchEnabled = true;
	export let searchPlaceholder = 'Search for a model';

	export let items = [
		{ value: 'mango', label: 'Mango' },
		{ value: 'watermelon', label: 'Watermelon' },
		{ value: 'apple', label: 'Apple' },
		{ value: 'pineapple', label: 'Pineapple' },
		{ value: 'orange', label: 'Orange' }
	];

	let searchValue = '';

	$: filteredItems = searchValue
		? items.filter((item) => item.value.toLowerCase().includes(searchValue.toLowerCase()))
		: items;
</script>

<Select.Root
	{items}
	onOpenChange={() => {
		searchValue = '';
	}}
	selected={items.find((item) => item.value === value)}
	onSelectedChange={(selectedItem) => {
		value = selectedItem.value;
	}}
>
	<Select.Trigger style="--pos:relative; --w:100%" aria-label={placeholder}>
		<Select.Value
			style="--d:inline-flex; --px:0.125rem; --w:100%; --oe:none; --bgc:transparent; overflow:hidden; text-overflow:ellipsis; --ws:nowrap; --size:1.125rem; --weight:600"
	class="h-input placeholder-gray-400 focus:outline-hidden"
			{placeholder}
		/>
		<ChevronDown className="absolute end-2 top-1/2 -translate-y-[45%] size-3.5" strokeWidth="2.5" />
	</Select.Trigger>
	<Select.Content
		style="--w:100%; --radius:0.5rem; --bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-c:#fff; --shadow:4;  --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.4); --oe:none"
		transition={flyAndScale}
		sideOffset={4}
	>
		<slot>
			{#if searchEnabled}
				<div style="--d:flex; --ai:center; --g:0.625rem; --px:1.25rem; --mt:0.875rem; --mb:0.75rem">
					<Search className="size-4" strokeWidth="2.5" />

					<input
						bind:value={searchValue}
						style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
						placeholder={searchPlaceholder}
					/>
				</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)" />
			{/if}

			<div style="--px:0.75rem; --my:0.5rem; --maxh:20rem; --ofy:auto">
				{#each filteredItems as item}
					<Select.Item
						style="--d:flex; --w:100%; --weight:500; --line-clamp:1; --us:none; --ai:center; --radius:var(--button-border-radius, 0.5rem); --py:0.5rem; --pl:0.75rem; --pr:0.375rem; --size:0.875rem; --bg:var(--white); --br: 1rem; --shadow:6; --oe:none; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:75ms; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --radius:0.5rem; --cur:pointer"
	class="data-highlighted:bg-muted"
						value={item.value}
						label={item.label}
					>
						{item.label}

						{#if value === item.value}
							<div style="--ml:auto">
								<Check />
							</div>
						{/if}
					</Select.Item>
				{:else}
					<div>
						<div style="--d:block; --px:1.25rem; --py:0.5rem; --size:0.875rem; --c:var(--color-gray-700); --dark-c:var(--color-gray-100)">
							No results found
						</div>
					</div>
				{/each}
			</div>
		</slot>
	</Select.Content>
</Select.Root>
