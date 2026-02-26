<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import { verifyOpenAIConnection } from '$lib/apis/openai';
	import { verifyOllamaConnection } from '$lib/apis/ollama';

	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tags from './common/Tags.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let ollama = false;
	export let direct = false;

	export let connection = null;

	let url = '';
	let key = '';

	let connectionType = 'external';
	let azure = false;
	$: azure =
		(url.includes('azure.com') || url.includes('cognitive.microsoft.com')) && !direct
			? true
			: false;

	let prefixId = '';
	let enable = true;
	let apiVersion = '';

	let tags = [];

	let modelId = '';
	let modelIds = [];

	let loading = false;

	const verifyOllamaHandler = async () => {
		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		const res = await verifyOllamaConnection(localStorage.token, {
			url,
			key
		}).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyOpenAIHandler = async () => {
		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		const res = await verifyOpenAIConnection(
			localStorage.token,
			{
				url,
				key,
				config: {
					azure: azure,
					api_version: apiVersion
				}
			},
			direct
		).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Server connection verified'));
		}
	};

	const verifyHandler = () => {
		if (ollama) {
			verifyOllamaHandler();
		} else {
			verifyOpenAIHandler();
		}
	};

	const addModelHandler = () => {
		if (modelId) {
			modelIds = [...modelIds, modelId];
			modelId = '';
		}
	};

	const submitHandler = async () => {
		loading = true;

		if (!ollama && !url) {
			loading = false;
			toast.error('URL is required');
			return;
		}

		if (azure) {
			if (!apiVersion) {
				loading = false;

				toast.error('API Version is required');
				return;
			}

			if (!key) {
				loading = false;

				toast.error('Key is required');
				return;
			}

			if (modelIds.length === 0) {
				loading = false;
				toast.error('Deployment names are required');
				return;
			}
		}

		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		const connection = {
			url,
			key,
			config: {
				enable: enable,
				tags: tags,
				prefix_id: prefixId,
				model_ids: modelIds,
				connection_type: connectionType,
				...(!ollama && azure ? { azure: true, api_version: apiVersion } : {})
			}
		};

		await onSubmit(connection);

		loading = false;
		show = false;

		url = '';
		key = '';
		prefixId = '';
		tags = [];
		modelIds = [];
	};

	const init = () => {
		if (connection) {
			url = connection.url;
			key = connection.key;

			enable = connection.config?.enable ?? true;
			tags = connection.config?.tags ?? [];
			prefixId = connection.config?.prefix_id ?? '';
			modelIds = connection.config?.model_ids ?? [];

			if (ollama) {
				connectionType = connection.config?.connection_type ?? 'local';
			} else {
				connectionType = connection.config?.connection_type ?? 'external';
				azure = connection.config?.azure ?? false;
				apiVersion = connection.config?.api_version ?? '';
			}
		}
	};

	$: if (show) {
		init();
	}

	onMount(() => {
		init();
	});
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.25rem; --pt:1rem; --pb:0.375rem">
			<h1 style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{#if edit}
					{$i18n.t('Edit Connection')}
				{:else}
					{$i18n.t('Add Connection')}
				{/if}
			</h1>
			<button
				style="--as:center"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:1rem; --g-md:1rem; --dark-c:var(--color-gray-200)">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div style="--px:0.25rem">
						{#if !direct}
							<div style="--d:flex; --g:0.5rem">
								<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
									<div style="--size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Connection Type')}</div>

									<div class="">
										<button
											on:click={() => {
												connectionType = connectionType === 'local' ? 'external' : 'local';
											}}
											type="button"
											style="--size:0.75rem; --c:var(--color-gray-700); --dark-c:var(--color-gray-300)"
										>
											{#if connectionType === 'local'}
												{$i18n.t('Local')}
											{:else}
												{$i18n.t('External')}
											{/if}
										</button>
									</div>
								</div>
							</div>
						{/if}

						<div style="--d:flex; --g:0.5rem; --mt:0.375rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<label
									for="url-input"
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
									>{$i18n.t('URL')}</label
								>

								<div style="--fx:1 1 0%">
									<input
										id="url-input"
										class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={url}
										placeholder={$i18n.t('API Base URL')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<Tooltip content={$i18n.t('Verify Connection')} className="self-end -mb-1">
								<button
									style="--as:center; --p:0.25rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									on:click={() => {
										verifyHandler();
									}}
									type="button"
									aria-label={$i18n.t('Verify Connection')}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										aria-hidden="true"
										style="--w:1rem; --h:1rem"
									>
										<path
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</Tooltip>

							<div style="--d:flex; --fd:column; --fs:0; --as:flex-end">
								<label class="sr-only" for="toggle-connection"
									>{$i18n.t('Toggle whether current connection is active.')}</label
								>
								<Tooltip content={enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch id="toggle-connection" bind:state={enable} />
								</Tooltip>
							</div>
						</div>

						<div style="--d:flex; --g:0.5rem; --mt:0.5rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<div
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
								>
									{$i18n.t('Key')}
								</div>

								<div style="--fx:1 1 0%">
									<SensitiveInput
										inputClassName={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										bind:value={key}
										placeholder={$i18n.t('API Key')}
										required={false}
									/>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%">
								<label
									for="prefix-id-input"
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
									>{$i18n.t('Prefix ID')}</label
								>

								<div style="--fx:1 1 0%">
									<Tooltip
										content={$i18n.t(
											'Prefix ID is used to avoid conflicts with other connections by adding a prefix to the model IDs - leave empty to disable'
										)}
									>
										<input
											class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											id="prefix-id-input"
											bind:value={prefixId}
											placeholder={$i18n.t('Prefix ID')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						</div>

						{#if azure}
							<div style="--d:flex; --g:0.5rem; --mt:0.5rem">
								<div style="--d:flex; --fd:column; --w:100%">
									<label
										for="api-version-input"
										class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
										>{$i18n.t('API Version')}</label
									>

									<div style="--fx:1 1 0%">
										<input
											id="api-version-input"
											class={`w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={apiVersion}
											placeholder={$i18n.t('API Version')}
											autocomplete="off"
											required
										/>
									</div>
								</div>
							</div>
						{/if}

						<div style="--d:flex; --g:0.5rem; --mt:0.5rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<div
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
								>
									{$i18n.t('Tags')}
								</div>

								<div style="--fx:1 1 0%">
									<Tags
										bind:tags
										on:add={(e) => {
											tags = [
												...tags,
												{
													name: e.detail
												}
											];
										}}
										on:delete={(e) => {
											tags = tags.filter((tag) => tag.name !== e.detail);
										}}
									/>
								</div>
							</div>
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

						<div style="--d:flex; --fd:column; --w:100%">
							<div style="--mb:0.25rem; --d:flex; --jc:space-between">
								<div
									class={`mb-0.5 text-xs text-gray-500
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
								>
									{$i18n.t('Model IDs')}
								</div>
							</div>

							{#if modelIds.length > 0}
								<ul style="--d:flex; --fd:column">
									{#each modelIds as modelId, modelIdx}
										<li style="--d:flex; --g:0.5rem; --w:100%; --jc:space-between; --ai:center">
											<div style="--size:0.875rem; --fx:1 1 0%; --py:0.25rem; --radius:0.5rem">
												{modelId}
											</div>
											<div style="--fs:0">
												<button
													aria-label={$i18n.t(`Remove {{MODELID}} from list.`, {
														MODELID: modelId
													})}
													type="button"
													on:click={() => {
														modelIds = modelIds.filter((_, idx) => idx !== modelIdx);
													}}
												>
													<Minus strokeWidth="2" className="size-3.5" />
												</button>
											</div>
										</li>
									{/each}
								</ul>
							{:else}
								<div
									class={`text-gray-500 text-xs text-center py-2 px-10
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : ''}`}
								>
									{#if ollama}
										{$i18n.t('Leave empty to include all models from "{{url}}/api/tags" endpoint', {
											url: url
										})}
									{:else if azure}
										{$i18n.t('Deployment names are required for Azure OpenAI')}
										<!-- {$i18n.t('Leave empty to include all models from "{{url}}" endpoint', {
											url: `${url}/openai/deployments`
										})} -->
									{:else}
										{$i18n.t('Leave empty to include all models from "{{url}}/models" endpoint', {
											url: url
										})}
									{/if}
								</div>
							{/if}
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.375rem; --w:100%" />

						<div style="--d:flex; --ai:center">
							<label class="sr-only" for="add-model-id-input">{$i18n.t('Add a model ID')}</label>
							<input
								style="--w:100%; --py:0.25rem; --size:0.875rem; --radius:0.5rem; --bgc:transparent"
	class="{modelId
									? ''
									: 'text-gray-500'} {($settings?.highContrastMode ?? false)
									? 'dark:placeholder:text-gray-100 placeholder:text-gray-700'
									: 'placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden'}"
								bind:value={modelId}
								id="add-model-id-input"
								placeholder={$i18n.t('Add a model ID')}
							/>

							<div>
								<button
									type="button"
									aria-label={$i18n.t('Add')}
									on:click={() => {
										addModelHandler();
									}}
								>
									<Plus className="size-3.5" strokeWidth="2" />
								</button>
							</div>
						</div>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500; --g:0.375rem">
						{#if edit}
							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --dark-bgc:#000; --hvr-dark-bgc:var(--color-gray-900); --dark-c:#fff; --bgc:#fff; --c:#000; --hvr-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
								type="button"
								on:click={() => {
									onDelete();
									show = false;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

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
			</div>
		</div>
	</div>
</Modal>
