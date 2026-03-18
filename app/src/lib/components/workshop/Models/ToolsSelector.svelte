<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import { getContext, onMount } from 'svelte';

	export let tools = [];

	let _tools = {};

	export let selectedToolIds = [];

	const i18n = getContext('i18n');

	onMount(() => {
		_tools = tools.reduce((acc, tool) => {
			acc[tool.id] = {
				...tool,
				selected: selectedToolIds.includes(tool.id)
			};

			return acc;
		}, {});
	});
</script>

<div>
	<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.2rem">
		<div style="--as:center; --size:0.8rem; --weight:600">{$i18n.t('Tools')}</div>
	</div>

	<div style="--size:0.6rem; --dark-c:var(--color-gray-500)">
		{$i18n.t('To select toolkits here, add them to the "Tools" workshop first.')}
	</div>

	<div style="--d:flex; --fd:column">
		{#if tools.length > 0}
			<div style="--d:flex; --ai:center; --mt:0.5rem; --fw:wrap">
				{#each Object.keys(_tools) as tool, toolIdx}
					<div style="--d:flex; --ai:center; --g:0.5rem; --mr:0.6rem">
						<div style="--as:center; --d:flex; --ai:center">
							<Checkbox
								state={_tools[tool].selected ? 'checked' : 'unchecked'}
								on:change={(e) => {
									_tools[tool].selected = e.detail === 'checked';
									selectedToolIds = Object.keys(_tools).filter((t) => _tools[t].selected);
								}}
							/>
						</div>

						<div style="--py:0.125rem; --size:0.8rem; --w:100%; --tt:capitalize; --weight:500">
							{_tools[tool].name}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
