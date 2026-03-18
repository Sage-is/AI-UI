<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let filters = [];
	export let selectedFilterIds = [];

	let _filters = {};

	onMount(() => {
		_filters = filters.reduce((acc, filter) => {
			acc[filter.id] = {
				...filter,
				selected: selectedFilterIds.includes(filter.id)
			};

			return acc;
		}, {});
	});
</script>

<div>
	<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.25rem">
		<div style="--as:center; --size:0.875rem; --weight:600">{$i18n.t('Filters')}</div>
	</div>

	<div style="--size:0.6rem; --dark-c:var(--color-gray-500)">
		{$i18n.t('To select filters here, add them to the "Functions" workshop first.')}
	</div>

	<!-- TODO: Filer order matters -->
	<div style="--d:flex; --fd:column">
		{#if filters.length > 0}
			<div style="--d:flex; --ai:center; --mt:0.5rem; --fw:wrap">
				{#each Object.keys(_filters) as filter, filterIdx}
					<div style="--d:flex; --ai:center; --g:0.5rem; --mr:0.6rem">
						<div style="--as:center; --d:flex; --ai:center">
							<Checkbox
								state={_filters[filter].is_global
									? 'checked'
									: _filters[filter].selected
										? 'checked'
										: 'unchecked'}
								disabled={_filters[filter].is_global}
								on:change={(e) => {
									if (!_filters[filter].is_global) {
										_filters[filter].selected = e.detail === 'checked';
										selectedFilterIds = Object.keys(_filters).filter((t) => _filters[t].selected);
									}
								}}
							/>
						</div>

						<div style="--py:0.125rem; --size:0.875rem; --w:100%; --tt:capitalize; --weight:500">
							<Tooltip content={_filters[filter].meta.description}>
								{_filters[filter].name}
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
