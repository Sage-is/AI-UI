<script lang="ts">
	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { models, tools, functions, knowledge as knowledgeCollections, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding, type Branding } from '$lib/apis/configs';

	const dispatch = createEventDispatcher();

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workshop/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workshop/Models/ToolsSelector.svelte';
	import FiltersSelector from '$lib/components/workshop/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workshop/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workshop/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import { getTools } from '$lib/apis/tools';
	import { getFunctions } from '$lib/apis/functions';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import AccessControl from '../common/AccessControl.svelte';
	import { stringify } from 'postcss';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { getNoteList } from '$lib/apis/notes';

	const i18n = getContext('i18n');

	export let onSubmit: Function;
	export let onBack: null | Function = null;

	export let model = null;
	export let edit = false;

	export let preset = true;

	let loading = false;
	let success = false;

	let filesInputElement;
	let inputFiles;

	let showAdvanced = false;
	let showPreview = false;

	let loaded = false;

	let branding: Branding | null = null;

	// ///////////
	// model
	// ///////////

	let id = '';
	let name = '';

	let enableDescription = true;

	$: if (!edit) {
		if (name) {
			id = name
				.replace(/\s+/g, '-')
				.replace(/[^a-zA-Z0-9-]/g, '')
				.toLowerCase();
		}
	}

	let system = '';
	let info = {
		id: '',
		base_model_id: null,
		name: '',
		meta: {
			profile_image_url: `${WEBUI_BASE_URL}/static/icons/favicon.png`,
			description: '',
			suggestion_prompts: null,
			tags: []
		},
		params: {
			system: ''
		}
	};

	let params = {
		system: ''
	};
	let capabilities = {
		vision: true,
		file_upload: true,

		image_generation: true,
		code_interpreter: true,
		citations: true,
		usage: undefined
	};

	let knowledge = [];
	let toolIds = [];
	let filterIds = [];
	let actionIds = [];

	let accessControl = {};

	// Dispatch model data changes for real-time testing
	$: if (loaded && name && id) {
		const currentModelData = {
			id: id,
			name: name,
			base_model_id: info.base_model_id,
			meta: {
				...info.meta,
				description: enableDescription ? info.meta.description : null,
				tags: info.meta.tags || [],
				capabilities: capabilities,
				knowledge: knowledge.length > 0 ? knowledge : undefined,
				toolIds: toolIds.length > 0 ? toolIds : undefined,
				filterIds: filterIds.length > 0 ? filterIds : undefined,
				actionIds: actionIds.length > 0 ? actionIds : undefined
			},
			params: {
				...params,
				system: system.trim() === '' ? null : system
			},
			access_control: accessControl
		};
		dispatch('dataChange', currentModelData);
	}

	const addUsage = (base_model_id) => {
		const baseModel = $models.find((m) => m.id === base_model_id);

		if (baseModel) {
			if (baseModel.owned_by === 'openai') {
				capabilities.usage = baseModel?.meta?.capabilities?.usage ?? false;
			} else {
				delete capabilities.usage;
			}
			capabilities = capabilities;
		}
	};

	const submitHandler = async () => {
		loading = true;

		info.id = id;
		info.name = name;

		if (id === '') {
			toast.error('Model ID is required.');
		}

		if (name === '') {
			toast.error('Model Name is required.');
		}

		info.params = { ...info.params, ...params };

		info.access_control = accessControl;
		info.meta.capabilities = capabilities;

		if (enableDescription) {
			info.meta.description = info.meta.description.trim() === '' ? null : info.meta.description;
		} else {
			info.meta.description = null;
		}

		if (knowledge.length > 0) {
			info.meta.knowledge = knowledge;
		} else {
			if (info.meta.knowledge) {
				delete info.meta.knowledge;
			}
		}

		if (toolIds.length > 0) {
			info.meta.toolIds = toolIds;
		} else {
			if (info.meta.toolIds) {
				delete info.meta.toolIds;
			}
		}

		if (filterIds.length > 0) {
			info.meta.filterIds = filterIds;
		} else {
			if (info.meta.filterIds) {
				delete info.meta.filterIds;
			}
		}

		if (actionIds.length > 0) {
			info.meta.actionIds = actionIds;
		} else {
			if (info.meta.actionIds) {
				delete info.meta.actionIds;
			}
		}

		info.params.system = system.trim() === '' ? null : system;
		info.params.stop = params.stop ? params.stop.split(',').filter((s) => s.trim()) : null;
		Object.keys(info.params).forEach((key) => {
			if (info.params[key] === '' || info.params[key] === null) {
				delete info.params[key];
			}
		});

		await onSubmit(info);

		loading = false;
		success = false;
	};

	onMount(async () => {
		await tools.set(await getTools(localStorage.token));
		await functions.set(await getFunctions(localStorage.token));
		await knowledgeCollections.set([...(await getKnowledgeBases(localStorage.token))]);

		// Fetch branding for fallback logo
		try {
			branding = await getBranding();
		} catch (e) {
			console.error('Failed to load branding:', e);
		}

		// Scroll to top 'workshop-container' element
		const workshopContainer = document.getElementById('workshop-container');
		if (workshopContainer) {
			workshopContainer.scrollTop = 0;
		}

		if (model) {
			name = model.name;
			await tick();

			id = model.id;

			enableDescription = model?.meta?.description !== null;

			if (model.base_model_id) {
				const base_model = $models
					.filter((m) => !m?.preset && !(m?.arena ?? false))
					.find((m) => [model.base_model_id, `${model.base_model_id}:latest`].includes(m.id));

				console.log('base_model', base_model);

				if (base_model) {
					model.base_model_id = base_model.id;
				} else {
					model.base_model_id = null;
				}
			}

			system = model?.params?.system ?? '';

			params = { ...params, ...model?.params };
			params.stop = params?.stop
				? (typeof params.stop === 'string' ? params.stop.split(',') : (params?.stop ?? [])).join(
						','
					)
				: null;

			toolIds = model?.meta?.toolIds ?? [];
			filterIds = model?.meta?.filterIds ?? [];
			actionIds = model?.meta?.actionIds ?? [];
			knowledge = (model?.meta?.knowledge ?? []).map((item) => {
				if (item?.collection_name && item?.type !== 'file') {
					return {
						id: item.collection_name,
						name: item.name,
						legacy: true
					};
				} else if (item?.collection_names) {
					return {
						name: item.name,
						type: 'collection',
						collection_names: item.collection_names,
						legacy: true
					};
				} else {
					return item;
				}
			});
			capabilities = { ...capabilities, ...(model?.meta?.capabilities ?? {}) };

			if ('access_control' in model) {
				accessControl = model.access_control;
			} else {
				accessControl = {};
			}

			console.log(model?.access_control);
			console.log(accessControl);

			info = {
				...info,
				...JSON.parse(
					JSON.stringify(
						model
							? model
							: {
									id: model.id,
									name: model.name
								}
					)
				)
			};

			console.log(model);
		}

		loaded = true;
	});
</script>

{#if loaded}
	{#if onBack}
		<button
			style="--d:flex; --g:0.25rem"
			on:click={() => {
				onBack();
			}}
		>
			<div style="--as:center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					style="--h:1rem; --w:1rem"
				>
					<path
						fill-rule="evenodd"
						d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div style="--as:center; --size:0.875rem; --weight:500">{'Back'}</div>
		</button>
	{/if}

	<div style="--w:100%; --maxh:100%; --d:flex; --jc:center">
		<input
			bind:this={filesInputElement}
			bind:files={inputFiles}
			type="file"
			hidden
			accept="image/*"
			on:change={() => {
				let reader = new FileReader();
				reader.onload = (event) => {
					let originalImageUrl = `${event.target.result}`;

					const img = new Image();
					img.src = originalImageUrl;

					img.onload = function () {
						const canvas = document.createElement('canvas');
						const ctx = canvas.getContext('2d');

						// Calculate the aspect ratio of the image
						const aspectRatio = img.width / img.height;

						// Calculate the new width and height to fit within 100x100
						let newWidth, newHeight;
						if (aspectRatio > 1) {
							newWidth = 250 * aspectRatio;
							newHeight = 250;
						} else {
							newWidth = 250;
							newHeight = 250 / aspectRatio;
						}

						// Set the canvas size
						canvas.width = 250;
						canvas.height = 250;

						// Calculate the position to center the image
						const offsetX = (250 - newWidth) / 2;
						const offsetY = (250 - newHeight) / 2;

						// Draw the image on the canvas
						ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

						// Get the base64 representation of the compressed image
						const compressedSrc = canvas.toDataURL();

						// Display the compressed image
						info.meta.profile_image_url = compressedSrc;

						inputFiles = null;
						filesInputElement.value = '';
					};
				};

				if (
					inputFiles &&
					inputFiles.length > 0 &&
					['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/svg+xml'].includes(
						inputFiles[0]['type']
					)
				) {
					reader.readAsDataURL(inputFiles[0]);
				} else {
					console.log(`Unsupported File Type '${inputFiles[0]['type']}'.`);
					inputFiles = null;
				}
			}}
		/>

		{#if !edit || (edit && model)}
			<form
				style="--d:flex; --fd:column; --fd-md:row; --w:100%; --g:0.75rem; --g-md:1.5rem"
				on:submit|preventDefault={() => {
					submitHandler();
				}}
			>


				<div style="--w:100%">
					<div style="--mt:0.5rem; --my:0.5rem; --d:flex; --fd:column">
						<div style="--fx:1 1 0%">
							<div>
								<input
									style="--size:1.875rem; --weight:600; --w:100%; --bgc:transparent; --oe:none"
									placeholder={$i18n.t('Model Name')}
									bind:value={name}
									required
								/>
							</div>

											<div style="--ml:auto;">
					<div style="--as:center">
						<button
							style="--radius:0.75rem; --d:flex; --fs:0; --ai:center; --shadow:5; --pos:relative"
	class="{info.meta.profile_image_url !==
							`${WEBUI_BASE_URL}/static/icons/favicon.png`
								? 'bg-transparent'
								: 'bg-white'} group"
							type="button"
							on:click={() => {
								filesInputElement.click();
							}}
						>
							{#if info.meta.profile_image_url}
								<img
									src={info.meta.profile_image_url}
									alt="model profile"
									style="--radius:0.75rem; --w:18rem; --h:18rem; --w-md:15rem; --h-md:15rem; --objf:cover; --fs:0"
								/>
							{:else}
								<img
									src={branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
									alt="model profile"
									style="--radius:0.75rem; --w:18rem; --h:18rem; --w-md:15rem; --h-md:15rem; --objf:cover; --fs:0"
								/>
							{/if}

							<div style="--pos:absolute; --bottom:0; --right:0; --z:10">
								<div style="--m:0.375rem">
									<div
										style="--shadow:5; --p:0.25rem; --radius:9999px; --bw:2px; --bc:#fff; --bgc:var(--color-gray-800, #333); --c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --dark-bc:#000; --dark-bgc:#fff; --dark-c:#000"
	class="group-hover:bg-gray-600 dark:group-hover:bg-gray-200"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											style="--w:1.25rem; --h:1.25rem"
										>
											<path
												fill-rule="evenodd"
												d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
								</div>
							</div>

							<div
								style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --bgc:#fff; --dark-bgc:#000; --radius:0.5rem; --op:0; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover:opacity-20"
							></div>
						</button>

						<div style="--d:flex; --w:100%; --mt:0.25rem; --jc:flex-end">
							<button
								style="--px:0.5rem; --py:0.25rem; --c:var(--color-gray-500, #9b9b9b); --radius:0.5rem; --size:0.75rem"
								on:click={() => {
									info.meta.profile_image_url = `${WEBUI_BASE_URL}/static/icons/favicon.png`;
								}}
								type="button"
							>
								Reset Image</button
							>
						</div>
					</div>
				</div>
						</div>

						<div style="--fx:1 1 0%">
							<div>
								<input
									style="--size:0.75rem; --w:100%; --bgc:transparent; --c:var(--color-gray-500, #9b9b9b); --oe:none"
									placeholder={$i18n.t('Model ID')}
									bind:value={id}
									disabled={edit}
									required
								/>
							</div>
						</div>
					</div>

					{#if preset}
						<div style="--my:0.25rem">
							<div style="--size:0.875rem; --weight:600; --mb:0.25rem">{$i18n.t('Base Model (From)')}</div>

							<div>
								<select
									style="--size:0.875rem; --w:100%; --bgc:transparent; --oe:none"
									placeholder="Select a base model (e.g. llama3, gpt-4o)"
									bind:value={info.base_model_id}
									on:change={(e) => {
										addUsage(e.target.value);
									}}
									required
								>
									<option value={null} style="--c:var(--color-gray-900, #171717)"
										>{$i18n.t('Select a base model')}</option
									>
									{#each $models.filter((m) => (model ? m.id !== model.id : true) && !m?.preset && m?.owned_by !== 'arena') as model}
										<option value={model.id} style="--c:var(--color-gray-900, #171717)">{model.name}</option>
									{/each}
								</select>
							</div>
						</div>
					{/if}

					<div style="--my:0.25rem">
						<div style="--mb:0.25rem; --d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--as:center; --size:0.875rem; --weight:600">{$i18n.t('Description')}</div>

							<button
								style="--p:0.25rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								type="button"
								aria-pressed={enableDescription ? 'true' : 'false'}
								aria-label={enableDescription
									? $i18n.t('Custom description enabled')
									: $i18n.t('Default description enabled')}
								on:click={() => {
									enableDescription = !enableDescription;
								}}
							>
								{#if !enableDescription}
									<span style="--ml:0.5rem; --as:center">{$i18n.t('Default')}</span>
								{:else}
									<span style="--ml:0.5rem; --as:center">{$i18n.t('Custom')}</span>
								{/if}
							</button>
						</div>

						{#if enableDescription}
							<Textarea
								className=" text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden "
								placeholder={$i18n.t('Add a short description about what this model does')}
								bind:value={info.meta.description}
							/>
						{/if}
					</div>

					<div style="--mt:0.5rem; --my:0.25rem">
						<div class="">
							<Tags
								tags={info?.meta?.tags ?? []}
								on:delete={(e) => {
									const tagName = e.detail;
									info.meta.tags = info.meta.tags.filter((tag) => tag.name !== tagName);
								}}
								on:add={(e) => {
									const tagName = e.detail;
									if (!(info?.meta?.tags ?? null)) {
										info.meta.tags = [{ name: tagName }];
									} else {
										info.meta.tags = [...info.meta.tags, { name: tagName }];
									}
								}}
							/>
						</div>
					</div>

					<div style="--my:0.5rem">
						<div style="--px:0.75rem; --py:0.5rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-950, #0d0d0d); --radius:0.5rem">
							<AccessControl
								bind:accessControl
								accessRoles={['read', 'write']}
								allowPublic={$user?.permissions?.sharing?.public_models || $user?.role === 'admin'}
							/>
						</div>
					</div>

					<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626); --my:0.375rem" />

					<div style="--my:0.5rem">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.875rem; --weight:600">{$i18n.t('Model Params')}</div>
						</div>

						<div style="--mt:0.5rem">
							<div style="--my:0.25rem">
								<div style="--size:0.75rem; --weight:600; --mb:0.5rem">{$i18n.t('System Prompt')}</div>
								<div>
									<Textarea
										className=" text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden "
										placeholder={`Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.`}
										rows={4}
										bind:value={system}
									/>
								</div>
							</div>

							<div style="--d:flex; --w:100%; --jc:space-between">
								<div style="--as:center; --size:0.75rem; --weight:600">
									{$i18n.t('Advanced Params')}
								</div>

								<button
									style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									type="button"
									on:click={() => {
										showAdvanced = !showAdvanced;
									}}
								>
									{#if showAdvanced}
										<span style="--ml:0.5rem; --as:center">{$i18n.t('Hide')}</span>
									{:else}
										<span style="--ml:0.5rem; --as:center">{$i18n.t('Show')}</span>
									{/if}
								</button>
							</div>

							{#if showAdvanced}
								<div style="--my:0.5rem">
									<AdvancedParams admin={true} custom={true} bind:params />
								</div>
							{/if}
						</div>
					</div>

					<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626); --my:0.25rem" />

					<div style="--my:0.5rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
								<div style="--as:center; --size:0.875rem; --weight:600">
									{$i18n.t('Prompt suggestions')}
								</div>

								<button
									style="--p:0.25rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									type="button"
									on:click={() => {
										if ((info?.meta?.suggestion_prompts ?? null) === null) {
											info.meta.suggestion_prompts = [{ content: '' }];
										} else {
											info.meta.suggestion_prompts = null;
										}
									}}
								>
									{#if (info?.meta?.suggestion_prompts ?? null) === null}
										<span style="--ml:0.5rem; --as:center">{$i18n.t('Default')}</span>
									{:else}
										<span style="--ml:0.5rem; --as:center">{$i18n.t('Custom')}</span>
									{/if}
								</button>
							</div>

							{#if (info?.meta?.suggestion_prompts ?? null) !== null}
								<button
									style="--p:0.25rem; --px:0.5rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									type="button"
									on:click={() => {
										if (
											info.meta.suggestion_prompts.length === 0 ||
											info.meta.suggestion_prompts.at(-1).content !== ''
										) {
											info.meta.suggestion_prompts = [
												...info.meta.suggestion_prompts,
												{ content: '' }
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
							{/if}
						</div>

						{#if info?.meta?.suggestion_prompts}
							<div style="--d:flex; --fd:column; --g:0.25rem; --mt:0.25rem; --mb:0.75rem">
								{#if info.meta.suggestion_prompts.length > 0}
									{#each info.meta.suggestion_prompts as prompt, promptIdx}
										<div style="--d:flex; --radius:0.5rem">
											<input
												style="--size:0.875rem; --w:100%; --bgc:transparent; --oe:none; --br:1px solid; --bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626)"
												placeholder={$i18n.t('Write a prompt suggestion (e.g. Who are you?)')}
												bind:value={prompt.content}
											/>

											<button
												style="--px:0.5rem"
												type="button"
												on:click={() => {
													info.meta.suggestion_prompts.splice(promptIdx, 1);
													info.meta.suggestion_prompts = info.meta.suggestion_prompts;
												}}
											>
												<XMark className={'size-4'} />
											</button>
										</div>
									{/each}
								{:else}
									<div style="--size:0.75rem; --ta:center">No suggestion prompts</div>
								{/if}
							</div>
						{/if}
					</div>

					<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626); --my:0.375rem" />

					<div style="--my:0.5rem">
						<Knowledge bind:selectedItems={knowledge} />
					</div>

					<div style="--my:0.5rem">
						<ToolsSelector bind:selectedToolIds={toolIds} tools={$tools} />
					</div>

					<div style="--my:0.5rem">
						<FiltersSelector
							bind:selectedFilterIds={filterIds}
							filters={$functions.filter((func) => func.type === 'filter')}
						/>
					</div>

					<div style="--my:0.5rem">
						<ActionsSelector
							bind:selectedActionIds={actionIds}
							actions={$functions.filter((func) => func.type === 'action')}
						/>
					</div>

					<div style="--my:0.5rem">
						<Capabilities bind:capabilities />
					</div>

					<div style="--my:0.5rem; --c:var(--color-gray-300, #cdcdcd); --dark-c:var(--color-gray-700, #4e4e4e)">
						<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.5rem">
							<div style="--as:center; --size:0.875rem; --weight:600">{$i18n.t('JSON Preview')}</div>

							<button
								style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								type="button"
								on:click={() => {
									showPreview = !showPreview;
								}}
							>
								{#if showPreview}
									<span style="--ml:0.5rem; --as:center">{$i18n.t('Hide')}</span>
								{:else}
									<span style="--ml:0.5rem; --as:center">{$i18n.t('Show')}</span>
								{/if}
							</button>
						</div>

						{#if showPreview}
							<div>
								<textarea
									style="--size:0.875rem; --w:100%; --bgc:transparent; --oe:none; resize:none"
									rows="10"
									value={JSON.stringify(info, null, 2)}
									disabled
									readonly
								/>
							</div>
						{/if}
					</div>

					<div style="--my:0.5rem; --d:flex; --fd:column; --g:0.75rem; --pb:5rem">
						<button
							style="--size:0.875rem; --px:0.75rem; --py:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --d:flex; --w:100%; --jc:center"
	class="{loading
								? ' cursor-not-allowed bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'
								: 'bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'}"
							type="submit"
							disabled={loading}
						>
							<div style="--as:center; --weight:500">
								{#if edit}
									{$i18n.t('Save & Update')}
								{:else}
									{$i18n.t('Save & Create')}
								{/if}
							</div>

							{#if loading}
								<div style="--ml:0.375rem; --as:center">
									<Spinner />
								</div>
							{/if}
						</button>

						<!-- Save and chat that saves and brings users to a new chat session -->
						<button
							style="--size:0.875rem; --px:1rem; --py:0.75rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --bw:2px; --d:flex; --w:100%; --jc:center; --ai:center; --g:0.5rem"
	class="{loading
								? 'cursor-not-allowed bg-blue-100 border-blue-300 text-blue-600 dark:bg-blue-900/20 dark:border-blue-700 dark:text-blue-400'
								: 'bg-blue-50 hover:bg-blue-100 border-blue-300 text-blue-700 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 dark:border-blue-700 dark:text-blue-300'}"
							type="button"
							on:click={async () => {
								// Save first, then navigate to chat
								await submitHandler();
								if (info?.id) {
									await goto(`/?models=${encodeURIComponent(info.id)}`);
								}
							}}
							disabled={loading}
						>
							<svg style="--w:1rem; --h:1rem" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
								></path>
							</svg>
							<div style="--as:center; --weight:500">
								{#if edit}
									{$i18n.t('Save & Chat')}
								{:else}
									{$i18n.t('Create & Chat')}
								{/if}
							</div>
						</button>
					</div>
				</div>
			</form>
		{/if}
	</div>
{/if}
