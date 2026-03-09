<script lang="ts">
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';
	import Sortable from 'sortablejs';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding, type Branding } from '$lib/apis/configs';
	import {
		createNewModel,
		deleteModelById,
		getModels as getWorkshopModels,
		toggleModelById,
		updateModelById
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import { getGroups } from '$lib/apis/groups';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ModelMenu from './Models/ModelMenu.svelte';
	import ModelDeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Switch from '../common/Switch.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { capitalizeFirstLetter, copyToClipboard } from '$lib/utils';
	import XMark from '../icons/XMark.svelte';
	import EyeSlash from '../icons/EyeSlash.svelte';
	import Eye from '../icons/Eye.svelte';

	let shiftKey = false;

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;
	let tagsContainerElement: HTMLDivElement;

	let loaded = false;

	let models = [];
	let tags = [];

	let branding: Branding | null = null;
	let selectedTag = '';

	let filteredModels = [];
	let selectedModel = null;

	let showModelDeleteConfirm = false;

	let group_ids = [];

	$: if (models) {
		filteredModels = models.filter((m) => {
			if (query === '' && selectedTag === '') return true;
			const lowerQuery = query.toLowerCase();
			return (
				((m.name || '').toLowerCase().includes(lowerQuery) ||
					(m.user?.name || '').toLowerCase().includes(lowerQuery) || // Search by user name
					(m.user?.email || '').toLowerCase().includes(lowerQuery)) && // Search by user email
				(selectedTag === '' ||
					m?.meta?.tags?.some((tag) => tag.name.toLowerCase() === selectedTag.toLowerCase()))
			);
		});
	}

	let query = '';

	const deleteModelHandler = async (model) => {
		const res = await deleteModelById(localStorage.token, model.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: model.id }));
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
		models = await getWorkshopModels(localStorage.token);
	};

	const cloneModelHandler = async (model) => {
		sessionStorage.model = JSON.stringify({
			...model,
			id: `${model.id}-clone`,
			name: `${model.name} (Clone)`
		});
		goto('/workshop/models/create');
	};

	// Handler to share a model to the Sage.is Community
	const shareModelHandler = async (model) => {
		toast.success($i18n.t('Redirecting you to the Sage.is Community'));

		const url = 'https://webhook.site/93a1d2e8-5b27-44c4-8493-0f915cad92c5';

		// Check if the model has a large knowledge base
		const isLarge = model?.knowledge_base && model.knowledge_base.length > 10000;

		if (!isLarge) {
			// Send small models via URL query param
			const encoded = encodeURIComponent(JSON.stringify(model));
			window.open(`${url}/models/create?model=${encoded}`, '_blank');
		} else {
			// Use postMessage for large models
			const tab = await window.open(`${url}/models/create`, '_blank');
			const messageHandler = (event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(JSON.stringify(model), '*');
					window.removeEventListener('message', messageHandler);
				}
			};
			window.addEventListener('message', messageHandler, false);
		}
	};

	const hideModelHandler = async (model) => {
		model.meta = {
			...model.meta,
			hidden: !(model?.meta?.hidden ?? false)
		};

		console.log(model);

		const res = await updateModelById(localStorage.token, model.id, model);

		if (res) {
			toast.success(
				$i18n.t(`Model {{name}} is now {{status}}`, {
					name: model.id,
					status: model.meta.hidden ? 'hidden' : 'visible'
				})
			);
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
		models = await getWorkshopModels(localStorage.token);
	};

	const copyLinkHandler = async (model) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(model.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	const downloadModels = async (models) => {
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const exportModelHandler = async (model) => {
		let blob = new Blob([JSON.stringify([model])], {
			type: 'application/json'
		});
		saveAs(blob, `${model.id}-${Date.now()}.json`);
	};

	onMount(async () => {
		models = await getWorkshopModels(localStorage.token);
		let groups = await getGroups(localStorage.token);
		group_ids = groups.map((group) => group.id);

		// Fetch branding for fallback logo
		try {
			branding = await getBranding();
		} catch (e) {
			console.error('Failed to load branding:', e);
		}

		if (models) {
			tags = models
				.filter((model) => !(model?.meta?.hidden ?? false))
				.flatMap((model) => model?.meta?.tags ?? [])
				.map((tag) => tag.name);

			// Remove duplicates and sort
			tags = Array.from(new Set(tags)).sort((a, b) => a.localeCompare(b));
		}

		loaded = true;

		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur-sm', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur-sm', onBlur);
		};
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Agents')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<ModelDeleteConfirmDialog
		bind:show={showModelDeleteConfirm}
		on:confirm={() => {
			deleteModelHandler(selectedModel);
		}}
	/>

	<div style="--d:flex; --fd:column; --g:0.25rem; --mt:0.375rem">
		<div style="--d:flex; --jc:space-between; --ai:center">
			<div style="--d:flex; --ai:center; --as-md:center; --size:1.25rem; --weight:500; --px:0.125rem">
				{$i18n.t('Agents')}
				<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />
				<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)"
					>{filteredModels.length}</span
				>
			</div>
		</div>

		<div style="--d:flex; --fx:1 1 0%; --ai:center; --w:100%; --g:0.5rem">
			<div style="--d:flex; --fx:1 1 0%; --ai:center">
				<div style="--as:center; --ml:0.25rem; --mr:0.75rem">
					<Search className="size-3.5" />
				</div>
				<input
					style="--w:100%; --size:0.875rem; --py:0.25rem; --btrr:0.75rem; --bbrr:0.75rem; --oe:none; --bgc:transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Models')}
				/>

				{#if query}
					<div style="--as:center; --pl:0.375rem; --translatey:0.5px; --btlr:0.75rem; --bblr:0.75rem; --bgc:transparent">
						<button
							style="--p:0.125rem; --radius:9999px; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<div>
				<a
					style="--px:0.5rem; --py:0.5rem; --radius:0.75rem; --hvr-bgc:rgb(78 78 78 / 0.1); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem; --d:flex; --ai:center; --g:0.25rem"
					href="/workshop/models/create"
				>
					<Plus className="size-3.5" />
				</a>
			</div>
		</div>
	</div>

	{#if tags.length > 0}
		<div
			style="--d:flex; --w:100%; --bgc:transparent; --ofx:auto"
	class="scrollbar-none"
			on:wheel={(e) => {
				if (e.deltaY !== 0) {
					e.preventDefault();
					e.currentTarget.scrollLeft += e.deltaY;
				}
			}}
		>
			<div
				style="--d:flex; --g:0.25rem; --w:fit-content; --ta:center; --size:0.875rem; --weight:500; --radius:9999px"
				bind:this={tagsContainerElement}
			>
				<button
					style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize"
	class="{selectedTag === ''
						? ''
						: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
					on:click={() => {
						selectedTag = '';
					}}
				>
					{$i18n.t('All')}
				</button>

				{#each tags as tag}
					<button
						style="--minw:fit-content; --oe:2px solid transparent; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tt:capitalize"
	class="{selectedTag === tag
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
						on:click={() => {
							selectedTag = tag;
						}}
					>
						{tag}
					</button>
				{/each}
			</div>
		</div>
	{/if}
	<div style="--my:0.5rem; --mb:1.25rem; --g:0.5rem; --d:grid; --gtc-lg:repeat(2, minmax(0, 1fr)); --gtc-xl:repeat(3, minmax(0, 1fr))" id="model-list">
		{#each filteredModels as model (model.id)}
			<div
				style="--d:flex; --fd:column; --cur:pointer; --w:100%; --px:0.75rem; --py:0.5rem; --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --radius:0.75rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				id="model-item-{model.id}"
			>
				<div style="--d:flex; --g:1rem; --mt:0.25rem; --mb:0.125rem">
					<div style="--w:44px">
						<div
							style="--radius:9999px; --objf:cover"
	class="{model.is_active
								? ''
								: 'opacity-50 dark:opacity-50'}"
						>
							<img
								src={model?.meta?.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
								alt="modelfile profile"
								style="--radius:9999px; --w:100%; --h:auto; --objf:cover"
							/>
						</div>
					</div>

					<a
						style="--d:flex; --fx:1 1 0%; --cur:pointer; --w:100%"
						href={`/?models=${encodeURIComponent(model.id)}`}
					>
						<div style="--fx:1 1 0%; --as:center"
	class="{model.is_active ? '' : 'text-gray-500'}">
							<Tooltip
								content={marked.parse(model?.meta?.description ?? model.id)}
								className=" w-fit"
								placement="top-start"
							>
								<div style="--weight:600; --line-clamp:1">{model.name}</div>
							</Tooltip>

							<div style="--d:flex; --g:0.25rem; --size:0.75rem; --of:hidden">
								<div style="--line-clamp:1">
									{#if (model?.meta?.description ?? '').trim()}
										{model?.meta?.description}
									{:else}
										{model.id}
									{/if}
								</div>
							</div>
						</div>
					</a>
				</div>

				<div style="--d:flex; --jc:space-between; --ai:center; --mb:-0.125rem; --px:0.125rem; --mt:0.375rem">
					<div style="--size:0.75rem; --mt:0.125rem">
						<Tooltip
							content={model?.user?.email ?? $i18n.t('Deleted User')}
							className="flex shrink-0"
							placement="top-start"
						>
							<div style="--fs:0; --c:var(--color-gray-500)">
								{$i18n.t('By {{name}}', {
									name: capitalizeFirstLetter(
										model?.user?.name ?? model?.user?.email ?? $i18n.t('Deleted User')
									)
								})}
							</div>
						</Tooltip>
					</div>

					<div style="--d:flex; --fd:row; --g:0.125rem; --ai:center">
						{#if shiftKey}
							<Tooltip content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
								<button
									style="--as:center; --w:fit-content; --size:0.875rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.75rem"
									type="button"
									on:click={() => {
										hideModelHandler(model);
									}}
								>
									{#if model?.meta?.hidden}
										<EyeSlash />
									{:else}
										<Eye />
									{/if}
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Delete')}>
								<button
									style="--as:center; --w:fit-content; --size:0.875rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.75rem"
									type="button"
									on:click={() => {
										deleteModelHandler(model);
									}}
								>
									<GarbageBin />
								</button>
							</Tooltip>
						{:else}
							{#if $user?.role === 'admin' || model.user_id === $user?.id || model.access_control.write.group_ids.some( (wg) => group_ids.includes(wg) )}
								<a
									style="--as:center; --w:fit-content; --size:0.875rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.75rem"
									type="button"
									href={`/workshop/models/edit?id=${encodeURIComponent(model.id)}`}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										style="--w:1rem; --h:1rem"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
										/>
									</svg>
								</a>
							{/if}

							<ModelMenu
								user={$user}
								{model}
								shareHandler={() => {
									shareModelHandler(model);
								}}
								cloneHandler={() => {
									cloneModelHandler(model);
								}}
								exportHandler={() => {
									exportModelHandler(model);
								}}
								hideHandler={() => {
									hideModelHandler(model);
								}}
								copyLinkHandler={() => {
									copyLinkHandler(model);
								}}
								deleteHandler={() => {
									selectedModel = model;
									showModelDeleteConfirm = true;
								}}
								onClose={() => {}}
							>
								<button
									style="--as:center; --w:fit-content; --size:0.875rem; --p:0.375rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.75rem"
									type="button"
								>
									<EllipsisHorizontal className="size-5" />
								</button>
							</ModelMenu>

							<div style="--ml:0.25rem">
								<Tooltip content={model.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch
										bind:state={model.is_active}
										on:change={async (e) => {
											toggleModelById(localStorage.token, model.id);
											_models.set(
												await getModels(
													localStorage.token,
													$config?.features?.enable_direct_connections &&
														($settings?.directConnections ?? null)
												)
											);
										}}
									/>
								</Tooltip>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/each}
	</div>

	{#if $user?.role === 'admin'}
		<div style="--d:flex; --jc:flex-end; --w:100%; --mb:0.75rem">
			<div style="--d:flex; --g:0.25rem">
				<input
					id="models-import-input"
					bind:this={modelsImportInputElement}
					bind:files={importFiles}
					type="file"
					accept=".json"
					hidden
					on:change={() => {
						console.log(importFiles);

						let reader = new FileReader();
						reader.onload = async (event) => {
							let savedModels = JSON.parse(event.target.result);
							console.log(savedModels);

							for (const model of savedModels) {
								if (model?.info ?? false) {
									if ($_models.find((m) => m.id === model.id)) {
										await updateModelById(localStorage.token, model.id, model.info).catch(
											(error) => {
												return null;
											}
										);
									} else {
										await createNewModel(localStorage.token, model.info).catch((error) => {
											return null;
										});
									}
								} else {
									if (model?.id && model?.name) {
										await createNewModel(localStorage.token, model).catch((error) => {
											return null;
										});
									}
								}
							}

							await _models.set(
								await getModels(
									localStorage.token,
									$config?.features?.enable_direct_connections &&
										($settings?.directConnections ?? null)
								)
							);
							models = await getWorkshopModels(localStorage.token);
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					style="--d:flex; --size:0.75rem; --ai:center; --g:0.25rem; --px:0.75rem; --py:0.375rem; --radius:0.75rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						modelsImportInputElement.click();
					}}
				>
					<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">{$i18n.t('Import Agents')}</div>

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

				{#if models.length}
					<button
						style="--d:flex; --size:0.75rem; --ai:center; --g:0.25rem; --px:0.75rem; --py:0.375rem; --radius:0.75rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={async () => {
							downloadModels(models);
						}}
					>
						<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
							{$i18n.t('Export Agents')} ({models.length})
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

	{#if $config?.features.enable_community_sharing}
		<div style="--my:4rem">
			<div style="--size:1.25rem; --weight:500; --mb:0.25rem; --line-clamp:1">
				{$i18n.t('Made by Sage.is AI Community')}
			</div>

			<a
				style="--d:flex; --cur:pointer; --ai:center; --jc:space-between; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --w:100%; --mb:0.5rem; --px:0.875rem; --py:0.375rem; --radius:0.75rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				href="https://sage.is/community"
				target="_blank"
			>
				<div style="--as:center">
					<div style="--weight:600; --line-clamp:1">{$i18n.t('Discover your next agent')}</div>
					<div style="--size:0.875rem; --line-clamp:1">
						{$i18n.t('Discover, download, and explore agents')}
					</div>
				</div>

				<div>
					<div>
						<ChevronRight />
					</div>
				</div>
			</a>
		</div>
	{/if}
{:else}
	<div style="--w:100%; --h:100%; --d:flex; --jc:center; --ai:center">
		<Spinner className="size-5" />
	</div>
{/if}
