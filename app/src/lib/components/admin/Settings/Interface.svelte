<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';

	import { getBackendConfig, getModels, getTaskConfig, updateTaskConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	import { banners as _banners } from '$lib/stores';
	import type { Banner } from '$lib/types';

	import { getBaseModels } from '$lib/apis/models';
	import { getBanners, setBanners } from '$lib/apis/configs';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Banners from './Interface/Banners.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let taskConfig = {
		TASK_MODEL: '',
		TASK_MODEL_EXTERNAL: '',
		ENABLE_TITLE_GENERATION: true,
		TITLE_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_FOLLOW_UP_GENERATION: false,
		FOLLOW_UP_GENERATION_PROMPT_TEMPLATE: '',
		IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_AUTOCOMPLETE_GENERATION: true,
		AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH: -1,
		TAGS_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_TAGS_GENERATION: true,

		ENABLE_RETRIEVAL_QUERY_GENERATION: true,
		QUERY_GENERATION_PROMPT_TEMPLATE: '',
		TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: ''
	};

	let promptSuggestions = [];
	let banners: Banner[] = [];

	const updateInterfaceHandler = async () => {
		taskConfig = await updateTaskConfig(localStorage.token, taskConfig);

		promptSuggestions = promptSuggestions.filter((p) => p.content !== '');
		promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
		await updateBanners();

		await config.set(await getBackendConfig());
	};

	onMount(async () => {
		await init();
		taskConfig = await getTaskConfig(localStorage.token);

		promptSuggestions = $config?.default_prompt_suggestions ?? [];
		banners = await getBanners(localStorage.token);
	});

	const updateBanners = async () => {
		_banners.set(await setBanners(localStorage.token, banners));
	};

	let workshopModels = null;
	let baseModels = null;

	let models = null;

	const init = async () => {
		workshopModels = await getBaseModels(localStorage.token);
		baseModels = await getModels(localStorage.token, null, false);

		models = baseModels.map((m) => {
			const workshopModel = workshopModels.find((wm) => wm.id === m.id);

			if (workshopModel) {
				return {
					...m,
					...workshopModel
				};
			} else {
				return {
					...m,
					id: m.id,
					name: m.name,

					is_active: true
				};
			}
		});

		console.debug('models', models);
	};
</script>

{#if models !== null && taskConfig}
	<form
		style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.875rem"
		on:submit|preventDefault={() => {
			updateInterfaceHandler();
			dispatch('save');
		}}
	>
		<div style="--ofy:scroll; --h:100%; --pr:0.375rem"
	class="scrollbar-hidden">
			<div style="--mb:0.875rem">
				<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Tasks')}</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

				<div style="--mb:0.5rem; --weight:500; --d:flex; --ai:center">
					<div style="--size:0.6rem; --mr:0.25rem">{$i18n.t('Task Model')}</div>
					<Tooltip
						content={$i18n.t(
							'A task model is used when performing tasks such as generating titles for chats and web search queries'
						)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							style="--w:0.875rem; --h:0.875rem"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
							/>
						</svg>
					</Tooltip>
				</div>

				<div style="--mb:0.625rem; --d:flex; --w:100%; --g:0.5rem">
					<div style="--fx:1 1 0%">
						<div style="--size:0.6rem; --mb:0.25rem">{$i18n.t('Local Task Model')}</div>
						<select
							style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
							bind:value={taskConfig.TASK_MODEL}
							placeholder={$i18n.t('Select a model')}
							on:change={() => {
								if (taskConfig.TASK_MODEL) {
									const model = models.find((m) => m.id === taskConfig.TASK_MODEL);
									if (model) {
										if (model?.access_control !== null) {
											toast.error(
												$i18n.t(
													'This model is not publicly available. Please select another model.'
												)
											);
										}

										taskConfig.TASK_MODEL = model.id;
									} else {
										taskConfig.TASK_MODEL = '';
									}
								}
							}}
						>
							<option value="" selected>{$i18n.t('Current Model')}</option>
							{#each models as model}
								<option value={model.id} style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)">
									{model.name}
									{model?.connection_type === 'local' ? `(${$i18n.t('Local')})` : ''}
								</option>
							{/each}
						</select>
					</div>

					<div style="--fx:1 1 0%">
						<div style="--size:0.6rem; --mb:0.25rem">{$i18n.t('External Task Model')}</div>
						<select
							style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
							bind:value={taskConfig.TASK_MODEL_EXTERNAL}
							placeholder={$i18n.t('Select a model')}
							on:change={() => {
								if (taskConfig.TASK_MODEL_EXTERNAL) {
									const model = models.find((m) => m.id === taskConfig.TASK_MODEL_EXTERNAL);
									if (model) {
										if (model?.access_control !== null) {
											toast.error(
												$i18n.t(
													'This model is not publicly available. Please select another model.'
												)
											);
										}

										taskConfig.TASK_MODEL_EXTERNAL = model.id;
									} else {
										taskConfig.TASK_MODEL_EXTERNAL = '';
									}
								}
							}}
						>
							<option value="" selected>{$i18n.t('Current Model')}</option>
							{#each models as model}
								<option value={model.id} style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)">
									{model.name}
									{model?.connection_type === 'local' ? `(${$i18n.t('Local')})` : ''}
								</option>
							{/each}
						</select>
					</div>
				</div>

				<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">
						{$i18n.t('Title Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_TITLE_GENERATION} />
				</div>

				{#if taskConfig.ENABLE_TITLE_GENERATION}
					<div style="--mb:0.625rem">
						<div style="--mb:0.25rem; --size:0.6rem; --weight:500">{$i18n.t('Title Generation Prompt')}</div>

						<Tooltip
							content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
							placement="top-start"
						>
							<Textarea
								bind:value={taskConfig.TITLE_GENERATION_PROMPT_TEMPLATE}
								placeholder={$i18n.t(
									'Leave empty to use the default prompt, or enter a custom prompt'
								)}
							/>
						</Tooltip>
					</div>
				{/if}

				<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">
						{$i18n.t('Follow Up Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_FOLLOW_UP_GENERATION} />
				</div>

				{#if taskConfig.ENABLE_FOLLOW_UP_GENERATION}
					<div style="--mb:0.625rem">
						<div style="--mb:0.25rem; --size:0.6rem; --weight:500">{$i18n.t('Follow Up Generation Prompt')}</div>

						<Tooltip
							content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
							placement="top-start"
						>
							<Textarea
								bind:value={taskConfig.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE}
								placeholder={$i18n.t(
									'Leave empty to use the default prompt, or enter a custom prompt'
								)}
							/>
						</Tooltip>
					</div>
				{/if}

				<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">
						{$i18n.t('Tags Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_TAGS_GENERATION} />
				</div>

				{#if taskConfig.ENABLE_TAGS_GENERATION}
					<div style="--mb:0.625rem">
						<div style="--mb:0.25rem; --size:0.6rem; --weight:500">{$i18n.t('Tags Generation Prompt')}</div>

						<Tooltip
							content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
							placement="top-start"
						>
							<Textarea
								bind:value={taskConfig.TAGS_GENERATION_PROMPT_TEMPLATE}
								placeholder={$i18n.t(
									'Leave empty to use the default prompt, or enter a custom prompt'
								)}
							/>
						</Tooltip>
					</div>
				{/if}

				<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">
						{$i18n.t('Retrieval Query Generation')}
					</div>

					<Switch bind:state={taskConfig.ENABLE_RETRIEVAL_QUERY_GENERATION} />
				</div>

				<div style="--mb:0.625rem">
					<div style="--mb:0.25rem; --size:0.6rem; --weight:500">{$i18n.t('Query Generation Prompt')}</div>

					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
					>
						<Textarea
							bind:value={taskConfig.QUERY_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>

				<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">
						{$i18n.t('Autocomplete Generation')}
					</div>

					<Tooltip content={$i18n.t('Enable autocomplete generation for chat messages')}>
						<Switch bind:state={taskConfig.ENABLE_AUTOCOMPLETE_GENERATION} />
					</Tooltip>
				</div>

				{#if taskConfig.ENABLE_AUTOCOMPLETE_GENERATION}
					<div style="--mb:0.625rem">
						<div style="--mb:0.25rem; --size:0.6rem; --weight:500">
							{$i18n.t('Autocomplete Generation Input Max Length')}
						</div>

						<Tooltip
							content={$i18n.t('Character limit for autocomplete generation input')}
							placement="top-start"
						>
							<input
								style="--w:100%; --oe:none; --bgc:transparent"
								bind:value={taskConfig.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH}
								placeholder={$i18n.t('-1 for no limit, or a positive integer for a specific limit')}
							/>
						</Tooltip>
					</div>
				{/if}

				<div style="--mb:0.625rem">
					<div style="--mb:0.25rem; --size:0.6rem; --weight:500">{$i18n.t('Image Prompt Generation Prompt')}</div>

					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
					>
						<Textarea
							bind:value={taskConfig.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>

				<div style="--mb:0.625rem">
					<div style="--mb:0.25rem; --size:0.6rem; --weight:500">{$i18n.t('Tools Function Calling Prompt')}</div>

					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
					>
						<Textarea
							bind:value={taskConfig.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>
			</div>

			<div style="--mb:0.875rem">
				<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('UI')}</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

				<div style="--mb:0.625rem">
					<div style="--d:flex; --w:100%; --jc:space-between">
						<div style="--as:center; --size:0.6rem">
							{$i18n.t('Banners')}
						</div>

						<button
							style="--p:0.25rem; --px:0.6rem; --size:0.6rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							type="button"
							on:click={() => {
								if (banners.length === 0 || banners.at(-1).content !== '') {
									banners = [
										...banners,
										{
											id: uuidv4(),
											type: '',
											title: '',
											content: '',
											dismissible: true,
											timestamp: Math.floor(Date.now() / 1000)
										}
									];
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
									d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
								/>
							</svg>
						</button>
					</div>

					<Banners bind:banners />
				</div>

				{#if $user?.role === 'admin'}
					<div style="--g:0.6rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.5rem">
							<div style="--as:center; --size:0.6rem">
								{$i18n.t('Default Prompt Suggestions')}
							</div>

							<button
								style="--p:0.25rem; --px:0.6rem; --size:0.6rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								type="button"
								on:click={() => {
									if (promptSuggestions.length === 0 || promptSuggestions.at(-1).content !== '') {
										promptSuggestions = [...promptSuggestions, { content: '', title: ['', ''] }];
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
										d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
									/>
								</svg>
							</button>
						</div>
						<div style="--d:grid; --gtc-lg:repeat(2, minmax(0, 1fr)); --fd:column; --g:0.375rem">
							{#each promptSuggestions as prompt, promptIdx}
								<div
									style="--d:flex;  --bc:var(--color-gray-100); --dark-bs:none; --dark-bgc:var(--color-gray-850); --radius:0.6rem; --py:0.375rem"
								>
									<div style="--d:flex; --fd:column; --fx:1 1 0%; --pl:0.25rem">
										<div style="--d:flex;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --w:100%">
											<input
												style="--px:0.6rem; --py:0.375rem; --size:0.6rem; --w:100%; --bgc:transparent; --oe:none; --br:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
												placeholder={$i18n.t('Title (e.g. Tell me a fun fact)')}
												bind:value={prompt.title[0]}
											/>

											<input
												style="--px:0.6rem; --py:0.375rem; --size:0.6rem; --w:100%; --bgc:transparent; --oe:none; --br:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
												placeholder={$i18n.t('Subtitle (e.g. about the Roman Empire)')}
												bind:value={prompt.title[1]}
											/>
										</div>

										<textarea
											style="--px:0.6rem; --py:0.375rem; --size:0.6rem; --w:100%; --bgc:transparent; --oe:none; --br:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); resize:none"
											placeholder={$i18n.t(
												'Prompt (e.g. Tell me a fun fact about the Roman Empire)'
											)}
											rows="3"
											bind:value={prompt.content}
										/>
									</div>

									<button
										style="--px:0.6rem"
										type="button"
										on:click={() => {
											promptSuggestions.splice(promptIdx, 1);
											promptSuggestions = promptSuggestions;
										}}
									>
										×
									</button>
								</div>
							{/each}
						</div>

						{#if promptSuggestions.length > 0}
							<div style="--size:0.6rem; --ta:left; --w:100%; --mt:0.5rem">
								{$i18n.t('Adjusting these settings will apply changes universally to all users.')}
							</div>
						{/if}

						<div style="--d:flex; --ai:center; --jc:flex-end; --g:0.5rem; --mt:0.5rem">
							<input
								id="prompt-suggestions-import-input"
								type="file"
								accept=".json"
								hidden
								on:change={(e) => {
									const files = e.target.files;
									if (!files || files.length === 0) {
										return;
									}

									console.log(files);

									let reader = new FileReader();
									reader.onload = async (event) => {
										try {
											let suggestions = JSON.parse(event.target.result);

											suggestions = suggestions.map((s) => {
												if (typeof s.title === 'string') {
													s.title = [s.title, ''];
												} else if (!Array.isArray(s.title)) {
													s.title = ['', ''];
												}

												return s;
											});

											promptSuggestions = [...promptSuggestions, ...suggestions];
										} catch (error) {
											toast.error($i18n.t('Invalid JSON file'));
											return;
										}
									};

									reader.readAsText(files[0]);

									e.target.value = ''; // Reset the input value
								}}
							/>

							<button
								style="--d:flex; --size:0.6rem; --ai:center; --g:0.25rem; --px:0.6rem; --py:0.375rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								type="button"
								on:click={() => {
									const input = document.getElementById('prompt-suggestions-import-input');
									if (input) {
										input.click();
									}
								}}
							>
								<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
									{$i18n.t('Import Prompt Suggestions')}
								</div>

								<div style="--as:center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										style="--w:0.875rem; --h:0.875rem"
									>
										<path
											fill-rule="evenodd"
											d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
							</button>

							{#if promptSuggestions.length}
								<button
									style="--d:flex; --size:0.6rem; --ai:center; --g:0.25rem; --px:0.6rem; --py:0.375rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									type="button"
									on:click={async () => {
										let blob = new Blob([JSON.stringify(promptSuggestions)], {
											type: 'application/json'
										});
										saveAs(blob, `prompt-suggestions-export-${Date.now()}.json`);
									}}
								>
									<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
										{$i18n.t('Export Prompt Suggestions')} ({promptSuggestions.length})
									</div>

									<div style="--as:center">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											style="--w:0.875rem; --h:0.875rem"
										>
											<path
												fill-rule="evenodd"
												d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<div style="--d:flex; --jc:flex-end; --size:0.875rem; --weight:500">
			<button
				style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
				type="submit"
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</form>
{:else}
	<div style="--h:100%; --w:100%; --d:flex; --jc:center; --ai:center">
		<Spinner className="size-5" />
	</div>
{/if}
