<script>
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { models } from '$lib/stores';
	import { deleteAllModels } from '$lib/apis/models';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ModelList from './ModelList.svelte';
	import { getModelsConfig, setModelsConfig } from '$lib/apis/configs';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let initHandler = () => {};

	let config = null;

	let selectedModelId = '';
	let defaultModelIds = [];
	let modelIds = [];

	let sortKey = '';
	let sortOrder = '';

	let loading = false;
	let showResetModal = false;

	$: if (show) {
		init();
	}

	$: if (selectedModelId) {
		onModelSelect();
	}

	const onModelSelect = () => {
		if (selectedModelId === '') {
			return;
		}

		if (defaultModelIds.includes(selectedModelId)) {
			selectedModelId = '';
			return;
		}

		defaultModelIds = [...defaultModelIds, selectedModelId];
		selectedModelId = '';
	};

	const init = async () => {
		config = await getModelsConfig(localStorage.token);

		if (config?.DEFAULT_MODELS) {
			defaultModelIds = (config?.DEFAULT_MODELS).split(',').filter((id) => id);
		} else {
			defaultModelIds = [];
		}
		const modelOrderList = config.MODEL_ORDER_LIST || [];
		const allModelIds = $models.map((model) => model.id);

		// Create a Set for quick lookup of ordered IDs
		const orderedSet = new Set(modelOrderList);

		modelIds = [
			// Add all IDs from MODEL_ORDER_LIST that exist in allModelIds
			...modelOrderList.filter((id) => orderedSet.has(id) && allModelIds.includes(id)),
			// Add remaining IDs not in MODEL_ORDER_LIST, sorted alphabetically
			...allModelIds.filter((id) => !orderedSet.has(id)).sort((a, b) => a.localeCompare(b))
		];

		sortKey = '';
		sortOrder = '';
	};
	const submitHandler = async () => {
		loading = true;

		const res = await setModelsConfig(localStorage.token, {
			DEFAULT_MODELS: defaultModelIds.join(','),
			MODEL_ORDER_LIST: modelIds,
			DEFAULT_MODEL_SELECTOR_FILTER: config?.DEFAULT_MODEL_SELECTOR_FILTER ?? 'agents'
		});

		if (res) {
			toast.success($i18n.t('Models configuration saved successfully'));
			initHandler();
			show = false;
		} else {
			toast.error($i18n.t('Failed to save models configuration'));
		}

		loading = false;
	};

	onMount(async () => {
		init();
	});
</script>

<ConfirmDialog
	title={$i18n.t('Reset All Models')}
	message={$i18n.t('This will delete all models including custom models and cannot be undone.')}
	bind:show={showResetModal}
	onConfirm={async () => {
		const res = deleteAllModels(localStorage.token);
		if (res) {
			toast.success($i18n.t('All models deleted successfully'));
			initHandler();
		}
	}}
/>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{$i18n.t('Settings')}
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.25rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				{#if config}
					<form
						style="--d:flex; --fd:column; --w:100%"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<div>
							<div style="--d:flex; --fd:column; --w:100%">
								<button
									style="--mb:0.25rem; --d:flex; --g:0.5rem"
									type="button"
									on:click={() => {
										sortKey = 'model';

										if (sortOrder === 'asc') {
											sortOrder = 'desc';
										} else {
											sortOrder = 'asc';
										}

										modelIds = modelIds
											.filter((id) => id !== '')
											.sort((a, b) => {
												const nameA = $models.find((model) => model.id === a)?.name || a;
												const nameB = $models.find((model) => model.id === b)?.name || b;
												return sortOrder === 'desc'
													? nameA.localeCompare(nameB)
													: nameB.localeCompare(nameA);
											});
									}}
								>
									<div style="--size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Reorder Models')}</div>

									{#if sortKey === 'model'}
										<span style="--weight:400; --as:center">
											{#if sortOrder === 'asc'}
												<ChevronUp className="size-3" />
											{:else}
												<ChevronDown className="size-3" />
											{/if}
										</span>
									{:else}
										<span style="--v:hidden">
											<ChevronUp className="size-3" />
										</span>
									{/if}
								</button>

								<ModelList bind:modelIds />
							</div>
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

						<div>
							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.25rem; --d:flex; --jc:space-between">
									<div style="--size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Default Selector Filter')}</div>
								</div>

								<div style="--d:flex; --ai:center; --mr:-0.25rem">
									<select
										style="--w:100%; --py:0.25rem; --size:0.875rem; --radius:0.5rem; --bgc:transparent; --oe:none"
										bind:value={config.DEFAULT_MODEL_SELECTOR_FILTER}
									>
										<option value="">{$i18n.t('All')}</option>
										<option value="agents">{$i18n.t('Agents')}</option>
										<option value="local">{$i18n.t('Local')}</option>
										<option value="external">{$i18n.t('External')}</option>
										<option value="direct">{$i18n.t('Direct')}</option>
									</select>
								</div>
							</div>
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

						<div>
							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.25rem; --d:flex; --jc:space-between">
									<div style="--size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Default Models')}</div>
								</div>

								<div style="--d:flex; --ai:center; --mr:-0.25rem">
									<select
										style="--w:100%; --py:0.25rem; --size:0.875rem; --radius:0.5rem; --bgc:transparent; --oe:none"
	class="{selectedModelId
											? ''
											: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700"
										bind:value={selectedModelId}
									>
										<option value="">{$i18n.t('Select a model')}</option>
										{#each $models as model}
											<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)"
												>{model.name}</option
											>
										{/each}
									</select>
								</div>

								<!-- <hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" /> -->

								{#if defaultModelIds.length > 0}
									<div style="--d:flex; --fd:column">
										{#each defaultModelIds as modelId, modelIdx}
											<div style="--d:flex; --g:0.5rem; --w:100%; --jc:space-between; --ai:center">
												<div style="--size:0.875rem; --fx:1 1 0%; --py:0.25rem; --radius:0.5rem">
													{$models.find((model) => model.id === modelId)?.name}
												</div>
												<div style="--fs:0">
													<button
														type="button"
														on:click={() => {
															defaultModelIds = defaultModelIds.filter(
																(_, idx) => idx !== modelIdx
															);
														}}
													>
														<Minus strokeWidth="2" className="size-3.5" />
													</button>
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<div style="--c:var(--color-gray-500); --size:0.6rem; --ta:center; --py:0.5rem">
										{$i18n.t('No models selected')}
									</div>
								{/if}
							</div>
						</div>

						<div style="--d:flex; --jc:space-between; --pt:0.6rem; --size:0.875rem; --weight:500; --g:0.375rem">
							<Tooltip content={$i18n.t('This will delete all models including custom models')}>
								<button
									style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --dark-bgc:#000; --hvr-dark-bgc:var(--color-gray-950); --dark-c:#fff; --bgc:#fff; --c:#000; --hvr-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
									type="button"
									on:click={() => {
										showResetModal = true;
									}}
								>
									<!-- {$i18n.t('Delete All Models')} -->
									{$i18n.t('Reset All Models')}
								</button>
							</Tooltip>

							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
									? ' cursor-not-allowed'
									: ''}"
								type="submit"
								disabled={loading}
							>
								{$i18n.t('Save')}

								{#if loading}
									<div style="--ml:0.5rem; --as:center">
										<Spinner />
									</div>
								{/if}
							</button>
						</div>
					</form>
				{:else}
					<div>
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
