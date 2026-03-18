<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	import Fuse from 'fuse.js';

	const { saveAs } = fileSaver;

	import dayjs, { loadLocale } from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	// Assuming $i18n.languages is an array of language codes
	$: loadLocale($i18n.languages);

	import { goto } from '$app/navigation';
	import { onMount, getContext, onDestroy } from 'svelte';
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import { createNewNote, deleteNoteById, getNotes } from '$lib/apis/notes';
	import { capitalizeFirstLetter, copyToClipboard, getTimeRange } from '$lib/utils';
	import { downloadPdf } from '$lib/utils/notes';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import { marked } from 'marked';
	import XMark from '../icons/XMark.svelte';

	const i18n = getContext('i18n');
	let loaded = false;

	let importFiles = '';
	let query = '';

	let noteItems = [];
	let fuse = null;

	let selectedNote = null;
	let notes = {};
	$: if (fuse) {
		notes = groupNotes(
			query
				? fuse.search(query).map((e) => {
						return e.item;
					})
				: noteItems
		);
	}

	let showDeleteConfirm = false;

	const groupNotes = (res) => {
		console.log(res);
		if (!Array.isArray(res)) {
			return {}; // or throw new Error("Notes response is not an array")
		}

		// Build the grouped object
		const grouped: Record<string, any[]> = {};
		for (const note of res) {
			const timeRange = getTimeRange(note.updated_at / 1000000000);
			if (!grouped[timeRange]) {
				grouped[timeRange] = [];
			}
			grouped[timeRange].push({
				...note,
				timeRange
			});
		}
		return grouped;
	};

	const init = async () => {
		noteItems = await getNotes(localStorage.token, true);

		fuse = new Fuse(noteItems, {
			keys: ['title']
		});
	};

	const createNoteHandler = async () => {
		//  $i18n.t('New Note'),
		const res = await createNewNote(localStorage.token, {
			// YYYY-MM-DD
			title: dayjs().format('YYYY-MM-DD'),
			data: {
				content: {
					json: null,
					html: '',
					md: ''
				}
			},
			meta: null,
			access_control: {}
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/notes/${res.id}`);
		}
	};

	const downloadHandler = async (type) => {
		console.log('downloadHandler', type);
		console.log('selectedNote', selectedNote);
		if (type === 'md') {
			const blob = new Blob([selectedNote.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${selectedNote.title}.md`);
		} else if (type === 'pdf') {
			await downloadPdf(selectedNote);
		}
	};

	const deleteNoteHandler = async (id) => {
		const res = await deleteNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			init();
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		// Check if all the file is a markdown file and extract name and content

		for (const file of inputFiles) {
			if (file.type !== 'text/markdown') {
				toast.error($i18n.t('Only markdown files are allowed'));
				return;
			}

			const reader = new FileReader();
			reader.onload = async (event) => {
				const content = event.target.result;
				let name = file.name.replace(/\.md$/, '');

				if (typeof content !== 'string') {
					toast.error($i18n.t('Invalid file content'));
					return;
				}

				// Create a new note with the content
				const res = await createNewNote(localStorage.token, {
					title: name,
					data: {
						content: {
							json: null,
							html: marked.parse(content ?? ''),
							md: content
						}
					},
					meta: null,
					access_control: {}
				}).catch((error) => {
					toast.error(`${error}`);
					return null;
				});

				if (res) {
					init();
				}
			};

			reader.readAsText(file);
		}
	};

	let dragged = false;

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being dragged.
		if (e.dataTransfer?.types?.includes('Files')) {
			dragged = true;
		} else {
			dragged = false;
		}
	};

	const onDragLeave = () => {
		dragged = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		console.log(e);

		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);
			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				inputFilesHandler(inputFiles);
			}
		}

		dragged = false;
	};

	onDestroy(() => {
		console.log('destroy');
		const dropzoneElement = document.getElementById('notes-container');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});

	onMount(async () => {
		await init();
		loaded = true;

		const dropzoneElement = document.getElementById('notes-container');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Notes')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<FilesOverlay show={dragged} />

<div id="notes-container" style="--w:100%; --minh:100%; --h:100%">
	{#if loaded}
		<DeleteConfirmDialog
			bind:show={showDeleteConfirm}
			title={$i18n.t('Delete note?')}
			on:confirm={() => {
				deleteNoteHandler(selectedNote.id);
				showDeleteConfirm = false;
			}}
		>
			<div style="--size:0.875rem; --c:var(--color-gray-500)">
				{$i18n.t('This will delete')} <span style="--weight:600">{selectedNote.title}</span>.
			</div>
		</DeleteConfirmDialog>

		<div style="--d:flex; --fd:column; --g:0.25rem; --px:0.875rem">
			<div style="--d:flex; --fx:1 1 0%; --ai:center; --w:100%; --g:0.5rem">
				<div style="--d:flex; --fx:1 1 0%; --ai:center">
					<div style="--as:center; --ml:0.25rem; --mr:0.6rem">
						<Search className="size-3.5" />
					</div>
					<input
						style="--w:100%; --size:0.875rem; --py:0.25rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Notes')}
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
			</div>
		</div>

		<div style="--px:1.125rem; --h:100%; --pt:0.5rem"
	class="@container">
			{#if Object.keys(notes).length > 0}
				<div style="--pb:2.5rem">
					{#each Object.keys(notes) as timeRange}
						<div style="--w:100%; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500); --weight:500; --pb:0.625rem">
							{$i18n.t(timeRange)}
						</div>

						<div
							style="--mb:1.25rem; --g:0.625rem; --d:grid; --gtc:repeat(1, minmax(0, 1fr)); --gtc-md:repeat(2, minmax(0, 1fr)); --gtc-lg:repeat(3, minmax(0, 1fr)); --gtc-xl:repeat(4, minmax(0, 1fr)); --gtc-xl:repeat(5, minmax(0, 1fr))"
						>
							{#each notes[timeRange] as note, idx (note.id)}
								<div
									style="--d:flex; --g:1rem; --cur:pointer; --w:100%; --px:1.125rem; --py:1rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --radius:0.6rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								>
									<div style="--d:flex; --fx:1 1 0%; --g:1rem; --cur:pointer; --w:100%">
										<a
											href={`/notes/${note.id}`}
											style="--w:100%; --translatey:-0.125rem; --d:flex; --fd:column; --jc:space-between"
										>
											<div style="--fx:1 1 0%">
												<div style="--d:flex; --ai:center; --g:0.5rem; --as:center; --mb:0.25rem; --jc:space-between">
													<div style="--weight:600; --line-clamp:1; --tt:capitalize">{note.title}</div>

													<div>
														<NoteMenu
															onDownload={(type) => {
																selectedNote = note;

																downloadHandler(type);
															}}
															onCopyLink={async () => {
																const baseUrl = window.location.origin;
																const res = await copyToClipboard(`${baseUrl}/notes/${note.id}`);

																if (res) {
																	toast.success($i18n.t('Copied link to clipboard'));
																} else {
																	toast.error($i18n.t('Failed to copy link'));
																}
															}}
															onDelete={() => {
																selectedNote = note;
																showDeleteConfirm = true;
															}}
														>
															<button
																style="--as:center; --w:fit-content; --size:0.875rem; --p:0.25rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
																type="button"
															>
																<EllipsisHorizontal className="size-5" />
															</button>
														</NoteMenu>
													</div>
												</div>

												<div
													style="--size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500); --mb:0.6rem; --line-clamp:3; --minh:2.5rem"
												>
													{#if note.data?.content?.md}
														{note.data?.content?.md}
													{:else}
														{$i18n.t('No content')}
													{/if}
												</div>
											</div>

											<div style="--size:0.6rem; --px:0.125rem; --w:100%; --d:flex; --jc:space-between; --ai:center">
												<div>
													{dayjs(note.updated_at / 1000000).fromNow()}
												</div>
												<Tooltip
													content={note?.user?.email ?? $i18n.t('Deleted User')}
													className="flex shrink-0"
													placement="top-start"
												>
													<div style="--fs:0; --c:var(--color-gray-500)">
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																note?.user?.name ?? note?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</div>
												</Tooltip>
											</div>
										</a>
									</div>
								</div>
							{/each}
						</div>
					{/each}
				</div>
			{:else}
				<div style="--w:100%; --h:100%; --d:flex; --fd:column; --ai:center; --jc:center">
					<div style="--pb:5rem; --ta:center">
						<div style="--size:1.25rem; --weight:500; --c:var(--color-gray-400); --dark-c:var(--color-gray-600)">
							{$i18n.t('No Notes')}
						</div>

						<div style="--mt:0.25rem; --size:0.875rem; --c:var(--color-gray-300); --dark-c:var(--color-gray-700)">
							{$i18n.t('Create your first note by clicking on the plus button below.')}
						</div>
					</div>
				</div>
			{/if}
		</div>

		<div style="--pos:absolute; --bottom:0; --left:0; --right:0; --p:1.25rem; --maxw:100%; --d:flex; --jc:flex-end">
			<div style="--d:flex; --g:0.125rem; --jc:flex-end; --w:100%">
				<Tooltip content={$i18n.t('Create Note')}>
					<button
						style="--cur:pointer; --p:0.625rem; --d:flex; --radius:9999px;  --bc:var(--color-gray-50); --bgc:#fff; --dark-bs:none; --dark-bgc:var(--color-gray-850); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --shadow:5"
						type="button"
						on:click={async () => {
							createNoteHandler();
						}}
					>
						<Plus className="size-4.5" strokeWidth="2.5" />
					</button>
				</Tooltip>

				<!-- <button
				style="--cur:pointer; --p:0.625rem; --d:flex; --radius:9999px; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --shadow:5"
			>
				<SparklesSolid className="size-4" />
			</button> -->
			</div>
		</div>

		<!-- {#if $user?.role === 'admin'}
		<div style="--d:flex; --jc:flex-end; --w:100%; --mb:0.6rem">
			<div style="--d:flex; --g:0.5rem">
				<input
					id="notes-import-input"
					bind:files={importFiles}
					type="file"
					accept=".md"
					hidden
					on:change={() => {
						console.log(importFiles);

						const reader = new FileReader();
						reader.onload = async (event) => {
							console.log(event.target.result);
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					style="--d:flex; --size:0.6rem; --ai:center; --g:0.25rem; --px:0.6rem; --py:0.375rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						const notesImportInputElement = document.getElementById('notes-import-input');
						if (notesImportInputElement) {
							notesImportInputElement.click();
						}
					}}
				>
					<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">{$i18n.t('Import Notes')}</div>

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
			</div>
		</div>
	{/if} -->
	{:else}
		<div style="--w:100%; --h:100%; --d:flex; --jc:center; --ai:center">
			<Spinner className="size-5" />
		</div>
	{/if}
</div>
