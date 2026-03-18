<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptByCommand,
		getPrompts,
		getPromptList
	} from '$lib/apis/prompts';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { capitalizeFirstLetter, slugify } from '$lib/utils';
	import XMark from '../icons/XMark.svelte';

	const i18n = getContext('i18n');
	let promptsImportInputElement: HTMLInputElement;
	let loaded = false;

	let importFiles = '';
	let query = '';

	let prompts = [];

	let showDeleteConfirm = false;
	let deletePrompt = null;

	let filteredItems = [];
	$: filteredItems = prompts.filter((p) => {
		if (query === '') return true;
		const lowerQuery = query.toLowerCase();
		return (
			(p.title || '').toLowerCase().includes(lowerQuery) ||
			(p.command || '').toLowerCase().includes(lowerQuery) ||
			(p.user?.name || '').toLowerCase().includes(lowerQuery) ||
			(p.user?.email || '').toLowerCase().includes(lowerQuery)
		);
	});

	const shareHandler = async (prompt) => {
		toast.success($i18n.t('Redirecting you to Sage.is AI Community'));

		const url = 'https://sage.is';

		const tab = await window.open(`${url}/prompts/create`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(JSON.stringify(prompt), '*');
				}
			},
			false
		);
	};

	const cloneHandler = async (prompt) => {
		const clonedPrompt = { ...prompt };

		clonedPrompt.title = `${clonedPrompt.title} (Clone)`;
		const baseCommand = clonedPrompt.command.startsWith('/')
			? clonedPrompt.command.substring(1)
			: clonedPrompt.command;
		clonedPrompt.command = slugify(`${baseCommand} clone`);

		sessionStorage.prompt = JSON.stringify(clonedPrompt);
		goto('/workshop/prompts/create');
	};

	const exportHandler = async (prompt) => {
		let blob = new Blob([JSON.stringify([prompt])], {
			type: 'application/json'
		});
		saveAs(blob, `prompt-export-${Date.now()}.json`);
	};

	const deleteHandler = async (prompt) => {
		const command = prompt.command;
		await deletePromptByCommand(localStorage.token, command);
		await init();
	};

	const init = async () => {
		prompts = await getPromptList(localStorage.token);
		await _prompts.set(await getPrompts(localStorage.token));
	};

	onMount(async () => {
		await init();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Prompts')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete prompt?')}
		on:confirm={() => {
			deleteHandler(deletePrompt);
		}}
	>
		<div style="--size:0.875rem; --c:var(--color-gray-500)">
			{$i18n.t('This will delete')} <span style="--weight:600">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<div style="--d:flex; --fd:column; --g:0.25rem; --my:0.375rem">
		<div style="--d:flex; --jc:space-between; --ai:center">
			<div style="--d:flex; --as-md:center; --size:1.25rem; --weight:500; --px:0.125rem; --ai:center">
				{$i18n.t('Prompts')}
				<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />
				<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)"
					>{filteredItems.length}</span
				>
			</div>
		</div>

		<div style="--d:flex; --w:100%; --g:0.5rem">
			<div style="--d:flex; --fx:1 1 0%">
				<div style="--as:center; --ml:0.25rem; --mr:0.6rem">
					<Search className="size-3.5" />
				</div>
				<input
					style="--w:100%; --size:0.875rem; --pr:1rem; --py:0.25rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Prompts')}
				/>

				{#if query}
					<div style="--as:center; --pl:0.375rem; --translatey:0.5px; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent">
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
					style="--px:0.5rem; --py:0.5rem; --radius:0.6rem; --hvr-bgc:rgb(78 78 78 / 0.1); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem; --d:flex; --ai:center; --g:0.25rem"
					href="/workshop/prompts/create"
				>
					<Plus className="size-3.5" />
				</a>
			</div>
		</div>
	</div>

	<div style="--mb:1.25rem; --g:0.5rem; --d:grid; --gtc-lg:repeat(2, minmax(0, 1fr)); --gtc-xl:repeat(3, minmax(0, 1fr))">
		{#each filteredItems as prompt}
			<div
				style="--d:flex; --g:1rem; --cur:pointer; --w:100%; --px:0.6rem; --py:0.5rem; --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --radius:0.6rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<div style="--d:flex; --fx:1 1 0%; --g:1rem; --cur:pointer; --w:100%">
					<a href={`/workshop/prompts/edit?command=${encodeURIComponent(prompt.command)}`}>
						<div style="--fx:1 1 0%; --d:flex; --ai:center; --g:0.5rem; --as:center">
							<div style="--weight:600; --line-clamp:1; --tt:capitalize">{prompt.title}</div>
							<div style="--size:0.6rem; --of:hidden; text-overflow:ellipsis; --line-clamp:1">
								{prompt.command}
							</div>
						</div>

						<div style="--size:0.6rem; --px:0.125rem">
							<Tooltip
								content={prompt?.user?.email ?? $i18n.t('Deleted User')}
								className="flex shrink-0"
								placement="top-start"
							>
								<div style="--fs:0; --c:var(--color-gray-500)">
									{$i18n.t('By {{name}}', {
										name: capitalizeFirstLetter(
											prompt?.user?.name ?? prompt?.user?.email ?? $i18n.t('Deleted User')
										)
									})}
								</div>
							</Tooltip>
						</div>
					</a>
				</div>
				<div style="--d:flex; --fd:row; --g:0.125rem; --as:center">
					<a
						style="--as:center; --w:fit-content; --size:0.875rem; --px:0.5rem; --py:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
						type="button"
						href={`/workshop/prompts/edit?command=${encodeURIComponent(prompt.command)}`}
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
								d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
							/>
						</svg>
					</a>

					<PromptMenu
						shareHandler={() => {
							shareHandler(prompt);
						}}
						cloneHandler={() => {
							cloneHandler(prompt);
						}}
						exportHandler={() => {
							exportHandler(prompt);
						}}
						deleteHandler={async () => {
							deletePrompt = prompt;
							showDeleteConfirm = true;
						}}
						onClose={() => {}}
					>
						<button
							style="--as:center; --w:fit-content; --size:0.875rem; --p:0.375rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
							type="button"
						>
							<EllipsisHorizontal className="size-5" />
						</button>
					</PromptMenu>
				</div>
			</div>
		{/each}
	</div>

	{#if $user?.role === 'admin'}
		<div style="--d:flex; --jc:flex-end; --w:100%; --mb:0.6rem">
			<div style="--d:flex; --g:0.5rem">
				<input
					id="prompts-import-input"
					bind:this={promptsImportInputElement}
					bind:files={importFiles}
					type="file"
					accept=".json"
					hidden
					on:change={() => {
						console.log(importFiles);

						const reader = new FileReader();
						reader.onload = async (event) => {
							const savedPrompts = JSON.parse(event.target.result);
							console.log(savedPrompts);

							for (const prompt of savedPrompts) {
								await createNewPrompt(localStorage.token, {
									command:
										prompt.command.charAt(0) === '/' ? prompt.command.slice(1) : prompt.command,
									title: prompt.title,
									content: prompt.content
								}).catch((error) => {
									toast.error(`${error}`);
									return null;
								});
							}

							prompts = await getPromptList(localStorage.token);
							await _prompts.set(await getPrompts(localStorage.token));

							importFiles = [];
							promptsImportInputElement.value = '';
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					style="--d:flex; --size:0.6rem; --ai:center; --g:0.25rem; --px:0.6rem; --py:0.375rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						promptsImportInputElement.click();
					}}
				>
					<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">{$i18n.t('Import Prompts')}</div>

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

				{#if prompts.length}
					<button
						style="--d:flex; --size:0.6rem; --ai:center; --g:0.25rem; --px:0.6rem; --py:0.375rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={async () => {
							let blob = new Blob([JSON.stringify(prompts)], {
								type: 'application/json'
							});
							saveAs(blob, `prompts-export-${Date.now()}.json`);
						}}
					>
						<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
							{$i18n.t('Export Prompts')} ({prompts.length})
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
			<div style="--size:1.25rem; --weight:500; --mb:0.25rem; --line-clamp:1">
				{$i18n.t('Sage.is AI Community')}
			</div>

			<a
				style="--d:flex; --cur:pointer; --ai:center; --jc:space-between; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --w:100%; --mb:0.5rem; --px:0.875rem; --py:0.375rem; --radius:0.6rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				href="https://sage.is/community"
				target="_blank"
			>
				<div style="--as:center">
					<div style="--weight:600; --line-clamp:1">{$i18n.t('Discover your next prompt')}</div>
					<div style="--size:0.875rem; --line-clamp:1">
						{$i18n.t('Discover, download, and explore custom prompts')}
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
