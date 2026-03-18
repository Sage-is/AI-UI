<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, prompts, tools as _tools, user } from '$lib/stores';
	import { createNewPrompt, deletePromptByCommand, getPrompts } from '$lib/apis/prompts';

	import { goto } from '$app/navigation';
	import {
		createNewTool,
		loadToolByUrl,
		deleteToolById,
		exportTools,
		getToolById,
		getToolList,
		getTools
	} from '$lib/apis/tools';
	import ArrowDownTray from '../icons/ArrowDownTray.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import ToolMenu from './Tools/ToolMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ValvesModal from './common/ValvesModal.svelte';
	import ManifestModal from './common/ManifestModal.svelte';
	import Heart from '../icons/Heart.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';
	import XMark from '../icons/XMark.svelte';
	import AddToolMenu from './Tools/AddToolMenu.svelte';
	import ImportModal from '../ImportModal.svelte';

	const i18n = getContext('i18n');

	let shiftKey = false;
	let loaded = false;

	let toolsImportInputElement: HTMLInputElement;
	let importFiles;

	let showConfirm = false;
	let query = '';

	let showManifestModal = false;
	let showValvesModal = false;
	let selectedTool = null;

	let showDeleteConfirm = false;

	let tools = [];
	let filteredItems = [];

	let showImportModal = false;

	$: filteredItems = tools.filter((t) => {
		if (query === '') return true;
		const lowerQuery = query.toLowerCase();
		return (
			(t.name || '').toLowerCase().includes(lowerQuery) ||
			(t.id || '').toLowerCase().includes(lowerQuery) ||
			(t.user?.name || '').toLowerCase().includes(lowerQuery) || // Search by user name
			(t.user?.email || '').toLowerCase().includes(lowerQuery) // Search by user email
		);
	});

	const shareHandler = async (tool) => {
		const item = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		toast.success($i18n.t('Redirecting you to Sage.is AI Community'));

		const url = 'https://sage.is';

		const tab = await window.open(`${url}/tools/create`, '_blank');

		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(item), '*');
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
		console.log(item);
	};

	const cloneHandler = async (tool) => {
		const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_tool) {
			sessionStorage.tool = JSON.stringify({
				..._tool,
				id: `${_tool.id}_clone`,
				name: `${_tool.name} (Clone)`
			});
			goto('/workshop/tools/create');
		}
	};

	const exportHandler = async (tool) => {
		const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_tool) {
			let blob = new Blob([JSON.stringify([_tool])], {
				type: 'application/json'
			});
			saveAs(blob, `tool-${_tool.id}-export-${Date.now()}.json`);
		}
	};

	const deleteHandler = async (tool) => {
		const res = await deleteToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Tool deleted successfully'));
			await init();
		}
	};

	const init = async () => {
		tools = await getToolList(localStorage.token);
		_tools.set(await getTools(localStorage.token));
	};

	onMount(async () => {
		await init();
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
		{$i18n.t('Tools')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<ImportModal
	bind:show={showImportModal}
	onImport={(tool) => {
		sessionStorage.tool = JSON.stringify({
			...tool
		});
		goto('/workshop/tools/create');
	}}
	loadUrlHandler={async (url) => {
		return await loadToolByUrl(localStorage.token, url);
	}}
	successMessage={$i18n.t('Tool imported successfully')}
/>

{#if loaded}
	<div style="--d:flex; --fd:column; --g:0.2rem; --my:0.4rem">
		<div style="--d:flex; --jc:space-between; --ai:center">
			<div style="--d:flex; --as-md:center; --size:1.2rem; --weight:500; --px:0.125rem; --ai:center">
				{$i18n.t('Tools')}
				<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />
				<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)"
					>{filteredItems.length}</span
				>
			</div>
		</div>

		<div style="--d:flex; --w:100%; --g:0.5rem">
			<div style="--d:flex; --fx:1 1 0%">
				<div style="--as:center; --ml:0.2rem; --mr:0.6rem">
					<Search className="size-3.5" />
				</div>
				<input
					style="--w:100%; --size:0.8rem; --pr:1rem; --py:0.2rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Tools')}
				/>
				{#if query}
					<div style="--as:center; --pl:0.4rem; --translatey:0.5px; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent">
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
				{#if $user?.role === 'admin'}
					<AddToolMenu
						createHandler={() => {
							goto('/workshop/tools/create');
						}}
						importFromLinkHandler={() => {
							showImportModal = true;
						}}
					>
						<div
							style="--px:0.5rem; --py:0.5rem; --radius:0.6rem; --hvr-bgc:rgb(78 78 78 / 0.1); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.8rem; --d:flex; --ai:center; --g:0.2rem"
						>
							<Plus className="size-3.5" />
						</div>
					</AddToolMenu>
				{:else}
					<a
						style="--px:0.5rem; --py:0.5rem; --radius:0.6rem; --hvr-bgc:rgb(78 78 78 / 0.1); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.8rem; --d:flex; --ai:center; --g:0.2rem"
						href="/workshop/tools/create"
					>
						<Plus className="size-3.5" />
					</a>
				{/if}
			</div>
		</div>
	</div>

	<div style="--mb:1.2rem; --g:0.5rem; --d:grid; --gtc-lg:repeat(2, minmax(0, 1fr)); --gtc-xl:repeat(3, minmax(0, 1fr))">
		{#each filteredItems as tool}
			<div
				style="--d:flex; --g:1rem; --cur:pointer; --w:100%; --px:0.6rem; --py:0.5rem; --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --radius:0.6rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<a
					style="--d:flex; --fx:1 1 0%; --g:0.8rem; --cur:pointer; --w:100%"
					href={`/workshop/tools/edit?id=${encodeURIComponent(tool.id)}`}
				>
					<div style="--d:flex; --ai:center; --ta:left">
						<div style="--fx:1 1 0%; --as:center">
							<Tooltip content={tool?.meta?.description ?? ''} placement="top-start">
								<div style="--weight:600; --d:flex; --ai:center; --g:0.4rem">
									<div
										style="--size:0.6rem; --weight:700; --px:0.2rem; --radius:0.125rem; --tt:uppercase; --line-clamp:1; --bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700); --dark-c:var(--color-gray-200)"
									>
										TOOL
									</div>

									{#if tool?.meta?.manifest?.version}
										<div
											style="--size:0.6rem; --weight:700; --px:0.2rem; --radius:0.125rem; --line-clamp:1; --bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700); --dark-c:var(--color-gray-200)"
										>
											v{tool?.meta?.manifest?.version ?? ''}
										</div>
									{/if}

									<div style="--line-clamp:1">
										{tool.name}

										<span style="--c:var(--color-gray-500); --size:0.6rem; --weight:500; --fs:0">{tool.id}</span>
									</div>
								</div>
							</Tooltip>

							<div style="--px:0.125rem">
								<div style="--d:flex; --g:0.4rem; --mt:0.125rem; --mb:0.125rem">
									<div style="--size:0.6rem; --of:hidden; text-overflow:ellipsis; --line-clamp:1">
										{tool.meta.description}
									</div>
								</div>

								<div style="--size:0.6rem; --c:var(--color-gray-500); --fs:0">
									<Tooltip
										content={tool?.user?.email ?? $i18n.t('Deleted User')}
										className="flex shrink-0"
										placement="top-start"
									>
										{$i18n.t('By {{name}}', {
											name: capitalizeFirstLetter(
												tool?.user?.name ?? tool?.user?.email ?? $i18n.t('Deleted User')
											)
										})}
									</Tooltip>
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
									deleteHandler(tool);
								}}
							>
								<GarbageBin />
							</button>
						</Tooltip>
					{:else}
						{#if tool?.meta?.manifest?.funding_url ?? false}
							<Tooltip content="Support">
								<button
									style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
									type="button"
									on:click={() => {
										selectedTool = tool;
										showManifestModal = true;
									}}
								>
									<Heart />
								</button>
							</Tooltip>
						{/if}

						<Tooltip content={$i18n.t('Valves')}>
							<button
								style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
								type="button"
								on:click={() => {
									selectedTool = tool;
									showValvesModal = true;
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
										d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
									/>
								</svg>
							</button>
						</Tooltip>

						<ToolMenu
							editHandler={() => {
								goto(`/workshop/tools/edit?id=${encodeURIComponent(tool.id)}`);
							}}
							shareHandler={() => {
								shareHandler(tool);
							}}
							cloneHandler={() => {
								cloneHandler(tool);
							}}
							exportHandler={() => {
								exportHandler(tool);
							}}
							deleteHandler={async () => {
								selectedTool = tool;
								showDeleteConfirm = true;
							}}
							onClose={() => {}}
						>
							<button
								style="--as:center; --w:fit-content; --size:0.8rem; --p:0.4rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
								type="button"
							>
								<EllipsisHorizontal className="size-5" />
							</button>
						</ToolMenu>
					{/if}
				</div>
			</div>
		{/each}
	</div>

	{#if $user?.role === 'admin'}
		<div style="--d:flex; --jc:flex-end; --w:100%; --mb:0.5rem">
			<div style="--d:flex; --g:0.5rem">
				<input
					id="documents-import-input"
					bind:this={toolsImportInputElement}
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
						toolsImportInputElement.click();
					}}
				>
					<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">{$i18n.t('Import Tools')}</div>

					<div style="--as:center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>

				{#if tools.length}
					<button
						style="--d:flex; --size:0.6rem; --ai:center; --g:0.2rem; --px:0.6rem; --py:0.4rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={async () => {
							const _tools = await exportTools(localStorage.token).catch((error) => {
								toast.error(`${error}`);
								return null;
							});

							if (_tools) {
								let blob = new Blob([JSON.stringify(_tools)], {
									type: 'application/json'
								});
								saveAs(blob, `tools-export-${Date.now()}.json`);
							}
						}}
					>
						<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
							{$i18n.t('Export Tools')} ({tools.length})
						</div>

						<div style="--as:center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								style="--w:1rem; --h:1rem"
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
			<div style="--size:1.2rem; --weight:500; --mb:0.2rem; --line-clamp:1">
				{$i18n.t('Sage.is AI Community')}
			</div>

			<a
				style="--d:flex; --cur:pointer; --ai:center; --jc:space-between; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --w:100%; --mb:0.5rem; --px:0.8rem; --py:0.4rem; --radius:0.6rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				href="https://sage.is/community"
				target="_blank"
			>
				<div style="--as:center">
					<div style="--weight:600; --line-clamp:1">{$i18n.t('Discover your next tool')}</div>
					<div style="--size:0.8rem; --line-clamp:1">
						{$i18n.t('Discover, download, and explore custom tools')}
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

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete tool?')}
		on:confirm={() => {
			deleteHandler(selectedTool);
		}}
	>
		<div style="--size:0.8rem; --c:var(--color-gray-500)">
			{$i18n.t('This will delete')} <span style="--weight:600">{selectedTool.name}</span>.
		</div>
	</DeleteConfirmDialog>

	<ValvesModal bind:show={showValvesModal} type="tool" id={selectedTool?.id ?? null} />
	<ManifestModal bind:show={showManifestModal} manifest={selectedTool?.meta?.manifest ?? {}} />

	<ConfirmDialog
		bind:show={showConfirm}
		on:confirm={() => {
			const reader = new FileReader();
			reader.onload = async (event) => {
				const _tools = JSON.parse(event.target.result);
				console.log(_tools);

				for (const tool of _tools) {
					const res = await createNewTool(localStorage.token, tool).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}

				toast.success($i18n.t('Tool imported successfully'));
				tools.set(await getTools(localStorage.token));
			};

			reader.readAsText(importFiles[0]);
		}}
	>
		<div style="--size:0.8rem; --c:var(--color-gray-500)">
			<div style="--bgc:rgb(234 179 8 / 0.2); --c:#a16207; --dark-c:#fef08a; --radius:0.5rem; --px:1rem; --py:0.6rem">
				<div>{$i18n.t('Please carefully review the following warnings:')}</div>

				<ul style="--mt:0.2rem; list-style-type:disc; --pl:1rem; --size:0.6rem">
					<li>
						{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}.
					</li>
					<li>{$i18n.t('Do not install tools from sources you do not fully trust.')}</li>
				</ul>
			</div>

			<div style="--my:0.6rem">
				{$i18n.t(
					'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
				)}
			</div>
		</div>
	</ConfirmDialog>
{:else}
	<div style="--w:100%; --h:100%; --d:flex; --jc:center; --ai:center">
		<Spinner className="size-5" />
	</div>
{/if}
