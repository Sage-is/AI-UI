<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import heic2any from 'heic2any';

	import { tick, getContext, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import { config, mobile, settings, socket, user } from '$lib/stores';
	import {
		blobToFile,
		compressImage,
		extractInputVariables,
		getCurrentDateTime,
		getFormattedDate,
		getFormattedTime,
		getUserPosition,
		getUserTimezone,
		getWeekday
	} from '$lib/utils';

	import Tooltip from '../common/Tooltip.svelte';
	import RichTextInput from '../common/RichTextInput.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import InputMenu from './MessageInput/InputMenu.svelte';
	import { uploadFile } from '$lib/apis/files';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import FileItem from '../common/FileItem.svelte';
	import Image from '../common/Image.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import Commands from '../chat/MessageInput/Commands.svelte';
	import Mentions from './MessageInput/Mentions.svelte';
	import InputVariablesModal from '../chat/MessageInput/InputVariablesModal.svelte';
	import IndicatorStack from './IndicatorStack.svelte';
	import Icon from '$lib/components/Icon.svelte';

	export let placeholder = $i18n.t('Send a Message');
	export let transparentBackground = false;

	export let id = null;

	let draggedOver = false;

	let recording = false;
	let content = '';
	let files = [];

	export let chatInputElement;

	let commandsElement;
	let filesInputElement;
	let inputFiles;

	export let typingUsers = [];
	export let inputLoading = false;

	export let onSubmit: Function = (e) => {};
	export let onChange: Function = (e) => {};
	export let onStop: Function = (e) => {};

	export let scrollEnd = true;
	export let scrollToBottom: Function = () => {};

	export let acceptFiles = true;
	export let showFormattingButtons = true;
	export let participants: { users: any[]; agents: any[] } = { users: [], agents: [] };
	export let thinkingAgents: any[] = [];

	let showInputVariablesModal = false;
	let inputVariables: Record<string, any> = {};
	let inputVariableValues = {};

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
			const name = $user?.name || 'User';
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
		if (!chatInputElement) return;
		console.log('Replacing variables:', variables);

		chatInputElement.replaceVariables(variables);
		chatInputElement.focus();
	};

	export const setText = async (text?: string) => {
		if (!chatInputElement) return;

		text = await textVariableHandler(text || '');

		chatInputElement?.setText(text);
		chatInputElement?.focus();
	};

	const getCommand = () => {
		if (!chatInputElement) return;

		let word = '';
		word = chatInputElement?.getWordAtDocPos();

		return word;
	};

	const replaceCommandWithText = (text) => {
		if (!chatInputElement) return;

		chatInputElement?.replaceCommandWithText(text);
	};

	const insertTextAtCursor = async (text: string) => {
		text = await textVariableHandler(text);

		if (command) {
			replaceCommandWithText(text);
		} else {
			const selection = window.getSelection();
			if (selection && selection.rangeCount > 0) {
				const range = selection.getRangeAt(0);
				range.deleteContents();
				range.insertNode(document.createTextNode(text));
				range.collapse(false);
				selection.removeAllRanges();
				selection.addRange(range);
			}
		}

		await tick();
		const chatInputContainer = document.getElementById('chat-input-container');
		if (chatInputContainer) {
			chatInputContainer.scrollTop = chatInputContainer.scrollHeight;
		}

		await tick();
		if (chatInputElement) {
			chatInputElement.focus();
		}
	};

	let command = '';

	export let showCommands = false;
	$: showCommands = ['/'].includes(command?.charAt(0));

	let mentionsElement;
	let mentionQuery = '';
	let showMentions = false;

	$: {
		if (command?.startsWith('@')) {
			showMentions = true;
			mentionQuery = command.slice(1);
		} else {
			showMentions = false;
			mentionQuery = '';
		}
	}

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

	const inputFilesHandler = async (inputFiles) => {
		inputFiles.forEach(async (file) => {
			console.info('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.error('File exceeds max size limit:', {
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

					// Compress the image if settings or config require it
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

		try {
			// During the file upload, file content is automatically extracted.

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

			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (uploadedFile) {
				console.info('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.error('File upload warning:', uploadedFile.error);
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
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			draggedOver = false;
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
		if (e.dataTransfer?.types?.includes('Files')) {
			draggedOver = true;
		} else {
			draggedOver = false;
		}
	};

	const onDragLeave = () => {
		draggedOver = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();

		if (e.dataTransfer?.files && acceptFiles) {
			const inputFiles = Array.from(e.dataTransfer?.files);
			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				inputFilesHandler(inputFiles);
			}
		}

		draggedOver = false;
	};

	const submitHandler = async () => {
		if (content === '' && files.length === 0) {
			return;
		}

		onSubmit({
			content,
			data: {
				files: files
			}
		});

		content = '';
		files = [];

		if (chatInputElement) {
			chatInputElement?.setText('');

			await tick();

			chatInputElement.focus();
		}
	};

	$: if (content) {
		onChange();
	}

	onMount(async () => {
		window.setTimeout(() => {
			if (chatInputElement) {
				chatInputElement.focus();
			}
		}, 100);

		window.addEventListener('keydown', handleKeyDown);
		await tick();

		const dropzoneElement = document.getElementById('space-container');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeyDown);

		const dropzoneElement = document.getElementById('space-container');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<FilesOverlay show={draggedOver} />

{#if acceptFiles}
	<input
		bind:this={filesInputElement}
		bind:files={inputFiles}
		type="file"
		hidden
		multiple
		on:change={async () => {
			if (inputFiles && inputFiles.length > 0) {
				inputFilesHandler(Array.from(inputFiles));
			} else {
				toast.error($i18n.t(`File not found.`));
			}

			filesInputElement.value = '';
		}}
	/>
{/if}

<InputVariablesModal
	bind:show={showInputVariablesModal}
	variables={inputVariables}
	onSave={(variableValues) => {
		inputVariableValues = { ...inputVariableValues, ...variableValues };
		replaceVariables(inputVariableValues);
	}}
/>

<div style="--bgc:transparent">
	<div
		style="--mx:auto; --left:0; --right:0; --pos:relative"
		class={($settings?.widescreenMode ?? null) ? 'max-w-full' : 'max-w-6xl'}
	>
		<div
			style="--pos:absolute; --top:0; --left:0; --right:0; --mx:auto; --left:0; --right:0; --bgc:transparent; --d:flex; --jc:center"
		>
			<div style="--d:flex; --fd:column; --px:0.6rem; --w:100%">
				<div style="--pos:relative">
					{#if scrollEnd === false}
						<div
							style="--pos:absolute; --top:-3rem; --left:0; --right:0; --d:flex; --jc:center; --z:30; --pe:none"
						>
							<button
								style="--bgc:#fff;  --bc:var(--color-gray-100); --dark-bs:none; --dark-bgc:rgb(255 255 255 / 0.2); --p:0.4rem; --radius:9999px; --pe:auto"
								on:click={() => {
									scrollEnd = true;
									scrollToBottom();
								}}
							>
								<Icon name="arrow-down-fill-20" className="size-[1.2rem]" />
							</button>
						</div>
					{/if}
				</div>

				<div style="--pos:relative">
					<div style="--mt:-1.2rem">
						<IndicatorStack {thinkingAgents} {typingUsers} />
					</div>

					<Commands
						bind:this={commandsElement}
						show={showCommands}
						{command}
						insertTextHandler={insertTextAtCursor}
					/>

					<Mentions
						bind:this={mentionsElement}
						show={showMentions}
						query={mentionQuery}
						{participants}
						onSelect={(participant) => {
							const name = participant.data.name.includes(' ')
								? participant.data.name.replace(/\s+/g, '-')
								: participant.data.name;
							replaceCommandWithText(`@${name} `);
							showMentions = false;
						}}
					/>
				</div>
			</div>
		</div>

		<div class="">
			{#if recording}
				<VoiceRecording
					bind:recording
					onCancel={async () => {
						recording = false;

						await tick();

						if (chatInputElement) {
							chatInputElement.focus();
						}
					}}
					onConfirm={async (data) => {
						const { text, filename } = data;
						recording = false;

						await tick();
						insertTextAtCursor(text);

						await tick();

						if (chatInputElement) {
							chatInputElement.focus();
						}
					}}
				/>
			{:else}
				<form
					style="--w:100%; --d:flex; --g:0.4rem"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div
						style="--fx:1 1 0%;
							--d:flex;
							--fd:column;
							--pos:relative;
							--w:100%;
							--radius:1.5rem;
							--px:0.2rem;
							--bgc:rgb(103 103 103 / 0.05); --dark-bgc:rgb(180 180 180 / 0.05); --dark-c:var(--color-gray-100)"
						dir={$settings?.chatDirection ?? 'auto'}
					>
						{#if files.length > 0}
							<div
								style="--mx:0.5rem; --mt:0.625rem; --mb:-0.2rem; --d:flex; --fw:wrap; --g:0.5rem"
							>
								{#each files as file, fileIdx}
									{#if file.type === 'image'}
										<div style="--pos:relative" class="group">
											<div style="--pos:relative">
												<Image
													src={file.url}
													alt="input"
													imageClassName=" h-16 w-16 rounded-xl object-cover"
												/>
											</div>
											<div style="--pos:absolute; --top:-0.2rem; --right:-0.2rem">
												<button
													style="--bgc:#fff; --c:#000;  --bc:#fff; --radius:9999px; --v:hidden; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
													class="group-hover:visible"
													type="button"
													on:click={() => {
														files.splice(fileIdx, 1);
														files = files;
													}}
												>
													<Icon name="x-mark" className="size-4" />
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
											on:dismiss={() => {
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
							<div
								style="--ta:left; --bgc:transparent; --dark-c:var(--color-gray-100); --oe:none; --w:100%; --pt:0.6rem; --px:0.2rem; resize:none; --h:fit-content; --maxh:20rem; --of:auto"
								class="scrollbar-hidden font-primary"
							>
								<RichTextInput
									bind:this={chatInputElement}
									json={true}
									messageInput={true}
									{showFormattingButtons}
									shiftEnter={!($settings?.ctrlEnterToSend ?? false) &&
										(!$mobile ||
											!(
												'ontouchstart' in window ||
												navigator.maxTouchPoints > 0 ||
												navigator.msMaxTouchPoints > 0
											))}
									largeTextAsFile={$settings?.largeTextAsFile ?? false}
									floatingMenuPlacement={'top-start'}
									onChange={(e) => {
										const { md } = e;
										content = md;
										command = getCommand();
									}}
									on:keydown={async (e) => {
										e = e.detail.event;
										const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac

										const mentionsContainerElement = document.getElementById('mentions-container');

										if (mentionsContainerElement) {
											if (e.key === 'ArrowUp') {
												e.preventDefault();
												mentionsElement.selectUp();
												const btn = [
													...document.getElementsByClassName('selected-mention-option-button')
												]?.at(-1);
												btn?.scrollIntoView({ block: 'center' });
											}
											if (e.key === 'ArrowDown') {
												e.preventDefault();
												mentionsElement.selectDown();
												const btn = [
													...document.getElementsByClassName('selected-mention-option-button')
												]?.at(-1);
												btn?.scrollIntoView({ block: 'center' });
											}
											if (e.key === 'Tab' || e.key === 'Enter') {
												e.preventDefault();
												const btn = [
													...document.getElementsByClassName('selected-mention-option-button')
												]?.at(-1);
												btn?.click();
											}
											if (e.key === 'Escape') {
												showMentions = false;
											}
											return;
										}

										const commandsContainerElement = document.getElementById('commands-container');

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
												// Prevent Enter key from creating a new line
												// Uses keyCode '13' for Enter key for chinese/japanese keyboards
												if (e.keyCode === 13 && !e.shiftKey) {
													e.preventDefault();
												}

												// Submit the content when Enter key is pressed
												if (content !== '' && e.keyCode === 13 && !e.shiftKey) {
													submitHandler();
												}
											}
										}

										if (e.key === 'Escape') {
											console.info('Escape');
										}
									}}
									on:paste={async (e) => {
										e = e.detail.event;
										console.info(e);
									}}
								/>
							</div>
						</div>

						<div style="--d:flex; --jc:space-between; --mb:0.625rem; --mt:0.4rem; --mx:0.125rem">
							<div style="--ml:0.2rem; --as:flex-end; --d:flex; --g:0.2rem; --fx:1 1 0%">
								<slot name="menu">
									{#if acceptFiles}
										<InputMenu
											{screenCaptureHandler}
											uploadFilesHandler={() => {
												filesInputElement.click();
											}}
										>
											<button
												style="--bgc:transparent; --hvr-bgc:rgb(255 255 255 / 0.8); --c:var(--color-gray-800); --dark-c:#fff; --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.4rem; --oe:none"
												class="focus:outline-hidden"
												type="button"
												aria-label="More"
											>
												<Icon name="plus-fill-20-51dd" className="size-[1.2rem]" />
											</button>
										</InputMenu>
									{/if}
								</slot>
							</div>

							<div style="--as:flex-end; --d:flex; --g:0.2rem; --mr:0.2rem">
								{#if content === ''}
									<Tooltip content={$i18n.t('Record voice')}>
										<button
											id="voice-input-button"
											style="--c:var(--color-gray-600); --dark-c:var(--color-gray-300); --hvr-c:var(--color-gray-700); --hvr-dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.4rem; --mr:0.125rem; --as:center"
											type="button"
											on:click={async () => {
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
											aria-label="Voice Input"
										>
											<Icon name="mic-fill-20" className="size-[1.2rem]" />
										</button>
									</Tooltip>
								{/if}

								<div style="--d:flex; --ai:center">
									{#if inputLoading && onStop}
										<div style="--d:flex; --ai:center">
											<Tooltip content={$i18n.t('Stop')}>
												<button
													style="--bgc:#fff; --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-700); --dark-c:#fff; --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.4rem"
													on:click={() => {
														onStop();
													}}
												>
													<Icon name="stop-circle-fill" className="size-[1.2rem]" />
												</button>
											</Tooltip>
										</div>
									{:else}
										<div style="--d:flex; --ai:center">
											<Tooltip content={$i18n.t('Send message')}>
												<button
													id="send-message-button"
													style="--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.4rem; --as:center"
													class={content !== '' || files.length !== 0
														? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
														: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'}
													type="submit"
													disabled={content === '' && files.length === 0}
												>
													<Icon name="send-up-fill-16" className="size-[1.2rem]" />
												</button>
											</Tooltip>
										</div>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</form>
			{/if}
		</div>
	</div>
</div>
