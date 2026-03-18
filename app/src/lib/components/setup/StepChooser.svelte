<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let onStart: (steps: string[]) => void = () => {};

	let includeConnection = true;
	let includeUsers = true;

	$: canStart = includeConnection || includeUsers;

	const handleStart = () => {
		const steps: string[] = [];
		if (includeConnection) steps.push('connection');
		if (includeUsers) steps.push('users');
		onStart(steps);
	};
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	<div style="--size:1.2rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
		{$i18n.t('What would you like to configure?')}
	</div>
	<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
		{$i18n.t('Select the steps need want to run.')}
	</div>

	<div style="--d:flex; --fd:column; --g:0.6rem; --mb:1.5rem">
		<label
			style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
		>
			<input
				type="checkbox"
				bind:checked={includeConnection}
				style="--w:1rem; --h:1rem; --shrink:0"
			/>
			<div>
				<div style="--size:0.85rem; --weight:500">{$i18n.t('Model Connections')}</div>
				<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
					{$i18n.t('Add or update API connections')}
				</div>
			</div>
		</label>

		<label
			style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
		>
			<input
				type="checkbox"
				bind:checked={includeUsers}
				style="--w:1rem; --h:1rem; --shrink:0"
			/>
			<div>
				<div style="--size:0.85rem; --weight:500">{$i18n.t('Users')}</div>
				<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
					{$i18n.t('Add users or change working-alone mode')}
				</div>
			</div>
		</label>
	</div>

	<div style="--d:flex; --jc:flex-end">
		<button
			on:click={handleStart}
			disabled={!canStart}
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:{canStart ? '#000' : 'var(--color-gray-300)'}; --hvr-bgc:{canStart ? 'var(--color-gray-900)' : 'var(--color-gray-300)'}; --c:#fff; --dark-bgc:{canStart ? '#fff' : 'var(--color-gray-600)'}; --dark-c:{canStart ? '#000' : 'var(--color-gray-400)'}; --hvr-dark-bgc:{canStart ? 'var(--color-gray-100)' : 'var(--color-gray-600)'}; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
		>
			{$i18n.t('Start')}
		</button>
	</div>
</div>
