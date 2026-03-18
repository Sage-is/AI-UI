<script lang="ts">
	import { marked } from 'marked';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import {
		createNewModel,
		deleteAllModels,
		getBaseModels,
		toggleModelById,
		updateModelById
	} from '$lib/apis/models';
	import { copyToClipboard } from '$lib/utils';
	import { page } from '$app/stores';

	import { getModels } from '$lib/apis';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import ModelEditor from '$lib/components/workshop/Models/ModelEditor.svelte';
	import { toast } from 'svelte-sonner';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ConfigureModelsModal from './Models/ConfigureModelsModal.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ManageModelsModal from './Models/ManageModelsModal.svelte';
	import ModelMenu from '$lib/components/admin/Settings/Models/ModelMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding, type Branding } from '$lib/apis/configs';

	let shiftKey = false;

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;

	let models = null;

	let workshopModels = null;
	let baseModels = null;

	let branding: Branding | null = null;

	let filteredModels = [];
	let selectedModelId = null;

	let showConfigModal = false;
	let showManageModal = false;

	$: if (models) {
		filteredModels = models
			.filter((m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase()))
			.sort((a, b) => {
				// // Check if either model is inactive and push them to the bottom
				// if ((a.is_active ?? true) !== (b.is_active ?? true)) {
				// 	return (b.is_active ?? true) - (a.is_active ?? true);
				// }
				// If both models' active states are the same, sort alphabetically
				return a.name.localeCompare(b.name);
			});
	}

	let searchValue = '';

	const downloadModels = async (models) => {
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const init = async () => {
		models = null;

		workshopModels = await getBaseModels(localStorage.token);
		baseModels = await getModels(localStorage.token, null, true);

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
	};

	const upsertModelHandler = async (model) => {
		model.base_model_id = null;

		if (workshopModels.find((m) => m.id === model.id)) {
			const res = await updateModelById(localStorage.token, model.id, model).catch((error) => {
				return null;
			});

			if (res) {
				toast.success($i18n.t('Model updated successfully'));
			}
		} else {
			const res = await createNewModel(localStorage.token, {
				meta: {},
				id: model.id,
				name: model.name,
				base_model_id: null,
				params: {},
				access_control: {},
				...model
			}).catch((error) => {
				return null;
			});

			if (res) {
				toast.success($i18n.t('Model updated successfully'));
			}
		}
		await init();

		_models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const toggleModelHandler = async (model) => {
		if (!Object.keys(model).includes('base_model_id')) {
			await createNewModel(localStorage.token, {
				id: model.id,
				name: model.name,
				base_model_id: null,
				meta: {},
				params: {},
				access_control: {},
				is_active: model.is_active
			}).catch((error) => {
				return null;
			});
		} else {
			await toggleModelById(localStorage.token, model.id);
		}

		// await init();
		_models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const hideModelHandler = async (model) => {
		model.meta = {
			...model.meta,
			hidden: !(model?.meta?.hidden ?? false)
		};

		console.debug(model);

		toast.success(
			model.meta.hidden
				? $i18n.t(`Model {{name}} is now hidden`, {
						name: model.id
					})
				: $i18n.t(`Model {{name}} is now visible`, {
						name: model.id
					})
		);

		upsertModelHandler(model);
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

	const exportModelHandler = async (model) => {
		let blob = new Blob([JSON.stringify([model])], {
			type: 'application/json'
		});
		saveAs(blob, `${model.id}-${Date.now()}.json`);
	};

	onMount(async () => {
		await init();

		// Fetch branding for fallback logo
		try {
			branding = await getBranding();
		} catch (e) {
			console.error('Failed to load branding:', e);
		}

		const id = $page.url.searchParams.get('id');

		if (id) {
			selectedModelId = id;
		}

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

<ConfigureModelsModal bind:show={showConfigModal} initHandler={init} />
<ManageModelsModal bind:show={showManageModal} />

{#if models !== null}
	{#if selectedModelId === null}
		<div style="--d:flex; --fd:column; --g:0.2rem; --mt:0.4rem; --mb:0.5rem">
			<div style="--d:flex; --jc:space-between; --ai:center">
				<div style="--d:flex; --ai:center; --as-md:center; --size:1.2rem; --weight:500; --px:0.125rem">
					{$i18n.t('Models')}
					<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />
					<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)"
						>{filteredModels.length}</span
					>
				</div>

				<div style="--d:flex; --ai:center; --g:0.4rem">
					<Tooltip content={$i18n.t('Manage Models')}>
						<button
							style="--p:0.2rem; --radius:9999px; --d:flex; --g:0.2rem; --ai:center"
							type="button"
							on:click={() => {
								showManageModal = true;
							}}
						>
							<ArrowDownTray />
						</button>
					</Tooltip>

					<Tooltip content={$i18n.t('Settings')}>
						<button
							style="--p:0.2rem; --radius:9999px; --d:flex; --g:0.2rem; --ai:center"
							type="button"
							on:click={() => {
								showConfigModal = true;
							}}
						>
							<Cog6 />
						</button>
					</Tooltip>
				</div>
			</div>

			<div style="--d:flex; --fx:1 1 0%; --ai:center; --w:100%; --g:0.5rem">
				<div style="--d:flex; --fx:1 1 0%; --ai:center">
					<div style="--as:center; --ml:0.2rem; --mr:0.6rem">
						<Search className="size-3.5" />
					</div>
					<input
						style="--w:100%; --size:0.8rem; --py:0.2rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
						bind:value={searchValue}
						placeholder={$i18n.t('Search Models')}
					/>
					{#if searchValue}
						<div style="--as:center; --pl:0.4rem; --translatey:0.5px; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent">
							<button
								style="--p:0.125rem; --radius:9999px; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								on:click={() => {
									searchValue = '';
								}}
							>
								<XMark className="size-3" strokeWidth="2" />
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div style="--my:0.5rem; --mb:1.2rem" id="model-list">
			{#if models.length > 0}
				{#each filteredModels as model, modelIdx (model.id)}
					<div
						style="--d:flex; --g:1rem; --cur:pointer; --w:100%; --px:0.6rem; --py:0.5rem; --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{model
							?.meta?.hidden
							? 'opacity-50 dark:opacity-50'
							: ''}"
						id="model-item-{model.id}"
					>
						<button
							style="--d:flex; --fx:1 1 0%; --ta:left; --g:0.8rem; --cur:pointer; --w:100%"
							type="button"
							on:click={() => {
								selectedModelId = model.id;
							}}
						>
							<div style="--as:center; --w:2rem">
								<div
									style="--radius:9999px; --objf:cover"
	class="{(model?.is_active ?? true)
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

							<div style="--fx:1 1 0%; --as:center"
	class="{(model?.is_active ?? true) ? '' : 'text-gray-500'}">
								<Tooltip
									content={marked.parse(
										!!model?.meta?.description
											? model?.meta?.description
											: model?.ollama?.digest
												? `${model?.ollama?.digest} **(${model?.ollama?.modified_at})**`
												: model.id
									)}
									className=" w-fit"
									placement="top-start"
								>
									<div style="--weight:600; --line-clamp:1">{model.name}</div>
								</Tooltip>
								<div style="--size:0.6rem; --of:hidden; text-overflow:ellipsis; --line-clamp:1; --c:var(--color-gray-500)">
									<span style="--line-clamp:1">
										{!!model?.meta?.description
											? model?.meta?.description
											: model?.ollama?.digest
												? `${model.id} (${model?.ollama?.digest})`
												: model.id}
									</span>
								</div>
							</div>
						</button>
						<div style="--d:flex; --fd:row; --g:0.125rem; --ai:center; --as:center">
							{#if shiftKey}
								<Tooltip content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
									<button
										style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
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
							{:else}
								<button
									style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
									type="button"
									on:click={() => {
										selectedModelId = model.id;
									}}
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
								</button>

								<ModelMenu
									user={$user}
									{model}
									exportHandler={() => {
										exportModelHandler(model);
									}}
									hideHandler={() => {
										hideModelHandler(model);
									}}
									copyLinkHandler={() => {
										copyLinkHandler(model);
									}}
									onClose={() => {}}
								>
									<button
										style="--as:center; --w:fit-content; --size:0.8rem; --p:0.4rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
										type="button"
									>
										<EllipsisHorizontal className="size-5" />
									</button>
								</ModelMenu>

								<div style="--ml:0.2rem">
									<Tooltip
										content={(model?.is_active ?? true) ? $i18n.t('Enabled') : $i18n.t('Disabled')}
									>
										<Switch
											bind:state={model.is_active}
											on:change={async () => {
												toggleModelHandler(model);
											}}
										/>
									</Tooltip>
								</div>
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div style="--d:flex; --fd:column; --ai:center; --jc:center; --w:100%; --h:5rem">
					<div style="--c:var(--color-gray-500); --dark-c:var(--color-gray-400); --size:0.6rem">
						{$i18n.t('No models found')}
					</div>
				</div>
			{/if}
		</div>

		{#if $user?.role === 'admin'}
			<div style="--d:flex; --jc:flex-end; --w:100%; --mb:0.6rem">
				<div style="--d:flex; --g:0.2rem">
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
									if (Object.keys(model).includes('base_model_id')) {
										if (model.base_model_id === null) {
											upsertModelHandler(model);
										}
									} else {
										if (model?.info ?? false) {
											if (model.info.base_model_id === null) {
												upsertModelHandler(model.info);
											}
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
								init();
							};

							reader.readAsText(importFiles[0]);
						}}
					/>

					<button
						style="--d:flex; --size:0.6rem; --ai:center; --g:0.2rem; --px:0.6rem; --py:0.4rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							modelsImportInputElement.click();
						}}
					>
						<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
							{$i18n.t('Import Presets')}
						</div>

						<div style="--as:center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								style="--w:0.8rem; --h:0.8rem"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>

					<button
						style="--d:flex; --size:0.6rem; --ai:center; --g:0.2rem; --px:0.6rem; --py:0.4rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={async () => {
							downloadModels(models);
						}}
					>
						<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
							{$i18n.t('Export Presets')} ({models.length})
						</div>

						<div style="--as:center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								style="--w:0.8rem; --h:0.8rem"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>
				</div>
			</div>
		{/if}
	{:else}
		<ModelEditor
			edit
			model={models.find((m) => m.id === selectedModelId)}
			preset={false}
			onSubmit={(model) => {
				console.log(model);
				upsertModelHandler(model);
				selectedModelId = null;
			}}
			onBack={() => {
				selectedModelId = null;
			}}
		/>
	{/if}
{:else}
	<div style="--h:100%; --w:100%; --d:flex; --jc:center; --ai:center">
		<Spinner className="size-5" />
	</div>
{/if}
