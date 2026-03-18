<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import heic2any from 'heic2any';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { downloadPdf } from '$lib/utils/notes';

	const i18n = getContext('i18n');

	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';

	import dayjs, { loadLocale } from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(calendar);
	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { compressImage, copyToClipboard, splitStream } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { uploadFile } from '$lib/apis/files';
	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';

	import { config, models, settings, showSidebar, socket, user, WEBUI_NAME } from '$lib/stores';

	import NotePanel from '$lib/components/notes/NotePanel.svelte';

	import Controls from './NoteEditor/Controls.svelte';
	import Chat from './NoteEditor/Chat.svelte';

	import AccessControlModal from '$lib/components/workshop/common/AccessControlModal.svelte';

	// Assuming $i18n.languages is an array of language codes
	$: loadLocale($i18n.languages);

	import { deleteNoteById, getNoteById, updateNoteById } from '$lib/apis/notes';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Spinner from '../common/Spinner.svelte';
	import MicSolid from '../icons/MicSolid.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';

	import Calendar from '../icons/Calendar.svelte';
	import Users from '../icons/Users.svelte';

	import Image from '../common/Image.svelte';
	import FileItem from '../common/FileItem.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import RecordMenu from './RecordMenu.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import SparklesSolid from '../icons/SparklesSolid.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Bars3BottomLeft from '../icons/Bars3BottomLeft.svelte';
	import ArrowUturnLeft from '../icons/ArrowUturnLeft.svelte';
	import ArrowUturnRight from '../icons/ArrowUturnRight.svelte';
	import Sidebar from '../common/Sidebar.svelte';
	import ArrowRight from '../icons/ArrowRight.svelte';
	import Cog6 from '../icons/Cog6.svelte';
	import AiMenu from './AIMenu.svelte';
	import AdjustmentsHorizontalOutline from '../icons/AdjustmentsHorizontalOutline.svelte';

	export let id: null | string = null;

	let editor = null;
	let note = null;
	let title = '';

	const newNote = {
		title: '',
		data: {
			content: {
				json: null,
				html: '',
				md: ''
			},
			versions: [],
			files: null
		},
		// pages: [], // TODO: Implement pages for notes to allow users to create multiple pages in a note
		meta: null,
		access_control: {}
	};

	let files = [];
	let messages = [];

	let wordCount = 0;
	let charCount = 0;

	let versionIdx = null;
	let selectedModelId = null;

	let recording = false;
	let displayMediaRecord = false;

	let showPanel = false;
	let selectedPanel = 'chat';

	let selectedContent = null;

	let showDeleteConfirm = false;
	let showAccessControlModal = false;

	let titleInputFocused = false;
	let titleGenerating = false;

	let dragged = false;
	let loading = false;

	let editing = false;
	let streaming = false;

	let stopResponseFlag = false;

	let inputElement = null;

	const init = async () => {
		loading = true;
		const res = await getNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		messages = [];

		if (res) {
			note = res;
			title = res.title || '';
			files = res.data.files || [];
		} else {
			goto('/');
			return;
		}

		loading = false;
	};

	let debounceTimeout: NodeJS.Timeout | null = null;

	const saveNote = async () => {
		const titleToSave = title === '' ? $i18n.t('Untitled') : title;
		note.title = titleToSave;
		await updateNoteById(localStorage.token, id, {
			title: titleToSave,
			data: {
				files: files
			},
			access_control: note?.access_control
		}).catch((e) => {
			toast.error(`${e}`);
		});
	};

	const changeDebounceHandler = () => {
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(saveNote, 500);
	};

	$: if (id) {
		init();
	}

	function areContentsEqual(a, b) {
		return JSON.stringify(a) === JSON.stringify(b);
	}

	function insertNoteVersion(note) {
		const current = {
			json: note.data.content.json,
			html: note.data.content.html,
			md: note.data.content.md
		};
		const lastVersion = note.data.versions?.at(-1);

		if (!lastVersion || !areContentsEqual(lastVersion, current)) {
			note.data.versions = (note.data.versions ?? []).concat(current);
			return true;
		}
		return false;
	}

	const onEdited = async () => {
		if (!editor) return;
		editor.commands.setContent(note.data.content.html);
	};

	const generateTitleHandler = async () => {
		const content = note.data.content.md;
		const DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE = `### Task:
Generate a concise, 3-5 word title with an emoji summarizing the content in the content's primary language.
### Guidelines:
- The title should clearly represent the main theme or subject of the content.
- Use emojis that enhance understanding of the topic, but avoid quotation marks or special formatting.
- Write the title in the content's primary language.
- Prioritize accuracy over excessive creativity; keep it clear and simple.
- Your entire response must consist solely of the JSON object, without any introductory or concluding text.
- The output must be a single, raw JSON object, without any markdown code fences or other encapsulating text.
- Ensure no conversational text, affirmations, or explanations precede or follow the raw JSON output, as this will cause direct parsing failure.
### Output:
JSON format: { "title": "your concise title here" }
### Examples:
- { "title": "📉 Stock Market Trends" },
- { "title": "🍪 Perfect Chocolate Chip Recipe" },
- { "title": "Evolution of Music Streaming" },
- { "title": "Remote Work Productivity Tips" },
- { "title": "Artificial Intelligence in Healthcare" },
- { "title": "🎮 Video Game Development Insights" }
### Content:
<content>
${content}
</content>`;

		const oldTitle = title;
		title = '';
		titleGenerating = true;

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				model: selectedModelId,
				stream: false,
				messages: [
					{
						role: 'user',
						content: DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE
					}
				]
			},
			`${WEBUI_BASE_URL}/api`
		);
		if (res) {
			// Step 1: Safely extract the response string
			const response = res?.choices[0]?.message?.content ?? '';

			try {
				const jsonStartIndex = response.indexOf('{');
				const jsonEndIndex = response.lastIndexOf('}');

				if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
					const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);
					const parsed = JSON.parse(jsonResponse);

					if (parsed && parsed.title) {
						title = parsed.title.trim();
					}
				}
			} catch (e) {
				console.error('Error parsing JSON response:', e);
				toast.error($i18n.t('Failed to generate title'));
			}
		}

		if (!title) {
			title = oldTitle;
		}
		note.title = title;

		titleGenerating = false;
		await tick();
		changeDebounceHandler();
	};

	async function enhanceNoteHandler() {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models
			.filter((model) => model.id === selectedModelId && !(model?.info?.meta?.hidden ?? false))
			.find((model) => model.id === selectedModelId);

		if (!model) {
			selectedModelId = '';
			return;
		}

		editing = true;
		await enhanceCompletionHandler(model);
		editing = false;

		onEdited();
		versionIdx = null;
	}

	const stopResponseHandler = async () => {
		stopResponseFlag = true;
		console.log('stopResponse', stopResponseFlag);
	};

	function setContentByVersion(versionIdx) {
		if (!note.data.versions?.length) return;
		let idx = versionIdx;

		if (idx === null) idx = note.data.versions.length - 1; // latest
		const v = note.data.versions[idx];

		note.data.content.json = v.json;
		note.data.content.html = v.html;
		note.data.content.md = v.md;

		if (versionIdx === null) {
			const lastVersion = note.data.versions.at(-1);
			const currentContent = note.data.content;

			if (areContentsEqual(lastVersion, currentContent)) {
				// remove the last version
				note.data.versions = note.data.versions.slice(0, -1);
			}
		}
	}

	// Navigation
	function versionNavigateHandler(direction) {
		if (!note.data.versions || note.data.versions.length === 0) return;

		if (versionIdx === null) {
			// Get latest snapshots
			const lastVersion = note.data.versions.at(-1);
			const currentContent = note.data.content;

			if (!areContentsEqual(lastVersion, currentContent)) {
				// If the current content is different from the last version, insert a new version
				insertNoteVersion(note);
				versionIdx = note.data.versions.length - 1;
			} else {
				versionIdx = note.data.versions.length;
			}
		}

		if (direction === 'prev') {
			if (versionIdx > 0) versionIdx -= 1;
		} else if (direction === 'next') {
			if (versionIdx < note.data.versions.length - 1) versionIdx += 1;
			else versionIdx = null; // Reset to latest

			if (versionIdx === note.data.versions.length - 1) {
				// If we reach the latest version, reset to null
				versionIdx = null;
			}
		}

		setContentByVersion(versionIdx);
	}

	const uploadFileHandler = async (file) => {
		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		files = [...files, fileItem];

		// open the settings panel if it is not open
		selectedPanel = 'settings';

		if (!showPanel) {
			showPanel = true;
		}

		try {
			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			// During the file upload, file content is automatically extracted.
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (uploadedFile) {
				console.log('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
				}

				fileItem.status = 'uploaded';
				fileItem.file = uploadedFile;
				fileItem.id = uploadedFile.id;
				fileItem.collection_name =
					uploadedFile?.meta?.collection_name || uploadedFile?.collection_name;

				fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

				files = files;
			} else {
				files = files.filter((item) => item?.itemId !== tempItemId);
			}
		} catch (e) {
			toast.error(`${e}`);
			files = files.filter((item) => item?.itemId !== tempItemId);
		}

		if (files.length > 0) {
			note.data.files = files;
		} else {
			note.data.files = null;
		}

		editor.storage.files = files;

		changeDebounceHandler();

		return fileItem;
	};

	const compressImageHandler = async (imageUrl, settings = {}, config = {}) => {
		// Quick shortcut so we don’t do unnecessary work.
		const settingsCompression = settings?.imageCompression ?? false;
		const configWidth = config?.file?.image_compression?.width ?? null;
		const configHeight = config?.file?.image_compression?.height ?? null;

		// If neither settings nor config wants compression, return original URL.
		if (!settingsCompression && !configWidth && !configHeight) {
			return imageUrl;
		}

		// Default to null (no compression unless set)
		let width = null;
		let height = null;

		// If user/settings want compression, pick their preferred size.
		if (settingsCompression) {
			width = settings?.imageCompressionSize?.width ?? null;
			height = settings?.imageCompressionSize?.height ?? null;
		}

		// Apply config limits as an upper bound if any
		if (configWidth && (width === null || width > configWidth)) {
			width = configWidth;
		}
		if (configHeight && (height === null || height > configHeight)) {
			height = configHeight;
		}

		// Do the compression if required
		if (width || height) {
			return await compressImage(imageUrl, width, height);
		}
		return imageUrl;
	};

	const inputFileHandler = async (file) => {
		console.log('Processing file:', {
			name: file.name,
			type: file.type,
			size: file.size,
			extension: file.name.split('.').at(-1)
		});

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

		if (file['type'].startsWith('image/')) {
			const uploadImagePromise = new Promise(async (resolve, reject) => {
				let reader = new FileReader();
				reader.onload = async (event) => {
					try {
						let imageUrl = event.target.result;
						imageUrl = await compressImageHandler(imageUrl, $settings, $config);

						const fileId = uuidv4();
						const fileItem = {
							id: fileId,
							type: 'image',
							url: `${imageUrl}`
						};
						files = [...files, fileItem];
						note.data.files = files;
						editor.storage.files = files;

						changeDebounceHandler();
						resolve(fileItem);
					} catch (err) {
						reject(err);
					}
				};

				reader.readAsDataURL(
					file['type'] === 'image/heic'
						? await heic2any({ blob: file, toType: 'image/jpeg' })
						: file
				);
			});

			return await uploadImagePromise;
		} else {
			return await uploadFileHandler(file);
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);
		inputFiles.forEach(async (file) => {
			await inputFileHandler(file);
		});
	};

	const downloadHandler = async (type) => {
		console.log('downloadHandler', type);
		if (type === 'txt') {
			const blob = new Blob([note.data.content.md], { type: 'text/plain' });
			saveAs(blob, `${title}.txt`);
		} else if (type === 'md') {
			const blob = new Blob([note.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${title}.md`);
		} else if (type === 'pdf') {
			await downloadPdf(note);
		}
	};

	const deleteNoteHandler = async (id) => {
		const res = await deleteNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Note deleted successfully'));
			goto('/notes');
		} else {
			toast.error($i18n.t('Failed to delete note'));
		}
	};

	const scrollToBottom = () => {
		const element = document.getElementById('note-content-container');

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const enhanceCompletionHandler = async (model) => {
		stopResponseFlag = false;
		let enhancedContent = {
			json: null,
			html: '',
			md: ''
		};

		const systemPrompt = `Enhance existing notes using additional context provided from audio transcription or uploaded file content in the content's primary language. Your task is to make the notes more useful and comprehensive by incorporating relevant information from the provided context.

Input will be provided within <notes> and <context> XML tags, providing a structure for the existing notes and context respectively.

# Output Format

Provide the enhanced notes in markdown format. Use markdown syntax for headings, lists, task lists ([ ]) where tasks or checklists are strongly implied, and emphasis to improve clarity and presentation. Ensure that all integrated content from the context is accurately reflected. Return only the markdown formatted note.
`;

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					{
						role: 'system',
						content: systemPrompt
					},
					{
						role: 'user',
						content:
							`<notes>${note.data.content.md}</notes>` +
							(files && files.length > 0
								? `\n<context>${files.map((file) => `${file.name}: ${file?.file?.data?.content ?? 'Could not extract content'}\n`).join('')}</context>`
								: '')
					}
				]
			},
			`${WEBUI_BASE_URL}/api`
		);

		await tick();

		streaming = true;

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
					}

					editing = false;
					streaming = false;
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								console.log(line);
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if (data.choices && data.choices.length > 0) {
									const choice = data.choices[0];
									if (choice.delta && choice.delta.content) {
										enhancedContent.md += choice.delta.content;
										enhancedContent.html = marked.parse(enhancedContent.md);

										note.data.content.md = enhancedContent.md;
										note.data.content.html = enhancedContent.html;
										note.data.content.json = null;

										scrollToBottom();
									}
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}
			}
		}

		streaming = false;
	};

	const onDragOver = (e) => {
		e.preventDefault();

		if (
			e.dataTransfer?.types?.includes('text/plain') ||
			e.dataTransfer?.types?.includes('text/html')
		) {
			dragged = false;
			return;
		}

		// Check if the dragged item is a file or image
		if (e.dataTransfer?.types?.includes('Files') && e.dataTransfer?.items) {
			const items = Array.from(e.dataTransfer.items);
			const hasFiles = items.some((item) => item.kind === 'file');
			const hasImages = items.some((item) => item.type.startsWith('image/'));

			if (hasFiles && !hasImages) {
				dragged = true;
			} else {
				dragged = false;
			}
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

	const insertHandler = (content) => {
		insertNoteVersion(note);
		inputElement?.insertContent(content);
	};

	const noteEventHandler = async (_note) => {
		console.log('noteEventHandler', _note);
		if (_note.id !== id) return;

		if (
			_note.access_control &&
			JSON.stringify(_note.access_control) !== JSON.stringify(note.access_control)
		) {
			note.access_control = _note.access_control;
		}

		if (
			_note.data &&
			_note.data.files &&
			JSON.stringify(_note.data.files) !== JSON.stringify(files)
		) {
			files = _note.data.files;
			note.data.files = files;
		}

		// Skip title update while user is editing
		if (_note.title && !titleInputFocused) {
			title = _note.title;
			note.title = _note.title;
		}

		editor.storage.files = files;
		await tick();

		for (const file of files) {
			if (file.type === 'image') {
				const e = new CustomEvent('data', { files: files });

				const img = document.getElementById(`image:${file.id}`);
				if (img) {
					img.dispatchEvent(e);
				}
			}
		}
	};

	onMount(async () => {
		await tick();
		$socket?.emit('join-note', {
			note_id: id,
			auth: {
				token: localStorage.token
			}
		});
		$socket?.on('note-events', noteEventHandler);

		if ($settings?.models) {
			selectedModelId = $settings?.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config?.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}

		if (selectedModelId) {
			const model = $models
				.filter((model) => model.id === selectedModelId && !(model?.info?.meta?.hidden ?? false))
				.find((model) => model.id === selectedModelId);

			if (!model) {
				selectedModelId = '';
			}
		}

		if (!selectedModelId) {
			selectedModelId = $models.at(0)?.id || '';
		}

		const dropzoneElement = document.getElementById('note-editor');

		// dropzoneElement?.addEventListener('dragover', onDragOver);
		// dropzoneElement?.addEventListener('drop', onDrop);
		// dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		console.log('destroy');
		$socket?.off('note-events', noteEventHandler);

		const dropzoneElement = document.getElementById('note-editor');

		if (dropzoneElement) {
			// dropzoneElement?.removeEventListener('dragover', onDragOver);
			// dropzoneElement?.removeEventListener('drop', onDrop);
			// dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<svelte:head>
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if note}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessControl={note.access_control}
		accessRoles={['read', 'write']}
		onChange={() => {
			changeDebounceHandler();
		}}
	/>
{/if}

<FilesOverlay show={dragged} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete note?')}
	on:confirm={() => {
		deleteNoteHandler(note.id);
		showDeleteConfirm = false;
	}}
>
	<div style="--size:0.8rem; --c:var(--color-gray-500)">
		{$i18n.t('This will delete')} <span style="--weight:600">{title}</span>.
	</div>
</DeleteConfirmDialog>

<PaneGroup direction="horizontal" style="--w:100%; --h:100%">
	<Pane
		defaultSize={70}
		minSize={30}
		style="--h:100%; --d:flex; --fd:column; --w:100%; --pos:relative"
	>
		<div
			style="--pos:relative; --fx:1 1 0%; --w:100%; --h:100%; --d:flex; --jc:center; --pt:11px"
			id="note-editor"
		>
			{#if loading}
				<div style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --d:flex">
					<div style="--m:auto">
						<Spinner className="size-5" />
					</div>
				</div>
			{:else}
				<div style="--w:100%; --d:flex; --fd:column" class={loading ? 'opacity-20' : ''}>
					<div
						style="--fs:0; --w:100%; --d:flex; --jc:space-between; --ai:center; --px:0.8rem; --mb:0.4rem"
						id="note-header"
					>
						<div style="--w:100%; --d:flex; --ai:center">
							<div
								style="--d:flex; --fx:none; --ai:center; --pr:0.2rem; --translatex:-0.2rem; {$showSidebar
									? '--d:none'
									: ''}"
								class={$showSidebar ? 'md:hidden pl-0.5' : ''}
							>
								<button
									id="sidebar-toggle-button"
									style="--cur:pointer; --p:0.4rem; --d:flex; --radius:0.6rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									on:click={() => {
										showSidebar.set(!$showSidebar);
									}}
									aria-label="Toggle Sidebar"
								>
									<div style="--m:auto; --as:center">
										<MenuLines />
									</div>
								</button>
							</div>

							<input
								id="note-title-input"
								style="--w:100%; --size:1.5rem; --weight:500; --bgc:transparent; --oe:none; --b:none"
								type="text"
								bind:value={title}
								placeholder={titleGenerating ? $i18n.t('Generating...') : $i18n.t('Title')}
								disabled={(note?.user_id !== $user?.id && $user?.role !== 'admin') ||
									titleGenerating}
								required
								on:focus={() => {
									titleInputFocused = true;
								}}
								on:blur={async (e) => {
									// Don't blur if clicking the generate button
									if (e.relatedTarget?.id === 'generate-title-button') return;
									await saveNote();
									titleInputFocused = false;
								}}
							/>

							<div
								style="--d:flex; 
									--as:center; 
									--ai:center; 
									--g:0.4rem; 
									--pl:0.5rem; 
								{titleInputFocused && !titleGenerating ? '' : '--d:none; --pe:none; --w:0; --overflow:hidden'}"
							>
								<Tooltip content={$i18n.t('Generate')}>
									<button
										style="--as:center; --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										id="generate-title-button"
										on:click={(e) => {
											e.preventDefault();
											e.stopImmediatePropagation();
											e.stopPropagation();

											generateTitleHandler();
											titleInputFocused = false;
										}}
									>
										<Sparkles strokeWidth="2" />
									</button>
								</Tooltip>
							</div>

							<div
								style="--d:flex; --ai:center; --g:0.125rem; --translatex:0.2rem"
								id="note-controls"
							>
								{#if editor}
									<div>
										<div
											style="--d:flex; --ai:center; --g:0.125rem; --as:center; --minw:fit-content"
											dir="ltr"
										>
											<button
												style="--as:center; --p:0.2rem; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
												class="hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
												on:click={() => {
													editor.chain().focus().undo().run();
													// versionNavigateHandler('prev');
												}}
												disabled={!editor.can().undo()}
											>
												<ArrowUturnLeft className="size-4" />
											</button>

											<button
												style="--as:center; --p:0.2rem; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
												class="hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
												on:click={() => {
													editor.chain().focus().redo().run();
													// versionNavigateHandler('next');
												}}
												disabled={!editor.can().redo()}
											>
												<ArrowUturnRight className="size-4" />
											</button>
										</div>
									</div>
								{/if}

								<Tooltip placement="top" content={$i18n.t('Chat')} className="cursor-pointer">
									<button
										style="--p:0.4rem; --bgc:transparent; --hvr-bgc:rgb(255 255 255 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
										on:click={() => {
											if (showPanel && selectedPanel === 'chat') {
												showPanel = false;
											} else {
												if (!showPanel) {
													showPanel = true;
												}
												selectedPanel = 'chat';
											}
										}}
									>
										<ChatBubbleOval />
									</button>
								</Tooltip>

								<Tooltip placement="top" content={$i18n.t('Controls')} className="cursor-pointer">
									<button
										style="--p:0.4rem; --bgc:transparent; --hvr-bgc:rgb(255 255 255 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
										on:click={() => {
											if (showPanel && selectedPanel === 'settings') {
												showPanel = false;
											} else {
												if (!showPanel) {
													showPanel = true;
												}
												selectedPanel = 'settings';
											}
										}}
									>
										<AdjustmentsHorizontalOutline />
									</button>
								</Tooltip>

								<NoteMenu
									onDownload={(type) => {
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
									onCopyToClipboard={async () => {
										const res = await copyToClipboard(
											note.data.content.md,
											note.data.content.html,
											true
										).catch((error) => {
											toast.error(`${error}`);
											return null;
										});

										if (res) {
											toast.success($i18n.t('Copied to clipboard'));
										}
									}}
									onDelete={() => {
										showDeleteConfirm = true;
									}}
								>
									<div
										style="--p:0.2rem; --bgc:transparent; --hvr-bgc:rgb(255 255 255 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
									>
										<EllipsisHorizontal className="size-5" />
									</div>
								</NoteMenu>
							</div>
						</div>
					</div>

					<div style="--px:0.625rem" id="note-meta-info">
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
								style="--d:flex; --g:0.2rem; --ai:center; --size:0.6rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-500); --w:fit-content"
							>
								<button
									style="--d:flex; --ai:center; --g:0.2rem; --w:fit-content; --py:0.2rem; --px:0.4rem; --radius:0.5rem; --minw:fit-content"
								>
									<Calendar className="size-3.5" strokeWidth="2" />

									<!-- check for same date, yesterday, last week, and other -->

									{#if dayjs(note.created_at / 1000000).isSame(dayjs(), 'day')}
										<span
											>{dayjs(note.created_at / 1000000).format($i18n.t('[Today at] h:mm A'))}</span
										>
									{:else if dayjs(note.created_at / 1000000).isSame(dayjs().subtract(1, 'day'), 'day')}
										<span
											>{dayjs(note.created_at / 1000000).format(
												$i18n.t('[Yesterday at] h:mm A')
											)}</span
										>
									{:else if dayjs(note.created_at / 1000000).isSame(dayjs().subtract(1, 'week'), 'week')}
										<span
											>{dayjs(note.created_at / 1000000).format(
												$i18n.t('[Last] dddd [at] h:mm A')
											)}</span
										>
									{:else}
										<span>{dayjs(note.created_at / 1000000).format($i18n.t('DD/MM/YYYY'))}</span>
									{/if}
								</button>

								<button
									style="--d:flex; --ai:center; --g:0.2rem; --w:fit-content; --py:0.2rem; --px:0.4rem; --radius:0.5rem; --minw:fit-content"
									on:click={() => {
										showAccessControlModal = true;
									}}
									disabled={note?.user_id !== $user?.id && $user?.role !== 'admin'}
								>
									<Users className="size-3.5" strokeWidth="2" />

									<span> {note?.access_control ? $i18n.t('Private') : $i18n.t('Everyone')} </span>
								</button>

								{#if editor}
									<div style="--d:flex; --ai:center; --g:0.2rem; --px:0.2rem; --minw:fit-content">
										<div>
											{$i18n.t('{{COUNT}} words', {
												COUNT: wordCount
											})}
										</div>
										<div>
											{$i18n.t('{{COUNT}} characters', {
												COUNT: charCount
											})}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>

					<div
						style="--fx:1 1 0%; --w:100%; --h:100%; --of:auto; --px:0.8rem; --pb:5rem; --pos:relative; --pt:0.625rem"
						id="note-content-container"
					>
						{#if editing}
							<div
								style="--w:100%; --h:100%; --pos:fixed; --top:0; --left:0; --d:flex; --ai:center; --jc:center; --z:10; --cur:not-allowed"
								class={streaming ? '' : ' backdrop-blur-xs  bg-white/10 dark:bg-gray-900/10'}
							></div>
						{/if}

						<RichTextInput
							bind:this={inputElement}
							bind:editor
							id={`note-${note.id}`}
							className="input-prose-sm px-0.5"
							json={true}
							bind:value={note.data.content.json}
							html={note.data?.content?.html}
							documentId={`note:${note.id}`}
							collaboration={true}
							socket={$socket}
							user={$user}
							link={true}
							image={true}
							{files}
							placeholder={$i18n.t('Write something...')}
							editable={versionIdx === null && !editing}
							onSelectionUpdate={({ editor }) => {
								const { from, to } = editor.state.selection;
								const selectedText = editor.state.doc.textBetween(from, to, ' ');

								if (selectedText.length === 0) {
									selectedContent = null;
								} else {
									selectedContent = {
										text: selectedText,
										from: from,
										to: to
									};
								}
							}}
							onChange={(content) => {
								note.data.content.html = content.html;
								note.data.content.md = content.md;

								if (editor) {
									wordCount = editor.storage.characterCount.words();
									charCount = editor.storage.characterCount.characters();
								}
							}}
							fileHandler={true}
							onFileDrop={(currentEditor, files, pos) => {
								files.forEach(async (file) => {
									const fileItem = await inputFileHandler(file).catch((error) => {
										return null;
									});

									if (fileItem.type === 'image') {
										// If the file is an image, insert it directly
										currentEditor
											.chain()
											.insertContentAt(pos, {
												type: 'image',
												attrs: {
													src: `data://${fileItem.id}`
												}
											})
											.focus()
											.run();
									}
								});
							}}
							onFilePaste={() => {}}
							on:paste={async (e) => {
								e = e.detail.event || e;
								const clipboardData = e.clipboardData || window.clipboardData;
								console.log('Clipboard data:', clipboardData);

								if (clipboardData && clipboardData.items) {
									console.log('Clipboard data items:', clipboardData.items);
									for (const item of clipboardData.items) {
										console.log('Clipboard item:', item);
										if (item.type.indexOf('image') !== -1) {
											const blob = item.getAsFile();
											const fileItem = await inputFileHandler(blob);

											if (editor) {
												editor
													?.chain()
													.insertContentAt(editor.state.selection.$anchor.pos, {
														type: 'image',
														attrs: {
															src: `data://${fileItem.id}` // Use data URI for the image
														}
													})
													.focus()
													.run();
											}
										} else if (item?.kind === 'file') {
											const file = item.getAsFile();
											await inputFileHandler(file);
											e.preventDefault();
										}
									}
								}
							}}
						/>
					</div>
				</div>
			{/if}
		</div>
		<div
			style="--pos:absolute; --z:20; --bottom:0; --right:0; --p:0.8rem; --maxw:100%; --w:100%; --d:flex"
			id="note-bottom-bar"
		>
			<div style="--d:flex; --g:0.2rem; --w:100%; --minw:100%; --jc:space-between">
				{#if recording}
					<div style="--fx:1 1 0%; --w:100%">
						<VoiceRecording
							bind:recording
							className="p-1 w-full max-w-full"
							transcribe={false}
							displayMedia={displayMediaRecord}
							echoCancellation={false}
							noiseSuppression={false}
							onCancel={() => {
								recording = false;
								displayMediaRecord = false;
							}}
							onConfirm={(data) => {
								if (data?.file) {
									uploadFileHandler(data?.file);
								}

								recording = false;
								displayMediaRecord = false;
							}}
						/>
					</div>
				{:else}
					<RecordMenu
						onRecord={async () => {
							displayMediaRecord = false;

							try {
								let stream = await navigator.mediaDevices
									.getUserMedia({ audio: true })
									.catch(function (err) {
										toast.error(
											$i18n.t(`Permission denied when accessing microphone: {{error}}`, {
												error: err
											})
										);
										return null;
									});

								if (stream) {
									recording = true;
									const tracks = stream.getTracks();
									tracks.forEach((track) => track.stop());
								}
								stream = null;
							} catch {
								toast.error($i18n.t('Permission denied when accessing microphone'));
							}
						}}
						onCaptureAudio={async () => {
							displayMediaRecord = true;

							recording = true;
						}}
						onUpload={async () => {
							const input = document.createElement('input');
							input.type = 'file';
							input.accept = 'audio/*';
							input.multiple = false;
							input.click();

							input.onchange = async (e) => {
								const files = e.target.files;

								if (files && files.length > 0) {
									await uploadFileHandler(files[0]);
								}
							};
						}}
					>
						<Tooltip content={$i18n.t('Record')} placement="top">
							<div
								style="--cur:pointer; --p:0.625rem; --d:flex; --radius:9999px;  --bc:var(--color-gray-50); --bgc:#fff; --dark-bs:none; --dark-bgc:var(--color-gray-850); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --shadow:5"
							>
								<MicSolid className="size-4.5" />
							</div>
						</Tooltip>
					</RecordMenu>

					<div
						style="--cur:pointer; --d:flex; --g:0.125rem; --radius:9999px;  --bc:var(--color-gray-50); --dark-bc:var(--color-gray-850); --dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --shadow:5"
					>
						<Tooltip content={$i18n.t('AI')} placement="top">
							{#if editing}
								<button
									style="--p:0.5rem; --d:flex; --jc:center; --ai:center; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --fs:0"
									on:click={() => {
										stopResponseHandler();
									}}
									type="button"
								>
									<Spinner className="size-5" />
								</button>
							{:else}
								<AiMenu
									onEdit={() => {
										enhanceNoteHandler();
									}}
									onChat={() => {
										showPanel = true;
										selectedPanel = 'chat';
									}}
								>
									<div
										style="--cur:pointer; --p:0.625rem; --d:flex; --radius:9999px;  --bc:var(--color-gray-50); --bgc:#fff; --dark-bs:none; --dark-bgc:var(--color-gray-850); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --shadow:5"
									>
										<SparklesSolid />
									</div>
								</AiMenu>
							{/if}
						</Tooltip>
					</div>
				{/if}
			</div>
		</div>
	</Pane>
	<NotePanel bind:show={showPanel}>
		{#if selectedPanel === 'chat'}
			<Chat
				bind:show={showPanel}
				bind:selectedModelId
				bind:messages
				bind:note
				bind:editing
				bind:streaming
				bind:stopResponseFlag
				{editor}
				{inputElement}
				{selectedContent}
				{files}
				onInsert={insertHandler}
				onStop={stopResponseHandler}
				{onEdited}
				insertNoteHandler={() => {
					insertNoteVersion(note);
				}}
				scrollToBottomHandler={scrollToBottom}
			/>
		{:else if selectedPanel === 'settings'}
			<Controls
				bind:show={showPanel}
				bind:selectedModelId
				bind:files
				onUpdate={() => {
					changeDebounceHandler();
				}}
			/>
		{/if}
	</NotePanel>
</PaneGroup>
