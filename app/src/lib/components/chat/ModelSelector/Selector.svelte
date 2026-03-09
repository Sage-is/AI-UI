<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { marked } from 'marked';
	import Fuse from 'fuse.js';

	import dayjs from '$lib/dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import Spinner from '$lib/components/common/Spinner.svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { deleteModel, getOllamaVersion, pullModel, unloadModel } from '$lib/apis/ollama';

	import {
		user,
		MODEL_DOWNLOAD_POOL,
		models,
		mobile,
		settings,
		config
	} from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { capitalizeFirstLetter, sanitizeResponseContent, splitStream } from '$lib/utils';
	import { getModels } from '$lib/apis';
	import { getBranding, type Branding } from '$lib/apis/configs';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import ModelItem from './ModelItem.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let id = '';
	export let value = '';
	export let placeholder = 'Select a model';
	export let searchEnabled = true;
	export let searchPlaceholder = $i18n.t('Search for an agent or model');

	export let items: {
		label: string;
		value: string;
		model: Model;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		[key: string]: any;
	}[] = [];

	export let className = 'w-[32rem]';
	export let triggerClassName = 'text-lg';

	export let pinModelHandler: (modelId: string) => void = () => {};

	let branding: Branding | null = null;

	let tagsContainerElement;

	let show = false;
	let tags = [];

	let selectedModel = '';
	$: selectedModel = items.find((item) => item.value === value) ?? '';

	let searchValue = '';

	let selectedTag = '';
	let selectedConnectionType = $config?.default_model_selector_filter ?? 'agents';

	// If 'agents' is selected but no agents exist, fall back to 'All'
	$: if (selectedConnectionType === 'agents' && !items.find((item) => item.model?.preset)) {
		selectedConnectionType = '';
	}

	let ollamaVersion = null;
	let selectedModelIdx = 0;

	const fuse = new Fuse(
		items.map((item) => {
			const _item = {
				...item,
				modelName: item.model?.name,
				tags: (item.model?.tags ?? []).map((tag) => tag.name).join(' '),
				desc: item.model?.info?.meta?.description
			};
			return _item;
		}),
		{
			keys: ['value', 'tags', 'modelName'],
			threshold: 0.4
		}
	);

	$: filteredItems = (
		searchValue
			? fuse
					.search(searchValue)
					.map((e) => {
						return e.item;
					})
					.filter((item) => {
						if (selectedTag === '') {
							return true;
						}
						return (item.model?.tags ?? []).map((tag) => tag.name).includes(selectedTag);
					})
					.filter((item) => {
						if (selectedConnectionType === '') {
							return true;
						} else if (selectedConnectionType === 'agents') {
							return item.model?.preset === true;
						} else if (selectedConnectionType === 'local') {
							return item.model?.connection_type === 'local';
						} else if (selectedConnectionType === 'external') {
							return item.model?.connection_type === 'external';
						} else if (selectedConnectionType === 'direct') {
							return item.model?.direct;
						}
					})
			: items
					.filter((item) => {
						if (selectedTag === '') {
							return true;
						}
						return (item.model?.tags ?? []).map((tag) => tag.name).includes(selectedTag);
					})
					.filter((item) => {
						if (selectedConnectionType === '') {
							return true;
						} else if (selectedConnectionType === 'agents') {
							return item.model?.preset === true;
						} else if (selectedConnectionType === 'local') {
							return item.model?.connection_type === 'local';
						} else if (selectedConnectionType === 'external') {
							return item.model?.connection_type === 'external';
						} else if (selectedConnectionType === 'direct') {
							return item.model?.direct;
						}
					})
	).filter((item) => !(item.model?.info?.meta?.hidden ?? false));

	$: if (selectedTag || selectedConnectionType) {
		resetView();
	} else {
		resetView();
	}

	const resetView = async () => {
		await tick();

		const selectedInFiltered = filteredItems.findIndex((item) => item.value === value);

		if (selectedInFiltered >= 0) {
			// The selected model is visible in the current filter
			selectedModelIdx = selectedInFiltered;
		} else {
			// The selected model is not visible, default to first item in filtered list
			selectedModelIdx = 0;
		}

		await tick();
		const item = document.querySelector(`[data-arrow-selected="true"]`);
		item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
	};

	const pullModelHandler = async () => {
		const sanitizedModelTag = searchValue.trim().replace(/^ollama\s+(run|pull)\s+/, '');

		console.log($MODEL_DOWNLOAD_POOL);
		if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag]) {
			toast.error(
				$i18n.t(`Model '{{modelTag}}' is already in queue for downloading.`, {
					modelTag: sanitizedModelTag
				})
			);
			return;
		}
		if (Object.keys($MODEL_DOWNLOAD_POOL).length === 3) {
			toast.error(
				$i18n.t('Maximum of 3 models can be downloaded simultaneously. Please try again later.')
			);
			return;
		}

		const [res, controller] = await pullModel(localStorage.token, sanitizedModelTag, '0').catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL,
				[sanitizedModelTag]: {
					...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
					abortController: controller,
					reader,
					done: false
				}
			});

			while (true) {
				try {
					const { value, done } = await reader.read();
					if (done) break;

					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line);
							console.log(data);
							if (data.error) {
								throw data.error;
							}
							if (data.detail) {
								throw data.detail;
							}

							if (data.status) {
								if (data.digest) {
									let downloadProgress = 0;
									if (data.completed) {
										downloadProgress = Math.round((data.completed / data.total) * 1000) / 10;
									} else {
										downloadProgress = 100;
									}

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											pullProgress: downloadProgress,
											digest: data.digest
										}
									});
								} else {
									toast.success(data.status);

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											done: data.status === 'success'
										}
									});
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
					if (typeof error !== 'string') {
						error = error.message;
					}

					toast.error(`${error}`);
					// opts.callback({ success: false, error, modelName: opts.modelName });
					break;
				}
			}

			if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag].done) {
				toast.success(
					$i18n.t(`Model '{{modelName}}' has been successfully downloaded.`, {
						modelName: sanitizedModelTag
					})
				);

				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			} else {
				toast.error($i18n.t('Download canceled'));
			}

			delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
		}
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => false);

		// Fetch branding for fallback logo
		try {
			branding = await getBranding();
		} catch (e) {
			console.error('Failed to load branding:', e);
		}

		if (items) {
			tags = items
				.filter((item) => !(item.model?.info?.meta?.hidden ?? false))
				.flatMap((item) => item.model?.tags ?? [])
				.map((tag) => tag.name);

			// Remove duplicates and sort
			tags = Array.from(new Set(tags)).sort((a, b) => a.localeCompare(b));
		}
	});

	const cancelModelPullHandler = async (model: string) => {
		const { reader, abortController } = $MODEL_DOWNLOAD_POOL[model];
		if (abortController) {
			abortController.abort();
		}
		if (reader) {
			await reader.cancel();
			delete $MODEL_DOWNLOAD_POOL[model];
			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
			await deleteModel(localStorage.token, model);
			toast.success(`${model} download has been canceled`);
		}
	};

	const unloadModelHandler = async (model: string) => {
		const res = await unloadModel(localStorage.token, model).catch((error) => {
			toast.error($i18n.t('Error unloading model: {{error}}', { error }));
		});

		if (res) {
			toast.success($i18n.t('Model unloaded successfully'));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={async () => {
		searchValue = '';
		window.setTimeout(() => document.getElementById('model-search-input')?.focus(), 0);

		resetView();
	}}
	closeFocus={false}
>
	<DropdownMenu.Trigger
		style="--pos:relative; --w:100%"
		class="font-primary {($settings?.highContrastMode ?? false)
			? ''
			: 'outline-hidden focus:outline-hidden'}"
		aria-label={placeholder}
		id="model-selector-{id}-button"
	>
		<div
			style="--d:flex; --w:100%; --ta:left; --px:0.125rem; --bgc:transparent; overflow:hidden; text-overflow:ellipsis; --ws:nowrap; --jc:space-between"
			class="{triggerClassName} {($settings?.highContrastMode ?? false)
				? 'dark:placeholder-gray-100 placeholder-gray-800'
				: 'placeholder-gray-400'}"
			on:mouseenter={async () => {
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			}}
		>
			{#if selectedModel}
				{selectedModel.label}
			{:else}
				{placeholder}
			{/if}
			<ChevronDown className=" self-center ml-2 size-3" strokeWidth="2.5" />
		</div>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		style="--z:40; --maxw:calc(100vw-1rem); --jc:flex-start; --radius:0.75rem; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4; --oe:none"
		class={$mobile ? `w-full` : `${className}`}
		transition={flyAndScale}
		side={$mobile ? 'bottom' : 'bottom-start'}
		sideOffset={3}
	>
		<slot>
			{#if searchEnabled}
				<div
					style="--d:flex; --ai:center; --g:0.625rem; --px:1.25rem; --mt:0.875rem; --mb:0.375rem"
				>
					<Search className="size-4" strokeWidth="2.5" />

					<input
						id="model-search-input"
						bind:value={searchValue}
						style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
						placeholder={searchPlaceholder}
						autocomplete="off"
						on:keydown={(e) => {
							if (e.code === 'Enter' && filteredItems.length > 0) {
								value = filteredItems[selectedModelIdx].value;
								show = false;
								return; // dont need to scroll on selection
							} else if (e.code === 'ArrowDown') {
								selectedModelIdx = Math.min(selectedModelIdx + 1, filteredItems.length - 1);
							} else if (e.code === 'ArrowUp') {
								selectedModelIdx = Math.max(selectedModelIdx - 1, 0);
							} else {
								// if the user types something, reset to the top selection.
								selectedModelIdx = 0;
							}

							const item = document.querySelector(`[data-arrow-selected="true"]`);
							item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
						}}
					/>
				</div>
			{/if}

			<div style="--px:0.75rem">
				{#if tags && items.filter((item) => !(item.model?.info?.meta?.hidden ?? false)).length > 0}
					<div
						style="--d:flex; --w:100%; --bgc:#fff; --dark-bgc:var(--color-gray-850); --ofx:auto"
						class="scrollbar-none"
						on:wheel={(e) => {
							if (e.deltaY !== 0) {
								e.preventDefault();
								e.currentTarget.scrollLeft += e.deltaY;
							}
						}}
					>
						<div
							style="--d:flex; --g:0.25rem; --w:fit-content; --ta:center; --size:0.875rem; --weight:500; --radius:9999px; --bgc:transparent; --p:0.2rem;"
							bind:this={tagsContainerElement}
						>
							{#if items.find((item) => item.model?.connection_type === 'local') || items.find((item) => item.model?.connection_type === 'external') || items.find((item) => item.model?.direct) || tags.length > 0}
								<button
									style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize; {selectedTag === '' && selectedConnectionType === '' ? '--weight:bold;' : ''}"
									class={selectedTag === '' && selectedConnectionType === ''
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
									on:click={() => {
										selectedConnectionType = '';
										selectedTag = '';
									}}
								>
									{$i18n.t('All')}
								</button>
							{/if}

							{#if items.find((item) => item.model?.preset)}
								<button
									style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize; {selectedConnectionType === 'agents' ? '--weight:bold;' : ''}"
									class={selectedConnectionType === 'agents'
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
									on:click={() => {
										selectedTag = '';
										selectedConnectionType = 'agents';
									}}
								>
									{$i18n.t('Agents')}
								</button>
							{/if}

							{#if items.find((item) => item.model?.connection_type === 'local')}
								<button
									style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize; {selectedConnectionType === 'local' ? '--weight:bold;' : ''}"
									class={selectedConnectionType === 'local'
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
									on:click={() => {
										selectedTag = '';
										selectedConnectionType = 'local';
									}}
								>
									{$i18n.t('Local')}
								</button>
							{/if}

							{#if items.find((item) => item.model?.connection_type === 'external')}
								<button
									style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize; {selectedConnectionType === 'external' ? '--weight:bold;' : ''}"
									class={selectedConnectionType === 'external'
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
									on:click={() => {
										selectedTag = '';
										selectedConnectionType = 'external';
									}}
								>
									{$i18n.t('External')}
								</button>
							{/if}

							{#if items.find((item) => item.model?.direct)}
								<button
									style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize; {selectedConnectionType === 'direct' ? '--weight:bold;' : ''}"
									class={selectedConnectionType === 'direct'
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
									on:click={() => {
										selectedTag = '';
										selectedConnectionType = 'direct';
									}}
								>
									{$i18n.t('Direct')}
								</button>
							{/if}

							{#each tags as tag}
								<button
									style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize; {selectedTag === tag ? '--weight:bold;' : ''}"
									class={selectedTag === tag
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
									on:click={() => {
										selectedConnectionType = '';
										selectedTag = tag;
									}}
								>
									{tag}
								</button>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<div style="--pos:relative; --ofy:auto; --maxh:16rem; --p:0 1em">
				{#each filteredItems as item, index}
					<ModelItem
						{selectedModelIdx}
						{item}
						{index}
						{value}
						{pinModelHandler}
						{unloadModelHandler}
						{branding}
						onClick={() => {
							value = item.value;
							selectedModelIdx = index;

							show = false;
						}}
					/>
				{:else}
					<div class="">
						<div
							style="--d:block; --px:0.75rem; --py:0.5rem; --size:0.875rem; --c:var(--color-gray-700); --dark-c:var(--color-gray-100)"
						>
							{$i18n.t('No results found')}
						</div>
					</div>
				{/each}

				{#if !(searchValue.trim() in $MODEL_DOWNLOAD_POOL) && searchValue && ollamaVersion && $user?.role === 'admin'}
					<Tooltip
						content={$i18n.t(`Pull "{{searchValue}}" from Ollama.com`, {
							searchValue: searchValue
						})}
						placement="top-start"
					>
						<button
							style="--d:flex; --w:100%; --weight:500; --line-clamp:1; --us:none; --ai:center; --radius:var(--button-border-radius, 0.5rem); --py:0.5rem; --pl:0.75rem; --pr:0.375rem; --size:0.875rem; --bg:var(--white); --br: 1rem; --shadow:6; --oe:none; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:75ms; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800); --radius:0.5rem; --cur:pointer"
							class="data-highlighted:bg-muted"
							on:click={() => {
								pullModelHandler();
							}}
						>
							<div style="overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
								{$i18n.t(`Pull "{{searchValue}}" from Ollama.com`, { searchValue: searchValue })}
							</div>
						</button>
					</Tooltip>
				{/if}

				{#each Object.keys($MODEL_DOWNLOAD_POOL) as model}
					<div
						style="--d:flex; --w:100%; --jc:space-between; --weight:500; --us:none; --radius:var(--button-border-radius, 0.5rem); --py:0.5rem; --pl:0.75rem; --pr:0.375rem; --size:0.875rem; --bg:var(--white); --br: 1rem; --shadow:6; --oe:none; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:75ms; --radius:0.5rem; --cur:pointer"
						class="data-highlighted:bg-muted"
					>
						<div style="--d:flex">
							<div style="--ml:-0.5rem; --mr:0.625rem; --translatey:0.125rem">
								<Spinner />
							</div>

							<div style="--d:flex; --fd:column; --as:flex-start">
								<div style="--d:flex; --g:0.25rem">
									<div style="--line-clamp:1">
										Downloading "{model}"
									</div>

									<div style="--fs:0">
										{'pullProgress' in $MODEL_DOWNLOAD_POOL[model]
											? `(${$MODEL_DOWNLOAD_POOL[model].pullProgress}%)`
											: ''}
									</div>
								</div>

								{#if 'digest' in $MODEL_DOWNLOAD_POOL[model] && $MODEL_DOWNLOAD_POOL[model].digest}
									<div
										style="--mt:-0.25rem; --h:fit-content; --size:0.7rem; --dark-c:var(--color-gray-500); --line-clamp:1"
									>
										{$MODEL_DOWNLOAD_POOL[model].digest}
									</div>
								{/if}
							</div>
						</div>

						<div style="--mr:0.5rem; --ml:0.25rem; --translatey:0.125rem">
							<Tooltip content={$i18n.t('Cancel')}>
								<button
									style="--c:var(--color-gray-800); --dark-c:var(--color-gray-100)"
									on:click={() => {
										cancelModelPullHandler(model);
									}}
								>
									<svg
										style="--w:1rem; --h:1rem; --c:var(--color-gray-800); --dark-c:#fff"
										aria-hidden="true"
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										fill="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke="currentColor"
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M6 18 17.94 6M18 18 6.06 6"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>

			<div style="--mb:0.75rem"></div>

			<div style="--d:none; --w:42rem" />
			<div style="--d:none; --w:32rem" />
		</slot>
	</DropdownMenu.Content>
</DropdownMenu.Root>
