<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { models, settings, user, config } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();
	import { getModels } from '$lib/apis';
	import { getConfig, updateConfig } from '$lib/apis/evaluations';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Model from './Evaluations/Model.svelte';
	import ArenaModelModal from './Evaluations/ArenaModelModal.svelte';

	const i18n = getContext('i18n');

	let evaluationConfig = null;
	let showAddModel = false;

	const submitHandler = async () => {
		evaluationConfig = await updateConfig(localStorage.token, evaluationConfig).catch((err) => {
			toast.error(err);
			return null;
		});

		if (evaluationConfig) {
			toast.success('Settings saved successfully');
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};

	const addModelHandler = async (model) => {
		evaluationConfig.EVALUATION_ARENA_MODELS.push(model);
		evaluationConfig.EVALUATION_ARENA_MODELS = [...evaluationConfig.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const editModelHandler = async (model, modelIdx) => {
		evaluationConfig.EVALUATION_ARENA_MODELS[modelIdx] = model;
		evaluationConfig.EVALUATION_ARENA_MODELS = [...evaluationConfig.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const deleteModelHandler = async (modelIdx) => {
		evaluationConfig.EVALUATION_ARENA_MODELS = evaluationConfig.EVALUATION_ARENA_MODELS.filter(
			(m, mIdx) => mIdx !== modelIdx
		);

		await submitHandler();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			evaluationConfig = await getConfig(localStorage.token).catch((err) => {
				toast.error(err);
				return null;
			});
		}
	});
</script>

<ArenaModelModal
	bind:show={showAddModel}
	on:submit={async (e) => {
		addModelHandler(e.detail);
	}}
/>

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.875rem"
	on:submit|preventDefault={() => {
		submitHandler();
		dispatch('save');
	}}
>
	<div style="--ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if evaluationConfig !== null}
			<div class="">
				<div style="--mb:0.75rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('General')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem; --d:flex; --w:100%; --jc:space-between">
						<div style="--size:0.75rem; --weight:500">{$i18n.t('Arena Models')}</div>

						<Tooltip content={$i18n.t(`Message rating should be enabled to use this feature`)}>
							<Switch bind:state={evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS} />
						</Tooltip>
					</div>
				</div>

				{#if evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS}
					<div style="--mb:0.75rem">
						<div style="--mb:0.625rem; --size:1rem; --weight:500; --d:flex; --jc:space-between; --ai:center">
							<div>
								{$i18n.t('Manage')}
							</div>

							<div>
								<Tooltip content={$i18n.t('Add Arena Model')}>
									<button
										style="--p:0.25rem"
										type="button"
										on:click={() => {
											showAddModel = true;
										}}
									>
										<Plus />
									</button>
								</Tooltip>
							</div>
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

						<div style="--d:flex; --fd:column; --g:0.5rem">
							{#if (evaluationConfig?.EVALUATION_ARENA_MODELS ?? []).length > 0}
								{#each evaluationConfig.EVALUATION_ARENA_MODELS as model, index}
									<Model
										{model}
										on:edit={(e) => {
											editModelHandler(e.detail, index);
										}}
										on:delete={(e) => {
											deleteModelHandler(index);
										}}
									/>
								{/each}
							{:else}
								<div style="--ta:center; --size:0.75rem; --c:var(--color-gray-500)">
									{$i18n.t(
										`Using the default arena model with all models. Click the plus button to add custom models.`
									)}
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		{:else}
			<div style="--d:flex; --h:100%; --jc:center">
				<div style="--my:auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
		<button
			style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
