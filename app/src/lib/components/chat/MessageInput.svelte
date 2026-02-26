<script lang="ts">
	import * as pdfjs from 'pdfjs-dist';
	import * as pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs';
	pdfjs.GlobalWorkerOptions.workerSrc = import.meta.url + 'pdfjs-dist/build/pdf.worker.mjs';

	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import heic2any from 'heic2any';

	import { toast } from 'svelte-sonner';

	import { v4 as uuidv4 } from 'uuid';
	import { createPicker, getAuthToken } from '$lib/utils/google-drive-picker';
	import { pickAndDownloadFile } from '$lib/utils/onedrive-file-picker';

	import { onMount, tick, getContext, createEventDispatcher, onDestroy } from 'svelte';
	const dispatch = createEventDispatcher();

	import {
		type Model,
		mobile,
		settings,
		showSidebar,
		models,
		config,
		showCallOverlay,
		tools,
		user as _user,
		showControls,
		TTSWorker,
		temporaryChatEnabled
	} from '$lib/stores';

	import {
		blobToFile,
		compressImage,
		createMessagesList,
		extractContentFromFile,
		extractCurlyBraceWords,
		extractInputVariables,
		getCurrentDateTime,
		getFormattedDate,
		getFormattedTime,
		getUserPosition,
		getUserTimezone,
		getWeekday
	} from '$lib/utils';
	import { uploadFile } from '$lib/apis/files';
	import { generateAutoCompletion } from '$lib/apis';
	import { deleteFileById } from '$lib/apis/files';
	import { getBranding, type Branding } from '$lib/apis/configs';

	import { WEBUI_BASE_URL, WEBUI_API_BASE_URL, PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

	import InputMenu from './MessageInput/InputMenu.svelte';
	import VoiceRecording from './MessageInput/VoiceRecording.svelte';
	import FilesOverlay from './MessageInput/FilesOverlay.svelte';
	import Commands from './MessageInput/Commands.svelte';
	import ToolServersModal from './ToolServersModal.svelte';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import FileItem from '../common/FileItem.svelte';
	import Image from '../common/Image.svelte';

	import XMark from '../icons/XMark.svelte';
	import Headphone from '../icons/Headphone.svelte';
	import GlobeAlt from '../icons/GlobeAlt.svelte';
	import Photo from '../icons/Photo.svelte';
	import Wrench from '../icons/Wrench.svelte';
	import CommandLine from '../icons/CommandLine.svelte';
	import Sparkles from '../icons/Sparkles.svelte';

	import { KokoroWorker } from '$lib/workers/KokoroWorker';
	import InputVariablesModal from './MessageInput/InputVariablesModal.svelte';
	const i18n = getContext('i18n');

	export let transparentBackground = false;

	export let onChange: Function = () => {};
	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined = undefined;
	export let selectedModels: [''];

	let selectedModelIds = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	export let history;
	export let taskIds = null;

	export let prompt = '';
	export let files = [];

	export let toolServers = [];

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let imageGenerationEnabled = false;
	export let webSearchEnabled = false;
	export let codeInterpreterEnabled = false;

	let showInputVariablesModal = false;
	let inputVariables = {};
	let inputVariableValues = {};

	$: onChange({
		prompt,
		files: files
			.filter((file) => file.type !== 'image')
			.map((file) => {
				return {
					...file,
					user: undefined,
					access_control: undefined
				};
			}),
		selectedToolIds,
		selectedFilterIds,
		imageGenerationEnabled,
		webSearchEnabled,
		codeInterpreterEnabled
	});

	const inputVariableHandler = async (text: string) => {
		inputVariables = extractInputVariables(text);
		if (Object.keys(inputVariables).length > 0) {
			showInputVariablesModal = true;
		}
	};

	const textVariableHandler = async (text: string) => {
		if (text.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch((err) => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});

			const clipboardItems = await navigator.clipboard.read();

			let imageUrl = null;
			for (const item of clipboardItems) {
				// Check for known image types
				for (const type of item.types) {
					if (type.startsWith('image/')) {
						const blob = await item.getType(type);
						imageUrl = URL.createObjectURL(blob);
					}
				}
			}

			if (imageUrl) {
				files = [
					...files,
					{
						type: 'image',
						url: imageUrl
					}
				];
			}

			text = text.replaceAll('{{CLIPBOARD}}', clipboardText);
		}

		if (text.includes('{{USER_LOCATION}}')) {
			let location;
			try {
				location = await getUserPosition();
			} catch (error) {
				toast.error($i18n.t('Location access not allowed'));
				location = 'LOCATION_UNKNOWN';
			}
			text = text.replaceAll('{{USER_LOCATION}}', String(location));
		}

		if (text.includes('{{USER_NAME}}')) {
			const name = $_user?.name || 'User';
			text = text.replaceAll('{{USER_NAME}}', name);
		}

		if (text.includes('{{USER_LANGUAGE}}')) {
			const language = localStorage.getItem('locale') || 'en-US';
			text = text.replaceAll('{{USER_LANGUAGE}}', language);
		}

		if (text.includes('{{CURRENT_DATE}}')) {
			const date = getFormattedDate();
			text = text.replaceAll('{{CURRENT_DATE}}', date);
		}

		if (text.includes('{{CURRENT_TIME}}')) {
			const time = getFormattedTime();
			text = text.replaceAll('{{CURRENT_TIME}}', time);
		}

		if (text.includes('{{CURRENT_DATETIME}}')) {
			const dateTime = getCurrentDateTime();
			text = text.replaceAll('{{CURRENT_DATETIME}}', dateTime);
		}

		if (text.includes('{{CURRENT_TIMEZONE}}')) {
			const timezone = getUserTimezone();
			text = text.replaceAll('{{CURRENT_TIMEZONE}}', timezone);
		}

		if (text.includes('{{CURRENT_WEEKDAY}}')) {
			const weekday = getWeekday();
			text = text.replaceAll('{{CURRENT_WEEKDAY}}', weekday);
		}

		inputVariableHandler(text);
		return text;
	};

	const replaceVariables = (variables: Record<string, any>) => {
		console.log('Replacing variables:', variables);

		const chatInput = document.getElementById('chat-input');

		if (chatInput) {
			if ($settings?.richTextInput ?? true) {
				chatInputElement.replaceVariables(variables);
				chatInputElement.focus();
			} else {
				// Get current value from the input element
				let currentValue = chatInput.value || '';

				// Replace template variables using regex
				const updatedValue = currentValue.replace(
					/{{\s*([^|}]+)(?:\|[^}]*)?\s*}}/g,
					(match, varName) => {
						const trimmedVarName = varName.trim();
						return variables.hasOwnProperty(trimmedVarName)
							? String(variables[trimmedVarName])
							: match;
					}
				);

				// Update the input value
				chatInput.value = updatedValue;
				chatInput.focus();
				chatInput.dispatchEvent(new Event('input', { bubbles: true }));
			}
		}
	};

	export const setText = async (text?: string) => {
		const chatInput = document.getElementById('chat-input');

		if (chatInput) {
			text = await textVariableHandler(text || '');

			if ($settings?.richTextInput ?? true) {
				chatInputElement?.setText(text);
				chatInputElement?.focus();
			} else {
				chatInput.value = text;
				prompt = text;

				chatInput.focus();
				chatInput.dispatchEvent(new Event('input'));
			}
		}
	};

	const getCommand = () => {
		const getWordAtCursor = (text, cursor) => {
			if (typeof text !== 'string' || cursor == null) return '';
			const left = text.slice(0, cursor);
			const right = text.slice(cursor);
			const leftWord = left.match(/(?:^|\s)([^\s]*)$/)?.[1] || '';

			const rightWord = right.match(/^([^\s]*)/)?.[1] || '';
			return leftWord + rightWord;
		};

		const chatInput = document.getElementById('chat-input');
		let word = '';

		if (chatInput) {
			if ($settings?.richTextInput ?? true) {
				word = chatInputElement?.getWordAtDocPos();
			} else {
				const cursor = chatInput ? chatInput.selectionStart : prompt.length;
				word = getWordAtCursor(prompt, cursor);
			}
		}

		return word;
	};

	const replaceCommandWithText = (text) => {
		const getWordBoundsAtCursor = (text, cursor) => {
			let start = cursor,
				end = cursor;
			while (start > 0 && !/\s/.test(text[start - 1])) --start;
			while (end < text.length && !/\s/.test(text[end])) ++end;
			return { start, end };
		};

		const chatInput = document.getElementById('chat-input');
		if (!chatInput) return;

		if ($settings?.richTextInput ?? true) {
			chatInputElement?.replaceCommandWithText(text);
		} else {
			const cursor = chatInput.selectionStart;
			const { start, end } = getWordBoundsAtCursor(prompt, cursor);
			prompt = prompt.slice(0, start) + text + prompt.slice(end);
			chatInput.focus();
			chatInput.setSelectionRange(start + text.length, start + text.length);
		}
	};

	const insertTextAtCursor = async (text: string) => {
		const chatInput = document.getElementById('chat-input');
		if (!chatInput) return;

		text = await textVariableHandler(text);

		if (command) {
			replaceCommandWithText(text);
		} else {
			if ($settings?.richTextInput ?? true) {
				chatInputElement?.insertContent(text);
			} else {
				const cursor = chatInput.selectionStart;
				prompt = prompt.slice(0, cursor) + text + prompt.slice(cursor);
				chatInput.focus();
				chatInput.setSelectionRange(cursor + text.length, cursor + text.length);
			}
		}

		await tick();
		const chatInputContainer = document.getElementById('chat-input-container');
		if (chatInputContainer) {
			chatInputContainer.scrollTop = chatInputContainer.scrollHeight;
		}

		await tick();
		if (chatInput) {
			chatInput.focus();
			chatInput.dispatchEvent(new Event('input'));

			const words = extractCurlyBraceWords(prompt);

			if (words.length > 0) {
				const word = words.at(0);
				await tick();

				if (!($settings?.richTextInput ?? true)) {
					// Move scroll to the first word
					chatInput.setSelectionRange(word.startIndex, word.endIndex + 1);
					chatInput.focus();

					const selectionRow =
						(word?.startIndex - (word?.startIndex % chatInput.cols)) / chatInput.cols;
					const lineHeight = chatInput.clientHeight / chatInput.rows;

					chatInput.scrollTop = lineHeight * selectionRow;
				}
			} else {
				chatInput.scrollTop = chatInput.scrollHeight;
			}
		}
	};

	let command = '';

	export let showCommands = false;
	$: showCommands = ['/', '#', '@'].includes(command?.charAt(0)) || '\\#' === command?.slice(0, 2);

	let showTools = false;

	let loaded = false;
	let recording = false;

	let isComposing = false;

	let chatInputContainerElement;
	let chatInputElement;

	let filesInputElement;
	let commandsElement;

	let inputFiles;

	let dragged = false;
	let shiftKey = false;

	let user = null;
	export let placeholder = '';

	let branding: Branding | null = null;

	let visionCapableModels = [];
	$: visionCapableModels = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.vision ?? true
	);

	let fileUploadCapableModels = [];
	$: fileUploadCapableModels = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.file_upload ?? true
	);

	let webSearchCapableModels = [];
	$: webSearchCapableModels = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).filter(
		(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.web_search ?? true
	);

	let imageGenerationCapableModels = [];
	$: imageGenerationCapableModels = (
		atSelectedModel?.id ? [atSelectedModel.id] : selectedModels
	).filter(
		(model) =>
			$models.find((m) => m.id === model)?.info?.meta?.capabilities?.image_generation ?? true
	);

	let codeInterpreterCapableModels = [];
	$: codeInterpreterCapableModels = (
		atSelectedModel?.id ? [atSelectedModel.id] : selectedModels
	).filter(
		(model) =>
			$models.find((m) => m.id === model)?.info?.meta?.capabilities?.code_interpreter ?? true
	);

	let toggleFilters = [];
	$: toggleFilters = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels)
		.map((id) => ($models.find((model) => model.id === id) || {})?.filters ?? [])
		.reduce((acc, filters) => acc.filter((f1) => filters.some((f2) => f2.id === f1.id)));

	let showToolsButton = false;
	$: showToolsButton = toolServers.length + selectedToolIds.length > 0;

	let showWebSearchButton = false;
	$: showWebSearchButton =
		(atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).length ===
			webSearchCapableModels.length &&
		$config?.features?.enable_web_search &&
		($_user.role === 'admin' || $_user?.permissions?.features?.web_search);

	let showImageGenerationButton = false;
	$: showImageGenerationButton =
		(atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).length ===
			imageGenerationCapableModels.length &&
		$config?.features?.enable_image_generation &&
		($_user.role === 'admin' || $_user?.permissions?.features?.image_generation);

	let showCodeInterpreterButton = false;
	$: showCodeInterpreterButton =
		(atSelectedModel?.id ? [atSelectedModel.id] : selectedModels).length ===
			codeInterpreterCapableModels.length &&
		$config?.features?.enable_code_interpreter &&
		($_user.role === 'admin' || $_user?.permissions?.features?.code_interpreter);

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		element.scrollTo({
			top: element.scrollHeight,
			behavior: 'smooth'
		});
	};

	const screenCaptureHandler = async () => {
		try {
			// Request screen media
			const mediaStream = await navigator.mediaDevices.getDisplayMedia({
				video: { cursor: 'never' },
				audio: false
			});
			// Once the user selects a screen, temporarily create a video element
			const video = document.createElement('video');
			video.srcObject = mediaStream;
			// Ensure the video loads without affecting user experience or tab switching
			await video.play();
			// Set up the canvas to match the video dimensions
			const canvas = document.createElement('canvas');
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			// Grab a single frame from the video stream using the canvas
			const context = canvas.getContext('2d');
			context.drawImage(video, 0, 0, canvas.width, canvas.height);
			// Stop all video tracks (stop screen sharing) after capturing the image
			mediaStream.getTracks().forEach((track) => track.stop());

			// bring back focus to this current tab, so that the user can see the screen capture
			window.focus();

			// Convert the canvas to a Base64 image URL
			const imageUrl = canvas.toDataURL('image/png');
			// Add the captured image to the files array to render it
			files = [...files, { type: 'image', url: imageUrl }];
			// Clean memory: Clear video srcObject
			video.srcObject = null;
		} catch (error) {
			// Handle any errors (e.g., user cancels screen sharing)
			console.error('Error capturing screen:', error);
		}
	};

	const uploadFileHandler = async (file, fullContext: boolean = false) => {
		if ($_user?.role !== 'admin' && !($_user?.permissions?.chat?.file_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload files.'));
			return null;
		}

		if (fileUploadCapableModels.length !== selectedModels.length) {
			toast.error($i18n.t('Model(s) do not support file upload'));
			return null;
		}

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
			itemId: tempItemId,
			...(fullContext ? { context: 'full' } : {})
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		files = [...files, fileItem];

		if (!$temporaryChatEnabled) {
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
		} else {
			// If temporary chat is enabled, we just add the file to the list without uploading it.

			const content = await extractContentFromFile(file, pdfjsLib).catch((error) => {
				toast.error(
					$i18n.t('Failed to extract content from the file: {{error}}', { error: error })
				);
				return null;
			});

			if (content === null) {
				toast.error($i18n.t('Failed to extract content from the file.'));
				files = files.filter((item) => item?.itemId !== tempItemId);
				return null;
			} else {
				console.log('Extracted content from file:', {
					name: file.name,
					size: file.size,
					content: content
				});

				fileItem.status = 'uploaded';
				fileItem.type = 'text';
				fileItem.content = content;
				fileItem.id = uuidv4(); // Temporary ID for the file

				files = files;
			}
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);

		if (
			($config?.file?.max_count ?? null) !== null &&
			files.length + inputFiles.length > $config?.file?.max_count
		) {
			toast.error(
				$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
					maxCount: $config?.file?.max_count
				})
			);
			return;
		}

		inputFiles.forEach(async (file) => {
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
				if (visionCapableModels.length === 0) {
					toast.error($i18n.t('Selected model(s) do not support image inputs'));
					return;
				}

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

				let reader = new FileReader();
				reader.onload = async (event) => {
					let imageUrl = event.target.result;

					imageUrl = await compressImageHandler(imageUrl, $settings, $config);

					files = [
						...files,
						{
							type: 'image',
							url: `${imageUrl}`
						}
					];
				};
				reader.readAsDataURL(
					file['type'] === 'image/heic'
						? await heic2any({ blob: file, toType: 'image/jpeg' })
						: file
				);
			} else {
				uploadFileHandler(file);
			}
		});
	};

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

	const onKeyDown = (e) => {
		if (e.key === 'Shift') {
			shiftKey = true;
		}

		if (e.key === 'Escape') {
			console.log('Escape');
			dragged = false;
		}
	};

	const onKeyUp = (e) => {
		if (e.key === 'Shift') {
			shiftKey = false;
		}
	};

	const onFocus = () => {};

	const onBlur = () => {
		shiftKey = false;
	};

	onMount(async () => {
		loaded = true;

		// Fetch branding for fallback logo
		try {
			branding = await getBranding();
		} catch (e) {
			console.error('Failed to load branding:', e);
		}

		window.setTimeout(() => {
			const chatInput = document.getElementById('chat-input');
			chatInput?.focus();
		}, 0);

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		await tick();

		const dropzoneElement = document.getElementById('chat-container');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		console.log('destroy');
		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);

		window.removeEventListener('focus', onFocus);
		window.removeEventListener('blur', onBlur);

		const dropzoneElement = document.getElementById('chat-container');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<FilesOverlay show={dragged} />
<ToolServersModal bind:show={showTools} {selectedToolIds} />
<InputVariablesModal
	bind:show={showInputVariablesModal}
	variables={inputVariables}
	onSave={(variableValues) => {
		inputVariableValues = { ...inputVariableValues, ...variableValues };
		replaceVariables(inputVariableValues);
	}}
/>

{#if loaded}
	<div style="--w:100%"
	class="font-primary">
		<div style="--mx:auto; --left:0; --right:0; --bgc:transparent; --d:flex; --jc:center">
			<div
				style="--d:flex; --fd:column; --px:0.75rem; --w:100%"
	class="{($settings?.widescreenMode ?? null)
					? 'max-w-full'
					: 'max-w-6xl'}"
			>
				<div style="--pos:relative">
					{#if autoScroll === false && history?.currentId}
						<div
							style="--pos:absolute; --top:-3rem; --left:0; --right:0; --d:flex; --jc:center; --z:30; --pe:none"
						>
							<button
								style="--bgc:#fff; --b:1px solid; --bc:var(--color-gray-100); --dark-bs:none; --dark-bgc:rgb(255 255 255 / 0.2); --p:0.375rem; --radius:9999px; --pe:auto"
								on:click={() => {
									autoScroll = true;
									scrollToBottom();
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									style="--w:1.25rem; --h:1.25rem"
								>
									<path
										fill-rule="evenodd"
										d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						</div>
					{/if}
				</div>

				<div style="--w:100%; --pos:relative">
					{#if atSelectedModel !== undefined}
						<div
							style="--px:0.75rem; --pb:0.125rem; --pt:0.375rem; --ta:left; --w:100%; --d:flex; --fd:column; --pos:absolute; --bottom:0; --left:0; --right:0; --bgi:linear-gradient(0deg, var(--tw-gradient-stops)); --tw-gradient-from:#fff; --dark-tw-gradient-from:var(--color-gray-900); --z:10"
						>
							<div style="--d:flex; --ai:center; --jc:space-between; --w:100%">
								<div style="--pl:1px; --d:flex; --ai:center; --g:0.5rem; --size:0.875rem; --dark-c:var(--color-gray-500)">
									<img
										crossorigin="anonymous"
										alt="model profile"
										style="--w:0.875rem; --h:0.875rem; --maxw:28px; --objf:cover; --radius:9999px"
										src={$models.find((model) => model.id === atSelectedModel.id)?.info?.meta
											?.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
									/>
									<div style="--translatey:0.5px">
										Talking to <span style="--weight:500">{atSelectedModel.name}</span>
									</div>
								</div>
								<div>
									<button
										style="--d:flex; --ai:center; --dark-c:var(--color-gray-500)"
										on:click={() => {
											atSelectedModel = undefined;
										}}
									>
										<XMark />
									</button>
								</div>
							</div>
						</div>
					{/if}

					<Commands
						bind:this={commandsElement}
						bind:files
						show={showCommands}
						{command}
						insertTextHandler={insertTextAtCursor}
						onUpload={(e) => {
							const { type, data } = e;

							if (type === 'file') {
								if (files.find((f) => f.id === data.id)) {
									return;
								}
								files = [
									...files,
									{
										...data,
										status: 'processed'
									}
								];
							} else {
								dispatch('upload', e);
							}
						}}
						onSelect={(e) => {
							const { type, data } = e;

							if (type === 'model') {
								atSelectedModel = data;
							}

							document.getElementById('chat-input')?.focus();
						}}
					/>
				</div>
			</div>
		</div>

		<div class="{transparentBackground ? 'bg-transparent' : 'bg-white dark:bg-gray-900'} ">
			<div
				style="--px:0.625rem; --mx:auto; --left:0; --right:0"
	class="{($settings?.widescreenMode ?? null)
					? 'max-w-full'
					: 'max-w-6xl'}"
			>
				<div class="">
					<input
						bind:this={filesInputElement}
						bind:files={inputFiles}
						type="file"
						hidden
						multiple
						on:change={async () => {
							if (inputFiles && inputFiles.length > 0) {
								const _inputFiles = Array.from(inputFiles);
								inputFilesHandler(_inputFiles);
							} else {
								toast.error($i18n.t(`File not found.`));
							}

							filesInputElement.value = '';
						}}
					/>

					{#if recording}
						<VoiceRecording
							bind:recording
							onCancel={async () => {
								recording = false;

								await tick();
								document.getElementById('chat-input')?.focus();
							}}
							onConfirm={async (data) => {
								const { text, filename } = data;

								recording = false;

								await tick();
								insertTextAtCursor(text);

								await tick();
								document.getElementById('chat-input')?.focus();

								if ($settings?.speechAutoSend ?? false) {
									dispatch('submit', prompt);
								}
							}}
						/>
					{:else}
						<form
							style="--w:100%; --d:flex; --fd:column; --g:0.375rem"
							on:submit|preventDefault={() => {
								// check if selectedModels support image input
								dispatch('submit', prompt);
							}}
						>
							<div
								style="--fx:1 1 0%; --d:flex; --fd:column; --pos:relative; --w:100%; --shadow:4; --radius:1.5rem; --b:1px solid; --bc:var(--color-gray-50); --dark-bc:var(--color-gray-850); --hvr-bc:var(--color-gray-100); --dark-hvr-bc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --px:0.25rem; --bgc:rgb(255 255 255 / 0.9); --dark-bgc:rgb(180 180 180 / 0.05); --dark-c:var(--color-gray-100)"
	class="focus-within:border-gray-100 focus-within:dark:border-gray-800"
								dir={$settings?.chatDirection ?? 'auto'}
							>
								{#if files.length > 0}
									<div style="--mx:0.5rem; --mt:0.625rem; --mb:-0.25rem; --d:flex; --ai:center; --fw:wrap; --g:0.5rem">
										{#each files as file, fileIdx}
											{#if file.type === 'image'}
												<div style="--pos:relative"
	class="group">
													<div style="--pos:relative; --d:flex; --ai:center">
														<Image
															src={file.url}
															alt=""
															imageClassName=" size-14 rounded-xl object-cover"
														/>
														{#if atSelectedModel ? visionCapableModels.length === 0 : selectedModels.length !== visionCapableModels.length}
															<Tooltip
																className=" absolute top-1 left-1"
																content={$i18n.t('{{ models }}', {
																	models: [
																		...(atSelectedModel ? [atSelectedModel] : selectedModels)
																	]
																		.filter((id) => !visionCapableModels.includes(id))
																		.join(', ')
																})}
															>
																<svg
																	xmlns="http://www.w3.org/2000/svg"
																	viewBox="0 0 24 24"
																	fill="currentColor"
																	aria-hidden="true"
																	style="--w:1rem; --h:1rem; fill:#fde047"
																>
																	<path
																		fill-rule="evenodd"
																		d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
																		clip-rule="evenodd"
																	/>
																</svg>
															</Tooltip>
														{/if}
													</div>
													<div style="--pos:absolute; --top:-0.25rem; --right:-0.25rem">
														<button
															style="--bgc:#fff; --c:#000; --b:1px solid; --bc:#fff; --radius:9999px"
	class="{($settings?.highContrastMode ??
															false)
																? ''
																: 'outline-hidden focus:outline-hidden group-hover:visible invisible transition'}"
															type="button"
															aria-label={$i18n.t('Remove file')}
															on:click={() => {
																files.splice(fileIdx, 1);
																files = files;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 20 20"
																fill="currentColor"
																aria-hidden="true"
																style="--w:1rem; --h:1rem"
															>
																<path
																	d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
																/>
															</svg>
														</button>
													</div>
												</div>
											{:else}
												<FileItem
													item={file}
													name={file.name}
													type={file.type}
													size={file?.size}
													loading={file.status === 'uploading'}
													dismissible={true}
													edit={true}
													modal={['file', 'collection'].includes(file?.type)}
													on:dismiss={async () => {
														// Remove from UI state
														files.splice(fileIdx, 1);
														files = files;
													}}
													on:click={() => {
														console.log(file);
													}}
												/>
											{/if}
										{/each}
									</div>
								{/if}

								<div style="--px:0.625rem">
									{#if $settings?.richTextInput ?? true}
										<div
											style="--bgc:transparent; --dark-c:var(--color-gray-100); --oe:none; --w:100%; --pt:0.625rem; --pb:5px; --px:0.25rem; resize:none; --h:fit-content; --maxh:20rem; --of:auto"
	class="scrollbar-hidden rtl:text-right ltr:text-left"
											id="chat-input-container"
										>
											<RichTextInput
												bind:this={chatInputElement}
												id="chat-input"
												onChange={(e) => {
													prompt = e.md;
													command = getCommand();
												}}
												json={true}
												messageInput={true}
												showFormattingButtons={false}
												insertPromptAsRichText={$settings?.insertPromptAsRichText ?? false}
												shiftEnter={!($settings?.ctrlEnterToSend ?? false) &&
													(!$mobile ||
														!(
															'ontouchstart' in window ||
															navigator.maxTouchPoints > 0 ||
															navigator.msMaxTouchPoints > 0
														))}
												placeholder={placeholder ? placeholder : $i18n.t('Send a Message')}
												largeTextAsFile={($settings?.largeTextAsFile ?? false) && !shiftKey}
												autocomplete={$config?.features?.enable_autocomplete_generation &&
													($settings?.promptAutocomplete ?? false)}
												generateAutoCompletion={async (text) => {
													if (selectedModelIds.length === 0 || !selectedModelIds.at(0)) {
														toast.error($i18n.t('Please select a model first.'));
													}

													const res = await generateAutoCompletion(
														localStorage.token,
														selectedModelIds.at(0),
														text,
														history?.currentId
															? createMessagesList(history, history.currentId)
															: null
													).catch((error) => {
														console.log(error);

														return null;
													});

													console.log(res);
													return res;
												}}
												oncompositionstart={() => (isComposing = true)}
												oncompositionend={() => (isComposing = false)}
												on:keydown={async (e) => {
													e = e.detail.event;

													const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac
													const commandsContainerElement =
														document.getElementById('commands-container');

													if (e.key === 'Escape') {
														stopResponse();
													}

													// Command/Ctrl + Shift + Enter to submit a message pair
													if (isCtrlPressed && e.key === 'Enter' && e.shiftKey) {
														e.preventDefault();
														createMessagePair(prompt);
													}

													// Check if Ctrl + R is pressed
													if (prompt === '' && isCtrlPressed && e.key.toLowerCase() === 'r') {
														e.preventDefault();
														console.log('regenerate');

														const regenerateButton = [
															...document.getElementsByClassName('regenerate-response-button')
														]?.at(-1);

														regenerateButton?.click();
													}

													if (prompt === '' && e.key == 'ArrowUp') {
														e.preventDefault();

														const userMessageElement = [
															...document.getElementsByClassName('user-message')
														]?.at(-1);

														if (userMessageElement) {
															userMessageElement.scrollIntoView({ block: 'center' });
															const editButton = [
																...document.getElementsByClassName('edit-user-message-button')
															]?.at(-1);

															editButton?.click();
														}
													}

													if (commandsContainerElement) {
														if (commandsContainerElement && e.key === 'ArrowUp') {
															e.preventDefault();
															commandsElement.selectUp();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);
															commandOptionButton.scrollIntoView({ block: 'center' });
														}

														if (commandsContainerElement && e.key === 'ArrowDown') {
															e.preventDefault();
															commandsElement.selectDown();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);
															commandOptionButton.scrollIntoView({ block: 'center' });
														}

														if (commandsContainerElement && e.key === 'Tab') {
															e.preventDefault();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);

															commandOptionButton?.click();
														}

														if (commandsContainerElement && e.key === 'Enter') {
															e.preventDefault();

															const commandOptionButton = [
																...document.getElementsByClassName('selected-command-option-button')
															]?.at(-1);

															if (commandOptionButton) {
																commandOptionButton?.click();
															} else {
																document.getElementById('send-message-button')?.click();
															}
														}
													} else {
														if (
															!$mobile ||
															!(
																'ontouchstart' in window ||
																navigator.maxTouchPoints > 0 ||
																navigator.msMaxTouchPoints > 0
															)
														) {
															if (isComposing) {
																return;
															}

															// Uses keyCode '13' for Enter key for chinese/japanese keyboards.
															//
															// Depending on the user's settings, it will send the message
															// either when Enter is pressed or when Ctrl+Enter is pressed.
															const enterPressed =
																($settings?.ctrlEnterToSend ?? false)
																	? (e.key === 'Enter' || e.keyCode === 13) && isCtrlPressed
																	: (e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey;

															if (enterPressed) {
																e.preventDefault();
																if (prompt !== '' || files.length > 0) {
																	dispatch('submit', prompt);
																}
															}
														}
													}

													if (e.key === 'Escape') {
														console.log('Escape');
														atSelectedModel = undefined;
														selectedToolIds = [];
														selectedFilterIds = [];

														webSearchEnabled = false;
														imageGenerationEnabled = false;
														codeInterpreterEnabled = false;
													}
												}}
												on:paste={async (e) => {
													e = e.detail.event;
													console.log(e);

													const clipboardData = e.clipboardData || window.clipboardData;

													if (clipboardData && clipboardData.items) {
														for (const item of clipboardData.items) {
															if (item.type.indexOf('image') !== -1) {
																const blob = item.getAsFile();
																const reader = new FileReader();

																reader.onload = function (e) {
																	files = [
																		...files,
																		{
																			type: 'image',
																			url: `${e.target.result}`
																		}
																	];
																};

																reader.readAsDataURL(blob);
															} else if (item?.kind === 'file') {
																const file = item.getAsFile();
																if (file) {
																	const _files = [file];
																	await inputFilesHandler(_files);
																	e.preventDefault();
																}
															} else if (item.type === 'text/plain') {
																if (($settings?.largeTextAsFile ?? false) && !shiftKey) {
																	const text = clipboardData.getData('text/plain');

																	if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
																		e.preventDefault();
																		const blob = new Blob([text], { type: 'text/plain' });
																		const file = new File([blob], `Pasted_Text_${Date.now()}.txt`, {
																			type: 'text/plain'
																		});

																		await uploadFileHandler(file, true);
																	}
																}
															}
														}
													}
												}}
											/>
										</div>
									{:else}
										<textarea
											id="chat-input"
											dir={$settings?.chatDirection ?? 'auto'}
											bind:this={chatInputElement}
											style="--bgc:transparent; --dark-c:var(--color-gray-200); --oe:none; --w:100%; --pt:0.75rem; --px:0.25rem; resize:none"
	class="scrollbar-hidden"
											placeholder={placeholder ? placeholder : $i18n.t('Send a Message')}
											bind:value={prompt}
											on:input={() => {
												command = getCommand();
											}}
											on:click={() => {
												command = getCommand();
											}}
											on:compositionstart={() => (isComposing = true)}
											on:compositionend={() => (isComposing = false)}
											on:keydown={async (e) => {
												const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac

												const commandsContainerElement =
													document.getElementById('commands-container');

												if (e.key === 'Escape') {
													stopResponse();
												}

												// Command/Ctrl + Shift + Enter to submit a message pair
												if (isCtrlPressed && e.key === 'Enter' && e.shiftKey) {
													e.preventDefault();
													createMessagePair(prompt);
												}

												// Check if Ctrl + R is pressed
												if (prompt === '' && isCtrlPressed && e.key.toLowerCase() === 'r') {
													e.preventDefault();
													console.log('regenerate');

													const regenerateButton = [
														...document.getElementsByClassName('regenerate-response-button')
													]?.at(-1);

													regenerateButton?.click();
												}

												if (prompt === '' && e.key == 'ArrowUp') {
													e.preventDefault();

													const userMessageElement = [
														...document.getElementsByClassName('user-message')
													]?.at(-1);

													const editButton = [
														...document.getElementsByClassName('edit-user-message-button')
													]?.at(-1);

													console.log(userMessageElement);

													userMessageElement?.scrollIntoView({ block: 'center' });
													editButton?.click();
												}

												if (commandsContainerElement) {
													if (commandsContainerElement && e.key === 'ArrowUp') {
														e.preventDefault();
														commandsElement.selectUp();

														const container = document.getElementById('command-options-container');
														const commandOptionButton = [
															...document.getElementsByClassName('selected-command-option-button')
														]?.at(-1);

														if (commandOptionButton && container) {
															const elTop = commandOptionButton.offsetTop;
															const elHeight = commandOptionButton.offsetHeight;
															const containerHeight = container.clientHeight;

															// Center the selected button in the container
															container.scrollTop = elTop - containerHeight / 2 + elHeight / 2;
														}
													}

													if (commandsContainerElement && e.key === 'ArrowDown') {
														e.preventDefault();
														commandsElement.selectDown();

														const container = document.getElementById('command-options-container');
														const commandOptionButton = [
															...document.getElementsByClassName('selected-command-option-button')
														]?.at(-1);

														if (commandOptionButton && container) {
															const elTop = commandOptionButton.offsetTop;
															const elHeight = commandOptionButton.offsetHeight;
															const containerHeight = container.clientHeight;

															// Center the selected button in the container
															container.scrollTop = elTop - containerHeight / 2 + elHeight / 2;
														}
													}

													if (commandsContainerElement && e.key === 'Enter') {
														e.preventDefault();

														const commandOptionButton = [
															...document.getElementsByClassName('selected-command-option-button')
														]?.at(-1);

														if (e.shiftKey) {
															prompt = `${prompt}\n`;
														} else if (commandOptionButton) {
															commandOptionButton?.click();
														} else {
															document.getElementById('send-message-button')?.click();
														}
													}

													if (commandsContainerElement && e.key === 'Tab') {
														e.preventDefault();

														const commandOptionButton = [
															...document.getElementsByClassName('selected-command-option-button')
														]?.at(-1);

														commandOptionButton?.click();
													}
												} else {
													if (
														!$mobile ||
														!(
															'ontouchstart' in window ||
															navigator.maxTouchPoints > 0 ||
															navigator.msMaxTouchPoints > 0
														)
													) {
														if (isComposing) {
															return;
														}

														// Prevent Enter key from creating a new line
														const isCtrlPressed = e.ctrlKey || e.metaKey;
														const enterPressed =
															($settings?.ctrlEnterToSend ?? false)
																? (e.key === 'Enter' || e.keyCode === 13) && isCtrlPressed
																: (e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey;

														if (enterPressed) {
															e.preventDefault();
														}

														// Submit the prompt when Enter key is pressed
														if ((prompt !== '' || files.length > 0) && enterPressed) {
															dispatch('submit', prompt);
														}
													}
												}

												if (e.key === 'Tab') {
													const words = extractCurlyBraceWords(prompt);

													if (words.length > 0) {
														const word = words.at(0);

														if (word && e.target instanceof HTMLTextAreaElement) {
															// Prevent default tab behavior
															e.preventDefault();
															e.target.setSelectionRange(word?.startIndex, word.endIndex + 1);
															e.target.focus();

															const selectionRow =
																(word?.startIndex - (word?.startIndex % e.target.cols)) /
																e.target.cols;
															const lineHeight = e.target.clientHeight / e.target.rows;

															e.target.scrollTop = lineHeight * selectionRow;
														}
													}

													e.target.style.height = '';
													e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
												}

												if (e.key === 'Escape') {
													console.log('Escape');
													atSelectedModel = undefined;
													selectedToolIds = [];
													selectedFilterIds = [];
													webSearchEnabled = false;
													imageGenerationEnabled = false;
													codeInterpreterEnabled = false;
												}
											}}
											rows="1"
											on:input={async (e) => {
												e.target.style.height = '';
												e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
											}}
											on:focus={async (e) => {
												e.target.style.height = '';
												e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
											}}
											on:paste={async (e) => {
												const clipboardData = e.clipboardData || window.clipboardData;

												if (clipboardData && clipboardData.items) {
													for (const item of clipboardData.items) {
														console.log(item);
														if (item.type.indexOf('image') !== -1) {
															const blob = item.getAsFile();
															const reader = new FileReader();

															reader.onload = function (e) {
																files = [
																	...files,
																	{
																		type: 'image',
																		url: `${e.target.result}`
																	}
																];
															};

															reader.readAsDataURL(blob);
														} else if (item?.kind === 'file') {
															const file = item.getAsFile();
															if (file) {
																const _files = [file];
																await inputFilesHandler(_files);
																e.preventDefault();
															}
														} else if (item.type === 'text/plain') {
															if (($settings?.largeTextAsFile ?? false) && !shiftKey) {
																const text = clipboardData.getData('text/plain');

																if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
																	e.preventDefault();
																	const blob = new Blob([text], { type: 'text/plain' });
																	const file = new File([blob], `Pasted_Text_${Date.now()}.txt`, {
																		type: 'text/plain'
																	});

																	await uploadFileHandler(file, true);
																}
															}
														}
													}
												}
											}}
										/>
									{/if}
								</div>

								<div style="--d:flex; --jc:space-between; --mt:0.125rem; --mb:0.625rem; --mx:0.125rem; --maxw:100%" dir="ltr">
									<div style="--ml:0.25rem; --as:flex-end; --d:flex; --ai:center; --fx:1 1 0%; --maxw:80%">
										<InputMenu
											bind:selectedToolIds
											selectedModels={atSelectedModel ? [atSelectedModel.id] : selectedModels}
											{fileUploadCapableModels}
											{screenCaptureHandler}
											{inputFilesHandler}
											uploadFilesHandler={() => {
												filesInputElement.click();
											}}
											uploadGoogleDriveHandler={async () => {
												try {
													const fileData = await createPicker();
													if (fileData) {
														const file = new File([fileData.blob], fileData.name, {
															type: fileData.blob.type
														});
														await uploadFileHandler(file);
													} else {
														console.log('No file was selected from Google Drive');
													}
												} catch (error) {
													console.error('Google Drive Error:', error);
													toast.error(
														$i18n.t('Error accessing Google Drive: {{error}}', {
															error: error.message
														})
													);
												}
											}}
											uploadOneDriveHandler={async (authorityType) => {
												try {
													const fileData = await pickAndDownloadFile(authorityType);
													if (fileData) {
														const file = new File([fileData.blob], fileData.name, {
															type: fileData.blob.type || 'application/octet-stream'
														});
														await uploadFileHandler(file);
													} else {
														console.log('No file was selected from OneDrive');
													}
												} catch (error) {
													console.error('OneDrive Error:', error);
												}
											}}
											onClose={async () => {
												await tick();

												const chatInput = document.getElementById('chat-input');
												chatInput?.focus();
											}}
										>
											<div
												style="--bgc:transparent; --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-800); --dark-c:#fff; --hvr-dark-bgc:var(--color-gray-800); --radius:9999px; --p:0.375rem; --oe:none"
	class="focus:outline-hidden"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													aria-hidden="true"
													fill="currentColor"
													style="--w:1.25rem; --h:1.25rem"
												>
													<path
														d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
													/>
												</svg>
											</div>
										</InputMenu>

										{#if $_user && (showToolsButton || (toggleFilters && toggleFilters.length > 0) || showWebSearchButton || showImageGenerationButton || showCodeInterpreterButton)}
											<div
												style="--d:flex; --as:center; --w:1px; --h:1rem; --mx:0.375rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800)"
											/>

											<div style="--d:flex; --g:0.25rem; --ai:center; --ofx:auto; --fx:1 1 0%"
	class="scrollbar-none">
												{#if showToolsButton}
													<Tooltip
														content={$i18n.t('{{COUNT}} Available Tools', {
															COUNT: toolServers.length + selectedToolIds.length
														})}
													>
														<button
															style="--translatey:0.5px; --d:flex; --g:0.25rem; --ai:center; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); --hvr-c:var(--color-gray-700); --hvr-dark-c:var(--color-gray-200); --radius:0.5rem; --p:0.25rem; --as:center; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
															aria-label="Available Tools"
															type="button"
															on:click={() => {
																showTools = !showTools;
															}}
														>
															<Wrench className="size-4" strokeWidth="1.75" />

															<span style="--size:0.875rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)">
																{toolServers.length + selectedToolIds.length}
															</span>
														</button>
													</Tooltip>
												{/if}

												{#each toggleFilters as filter, filterIdx (filter.id)}
													<Tooltip content={filter?.description} placement="top">
														<button
															on:click|preventDefault={() => {
																if (selectedFilterIds.includes(filter.id)) {
																	selectedFilterIds = selectedFilterIds.filter(
																		(id) => id !== filter.id
																	);
																} else {
																	selectedFilterIds = [...selectedFilterIds, filter.id];
																}
															}}
															type="button"
															style="--px:0.5rem; --py:0.5rem; --d:flex; --g:0.375rem; --ai:center; --size:0.875rem; --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:300ms; --maxw:100%; --of:hidden; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tt:capitalize"
	class="@xl:px-2.5 focus:outline-hidden {selectedFilterIds.includes(
																filter.id
															)
																? 'text-sky-500 dark:text-sky-300 bg-sky-50 dark:bg-sky-200/5'
																: 'bg-transparent text-gray-600 dark:text-gray-300  '}"
														>
															{#if filter?.icon}
																<div style="--w:1rem; --h:1rem; --ai:center; --d:flex; --jc:center">
																	<img
																		src={filter.icon}
																		class="{filter.icon.includes('svg')
																			? 'dark:invert-[80%]'
																			: ''}"
																		style="--w:0.875rem; --h:0.875rem; fill: currentColor;"
																		alt={filter.name}
																	/>
																</div>
															{:else}
																<Sparkles className="size-4" strokeWidth="1.75" />
															{/if}
															<span
																style="--d:none; --ws:nowrap; --of:hidden; text-overflow:ellipsis; --lh:1; --pr:0.125rem"
	class="@xl:block"
																>{filter?.name}</span
															>
														</button>
													</Tooltip>
												{/each}

												{#if showWebSearchButton}
													<Tooltip content={$i18n.t('Search the internet')} placement="top">
														<button
															on:click|preventDefault={() => (webSearchEnabled = !webSearchEnabled)}
															type="button"
															style="--px:0.5rem; --py:0.5rem; --d:flex; --g:0.375rem; --ai:center; --size:0.875rem; --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:300ms; --maxw:100%; --of:hidden; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800)"
	class="@xl:px-2.5 focus:outline-hidden {webSearchEnabled ||
															($settings?.webSearch ?? false) === 'always'
																? ' text-sky-500 dark:text-sky-300 bg-sky-50 dark:bg-sky-200/5'
																: 'bg-transparent text-gray-600 dark:text-gray-300 '}"
														>
															<GlobeAlt className="size-4" strokeWidth="1.75" />
															<span
																style="--d:none; --ws:nowrap; --of:hidden; text-overflow:ellipsis; --lh:1; --pr:0.125rem"
	class="@xl:block"
																>{$i18n.t('Web Search')}</span
															>
														</button>
													</Tooltip>
												{/if}

												{#if showImageGenerationButton}
													<Tooltip content={$i18n.t('Generate an image')} placement="top">
														<button
															on:click|preventDefault={() =>
																(imageGenerationEnabled = !imageGenerationEnabled)}
															type="button"
															style="--px:0.5rem; --py:0.5rem; --d:flex; --g:0.375rem; --ai:center; --size:0.875rem; --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:300ms; --maxw:100%; --of:hidden; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800)"
	class="@xl:px-2.5 focus:outline-hidden {imageGenerationEnabled
																? ' text-sky-500 dark:text-sky-300 bg-sky-50 dark:bg-sky-200/5'
																: 'bg-transparent text-gray-600 dark:text-gray-300 '}"
														>
															<Photo className="size-4" strokeWidth="1.75" />
															<span
																style="--d:none; --ws:nowrap; --of:hidden; text-overflow:ellipsis; --lh:1; --pr:0.125rem"
	class="@xl:block"
																>{$i18n.t('Image')}</span
															>
														</button>
													</Tooltip>
												{/if}

												{#if showCodeInterpreterButton}
													<Tooltip content={$i18n.t('Execute code for analysis')} placement="top">
														<button
															aria-label={codeInterpreterEnabled
																? $i18n.t('Disable Code Interpreter')
																: $i18n.t('Enable Code Interpreter')}
															aria-pressed={codeInterpreterEnabled}
															on:click|preventDefault={() =>
																(codeInterpreterEnabled = !codeInterpreterEnabled)}
															type="button"
															style="--px:0.5rem; --py:0.5rem; --d:flex; --g:0.375rem; --ai:center; --size:0.875rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:300ms; --maxw:100%; --of:hidden; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --c: var({codeInterpreterEnabled
																		? '--color-sky-500'
																		: '--color-gray-400'});
																		--m:0 .2em;"
															class="@xl:px-2.5 {codeInterpreterEnabled
																? ' text-sky-500 dark:text-sky-300 bg-sky-50 dark:bg-sky-200/5'
																: 'bg-transparent text-gray-600 dark:text-gray-300 '} {($settings?.highContrastMode ??
															false)
																? 'm-1'
																: 'focus:outline-hidden rounded-full'}"
														>
															<CommandLine className="size-4" strokeWidth="1.75" />
															<span
																style="--d:none; --ws:nowrap; --of:hidden; text-overflow:ellipsis; --lh:1; --pr:0.125rem"
	class="@xl:block"
																>{$i18n.t('Code Interpreter')}</span
															>
														</button>
													</Tooltip>
												{/if}
											</div>
										{/if}
									</div>

									<div style="--as:flex-end; --d:flex; --g:0.25rem; --mr:0.25rem; --fs:0">
										{#if (!history?.currentId || history.messages[history.currentId]?.done == true) && ($_user?.role === 'admin' || ($_user?.permissions?.chat?.stt ?? true))}
											<!-- {$i18n.t('Record voice')} -->
											<Tooltip content={$i18n.t('Dictate')}>
												<button
													id="voice-input-button"
													style="--c:var(--color-gray-600); --dark-c:var(--color-gray-300); --hvr-c:var(--color-gray-700); --hvr-dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.375rem; --mr:0.125rem; --as:center"
													type="button"
													on:click={async () => {
														try {
															let stream = await navigator.mediaDevices
																.getUserMedia({ audio: true })
																.catch(function (err) {
																	toast.error(
																		$i18n.t(
																			`Permission denied when accessing microphone: {{error}}`,
																			{
																				error: err
																			}
																		)
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
													aria-label="Voice Input"
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														style="--w:1.25rem; --h:1.25rem; --translatey:0.5px"
													>
														<path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
														<path
															d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"
														/>
													</svg>
												</button>
											</Tooltip>
										{/if}

										{#if (taskIds && taskIds.length > 0) || (history.currentId && history.messages[history.currentId]?.done != true)}
											<div style="--d:flex; --ai:center">
												<Tooltip content={$i18n.t('Stop')}>
													<button
														style="--bgc:#fff; --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-700); --dark-c:#fff; --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.375rem"
														on:click={() => {
															stopResponse();
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 24 24"
															fill="currentColor"
															style="--w:1.25rem; --h:1.25rem"
														>
															<path
																fill-rule="evenodd"
																d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm6-2.438c0-.724.588-1.312 1.313-1.312h4.874c.725 0 1.313.588 1.313 1.313v4.874c0 .725-.588 1.313-1.313 1.313H9.564a1.312 1.312 0 01-1.313-1.313V9.564z"
																clip-rule="evenodd"
															/>
														</svg>
													</button>
												</Tooltip>
											</div>
										{:else if prompt === '' && files.length === 0 && ($_user?.role === 'admin' || ($_user?.permissions?.chat?.call ?? true))}
											<div style="--d:flex; --ai:center">
												<!-- {$i18n.t('Call')} -->
												<Tooltip content={$i18n.t('Voice mode')}>
													<button
														style="--bgc:#000; --c:#fff; --hvr-bgc:var(--color-gray-900); --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.375rem; --as:center"
														type="button"
														on:click={async () => {
															if (selectedModels.length > 1) {
																toast.error($i18n.t('Select only one model to call'));

																return;
															}

															if ($config.audio.stt.engine === 'web') {
																toast.error(
																	$i18n.t('Call feature is not supported when using Web STT engine')
																);

																return;
															}
															// check if user has access to getUserMedia
															try {
																let stream = await navigator.mediaDevices.getUserMedia({
																	audio: true
																});
																// If the user grants the permission, proceed to show the call overlay

																if (stream) {
																	const tracks = stream.getTracks();
																	tracks.forEach((track) => track.stop());
																}

																stream = null;

																if ($settings.audio?.tts?.engine === 'browser-kokoro') {
																	// If the user has not initialized the TTS worker, initialize it
																	if (!$TTSWorker) {
																		await TTSWorker.set(
																			new KokoroWorker({
																				dtype: $settings.audio?.tts?.engineConfig?.dtype ?? 'fp32'
																			})
																		);

																		await $TTSWorker.init();
																	}
																}

																showCallOverlay.set(true);
																showControls.set(true);
															} catch (err) {
																// If the user denies the permission or an error occurs, show an error message
																toast.error(
																	$i18n.t('Permission denied when accessing media devices')
																);
															}
														}}
														aria-label={$i18n.t('Voice mode')}
													>
														<Headphone className="size-5" />
													</button>
												</Tooltip>
											</div>
										{:else}
											<div style="--d:flex; --ai:center">
												<Tooltip content={$i18n.t('Send message')}>
													<button
														id="send-message-button"
														style="--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.375rem; --as:center"
	class="{!(prompt === '' && files.length === 0)
															? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
															: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'}"
														type="submit"
														disabled={prompt === '' && files.length === 0}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 16 16"
															fill="currentColor"
															style="--w:1.25rem; --h:1.25rem"
														>
															<path
																fill-rule="evenodd"
																d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
																clip-rule="evenodd"
															/>
														</svg>
													</button>
												</Tooltip>
											</div>
										{/if}
									</div>
								</div>
							</div>

							{#if $config?.license_metadata?.input_footer}
								<div style="--size:0.75rem; --c:var(--color-gray-500); --ta:center; --line-clamp:1"
	class="marked">
									{@html DOMPurify.sanitize(marked($config?.license_metadata?.input_footer))}
								</div>
							{:else}
								<div style="--mb:0.25rem" />
							{/if}
						</form>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
