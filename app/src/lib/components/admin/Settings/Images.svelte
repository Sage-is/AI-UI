<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { config as backendConfig, user } from '$lib/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		getImageGenerationModels,
		getImageGenerationConfig,
		updateImageGenerationConfig,
		getConfig,
		updateConfig,
		verifyConfigUrl
	} from '$lib/apis/images';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let loading = false;

	let config = null;
	let imageGenerationConfig = null;

	let models = null;

	let samplers = [
		'DPM++ 2M',
		'DPM++ SDE',
		'DPM++ 2M SDE',
		'DPM++ 2M SDE Heun',
		'DPM++ 2S a',
		'DPM++ 3M SDE',
		'Euler a',
		'Euler',
		'LMS',
		'Heun',
		'DPM2',
		'DPM2 a',
		'DPM fast',
		'DPM adaptive',
		'Restart',
		'DDIM',
		'DDIM CFG++',
		'PLMS',
		'UniPC'
	];

	let schedulers = [
		'Automatic',
		'Uniform',
		'Karras',
		'Exponential',
		'Polyexponential',
		'SGM Uniform',
		'KL Optimal',
		'Align Your Steps',
		'Simple',
		'Normal',
		'DDIM',
		'Beta'
	];

	let requiredWorkflowNodes = [
		{
			type: 'prompt',
			key: 'text',
			node_ids: ''
		},
		{
			type: 'model',
			key: 'ckpt_name',
			node_ids: ''
		},
		{
			type: 'width',
			key: 'width',
			node_ids: ''
		},
		{
			type: 'height',
			key: 'height',
			node_ids: ''
		},
		{
			type: 'steps',
			key: 'steps',
			node_ids: ''
		},
		{
			type: 'seed',
			key: 'seed',
			node_ids: ''
		}
	];

	const getModels = async () => {
		models = await getImageGenerationModels(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const updateConfigHandler = async () => {
		const res = await updateConfig(localStorage.token, config)
			.catch((error) => {
				toast.error(`${error}`);
				return null;
			})
			.catch((error) => {
				toast.error(`${error}`);
				return null;
			});

		if (res) {
			config = res;
		}

		if (config.enabled) {
			backendConfig.set(await getBackendConfig());
			getModels();
		}
	};

	const validateJSON = (json) => {
		try {
			const obj = JSON.parse(json);

			if (obj && typeof obj === 'object') {
				return true;
			}
		} catch (e) {}
		return false;
	};

	const saveHandler = async () => {
		loading = true;

		if (config?.comfyui?.COMFYUI_WORKFLOW) {
			if (!validateJSON(config.comfyui.COMFYUI_WORKFLOW)) {
				toast.error('Invalid JSON format for ComfyUI Workflow.');
				loading = false;
				return;
			}
		}

		if (config?.comfyui?.COMFYUI_WORKFLOW) {
			config.comfyui.COMFYUI_WORKFLOW_NODES = requiredWorkflowNodes.map((node) => {
				return {
					type: node.type,
					key: node.key,
					node_ids:
						node.node_ids.trim() === '' ? [] : node.node_ids.split(',').map((id) => id.trim())
				};
			});
		}

		await updateConfig(localStorage.token, config).catch((error) => {
			toast.error(`${error}`);
			loading = false;
			return null;
		});

		await updateImageGenerationConfig(localStorage.token, imageGenerationConfig).catch((error) => {
			toast.error(`${error}`);
			loading = false;
			return null;
		});

		getModels();
		dispatch('save');
		loading = false;
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			const res = await getConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				config = res;
			}

			if (config.enabled) {
				getModels();
			}

			if (config.comfyui.COMFYUI_WORKFLOW) {
				try {
					config.comfyui.COMFYUI_WORKFLOW = JSON.stringify(
						JSON.parse(config.comfyui.COMFYUI_WORKFLOW),
						null,
						2
					);
				} catch (e) {
					console.error(e);
				}
			}

			requiredWorkflowNodes = requiredWorkflowNodes.map((node) => {
				const n = config.comfyui.COMFYUI_WORKFLOW_NODES.find((n) => n.type === node.type) ?? node;

				console.debug(n);

				return {
					type: n.type,
					key: n.key,
					node_ids: typeof n.node_ids === 'string' ? n.node_ids : n.node_ids.join(',')
				};
			});

			const imageConfigRes = await getImageGenerationConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (imageConfigRes) {
				imageGenerationConfig = imageConfigRes;
			}
		}
	});
</script>

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.75rem; --size:0.875rem"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div style="--g:0.75rem; --ofy:scroll; --pr:0.5rem"
	class="scrollbar-hidden">
		{#if config && imageGenerationConfig}
			<div>
				<div style="--mb:0.25rem; --size:0.875rem; --weight:500">{$i18n.t('Image Settings')}</div>

				<div>
					<div style="--py:0.25rem; --d:flex; --w:100%; --jc:space-between">
						<div style="--as:center; --size:0.75rem; --weight:500">
							{$i18n.t('Image Generation (Experimental)')}
						</div>

						<div style="--px:0.25rem">
							<Switch
								bind:state={config.enabled}
								on:change={(e) => {
									const enabled = e.detail;

									if (enabled) {
										if (
											config.engine === 'automatic1111' &&
											config.automatic1111.AUTOMATIC1111_BASE_URL === ''
										) {
											toast.error($i18n.t('AUTOMATIC1111 Base URL is required.'));
											config.enabled = false;
										} else if (
											config.engine === 'comfyui' &&
											config.comfyui.COMFYUI_BASE_URL === ''
										) {
											toast.error($i18n.t('ComfyUI Base URL is required.'));
											config.enabled = false;
										} else if (config.engine === 'openai' && config.openai.OPENAI_API_KEY === '') {
											toast.error($i18n.t('OpenAI Compatible API Key is required.'));
											config.enabled = false;
										} else if (config.engine === 'gemini' && config.gemini.GEMINI_API_KEY === '') {
											toast.error($i18n.t('Gemini API Key is required.'));
											config.enabled = false;
										}
									}

									updateConfigHandler();
								}}
							/>
						</div>
					</div>
				</div>

				{#if config.enabled}
					<div style="--py:0.25rem; --d:flex; --w:100%; --jc:space-between">
						<div style="--as:center; --size:0.75rem; --weight:500">{$i18n.t('Image Prompt Generation')}</div>
						<div style="--px:0.25rem">
							<Switch bind:state={config.prompt_generation} />
						</div>
					</div>
				{/if}

				<div style="--py:0.25rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.75rem; --weight:500">{$i18n.t('Image Generation Engine')}</div>
					<div style="--d:flex; --ai:center; --pos:relative">
						<select
							style="--dark-bgc:var(--color-gray-900, #171717); --w:fit-content; --pr:2rem; --cur:pointer; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.75rem; --bgc:transparent; --oe:none; --ta:right"
							bind:value={config.engine}
							placeholder={$i18n.t('Select Engine')}
							on:change={async () => {
								updateConfigHandler();
							}}
						>
							<option value="openai">{$i18n.t('Default (Open AI)')}</option>
							<option value="comfyui">{$i18n.t('ComfyUI')}</option>
							<option value="automatic1111">{$i18n.t('Automatic1111')}</option>
							<option value="gemini">{$i18n.t('Gemini')}</option>
						</select>
					</div>
				</div>
			</div>
			<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626)" />

			<div style="--d:flex; --fd:column; --g:0.5rem">
				{#if (config?.engine ?? 'automatic1111') === 'automatic1111'}
					<div>
						<div style="--mb:0.5rem; --size:0.875rem; --weight:500">{$i18n.t('AUTOMATIC1111 Base URL')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%; --mr:0.5rem">
								<input
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.automatic1111.AUTOMATIC1111_BASE_URL}
								/>
							</div>
							<button
								style="--px:0.625rem; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --c:var(--color-gray-800, #333); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --dark-c:var(--color-gray-100, #ececec); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								type="button"
								on:click={async () => {
									await updateConfigHandler();
									const res = await verifyConfigUrl(localStorage.token).catch((error) => {
										toast.error(`${error}`);
										return null;
									});

									if (res) {
										toast.success($i18n.t('Server connection verified'));
									}
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										fill-rule="evenodd"
										d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						</div>

						<div style="--mt:0.5rem; --size:0.75rem; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b)">
							{$i18n.t('Include `--api` flag when running stable-diffusion-webui')}
							<a
								style="--c:var(--color-gray-300, #cdcdcd); --weight:500"
								href="https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/3734"
								target="_blank"
							>
								{$i18n.t('(e.g. `sh webui.sh --api`)')}
							</a>
						</div>
					</div>

					<div>
						<div style="--mb:0.5rem; --size:0.875rem; --weight:500">
							{$i18n.t('AUTOMATIC1111 Api Auth String')}
						</div>
						<SensitiveInput
							placeholder={$i18n.t('Enter api auth string (e.g. username:password)')}
							bind:value={config.automatic1111.AUTOMATIC1111_API_AUTH}
							required={false}
						/>

						<div style="--mt:0.5rem; --size:0.75rem; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b)">
							{$i18n.t('Include `--api-auth` flag when running stable-diffusion-webui')}
							<a
								style="--c:var(--color-gray-300, #cdcdcd); --weight:500"
								href="https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/13993"
								target="_blank"
							>
								{$i18n
									.t('(e.g. `sh webui.sh --api --api-auth username_password`)')
									.replace('_', ':')}
							</a>
						</div>
					</div>

					<!---Sampler-->
					<div>
						<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Sampler')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%; --mr:0.5rem">
								<Tooltip content={$i18n.t('Enter Sampler (e.g. Euler a)')} placement="top-start">
									<input
										list="sampler-list"
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
										placeholder={$i18n.t('Enter Sampler (e.g. Euler a)')}
										bind:value={config.automatic1111.AUTOMATIC1111_SAMPLER}
									/>

									<datalist id="sampler-list">
										{#each samplers ?? [] as sampler}
											<option value={sampler}>{sampler}</option>
										{/each}
									</datalist>
								</Tooltip>
							</div>
						</div>
					</div>
					<!---Scheduler-->
					<div>
						<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Scheduler')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%; --mr:0.5rem">
								<Tooltip content={$i18n.t('Enter Scheduler (e.g. Karras)')} placement="top-start">
									<input
										list="scheduler-list"
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
										placeholder={$i18n.t('Enter Scheduler (e.g. Karras)')}
										bind:value={config.automatic1111.AUTOMATIC1111_SCHEDULER}
									/>

									<datalist id="scheduler-list">
										{#each schedulers ?? [] as scheduler}
											<option value={scheduler}>{scheduler}</option>
										{/each}
									</datalist>
								</Tooltip>
							</div>
						</div>
					</div>
					<!---CFG scale-->
					<div>
						<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set CFG Scale')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%; --mr:0.5rem">
								<Tooltip content={$i18n.t('Enter CFG Scale (e.g. 7.0)')} placement="top-start">
									<input
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
										placeholder={$i18n.t('Enter CFG Scale (e.g. 7.0)')}
										bind:value={config.automatic1111.AUTOMATIC1111_CFG_SCALE}
									/>
								</Tooltip>
							</div>
						</div>
					</div>
				{:else if config?.engine === 'comfyui'}
					<div class="">
						<div style="--mb:0.5rem; --size:0.875rem; --weight:500">{$i18n.t('ComfyUI Base URL')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%; --mr:0.5rem">
								<input
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.comfyui.COMFYUI_BASE_URL}
								/>
							</div>
							<button
								style="--px:0.625rem; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --c:var(--color-gray-800, #333); --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --dark-c:var(--color-gray-100, #ececec); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								type="button"
								on:click={async () => {
									await updateConfigHandler();
									const res = await verifyConfigUrl(localStorage.token).catch((error) => {
										toast.error(`${error}`);
										return null;
									});

									if (res) {
										toast.success($i18n.t('Server connection verified'));
									}
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										fill-rule="evenodd"
										d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						</div>
					</div>

					<div class="">
						<div style="--mb:0.5rem; --size:0.875rem; --weight:500">{$i18n.t('ComfyUI API Key')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%; --mr:0.5rem">
								<SensitiveInput
									placeholder={$i18n.t('sk-1234')}
									bind:value={config.comfyui.COMFYUI_API_KEY}
									required={false}
								/>
							</div>
						</div>
					</div>

					<div class="">
						<div style="--mb:0.5rem; --size:0.875rem; --weight:500">{$i18n.t('ComfyUI Workflow')}</div>

						{#if config.comfyui.COMFYUI_WORKFLOW}
							<Textarea
								style="--w:100%; --radius:0.5rem; --mb:0.25rem; --py:0.5rem; --px:1rem; --size:0.75rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none; resize:none"
	class="disabled:text-gray-600"
								rows="10"
								bind:value={config.comfyui.COMFYUI_WORKFLOW}
								required
							/>
						{/if}

						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%">
								<input
									id="upload-comfyui-workflow-input"
									hidden
									type="file"
									accept=".json"
									on:change={(e) => {
										const file = e.target.files[0];
										const reader = new FileReader();

										reader.onload = (e) => {
											config.comfyui.COMFYUI_WORKFLOW = e.target.result;
											e.target.value = null;
										};

										reader.readAsText(file);
									}}
								/>

								<button
									style="--w:100%; --size:0.875rem; --weight:500; --py:0.5rem; --bgc:transparent; --hvr-bgc:var(--color-gray-50, #f9f9f9); --b:1px solid; --bs:dashed; --bc:var(--color-gray-50, #f9f9f9); --dark-bc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-850, #262626); --ta:center; --radius:0.75rem"
									type="button"
									on:click={() => {
										document.getElementById('upload-comfyui-workflow-input')?.click();
									}}
								>
									{$i18n.t('Click here to upload a workflow.json file.')}
								</button>
							</div>
						</div>

						<div style="--mt:0.5rem; --size:0.75rem; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b)">
							{$i18n.t('Make sure to export a workflow.json file as API format from ComfyUI.')}
						</div>
					</div>

					{#if config.comfyui.COMFYUI_WORKFLOW}
						<div class="">
							<div style="--mb:0.5rem; --size:0.875rem; --weight:500">{$i18n.t('ComfyUI Workflow Nodes')}</div>

							<div style="--size:0.75rem; --d:flex; --fd:column; --g:0.375rem">
								{#each requiredWorkflowNodes as node}
									<div style="--d:flex; --w:100%; --ai:center">
										<div style="--fs:0">
											<div
												style="--tt:capitalize; --line-clamp:1; --weight:500; --px:0.75rem; --py:0.25rem; --w:5rem; --ta:center; --bgc:rgb(34 197 94 / 0.1); --c:#15803d; --dark-c:#bbf7d0"
											>
												{node.type}{node.type === 'prompt' ? '*' : ''}
											</div>
										</div>
										<div class="">
											<Tooltip content="Input Key (e.g. text, unet_name, steps)">
												<input
													style="--py:0.25rem; --px:0.75rem; --w:6rem; --size:0.75rem; --ta:center; --bgc:transparent; --oe:none; --br:1px solid; --bc:var(--color-gray-50, #f9f9f9); --dark-bc:var(--color-gray-850, #262626)"
													placeholder="Key"
													bind:value={node.key}
													required
												/>
											</Tooltip>
										</div>

										<div style="--w:100%">
											<Tooltip
												content="Comma separated Node Ids (e.g. 1 or 1,2)"
												placement="top-start"
											>
												<input
													style="--w:100%; --py:0.25rem; --px:1rem; --size:0.75rem; --bgc:transparent; --oe:none"
													placeholder="Node Ids"
													bind:value={node.node_ids}
												/>
											</Tooltip>
										</div>
									</div>
								{/each}
							</div>

							<div style="--mt:0.5rem; --size:0.75rem; --ta:right; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b)">
								{$i18n.t('*Prompt node ID(s) are required for image generation')}
							</div>
						</div>
					{/if}
				{:else if config?.engine === 'openai'}
					<div>
						<div style="--mb:0.375rem; --size:0.875rem; --weight:500">{$i18n.t('OpenAI Compatible API Config')}</div>

						<div style="--d:flex; --g:0.5rem; --mb:0.25rem">
							<input
								style="--fx:1 1 0%; --w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={config.openai.OPENAI_API_BASE_URL}
								required
							/>

							<SensitiveInput
								placeholder={$i18n.t('API Key')}
								bind:value={config.openai.OPENAI_API_KEY}
							/>
						</div>
					</div>
				{:else if config?.engine === 'gemini'}
					<div>
						<div style="--mb:0.375rem; --size:0.875rem; --weight:500">{$i18n.t('Gemini API Config')}</div>

						<div style="--d:flex; --g:0.5rem; --mb:0.25rem">
							<input
								style="--fx:1 1 0%; --w:100%; --size:0.875rem; --bgc:transparent; --oe:2px solid transparent"
								placeholder={$i18n.t('API Base URL')}
								bind:value={config.gemini.GEMINI_API_BASE_URL}
								required
							/>

							<SensitiveInput
								placeholder={$i18n.t('API Key')}
								bind:value={config.gemini.GEMINI_API_KEY}
							/>
						</div>
					</div>
				{/if}
			</div>

			{#if config?.enabled}
				<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626)" />

				<div>
					<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Default Model')}</div>
					<div style="--d:flex; --w:100%">
						<div style="--fx:1 1 0%; --mr:0.5rem">
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<Tooltip content={$i18n.t('Enter Model ID')} placement="top-start">
										<input
											list="model-list"
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
											bind:value={imageGenerationConfig.MODEL}
											placeholder="Select a model"
											required
										/>

										<datalist id="model-list">
											{#each models ?? [] as model}
												<option value={model.id}>{model.name}</option>
											{/each}
										</datalist>
									</Tooltip>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div>
					<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Image Size')}</div>
					<div style="--d:flex; --w:100%">
						<div style="--fx:1 1 0%; --mr:0.5rem">
							<Tooltip content={$i18n.t('Enter Image Size (e.g. 512x512)')} placement="top-start">
								<input
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
									placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
									bind:value={imageGenerationConfig.IMAGE_SIZE}
									required
								/>
							</Tooltip>
						</div>
					</div>
				</div>

				<div>
					<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Steps')}</div>
					<div style="--d:flex; --w:100%">
						<div style="--fx:1 1 0%; --mr:0.5rem">
							<Tooltip content={$i18n.t('Enter Number of Steps (e.g. 50)')} placement="top-start">
								<input
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-c:var(--color-gray-300, #cdcdcd); --dark-bgc:var(--color-gray-850, #262626); --oe:none"
									placeholder={$i18n.t('Enter Number of Steps (e.g. 50)')}
									bind:value={imageGenerationConfig.IMAGE_STEPS}
									required
								/>
							</Tooltip>
						</div>
					</div>
				</div>
			{/if}
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
		<button
			style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900, #171717); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
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
