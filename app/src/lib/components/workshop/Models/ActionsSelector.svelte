<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let actions = [];
	export let selectedActionIds = [];

	let _actions = {};

	onMount(() => {
		_actions = actions.reduce((acc, action) => {
			acc[action.id] = {
				...action,
				selected: selectedActionIds.includes(action.id)
			};

			return acc;
		}, {});
	});
</script>

<div>
	<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.25rem">
		<div style="--as:center; --size:0.875rem; --weight:600">{$i18n.t('Actions')}</div>
	</div>

	<div style="--size:0.75rem; --dark-c:var(--color-gray-500)">
		{$i18n.t('To select actions here, add them to the "Functions" workshop first.')}
	</div>

	<div style="--d:flex; --fd:column">
		{#if actions.length > 0}
			<div style="--d:flex; --ai:center; --mt:0.5rem; --fw:wrap">
				{#each Object.keys(_actions) as action, actionIdx}
					<div style="--d:flex; --ai:center; --g:0.5rem; --mr:0.75rem">
						<div style="--as:center; --d:flex; --ai:center">
							<Checkbox
								state={_actions[action].selected ? 'checked' : 'unchecked'}
								on:change={(e) => {
									_actions[action].selected = e.detail === 'checked';
									selectedActionIds = Object.keys(_actions).filter((t) => _actions[t].selected);
								}}
							/>
						</div>

						<div style="--py:0.125rem; --size:0.875rem; --w:100%; --tt:capitalize; --weight:500">
							<Tooltip content={_actions[action].meta.description}>
								{_actions[action].name}
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
