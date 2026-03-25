<script lang="ts">
	import Fuse from 'fuse.js';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { onMount, getContext, onDestroy, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		mobile,
		showSidebar,
		knowledge as _knowledge,
		config,
		user,
		settings
	} from '$lib/stores';

	import {
		updateFileDataContentById,
		uploadFile,
		deleteFileById,
		getFileById
	} from '$lib/apis/files';
	import {
		addFileToKnowledgeById,
		getKnowledgeById,
		getKnowledgeBases,
		removeFileFromKnowledgeById,
		resetKnowledgeById,
		updateFileFromKnowledgeById,
		updateKnowledgeById
	} from '$lib/apis/knowledge';
	import { blobToFile } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Files from './KnowledgeBase/Files.svelte';
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';

	import AddContentMenu from './KnowledgeBase/AddContentMenu.svelte';
	import AddTextContentModal from './KnowledgeBase/AddTextContentModal.svelte';

	import SyncConfirmDialog from '../../common/ConfirmDialog.svelte';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	let largeScreen = true;

	let pane;
	let showSidepanel = true;
	let minSize = 0;

	type Knowledge = {
		id: string;
		name: string;
		description: string;
		data: {
			file_ids: string[];
		};
		files: any[];
	};

	let id = null;
	let knowledge: Knowledge | null = null;
	let query = '';

	let showAddTextContentModal = false;
	let showSyncConfirmModal = false;
	let showAccessControlModal = false;

	let inputFiles = null;

	let filteredItems = [];
	$: if (knowledge && knowledge.files) {
		fuse = new Fuse(knowledge.files, {
			keys: ['meta.name', 'meta.description']
		});
	}

	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: (knowledge?.files ?? []);
	}

	let selectedFile = null;
	let selectedFileId = null;
	let selectedFileContent = '';

	// Add cache object
	let fileContentCache = new Map();

	$: if (selectedFileId) {
		const file = (knowledge?.files ?? []).find((file) => file.id === selectedFileId);
		if (file) {
			fileSelectHandler(file);
		} else {
			selectedFile = null;
		}
	} else {
		selectedFile = null;
	}

	let fuse = null;
	let debounceTimeout = null;
	let mediaQuery;
	let dragged = false;
	let ingestionMode = 'plain'; // 'plain' or 'ai_parsed'

	const createFileFromText = (name, content) => {
		const blob = new Blob([content], { type: 'text/plain' });
		const file = blobToFile(blob, `${name}.txt`);

		console.log(file);
		return file;
	};

	const uploadFileHandler = async (file) => {
		console.log(file);

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: '',
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		if (
			($config?.file?.max_size ?? null) !== null &&
			file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
		) {
			console.log('File exceeds max size limit:', {
				fileSize: file.size,
				maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
			});
			toast.error(
				$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
					maxSize: $config?.file?.max_size
				})
			);
			return;
		}

		knowledge.files = [...(knowledge.files ?? []), fileItem];

		try {
			// Build upload metadata
			let metadata: Record<string, any> = {};

			// If the file is an audio file, provide the language for STT.
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata.language = $settings?.audio?.stt?.language;
			}

			// Pass ingestion mode for AI parsing
			if (ingestionMode && ingestionMode !== 'plain') {
				metadata.ingestion_mode = ingestionMode;
			}

			const uploadedFile = await uploadFile(localStorage.token, file, Object.keys(metadata).length > 0 ? metadata : null).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (uploadedFile) {
				console.log(uploadedFile);
				knowledge.files = knowledge.files.map((item) => {
					if (item.itemId === tempItemId) {
						item.id = uploadedFile.id;
					}

					// Remove temporary item id
					delete item.itemId;
					return item;
				});
				await addFileHandler(uploadedFile.id);
			} else {
				toast.error($i18n.t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const uploadDirectoryHandler = async () => {
		// Check if File System Access API is supported
		const isFileSystemAccessSupported = 'showDirectoryPicker' in window;

		try {
			if (isFileSystemAccessSupported) {
				// Modern browsers (Chrome, Edge) implementation
				await handleModernBrowserUpload();
			} else {
				// Firefox fallback
				await handleFirefoxUpload();
			}
		} catch (error) {
			handleUploadError(error);
		}
	};

	// Helper function to check if a path contains hidden folders
	const hasHiddenFolder = (path) => {
		return path.split('/').some((part) => part.startsWith('.'));
	};

	// Modern browsers implementation using File System Access API
	const handleModernBrowserUpload = async () => {
		const dirHandle = await window.showDirectoryPicker();
		let totalFiles = 0;
		let uploadedFiles = 0;

		// Function to update the UI with the progress
		const updateProgress = () => {
			const percentage = (uploadedFiles / totalFiles) * 100;
			toast.info(`Upload Progress: ${uploadedFiles}/${totalFiles} (${percentage.toFixed(2)}%)`);
		};

		// Recursive function to count all files excluding hidden ones
		async function countFiles(dirHandle) {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				if (entry.kind === 'file') {
					totalFiles++;
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await countFiles(entry);
					}
				}
			}
		}

		// Recursive function to process directories excluding hidden files and folders
		async function processDirectory(dirHandle, path = '') {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				const entryPath = path ? `${path}/${entry.name}` : entry.name;

				// Skip if the path contains any hidden folders
				if (hasHiddenFolder(entryPath)) continue;

				if (entry.kind === 'file') {
					const file = await entry.getFile();
					const fileWithPath = new File([file], entryPath, { type: file.type });

					await uploadFileHandler(fileWithPath);
					uploadedFiles++;
					updateProgress();
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await processDirectory(entry, entryPath);
					}
				}
			}
		}

		await countFiles(dirHandle);
		updateProgress();

		if (totalFiles > 0) {
			await processDirectory(dirHandle);
		} else {
			console.log('No files to upload.');
		}
	};

	// Firefox fallback implementation using traditional file input
	const handleFirefoxUpload = async () => {
		return new Promise((resolve, reject) => {
			// Create hidden file input
			const input = document.createElement('input');
			input.type = 'file';
			input.webkitdirectory = true;
			input.directory = true;
			input.multiple = true;
			input.style.display = 'none';

			// Add input to DOM temporarily
			document.body.appendChild(input);

			input.onchange = async () => {
				try {
					const files = Array.from(input.files)
						// Filter out files from hidden folders
						.filter((file) => !hasHiddenFolder(file.webkitRelativePath));

					let totalFiles = files.length;
					let uploadedFiles = 0;

					// Function to update the UI with the progress
					const updateProgress = () => {
						const percentage = (uploadedFiles / totalFiles) * 100;
						toast.info(
							`Upload Progress: ${uploadedFiles}/${totalFiles} (${percentage.toFixed(2)}%)`
						);
					};

					updateProgress();

					// Process all files
					for (const file of files) {
						// Skip hidden files (additional check)
						if (!file.name.startsWith('.')) {
							const relativePath = file.webkitRelativePath || file.name;
							const fileWithPath = new File([file], relativePath, { type: file.type });

							await uploadFileHandler(fileWithPath);
							uploadedFiles++;
							updateProgress();
						}
					}

					// Clean up
					document.body.removeChild(input);
					resolve();
				} catch (error) {
					reject(error);
				}
			};

			input.onerror = (error) => {
				document.body.removeChild(input);
				reject(error);
			};

			// Trigger file picker
			input.click();
		});
	};

	// Error handler
	const handleUploadError = (error) => {
		if (error.name === 'AbortError') {
			toast.info('Directory selection was cancelled');
		} else {
			toast.error('Error accessing directory');
			console.error('Directory access error:', error);
		}
	};

	// Helper function to maintain file paths within zip
	const syncDirectoryHandler = async () => {
		if ((knowledge?.files ?? []).length > 0) {
			const res = await resetKnowledgeById(localStorage.token, id).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				knowledge = res;
				toast.success($i18n.t('Knowledge reset successfully.'));

				// Upload directory
				uploadDirectoryHandler();
			}
		} else {
			uploadDirectoryHandler();
		}
	};

	const addFileHandler = async (fileId) => {
		const updatedKnowledge = await addFileToKnowledgeById(localStorage.token, id, fileId).catch(
			(e) => {
				toast.error(`${e}`);
				return null;
			}
		);

		if (updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File added successfully.'));
		} else {
			toast.error($i18n.t('Failed to add file.'));
			knowledge.files = knowledge.files.filter((file) => file.id !== fileId);
		}
	};

	const deleteFileHandler = async (fileId) => {
		try {
			console.log('Starting file deletion process for:', fileId);

			// Remove from knowledge base only
			const updatedKnowledge = await removeFileFromKnowledgeById(localStorage.token, id, fileId);

			console.log('Knowledge base updated:', updatedKnowledge);

			if (updatedKnowledge) {
				knowledge = updatedKnowledge;
				toast.success($i18n.t('File removed successfully.'));
			}
		} catch (e) {
			console.error('Error in deleteFileHandler:', e);
			toast.error(`${e}`);
		}
	};

	const updateFileContentHandler = async () => {
		const fileId = selectedFile.id;
		const content = selectedFileContent;

		// Clear the cache for this file since we're updating it
		fileContentCache.delete(fileId);

		const res = updateFileDataContentById(localStorage.token, fileId, content).catch((e) => {
			toast.error(`${e}`);
		});

		const updatedKnowledge = await updateFileFromKnowledgeById(
			localStorage.token,
			id,
			fileId
		).catch((e) => {
			toast.error(`${e}`);
		});

		if (res && updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File content updated successfully.'));
		}
	};

	const changeDebounceHandler = () => {
		console.log('debounce');
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(async () => {
			if (knowledge.name.trim() === '' || knowledge.description.trim() === '') {
				toast.error($i18n.t('Please fill in all fields.'));
				return;
			}

			const res = await updateKnowledgeById(localStorage.token, id, {
				...knowledge,
				name: knowledge.name,
				description: knowledge.description,
				access_control: knowledge.access_control
			}).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				toast.success($i18n.t('Knowledge updated successfully'));
				_knowledge.set(await getKnowledgeBases(localStorage.token));
			}
		}, 1000);
	};

	const handleMediaQuery = async (e) => {
		if (e.matches) {
			largeScreen = true;
		} else {
			largeScreen = false;
		}
	};

	const fileSelectHandler = async (file) => {
		try {
			selectedFile = file;

			// Check cache first
			if (fileContentCache.has(file.id)) {
				selectedFileContent = fileContentCache.get(file.id);
				return;
			}

			const response = await getFileById(localStorage.token, file.id);
			if (response) {
				selectedFileContent = response.data.content;
				// Cache the content
				fileContentCache.set(file.id, response.data.content);
			} else {
				toast.error($i18n.t('No content found in file.'));
			}
		} catch (e) {
			toast.error($i18n.t('Failed to load file content.'));
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
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
		dragged = false;

		if (e.dataTransfer?.types?.includes('Files')) {
			if (e.dataTransfer?.files) {
				const inputFiles = e.dataTransfer?.files;

				if (inputFiles && inputFiles.length > 0) {
					for (const file of inputFiles) {
						await uploadFileHandler(file);
					}
				} else {
					toast.error($i18n.t(`File not found.`));
				}
			}
		}
	};

	onMount(async () => {
		// listen to resize 1024px
		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		// Select the container element you want to observe
		const container = document.getElementById('collection-container');

		// initialize the minSize based on the container width
		minSize = !largeScreen ? 100 : Math.floor((300 / container.clientWidth) * 100);

		// Create a new ResizeObserver instance
		const resizeObserver = new ResizeObserver((entries) => {
			for (let entry of entries) {
				const width = entry.contentRect.width;
				// calculate the percentage of 300
				const percentage = (300 / width) * 100;
				// set the minSize to the percentage, must be an integer
				minSize = !largeScreen ? 100 : Math.floor(percentage);

				if (showSidepanel) {
					if (pane && pane.isExpanded() && pane.getSize() < minSize) {
						pane.resize(minSize);
					}
				}
			}
		});

		// Start observing the container's size changes
		resizeObserver.observe(container);

		if (pane) {
			pane.expand();
		}

		id = $page.params.id;

		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			knowledge = res;
		} else {
			goto('/workshop/knowledge');
		}

		const dropZone = document.querySelector('body');
		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		mediaQuery?.removeEventListener('change', handleMediaQuery);
		const dropZone = document.querySelector('body');
		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

{#if dragged}
	<div
		style="--pos:fixed; --w:100%; --h:100%; --d:flex; --z:50; touch-action:none; --pe:none"
	class="{$showSidebar
			? 'left-0 md:left-[260px] md:w-[calc(100%-260px)]'
			: 'left-0'}"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
	>
		<div style="--pos:absolute; --w:100%; --h:100%; backdrop-filter:blur(4px); --bgc:rgb(51 51 51 / 0.4); --d:flex; --jc:center">
			<div style="--m:auto; --pt:16rem; --d:flex; --fd:column; --jc:center">
				<div style="--maxw:28rem">
					<AddFilesPlaceholder>
						<div style="--mt:0.5rem; --ta:center; --size:0.8rem; --dark-c:var(--color-gray-200); --w:100%">
							Drop any files here to add to my documents
						</div>
					</AddFilesPlaceholder>
				</div>
			</div>
		</div>
	</div>
{/if}

<SyncConfirmDialog
	bind:show={showSyncConfirmModal}
	message={$i18n.t(
		'This will reset the knowledge base and sync all files. Do you wish to continue?'
	)}
	on:confirm={() => {
		syncDirectoryHandler();
	}}
/>

<AddTextContentModal
	bind:show={showAddTextContentModal}
	on:submit={(e) => {
		const file = createFileFromText(e.detail.name, e.detail.content);
		uploadFileHandler(file);
	}}
/>

<input
	id="files-input"
	bind:files={inputFiles}
	type="file"
	multiple
	hidden
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			for (const file of inputFiles) {
				await uploadFileHandler(file);
			}

			inputFiles = null;
			const fileInputElement = document.getElementById('files-input');

			if (fileInputElement) {
				fileInputElement.value = '';
			}
		} else {
			toast.error($i18n.t(`File not found.`));
		}
	}}
/>

<div style="--d:flex; --fd:column; --w:100%; --translatey:0.2rem" id="collection-container">
	{#if id && knowledge}
		<AccessControlModal
			bind:show={showAccessControlModal}
			bind:accessControl={knowledge.access_control}
			allowPublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
			onChange={() => {
				changeDebounceHandler();
			}}
			accessRoles={['read', 'write']}
		/>
		<div style="--w:100%; --mb:0.625rem">
			<div style="--d:flex; --w:100%">
				<div style="--fx:1 1 0%">
					<div style="--d:flex; --ai:center; --jc:space-between; --w:100%; --px:0.125rem; --mb:0.2rem">
						<div style="--w:100%">
							<input
								type="text"
								style="--ta:left; --w:100%; --weight:600; --size:1.5rem; --bgc:transparent; --oe:none"
	class="font-primary"
								bind:value={knowledge.name}
								placeholder="Knowledge Name"
								on:input={() => {
									changeDebounceHandler();
								}}
							/>
						</div>

						<div style="--as:center; --fs:0">
							<button
								style="--bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --c:#000; --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --px:0.5rem; --py:0.2rem; --radius:9999px; --d:flex; --g:0.2rem; --ai:center"
								type="button"
								on:click={() => {
									showAccessControlModal = true;
								}}
							>
								<LockClosed strokeWidth="2.5" className="size-3.5" />

								<div style="--size:0.8rem; --weight:500; --fs:0">
									{$i18n.t('Access')}
								</div>
							</button>
						</div>
					</div>

					<div style="--d:flex; --w:100%; --px:0.2rem">
						<input
							type="text"
							style="--ta:left; --size:0.6rem; --w:100%; --c:var(--color-gray-500); --bgc:transparent; --oe:none"
							bind:value={knowledge.description}
							placeholder="Knowledge Description"
							on:input={() => {
								changeDebounceHandler();
							}}
						/>
					</div>
				</div>
			</div>
		</div>

		<div style="--d:flex; --fd:row; --fx:1 1 0%; --h:100%; --maxh:100%; --pb:0.625rem; --g:0.6rem">
			{#if largeScreen}
				<div style="--fx:1 1 0%; --d:flex; --jc:flex-start; --w:100%; --h:100%; --maxh:100%">
					{#if selectedFile}
						<div style="--d:flex; --fd:column; --w:100%; --h:100%; --maxh:100%">
							<div style="--fs:0; --mb:0.5rem; --d:flex; --ai:center">
								{#if !showSidepanel}
									<div style="--translatex:-0.5rem">
										<button
											style="--w:100%; --ta:left; --size:0.8rem; --p:0.4rem; --radius:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:var(--color-gray-850)"
											on:click={() => {
												pane.expand();
											}}
										>
											<ChevronLeft strokeWidth="2.5" />
										</button>
									</div>
								{/if}

								<div style="--fx:1 1 0%; --size:1.2rem; --weight:500">
									<a
										style="--hvr-c:var(--color-gray-500); --hvr-dark-c:var(--color-gray-100); --hvr-td:underline; --fg:1; --line-clamp:1"
										href={selectedFile.id ? `/api/v1/files/${selectedFile.id}/content` : '#'}
										target="_blank"
									>
										{decodeString(selectedFile?.meta?.name)}
									</a>
								</div>

								<div>
									<button
										style="--as:center; --w:fit-content; --size:0.8rem; --py:0.2rem; --px:0.625rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem"
										on:click={() => {
											updateFileContentHandler();
										}}
									>
										{$i18n.t('Save')}
									</button>
								</div>
							</div>

							<div
								style="--fx:1 1 0%; --w:100%; --h:100%; --maxh:100%; --size:0.8rem; --bgc:transparent; --oe:none; --ofy:auto"
	class="scrollbar-hidden"
							>
								{#key selectedFile.id}
									<RichTextInput
										className="input-prose-sm"
										bind:value={selectedFileContent}
										placeholder={$i18n.t('Add content here')}
										preserveBreaks={false}
									/>
								{/key}
							</div>
						</div>
					{:else}
						<div style="--h:100%; --d:flex; --w:100%">
							<div style="--m:auto; --size:0.6rem; --ta:center; --c:var(--color-gray-200); --dark-c:var(--color-gray-700)">
								{$i18n.t('Drag and drop a file to upload or select a file to view')}
							</div>
						</div>
					{/if}
				</div>
			{:else if !largeScreen && selectedFileId !== null}
				<Drawer
					className="h-full"
					show={selectedFileId !== null}
					onClose={() => {
						selectedFileId = null;
					}}
				>
					<div style="--d:flex; --fd:column; --jc:flex-start; --h:100%; --maxh:100%; --p:0.5rem">
						<div style="--d:flex; --fd:column; --w:100%; --h:100%; --maxh:100%">
							<div style="--fs:0; --mt:0.2rem; --mb:0.5rem; --d:flex; --ai:center">
								<div style="--mr:0.5rem">
									<button
										style="--w:100%; --ta:left; --size:0.8rem; --p:0.4rem; --radius:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:var(--color-gray-850)"
										on:click={() => {
											selectedFileId = null;
										}}
									>
										<ChevronLeft strokeWidth="2.5" />
									</button>
								</div>
								<div style="--fx:1 1 0%; --size:1.2rem; --line-clamp:1">
									{selectedFile?.meta?.name}
								</div>

								<div>
									<button
										style="--as:center; --w:fit-content; --size:0.8rem; --py:0.2rem; --px:0.625rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem"
										on:click={() => {
											updateFileContentHandler();
										}}
									>
										{$i18n.t('Save')}
									</button>
								</div>
							</div>

							<div
								style="--fx:1 1 0%; --w:100%; --h:100%; --maxh:100%; --py:0.625rem; --px:0.8rem; --radius:0.5rem; --size:0.8rem; --bgc:transparent; --ofy:auto"
	class="scrollbar-hidden"
							>
								{#key selectedFile.id}
									<RichTextInput
										className="input-prose-sm"
										bind:value={selectedFileContent}
										placeholder={$i18n.t('Add content here')}
										preserveBreaks={false}
									/>
								{/key}
							</div>
						</div>
					</div>
				</Drawer>
			{/if}

			<div
				style="--d:flex; --py:0.5rem; --radius:1rem;  --bc:var(--color-gray-50); --h:100%; --dark-bc:var(--color-gray-850)"
	class="{largeScreen ? 'shrink-0 w-72 max-w-72' : 'flex-1'}"
			>
				<div style="--d:flex; --fd:column; --w:100%; --g:0.5rem; --radius:0.5rem; --h:100%">
					<div style="--w:100%; --h:100%; --d:flex; --fd:column">
						<div style="--px:0.6rem">
							<div style="--d:flex; --mb:0.125rem">
								<div style="--as:center; --ml:0.2rem; --mr:0.6rem">
									<Search />
								</div>
								<input
									style="--w:100%; --size:0.8rem; --pr:1rem; --py:0.2rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
									bind:value={query}
									placeholder={$i18n.t('Search Collection')}
									on:focus={() => {
										selectedFileId = null;
									}}
								/>

								<div>
									<AddContentMenu
										on:upload={(e) => {
											if (e.detail.type === 'directory') {
												uploadDirectoryHandler();
											} else if (e.detail.type === 'text') {
												showAddTextContentModal = true;
											} else {
												document.getElementById('files-input').click();
											}
										}}
										on:sync={(e) => {
											showSyncConfirmModal = true;
										}}
									/>
								</div>
							</div>

							<div style="--d:flex; --ai:center; --g:0.5rem; --mt:0.4rem; --size:0.6rem; --c:var(--color-gray-500)">
								<span style="--weight:500; --ws:nowrap">{$i18n.t('Ingestion')}:</span>
								<label style="--d:flex; --ai:center; --g:0.2rem; --cursor:pointer">
									<input type="radio" bind:group={ingestionMode} value="plain" />
									<span>{$i18n.t('Plain')}</span>
								</label>
								<label style="--d:flex; --ai:center; --g:0.2rem; --cursor:pointer">
									<input type="radio" bind:group={ingestionMode} value="ai_parsed" />
									<span>{$i18n.t('AI Parse')}</span>
								</label>
							</div>
						</div>

						{#if filteredItems.length > 0}
							<div style="--d:flex; --ofy:auto; --h:100%; --w:100%; --size:0.6rem"
	class="scrollbar-hidden">
								<Files
									small
									files={filteredItems}
									{selectedFileId}
									on:click={(e) => {
										selectedFileId = selectedFileId === e.detail ? null : e.detail;
									}}
									on:delete={(e) => {
										console.log(e.detail);

										selectedFileId = null;
										deleteFileHandler(e.detail);
									}}
								/>
							</div>
						{:else}
							<div style="--my:0.6rem; --d:flex; --fd:column; --jc:center; --ta:center; --c:var(--color-gray-500); --size:0.6rem">
								<div>
									{$i18n.t('No content found')}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	{:else}
		<Spinner className="size-5" />
	{/if}
</div>
