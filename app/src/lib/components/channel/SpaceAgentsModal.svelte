<script lang="ts">
	import { getContext } from 'svelte';
	import { models } from '$lib/stores';
	import { updateSpaceById } from '$lib/apis/spaces';
	import Modal from '$lib/components/common/Modal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let space;
	export let onSave: () => void = () => {};

	let agents: { model_id: string; name: string; profile_image_url: string }[] = [];
	let selectedModelId = '';

	$: if (show && space) {
		agents = [...(space?.data?.agents ?? [])];
	}

	$: availableModels = ($models ?? []).filter(
		(m) => !agents.find((a) => a.model_id === m.id)
	);

	const addAgent = () => {
		if (!selectedModelId) return;
		const model = $models.find((m) => m.id === selectedModelId);
		if (!model) return;

		agents = [
			...agents,
			{
				model_id: model.id,
				name: model.name,
				profile_image_url:
					model?.info?.meta?.profile_image_url || '/static/icons/favicon.png'
			}
		];
		selectedModelId = '';
	};

	const removeAgent = (modelId: string) => {
		agents = agents.filter((a) => a.model_id !== modelId);
	};

	const saveHandler = async () => {
		const updatedData = { ...(space.data || {}), agents };
		await updateSpaceById(localStorage.token, space.id, {
			name: space.name,
			data: updatedData,
			meta: space.meta,
			access_control: space.access_control
		});
		show = false;
		onSave();
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --ai:center; --mb:1rem">
			<h3 style="--weight:600; --size:1.1rem">{$i18n.t('Manage Agents')}</h3>
			<button
				style="--c:var(--color-gray-500); --hvr-c:var(--color-gray-700)"
				on:click={() => (show = false)}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					style="--w:1.25rem; --h:1.25rem"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		{#if agents.length > 0}
			<div style="--d:flex; --fd:column; --g:0.5rem; --mb:1rem">
				{#each agents as agent}
					<div
						style="--d:flex; --ai:center; --jc:space-between; --px:0.75rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800)"
					>
						<div style="--d:flex; --ai:center; --g:0.5rem">
							<img
								src={agent.profile_image_url || '/static/icons/favicon.png'}
								alt={agent.name}
								style="--w:1.5rem; --h:1.5rem; --radius:9999px; --objf:cover"
							/>
							<span style="--weight:500; --size:0.9rem">{agent.name}</span>
							<span
								style="--size:0.6rem; --px:0.35rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-blue-100); --dark-bgc:var(--color-blue-900); --c:var(--color-blue-700); --dark-c:var(--color-blue-300); --weight:600"
							>
								BOT
							</span>
						</div>
						<Tooltip content={$i18n.t('Remove')}>
							<button
								style="--c:var(--color-gray-500); --hvr-c:var(--color-red-500); --tn:color 150ms"
								on:click={() => removeAgent(agent.model_id)}
							>
								<GarbageBin className="size-4" />
							</button>
						</Tooltip>
					</div>
				{/each}
			</div>
		{:else}
			<div
				style="--py:2rem; --ta:center; --c:var(--color-gray-400); --size:0.85rem; --mb:1rem"
			>
				{$i18n.t('No agents added yet')}
			</div>
		{/if}

		<div style="--d:flex; --g:0.5rem; --mb:1rem">
			<select
				bind:value={selectedModelId}
				style="--fx:1 1 0%; --px:0.75rem; --py:0.5rem; --radius:0.5rem;  --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bgc:#fff; --dark-bgc:var(--color-gray-850); --size:0.85rem"
			>
				<option value="">{$i18n.t('Select a model...')}</option>
				{#each availableModels as model}
					<option value={model.id}>{model.name}</option>
				{/each}
			</select>
			<button
				style="--px:1rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-900); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900); --weight:500; --size:0.85rem; --hvr-opacity:0.9; --tn:opacity 150ms"
				disabled={!selectedModelId}
				on:click={addAgent}
			>
				{$i18n.t('Add')}
			</button>
		</div>

		<div style="--d:flex; --jc:flex-end; --g:0.5rem">
			<button
				style="--px:1rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --weight:500; --size:0.85rem"
				on:click={() => (show = false)}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				style="--px:1rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-900); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900); --weight:500; --size:0.85rem; --hvr-opacity:0.9; --tn:opacity 150ms"
				on:click={saveHandler}
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</div>
</Modal>
