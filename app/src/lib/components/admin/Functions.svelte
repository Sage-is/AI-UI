<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { WEBUI_NAME, config, functions, models, settings } from '$lib/stores';
	import { onMount, getContext, tick } from 'svelte';

	import { goto } from '$app/navigation';
	import {
		createNewFunction,
		deleteFunctionById,
		exportFunctions,
		getFunctionById,
		getFunctions,
		loadFunctionByUrl,
		toggleFunctionById,
		toggleGlobalById
	} from '$lib/apis/functions';

	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import { getModels } from '$lib/apis';
	import FunctionMenu from './Functions/FunctionMenu.svelte';
	import Switch from '../common/Switch.svelte';
	import ValvesModal from '../workshop/common/ValvesModal.svelte';
	import ManifestModal from '../workshop/common/ManifestModal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import AddFunctionMenu from './Functions/AddFunctionMenu.svelte';
	import ImportModal from '../ImportModal.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	let shiftKey = false;

	let functionsImportInputElement: HTMLInputElement;
	let importFiles;

	let showImportModal = false;

	let showConfirm = false;
	let query = '';

	let selectedType = 'all';

	let showManifestModal = false;
	let showValvesModal = false;
	let selectedFunction = null;

	let showDeleteConfirm = false;

	let filteredItems = [];
	$: filteredItems = $functions
		.filter(
			(f) =>
				(selectedType !== 'all' ? f.type === selectedType : true) &&
				(query === '' ||
					f.name.toLowerCase().includes(query.toLowerCase()) ||
					f.id.toLowerCase().includes(query.toLowerCase()))
		)
		.sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));

	const shareHandler = async (func) => {
		const item = await getFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		toast.success($i18n.t('Redirecting you to Sage.is AI Community'));

		const url = 'https://sage.is';

		const tab = await window.open(`${url}/functions/create`, '_blank');

		// Define the event handler function
		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(item), '*');

				// Remove the event listener after handling the message
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
		console.log(item);
	};

	const cloneHandler = async (func) => {
		const _function = await getFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_function) {
			sessionStorage.function = JSON.stringify({
				..._function,
				id: `${_function.id}_clone`,
				name: `${_function.name} (Clone)`
			});
			goto('/admin/functions/create');
		}
	};

	const exportHandler = async (func) => {
		const _function = await getFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_function) {
			let blob = new Blob([JSON.stringify([_function])], {
				type: 'application/json'
			});
			saveAs(blob, `function-${_function.id}-export-${Date.now()}.json`);
		}
	};

	const deleteHandler = async (func) => {
		const res = await deleteFunctionById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Function deleted successfully'));

			functions.set(await getFunctions(localStorage.token));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
					false,
					true
				)
			);
		}
	};

	const toggleGlobalHandler = async (func) => {
		const res = await toggleGlobalById(localStorage.token, func.id).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			if (func.is_global) {
				func.type === 'filter'
					? toast.success($i18n.t('Filter is now globally enabled'))
					: toast.success($i18n.t('Function is now globally enabled'));
			} else {
				func.type === 'filter'
					? toast.success($i18n.t('Filter is now globally disabled'))
					: toast.success($i18n.t('Function is now globally disabled'));
			}

			functions.set(await getFunctions(localStorage.token));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
					false,
					true
				)
			);
		}
	};

	onMount(() => {
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
		{$i18n.t('Functions')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<ImportModal
	bind:show={showImportModal}
	loadUrlHandler={async (url) => {
		return await loadFunctionByUrl(localStorage.token, url);
	}}
	onImport={(func) => {
		sessionStorage.function = JSON.stringify({
			...func
		});
		goto('/admin/functions/create');
	}}
/>

<div style="--d:flex; --fd:column; --mt:0.4rem; --mb:0.125rem">
	<div style="--d:flex; --jc:space-between; --ai:center; --mb:0.2rem">
		<div style="--d:flex; --as-md:center; --size:1.2rem; --ai:center; --weight:500; --px:0.125rem">
			{$i18n.t('Functions')}
			<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />
			<span style="--size:1rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)"
	class="font-lg">{filteredItems.length}</span>
		</div>
	</div>

	<div style="--d:flex; --w:100%; --g:0.5rem">
		<div style="--d:flex; --fx:1 1 0%">
			<div style="--as:center; --ml:0.2rem; --mr:0.6rem">
				<Icon name="search" className="size-3.5" />
			</div>
			<input
				style="--w:100%; --size:0.8rem; --pr:1rem; --py:0.2rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
				bind:value={query}
				placeholder={$i18n.t('Search Functions')}
			/>

			{#if query}
				<div style="--as:center; --pl:0.4rem; --translatey:0.5px; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent">
					<button
						style="--p:0.125rem; --radius:9999px; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							query = '';
						}}
					>
						<Icon name="x-mark" className="size-3" strokeWidth="2" />
					</button>
				</div>
			{/if}
		</div>

		<div>
			<AddFunctionMenu
				createHandler={() => {
					goto('/admin/functions/create');
				}}
				importFromLinkHandler={() => {
					showImportModal = true;
				}}
			>
				<div
					style="--px:0.5rem; --py:0.5rem; --radius:0.6rem; --hvr-bgc:rgb(78 78 78 / 0.1); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.8rem; --d:flex; --ai:center; --g:0.2rem"
				>
					<Icon name="plus" className="size-3.5" />
				</div>
			</AddFunctionMenu>
		</div>
	</div>

	<div style="--d:flex; --w:100%">
		<div
			style="--d:flex; --g:0.2rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.8rem; --weight:500; --radius:9999px; --bgc:transparent"
	class="scrollbar-none"
		>
			<button
				style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedType === 'all'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedType = 'all';
				}}>{$i18n.t('All')}</button
			>

			<button
				style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedType === 'pipe'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedType = 'pipe';
				}}>{$i18n.t('Pipe')}</button
			>

			<button
				style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedType === 'filter'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedType = 'filter';
				}}>{$i18n.t('Filter')}</button
			>

			<button
				style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedType === 'action'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedType = 'action';
				}}>{$i18n.t('Action')}</button
			>
		</div>
	</div>
</div>

<div style="--mb:1.2rem">
	{#each filteredItems as func (func.id)}
		<div
			style="--d:flex; --g:1rem; --cur:pointer; --w:100%; --px:0.5rem; --py:0.5rem; --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --radius:0.6rem"
		>
			<a
				style="--d:flex; --fx:1 1 0%; --g:0.8rem; --cur:pointer; --w:100%"
				href={`/admin/functions/edit?id=${encodeURIComponent(func.id)}`}
			>
				<div style="--d:flex; --ai:center; --ta:left">
					<div style="--fx:1 1 0%; --as:center; --pl:0.2rem">
						<div style="--weight:600; --d:flex; --ai:center; --g:0.4rem">
							<div
								style="--size:0.6rem; --weight:700; --px:0.2rem; --radius:0.125rem; --tt:uppercase; --line-clamp:1; --bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700); --dark-c:var(--color-gray-200)"
							>
								{func.type}
							</div>

							{#if func?.meta?.manifest?.version}
								<div
									style="--size:0.6rem; --weight:700; --px:0.2rem; --radius:0.125rem; --line-clamp:1; --bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700); --dark-c:var(--color-gray-200)"
								>
									v{func?.meta?.manifest?.version ?? ''}
								</div>
							{/if}

							<div style="--line-clamp:1">
								{func.name}
							</div>
						</div>

						<div style="--d:flex; --g:0.4rem; --px:0.2rem">
							<div style="--c:var(--color-gray-500); --size:0.6rem; --weight:500; --fs:0">{func.id}</div>

							<div style="--size:0.6rem; --of:hidden; text-overflow:ellipsis; --line-clamp:1">
								{func.meta.description}
							</div>
						</div>
					</div>
				</div>
			</a>
			<div style="--d:flex; --fd:row; --g:0.125rem; --as:center">
				{#if shiftKey}
					<Tooltip content={$i18n.t('Delete')}>
						<button
							style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
							type="button"
							on:click={() => {
								deleteHandler(func);
							}}
						>
							<Icon name="garbage-bin" />
						</button>
					</Tooltip>
				{:else}
					{#if func?.meta?.manifest?.funding_url ?? false}
						<Tooltip content={$i18n.t('Support')}>
							<button
								style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
								type="button"
								on:click={() => {
									selectedFunction = func;
									showManifestModal = true;
								}}
							>
								<Icon name="heart" />
							</button>
						</Tooltip>
					{/if}

					<Tooltip content={$i18n.t('Valves')}>
						<button
							style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
							type="button"
							on:click={() => {
								selectedFunction = func;
								showValvesModal = true;
							}}
						>
							<Icon name="cog6" className="size-4" />
						</button>
					</Tooltip>

					<FunctionMenu
						{func}
						editHandler={() => {
							goto(`/admin/functions/edit?id=${encodeURIComponent(func.id)}`);
						}}
						shareHandler={() => {
							shareHandler(func);
						}}
						cloneHandler={() => {
							cloneHandler(func);
						}}
						exportHandler={() => {
							exportHandler(func);
						}}
						deleteHandler={async () => {
							selectedFunction = func;
							showDeleteConfirm = true;
						}}
						toggleGlobalHandler={() => {
							if (['filter', 'action'].includes(func.type)) {
								toggleGlobalHandler(func);
							}
						}}
						onClose={() => {}}
					>
						<button
							style="--as:center; --w:fit-content; --size:0.8rem; --p:0.4rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
							type="button"
						>
							<Icon name="ellipsis-horizontal" className="size-5" />
						</button>
					</FunctionMenu>
				{/if}

				<div style="--as:center; --mx:0.2rem">
					<Tooltip content={func.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
						<Switch
							bind:state={func.is_active}
							on:change={async (e) => {
								toggleFunctionById(localStorage.token, func.id);
								models.set(
									await getModels(
										localStorage.token,
										$config?.features?.enable_direct_connections &&
											($settings?.directConnections ?? null),
										false,
										true
									)
								);
							}}
						/>
					</Tooltip>
				</div>
			</div>
		</div>
	{/each}
</div>

<!-- <div style="--c:var(--color-gray-500); --size:0.6rem; --mt:0.2rem; --mb:0.5rem">
	ⓘ {$i18n.t(
		'Admins have access to all tools at all times; users need tools assigned per model in the workshop.'
	)}
</div> -->

<div style="--d:flex; --jc:flex-end; --w:100%; --mb:0.5rem">
	<div style="--d:flex; --g:0.5rem">
		<input
			id="documents-import-input"
			bind:this={functionsImportInputElement}
			bind:files={importFiles}
			type="file"
			accept=".json"
			hidden
			on:change={() => {
				console.log(importFiles);
				showConfirm = true;
			}}
		/>

		<button
			style="--d:flex; --size:0.6rem; --ai:center; --g:0.2rem; --px:0.6rem; --py:0.4rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			on:click={() => {
				functionsImportInputElement.click();
			}}
		>
			<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">{$i18n.t('Import Functions')}</div>

			<div style="--as:center">
				<Icon name="clipboard-import" className="size-4" />
			</div>
		</button>

		{#if $functions.length}
			<button
				style="--d:flex; --size:0.6rem; --ai:center; --g:0.2rem; --px:0.6rem; --py:0.4rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={async () => {
					const _functions = await exportFunctions(localStorage.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					});

					if (_functions) {
						let blob = new Blob([JSON.stringify(_functions)], {
							type: 'application/json'
						});
						saveAs(blob, `functions-export-${Date.now()}.json`);
					}
				}}
			>
				<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
					{$i18n.t('Export Functions')} ({$functions.length})
				</div>

				<div style="--as:center">
					<Icon name="clipboard-import-331f" className="size-4" />
				</div>
			</button>
		{/if}
	</div>
</div>

{#if $config?.features.enable_community_sharing}
	<div style="--my:4rem">
		<div style="--size:1.2rem; --weight:500; --mb:0.2rem; --line-clamp:1">
			{$i18n.t('Sage.is AI Community')}
		</div>

		<a
			style="--d:flex; --cur:pointer; --ai:center; --jc:space-between; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --w:100%; --mb:0.5rem; --px:0.8rem; --py:0.4rem; --radius:0.6rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			href="https://sage.is/community"
			target="_blank"
		>
			<div style="--as:center">
				<div style="--weight:600; --line-clamp:1">{$i18n.t('Discover your next function')}</div>
				<div style="--size:0.8rem; --line-clamp:1">
					{$i18n.t('Discover, download, and explore custom functions')}
				</div>
			</div>

			<div>
				<div>
					<Icon name="chevron-right" />
				</div>
			</div>
		</a>
	</div>
{/if}

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete function?')}
	on:confirm={() => {
		deleteHandler(selectedFunction);
	}}
>
	<div style="--size:0.8rem; --c:var(--color-gray-500)">
		{$i18n.t('This will delete')} <span style="--weight:600">{selectedFunction.name}</span>.
	</div>
</DeleteConfirmDialog>

<ManifestModal bind:show={showManifestModal} manifest={selectedFunction?.meta?.manifest ?? {}} />
<ValvesModal
	bind:show={showValvesModal}
	type="function"
	id={selectedFunction?.id ?? null}
	on:save={async () => {
		await tick();
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
				false,
				true
			)
		);
	}}
/>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		const reader = new FileReader();
		reader.onload = async (event) => {
			const _functions = JSON.parse(event.target.result);
			console.log(_functions);

			for (const func of _functions) {
				const res = await createNewFunction(localStorage.token, func).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}

			toast.success($i18n.t('Functions imported successfully'));
			functions.set(await getFunctions(localStorage.token));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
					false,
					true
				)
			);
		};

		reader.readAsText(importFiles[0]);
	}}
>
	<div style="--size:0.8rem; --c:var(--color-gray-500)">
		<div style="--bgc:rgb(234 179 8 / 0.2); --c:#a16207; --dark-c:#fef08a; --radius:0.5rem; --px:1rem; --py:0.6rem">
			<div>Please carefully review the following warnings:</div>

			<ul style="--mt:0.2rem; list-style-type:disc; --pl:1rem; --size:0.6rem">
				<li>{$i18n.t('Functions allow arbitrary code execution.')}</li>
				<li>{$i18n.t('Do not install functions from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div style="--my:0.6rem">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
