<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import Icon from '$lib/components/Icon.svelte';

	import { createEventDispatcher } from 'svelte';
	import { onMount, tick, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType, t } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	const dispatch = createEventDispatcher();

	import { createNewFeedback, getFeedbackById, updateFeedbackById } from '$lib/apis/evaluations';
	import { getChatById } from '$lib/apis/chats';
	import { generateTags } from '$lib/apis';

	import { config, models, settings, temporaryChatEnabled, TTSWorker, user } from '$lib/stores';
	import { synthesizeOpenAISpeech } from '$lib/apis/audio';
	import { imageGenerations } from '$lib/apis/images';
	import {
		copyToClipboard as _copyToClipboard,
		approximateToHumanReadable,
		getMessageContentParts,
		sanitizeResponseContent,
		createMessagesList,
		formatDate,
		removeDetails,
		removeAllDetails
	} from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding, type BrandingConfig } from '$lib/apis/configs';

	let branding: BrandingConfig | null = null;

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Skeleton from './Skeleton.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import RateComment from './RateComment.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import WebSearchResults from './ResponseMessage/WebSearchResults.svelte';

	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Error from './Error.svelte';
	import Citations from './Citations.svelte';
	import CodeExecutions from './CodeExecutions.svelte';
	import ContentRenderer from './ContentRenderer.svelte';
	import { KokoroWorker } from '$lib/workers/KokoroWorker';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import FollowUps from './ResponseMessage/FollowUps.svelte';
	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	interface MessageType {
		id: string;
		model: string;
		content: string;
		files?: { type: string; url: string }[];
		timestamp: number;
		role: string;
		statusHistory?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		}[];
		status?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		};
		done: boolean;
		error?: boolean | { content: string };
		sources?: string[];
		code_executions?: {
			uuid: string;
			name: string;
			code: string;
			language?: string;
			result?: {
				error?: string;
				output?: string;
				files?: { name: string; url: string }[];
			};
		}[];
		info?: {
			openai?: boolean;
			prompt_tokens?: number;
			completion_tokens?: number;
			total_tokens?: number;
			eval_count?: number;
			eval_duration?: number;
			prompt_eval_count?: number;
			prompt_eval_duration?: number;
			total_duration?: number;
			load_duration?: number;
			usage?: unknown;
		};
		annotation?: { type: string; rating: number };
	}

	export let chatId = '';
	export let history;
	export let messageId;
	export let selectedModels = [];

	let message: MessageType = JSON.parse(JSON.stringify(history.messages[messageId]));
	$: if (history.messages) {
		if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
			message = JSON.parse(JSON.stringify(history.messages[messageId]));
		}
	}

	export let siblings;

	export let setInputText: Function = () => {};
	export let gotoMessage: Function = () => {};
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;

	export let updateChat: Function;
	export let editMessage: Function;
	export let saveMessage: Function;
	export let rateMessage: Function;
	export let actionMessage: Function;
	export let deleteMessage: Function;

	export let submitMessage: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;

	export let addMessages: Function;

	export let isLastMessage = true;
	export let readOnly = false;

	let buttonsContainerElement: HTMLDivElement;
	let showDeleteConfirm = false;

	let model = null;
	$: model = $models.find((m) => m.id === message.model);

	let edit = false;
	let editedContent = '';
	let editTextAreaElement: HTMLTextAreaElement;

	let messageIndexEdit = false;

	let audioParts: Record<number, HTMLAudioElement | null> = {};
	let speaking = false;
	let speakingIdx: number | undefined;

	let loadingSpeech = false;
	let generatingImage = false;

	let showRateComment = false;

	const copyToClipboard = async (text) => {
		text = removeAllDetails(text);

		if (($config?.ui?.response_watermark ?? '').trim() !== '') {
			text = `${text}\n\n${$config?.ui?.response_watermark}`;
		}

		const res = await _copyToClipboard(text, null, $settings?.copyFormatted ?? false);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const playAudio = (idx: number) => {
		return new Promise<void>((res) => {
			speakingIdx = idx;
			const audio = audioParts[idx];

			if (!audio) {
				return res();
			}

			audio.play();
			audio.onended = async () => {
				await new Promise((r) => setTimeout(r, 300));

				if (Object.keys(audioParts).length - 1 === idx) {
					speaking = false;
				}

				res();
			};
		});
	};

	const toggleSpeakMessage = async () => {
		if (speaking) {
			try {
				speechSynthesis.cancel();

				if (speakingIdx !== undefined && audioParts[speakingIdx]) {
					audioParts[speakingIdx]!.pause();
					audioParts[speakingIdx]!.currentTime = 0;
				}
			} catch {}

			speaking = false;
			speakingIdx = undefined;
			return;
		}

		if (!(message?.content ?? '').trim().length) {
			toast.info($i18n.t('No content to speak'));
			return;
		}

		speaking = true;

		const content = removeAllDetails(message.content);

		// Check personal settings first, then fallback to global config
		const useWebAPI = ($settings?.audio?.tts?.engine ?? $config.audio.tts.engine) === '';

		if (useWebAPI) {
			let voices = [];
			const getVoicesLoop = setInterval(() => {
				voices = speechSynthesis.getVoices();
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);

					const voice =
						voices
							?.filter(
								(v) => v.voiceURI === ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							)
							?.at(0) ?? undefined;

					console.log(voice);

					const speak = new SpeechSynthesisUtterance(content);
					speak.rate = $settings.audio?.tts?.playbackRate ?? 1;

					console.log(speak);

					speak.onend = () => {
						speaking = false;
						if ($settings.conversationMode) {
							document.getElementById('voice-input-button')?.click();
						}
					};

					if (voice) {
						speak.voice = voice;
					}

					speechSynthesis.speak(speak);
				}
			}, 100);
		} else {
			loadingSpeech = true;

			const messageContentParts: string[] = getMessageContentParts(
				content,
				$config?.audio?.tts?.split_on ?? 'punctuation'
			);

			if (!messageContentParts.length) {
				console.log('No content to speak');
				toast.info($i18n.t('No content to speak'));

				speaking = false;
				loadingSpeech = false;
				return;
			}

			console.debug('Prepared message content for TTS', messageContentParts);

			audioParts = messageContentParts.reduce(
				(acc, _sentence, idx) => {
					acc[idx] = null;
					return acc;
				},
				{} as typeof audioParts
			);

			let lastPlayedAudioPromise = Promise.resolve(); // Initialize a promise that resolves immediately

			if ($settings.audio?.tts?.engine === 'browser-kokoro') {
				if (!$TTSWorker) {
					await TTSWorker.set(
						new KokoroWorker({
							dtype: $settings.audio?.tts?.engineConfig?.dtype ?? 'fp32'
						})
					);

					await $TTSWorker.init();
				}

				for (const [idx, sentence] of messageContentParts.entries()) {
					const blob = await $TTSWorker
						.generate({
							text: sentence,
							voice: $settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice
						})
						.catch((error) => {
							console.error(error);
							toast.error(`${error}`);

							speaking = false;
							loadingSpeech = false;
						});

					if (blob) {
						const audio = new Audio(blob);
						audio.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

						audioParts[idx] = audio;
						loadingSpeech = false;
						lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
					}
				}
			} else {
				for (const [idx, sentence] of messageContentParts.entries()) {
					const res = await synthesizeOpenAISpeech(
						localStorage.token,
						$settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice
							? ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							: $config?.audio?.tts?.voice,
						sentence
					).catch((error) => {
						console.error(error);
						toast.error(`${error}`);

						speaking = false;
						loadingSpeech = false;
					});

					if (res) {
						const blob = await res.blob();
						const blobUrl = URL.createObjectURL(blob);
						const audio = new Audio(blobUrl);
						audio.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

						audioParts[idx] = audio;
						loadingSpeech = false;
						lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
					}
				}
			}
		}
	};

	let preprocessedDetailsCache = [];

	function preprocessForEditing(content: string): string {
		// Replace <details>...</details> with unique ID placeholder
		const detailsBlocks = [];
		let i = 0;

		content = content.replace(/<details[\s\S]*?<\/details>/gi, (match) => {
			detailsBlocks.push(match);
			return `<details id="__DETAIL_${i++}__"/>`;
		});

		// Store original blocks in the editedContent or globally (see merging later)
		preprocessedDetailsCache = detailsBlocks;

		return content;
	}

	function postprocessAfterEditing(content: string): string {
		const restoredContent = content.replace(
			/<details id="__DETAIL_(\d+)__"\/>/g,
			(_, index) => preprocessedDetailsCache[parseInt(index)] || ''
		);

		return restoredContent;
	}

	const editMessageHandler = async () => {
		edit = true;

		editedContent = preprocessForEditing(message.content);

		await tick();

		editTextAreaElement.style.height = '';
		editTextAreaElement.style.height = `${editTextAreaElement.scrollHeight}px`;
	};

	const editMessageConfirmHandler = async () => {
		const messageContent = postprocessAfterEditing(editedContent ? editedContent : '');
		editMessage(message.id, { content: messageContent }, false);

		edit = false;
		editedContent = '';

		await tick();
	};

	const saveAsCopyHandler = async () => {
		const messageContent = postprocessAfterEditing(editedContent ? editedContent : '');

		editMessage(message.id, { content: messageContent });

		edit = false;
		editedContent = '';

		await tick();
	};

	const cancelEditMessage = async () => {
		edit = false;
		editedContent = '';
		await tick();
	};

	const generateImage = async (message: MessageType) => {
		generatingImage = true;
		const res = await imageGenerations(localStorage.token, message.content).catch((error) => {
			toast.error(`${error}`);
		});
		console.log(res);

		if (res) {
			const files = res.map((image) => ({
				type: 'image',
				url: `${image.url}`
			}));

			saveMessage(message.id, {
				...message,
				files: files
			});
		}

		generatingImage = false;
	};

	let feedbackLoading = false;

	const feedbackHandler = async (rating: number | null = null, details: object | null = null) => {
		feedbackLoading = true;
		console.log('Feedback', rating, details);

		const updatedMessage = {
			...message,
			annotation: {
				...(message?.annotation ?? {}),
				...(rating !== null ? { rating: rating } : {}),
				...(details ? details : {})
			}
		};

		const chat = await getChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});
		if (!chat) {
			return;
		}

		const messages = createMessagesList(history, message.id);

		let feedbackItem = {
			type: 'rating',
			data: {
				...(updatedMessage?.annotation ? updatedMessage.annotation : {}),
				model_id: message?.selectedModelId ?? message.model,
				...(history.messages[message.parentId].childrenIds.length > 1
					? {
							sibling_model_ids: history.messages[message.parentId].childrenIds
								.filter((id) => id !== message.id)
								.map((id) => history.messages[id]?.selectedModelId ?? history.messages[id].model)
						}
					: {})
			},
			meta: {
				arena: message ? message.arena : false,
				model_id: message.model,
				message_id: message.id,
				message_index: messages.length,
				chat_id: chatId
			},
			snapshot: {
				chat: chat
			}
		};

		const baseModels = [
			feedbackItem.data.model_id,
			...(feedbackItem.data.sibling_model_ids ?? [])
		].reduce((acc, modelId) => {
			const model = $models.find((m) => m.id === modelId);
			if (model) {
				acc[model.id] = model?.info?.base_model_id ?? null;
			} else {
				// Log or handle cases where corresponding model is not found
				console.warn(`Model with ID ${modelId} not found`);
			}
			return acc;
		}, {});
		feedbackItem.meta.base_models = baseModels;

		let feedback = null;
		if (message?.feedbackId) {
			feedback = await updateFeedbackById(
				localStorage.token,
				message.feedbackId,
				feedbackItem
			).catch((error) => {
				toast.error(`${error}`);
			});
		} else {
			feedback = await createNewFeedback(localStorage.token, feedbackItem).catch((error) => {
				toast.error(`${error}`);
			});

			if (feedback) {
				updatedMessage.feedbackId = feedback.id;
			}
		}

		console.log(updatedMessage);
		saveMessage(message.id, updatedMessage);

		await tick();

		if (!details) {
			showRateComment = true;

			if (!updatedMessage.annotation?.tags) {
				// attempt to generate tags
				const tags = await generateTags(localStorage.token, message.model, messages, chatId).catch(
					(error) => {
						console.error(error);
						return [];
					}
				);
				console.log(tags);

				if (tags) {
					updatedMessage.annotation.tags = tags;
					feedbackItem.data.tags = tags;

					saveMessage(message.id, updatedMessage);
					await updateFeedbackById(
						localStorage.token,
						updatedMessage.feedbackId,
						feedbackItem
					).catch((error) => {
						toast.error(`${error}`);
					});
				}
			}
		}

		feedbackLoading = false;
	};

	const deleteMessageHandler = async () => {
		deleteMessage(message.id);
	};

	$: if (!edit) {
		(async () => {
			await tick();
		})();
	}

	onMount(async () => {
		// console.log('ResponseMessage mounted');
		branding = await getBranding();

		await tick();
		if (buttonsContainerElement) {
			console.log(buttonsContainerElement);

			buttonsContainerElement.addEventListener('wheel', function (event) {
				if (buttonsContainerElement.scrollWidth <= buttonsContainerElement.clientWidth) {
					// If the container is not scrollable, horizontal scroll
					return;
				} else {
					event.preventDefault();

					if (event.deltaY !== 0) {
						// Adjust horizontal scroll position based on vertical scroll
						buttonsContainerElement.scrollLeft += event.deltaY;
					}
				}
			});
		}
	});
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete message?')}
	on:confirm={() => {
		deleteMessageHandler();
	}}
/>

{#key message.id}
	<div
		style="--d:flex; --w:100%"
	class="message- {message.id}"
		id="message-{message.id}"
		dir={$settings.chatDirection}
	>
		<div class={`shrink-0 ltr:mr-3 rtl:ml-3 hidden @lg:flex mt-1 `}>
			<ProfileImage
				src={model?.info?.meta?.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
				className={'size-8 assistant-message-profile-image'}
				{branding}
			/>
		</div>

		<div style="--fx:1 1 auto; --w:0; --pl:0.2rem; --pos:relative">
			<Name>
				<Tooltip content={model?.name ?? message.model} placement="top-start">
					<span style="--line-clamp:1; --c:#000; --dark-c:#fff">
						{model?.name ?? message.model}
					</span>
				</Tooltip>

				{#if message.timestamp}
					<div
						style="--as:center; --size:0.6rem; --v:hidden; --c:var(--color-gray-400); --weight:500; --ml:0.125rem; --translatey:1px"
	class="group-hover:visible first-letter:capitalize"
					>
						<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
							<span style="--line-clamp:1">{formatDate(message.timestamp * 1000)}</span>
						</Tooltip>
					</div>
				{/if}
			</Name>

			<div>
				<div style="--w:100%; --minw:100%"
	class="chat- {message.role} markdown-prose">
					<div>
						{#if (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length > 0}
							{@const status = (
								message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]
							).at(-1)}
							{#if !status?.hidden}
								<div style="--d:flex; --ai:center; --g:0.5rem; --py:0.125rem"
	class="status-description">
									{#if status?.action === 'web_search' && status?.urls}
										<WebSearchResults {status}>
											<div style="--d:flex; --fd:column; --jc:center; --g:-0.125rem">
												<div
													style="--size:1rem; --line-clamp:1; text-wrap:wrap"
	class="{status?.done === false
														? 'shimmer'
														: ''}"
												>
													<!-- $i18n.t("Generating search query") -->
													<!-- $i18n.t("No search query generated") -->

													<!-- $i18n.t('Searched {{count}} sites') -->
													{#if status?.description.includes('{{count}}')}
														{$i18n.t(status?.description, {
															count: status?.urls.length
														})}
													{:else if status?.description === 'No search query generated'}
														{$i18n.t('No search query generated')}
													{:else if status?.description === 'Generating search query'}
														{$i18n.t('Generating search query')}
													{:else}
														{status?.description}
													{/if}
												</div>
											</div>
										</WebSearchResults>
									{:else if status?.action === 'knowledge_search'}
										<div style="--d:flex; --fd:column; --jc:center; --g:-0.125rem">
											<div
												style="--c:var(--color-gray-500); --dark-c:var(--color-gray-500); --size:1rem; --line-clamp:1; text-wrap:wrap"
	class="{status?.done === false
													? 'shimmer'
													: ''}"
											>
												{$i18n.t(`Searching Knowledge for "{{searchQuery}}"`, {
													searchQuery: status.query
												})}
											</div>
										</div>
									{:else}
										<div style="--d:flex; --fd:column; --jc:center; --g:-0.125rem">
											<div
												style="--c:var(--color-gray-500); --dark-c:var(--color-gray-500); --size:1rem; --line-clamp:1; text-wrap:wrap"
	class="{status?.done === false
													? 'shimmer'
													: ''}"
											>
												<!-- $i18n.t(`Searching "{{searchQuery}}"`) -->
												{#if status?.description.includes('{{searchQuery}}')}
													{$i18n.t(status?.description, {
														searchQuery: status?.query
													})}
												{:else if status?.description === 'No search query generated'}
													{$i18n.t('No search query generated')}
												{:else if status?.description === 'Generating search query'}
													{$i18n.t('Generating search query')}
												{:else if status?.description === 'Searching the web'}
													{$i18n.t('Searching the web...')}
												{:else}
													{status?.description}
												{/if}
											</div>
										</div>
									{/if}
								</div>
							{/if}
						{/if}

						{#if message?.files && message.files?.filter((f) => f.type === 'image').length > 0}
							<div style="--my:0.2rem; --w:100%; --d:flex; --ofx:auto; --g:0.5rem; --fw:wrap">
								{#each message.files as file}
									<div>
										{#if file.type === 'image'}
											<Image src={file.url} alt={message.content} />
										{:else}
											<FileItem
												item={file}
												url={file.url}
												name={file.name}
												type={file.type}
												size={file?.size}
												colorClassName="bg-white dark:bg-gray-850 "
											/>
										{/if}
									</div>
								{/each}
							</div>
						{/if}

						{#if edit === true}
							<div style="--w:100%; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800); --radius:1.5rem; --px:1.2rem; --py:0.6rem; --my:0.5rem">
								<textarea
									id="message-edit-{message.id}"
									bind:this={editTextAreaElement}
									style="--bgc:transparent; --oe:none; --w:100%; resize:none"
									bind:value={editedContent}
									on:input={(e) => {
										e.target.style.height = '';
										e.target.style.height = `${e.target.scrollHeight}px`;
									}}
									on:keydown={(e) => {
										if (e.key === 'Escape') {
											document.getElementById('close-edit-message-button')?.click();
										}

										const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
										const isEnterPressed = e.key === 'Enter';

										if (isCmdOrCtrlPressed && isEnterPressed) {
											document.getElementById('confirm-edit-message-button')?.click();
										}
									}}
								/>

								<div style="--mt:0.5rem; --mb:0.2rem; --d:flex; --jc:space-between; --size:0.8rem; --weight:500">
									<div>
										<button
											id="save-new-message-button"
											style="--px:1rem; --py:0.5rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700);  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-700); --c:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
											on:click={() => {
												saveAsCopyHandler();
											}}
										>
											{$i18n.t('Save As Copy')}
										</button>
									</div>

									<div style="--d:flex; --g:0.4rem">
										<button
											id="close-edit-message-button"
											style="--px:1rem; --py:0.5rem; --bgc:#fff; --dark-bgc:var(--color-gray-900); --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-800); --dark-c:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
											on:click={() => {
												cancelEditMessage();
											}}
										>
											{$i18n.t('Cancel')}
										</button>

										<button
											id="confirm-edit-message-button"
											style="--px:1rem; --py:0.5rem; --bgc:var(--color-gray-900); --dark-bgc:#fff; --hvr-bgc:var(--color-gray-850); --c:var(--color-gray-100); --dark-c:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
											on:click={() => {
												editMessageConfirmHandler();
											}}
										>
											{$i18n.t('Save')}
										</button>
									</div>
								</div>
							</div>
						{:else}
							<div style="--w:100%; --d:flex; --fd:column; --pos:relative" id="response-content-container">
								{#if message.content === '' && !message.error && (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length === 0}
									<Skeleton />
								{:else if message.content && message.error !== true}
									<!-- always show message contents even if there's an error -->
									<!-- unless message.error === true which is legacy error handling, where the error message is stored in message.content -->
									<ContentRenderer
										id={message.id}
										{history}
										{selectedModels}
										content={message.content}
										sources={message.sources}
										floatingButtons={message?.done && !readOnly}
										save={!readOnly}
										preview={!readOnly}
										done={($settings?.chatFadeStreamingText ?? true)
											? (message?.done ?? false)
											: true}
										{model}
										{submitMessage}
										onTaskClick={async (e) => {
											console.log(e);
										}}
										onSourceClick={async (id, idx) => {
											console.log(id, idx);
											let sourceButton = document.getElementById(`source-${message.id}-${idx}`);
											const sourcesCollapsible = document.getElementById(
												`collapsible-${message.id}`
											);

											if (sourceButton) {
												sourceButton.click();
											} else if (sourcesCollapsible) {
												// Open sources collapsible so we can click the source button
												sourcesCollapsible
													.querySelector('div:first-child')
													.dispatchEvent(new PointerEvent('pointerup', {}));

												// Wait for next frame to ensure DOM updates
												await new Promise((resolve) => {
													requestAnimationFrame(() => {
														requestAnimationFrame(resolve);
													});
												});

												// Try clicking the source button again
												sourceButton = document.getElementById(`source-${message.id}-${idx}`);
												sourceButton && sourceButton.click();
											}
										}}
										onAddMessages={({ modelId, parentId, messages }) => {
											addMessages({ modelId, parentId, messages });
										}}
										onSave={({ raw, oldContent, newContent }) => {
											history.messages[message.id].content = history.messages[
												message.id
											].content.replace(raw, raw.replace(oldContent, newContent));

											updateChat();
										}}
									/>
								{/if}

								{#if message?.error}
									<Error content={message?.error?.content ?? message.content} />
								{/if}

								{#if (message?.sources || message?.citations) && (model?.info?.meta?.capabilities?.citations ?? true)}
									<Citations id={message?.id} {chatId} sources={message?.sources ?? message?.citations} />
								{/if}

								{#if message.code_executions}
									<CodeExecutions codeExecutions={message.code_executions} />
								{/if}
							</div>
						{/if}
					</div>
				</div>

				{#if !edit}
					<div
						bind:this={buttonsContainerElement}
						style="--d:flex; --jc:flex-start; --ofx:auto; --c:var(--color-gray-600); --dark-c:var(--color-gray-500); --mt:0.125rem"
	class="buttons"
					>
						{#if message.done || siblings.length > 1}
							{#if siblings.length > 1}
								<div style="--d:flex; --as:center; --minw:fit-content" dir="ltr">
									<button
										aria-label={$i18n.t('Previous message')}
										style="--as:center; --p:0.2rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										on:click={() => {
											showPreviousMessage(message);
										}}
									>
										<svg
											aria-hidden="true"
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
											stroke-width="2.5"
											style="--w:0.8rem; --h:0.8rem"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 19.5 8.25 12l7.5-7.5"
											/>
										</svg>
									</button>

									{#if messageIndexEdit}
										<div
											style="--size:0.8rem; --d:flex; --jc:center; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
										>
											<input
												id="message-index-input-{message.id}"
												type="number"
												value={siblings.indexOf(message.id) + 1}
												min="1"
												max={siblings.length}
												on:focus={(e) => {
													e.target.select();
												}}
												on:blur={(e) => {
													gotoMessage(message, e.target.value - 1);
													messageIndexEdit = false;
												}}
												on:keydown={(e) => {
													if (e.key === 'Enter') {
														gotoMessage(message, e.target.value - 1);
														messageIndexEdit = false;
													}
												}}
												style="--bgc:transparent; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content; --oe:none"
											/>/{siblings.length}
										</div>
									{:else}
										<!-- svelte-ignore a11y-no-static-element-interactions -->
										<div
											style="--size:0.8rem; --ls:0.1em; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
											on:dblclick={async () => {
												messageIndexEdit = true;

												await tick();
												const input = document.getElementById(`message-index-input-${message.id}`);
												if (input) {
													input.focus();
													input.select();
												}
											}}
										>
											{siblings.indexOf(message.id) + 1}/{siblings.length}
										</div>
									{/if}

									<button
										style="--as:center; --p:0.2rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										on:click={() => {
											showNextMessage(message);
										}}
										aria-label={$i18n.t('Next message')}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											aria-hidden="true"
											viewBox="0 0 24 24"
											stroke="currentColor"
											stroke-width="2.5"
											style="--w:0.8rem; --h:0.8rem"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m8.25 4.5 7.5 7.5-7.5 7.5"
											/>
										</svg>
									</button>
								</div>
							{/if}

							{#if message.done}
								{#if !readOnly}
									{#if $user?.role === 'user' ? ($user?.permissions?.chat?.edit ?? true) : true}
										<Tooltip content={$i18n.t('Edit')} placement="bottom">
											<button
												aria-label={$i18n.t('Edit')}
												style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'}"
												on:click={() => {
													editMessageHandler();
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													aria-hidden="true"
													stroke="currentColor"
													style="--w:1rem; --h:1rem"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}
								{/if}

								<Tooltip content={$i18n.t('Copy')} placement="bottom">
									<button
										aria-label={$i18n.t('Copy')}
										style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
											? 'visible'
											: 'invisible group-hover:visible'} copy-response-button"
										on:click={() => {
											copyToClipboard(message.content);
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											aria-hidden="true"
											viewBox="0 0 24 24"
											stroke-width="2.3"
											stroke="currentColor"
											style="--w:1rem; --h:1rem"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
											/>
										</svg>
									</button>
								</Tooltip>

								{#if $user?.role === 'admin' || ($user?.permissions?.chat?.tts ?? true)}
									<Tooltip content={$i18n.t('Read Aloud')} placement="bottom">
										<button
											aria-label={$i18n.t('Read Aloud')}
											id="speak-button-{message.id}"
											style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'}"
											on:click={() => {
												if (!loadingSpeech) {
													toggleSpeakMessage();
												}
											}}
										>
											{#if loadingSpeech}
												<svg
													style="--w:1rem; --h:1rem"
													fill="currentColor"
													viewBox="0 0 24 24"
													aria-hidden="true"
													xmlns="http://www.w3.org/2000/svg"
												>
													<style>
														.spinner_S1WN {
															animation: spinner_MGfb 0.8s linear infinite;
															animation-delay: -0.8s;
														}

														.spinner_Km9P {
															animation-delay: -0.65s;
														}

														.spinner_JApP {
															animation-delay: -0.5s;
														}

														@keyframes spinner_MGfb {
															93.75%,
															100% {
																opacity: 0.2;
															}
														}
													</style>
													<circle class="spinner_S1WN" cx="4" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_Km9P" cx="12" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_JApP" cx="20" cy="12" r="3" />
												</svg>
											{:else if speaking}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													aria-hidden="true"
													stroke-width="2.3"
													stroke="currentColor"
													style="--w:1rem; --h:1rem"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
													/>
												</svg>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													aria-hidden="true"
													stroke-width="2.3"
													stroke="currentColor"
													style="--w:1rem; --h:1rem"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z"
													/>
												</svg>
											{/if}
										</button>
									</Tooltip>
								{/if}

								{#if $config?.features.enable_image_generation && ($user?.role === 'admin' || $user?.permissions?.features?.image_generation) && !readOnly}
									<Tooltip content={$i18n.t('Generate Image')} placement="bottom">
										<button
											aria-label={$i18n.t('Generate Image')}
											style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'}"
											on:click={() => {
												if (!generatingImage) {
													generateImage(message);
												}
											}}
										>
											{#if generatingImage}
												<svg
													aria-hidden="true"
													style="--w:1rem; --h:1rem"
													fill="currentColor"
													viewBox="0 0 24 24"
													xmlns="http://www.w3.org/2000/svg"
												>
													<style>
														.spinner_S1WN {
															animation: spinner_MGfb 0.8s linear infinite;
															animation-delay: -0.8s;
														}

														.spinner_Km9P {
															animation-delay: -0.65s;
														}

														.spinner_JApP {
															animation-delay: -0.5s;
														}

														@keyframes spinner_MGfb {
															93.75%,
															100% {
																opacity: 0.2;
															}
														}
													</style>
													<circle class="spinner_S1WN" cx="4" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_Km9P" cx="12" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_JApP" cx="20" cy="12" r="3" />
												</svg>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													aria-hidden="true"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													style="--w:1rem; --h:1rem"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
													/>
												</svg>
											{/if}
										</button>
									</Tooltip>
								{/if}

								{#if message.usage}
									<Tooltip
										content={message.usage
											? `<pre>${sanitizeResponseContent(
													JSON.stringify(message.usage, null, 2)
														.replace(/"([^(")"]+)":/g, '$1:')
														.slice(1, -1)
														.split('\n')
														.map((line) => line.slice(2))
														.map((line) => (line.endsWith(',') ? line.slice(0, -1) : line))
														.join('\n')
												)}</pre>`
											: ''}
										placement="bottom"
									>
										<button
											aria-hidden="true"
											style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --ws:pre-wrap"
	class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'}"
											on:click={() => {
												console.log(message);
											}}
											id="info-{message.id}"
										>
											<svg
												aria-hidden="true"
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2.3"
												stroke="currentColor"
												style="--w:1rem; --h:1rem"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}

								{#if !readOnly}
									{#if !$temporaryChatEnabled && ($config?.features.enable_message_rating ?? true)}
										<Tooltip content={$i18n.t('Good Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Good Response')}
												style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} {(
													message?.annotation?.rating ?? ''
												).toString() === '1'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async () => {
													await feedbackHandler(1);
													window.setTimeout(() => {
														document
															.getElementById(`message-feedback-${message.id}`)
															?.scrollIntoView();
													}, 0);
												}}
											>
												<svg
													aria-hidden="true"
													stroke="currentColor"
													fill="none"
													stroke-width="2.3"
													viewBox="0 0 24 24"
													stroke-linecap="round"
													stroke-linejoin="round"
													style="--w:1rem; --h:1rem"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"
													/>
												</svg>
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Bad Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Bad Response')}
												style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} {(
													message?.annotation?.rating ?? ''
												).toString() === '-1'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async () => {
													await feedbackHandler(-1);
													window.setTimeout(() => {
														document
															.getElementById(`message-feedback-${message.id}`)
															?.scrollIntoView();
													}, 0);
												}}
											>
												<svg
													aria-hidden="true"
													stroke="currentColor"
													fill="none"
													stroke-width="2.3"
													viewBox="0 0 24 24"
													stroke-linecap="round"
													stroke-linejoin="round"
													style="--w:1rem; --h:1rem"
													xmlns="http://www.w3.org/2000/svg"
												>
													<path
														d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									{#if isLastMessage}
										<Tooltip content={$i18n.t('Continue Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Continue Response')}
												type="button"
												id="continue-response-button"
												style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} regenerate-response-button"
												on:click={() => {
													continueResponse();
												}}
											>
												<svg
													aria-hidden="true"
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													style="--w:1rem; --h:1rem"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
													/>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
										<button
											type="button"
											aria-label={$i18n.t('Regenerate')}
											style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'} regenerate-response-button"
											on:click={() => {
												showRateComment = false;
												regenerateResponse(message);

												(model?.actions ?? []).forEach((action) => {
													dispatch('action', {
														id: action.id,
														event: {
															id: 'regenerate-response',
															data: {
																messageId: message.id
															}
														}
													});
												});
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2.3"
												aria-hidden="true"
												stroke="currentColor"
												style="--w:1rem; --h:1rem"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
												/>
											</svg>
										</button>
									</Tooltip>

									{#if siblings.length > 1}
										<Tooltip content={$i18n.t('Delete')} placement="bottom">
											<button
												type="button"
												aria-label={$i18n.t('Delete')}
												id="delete-response-button"
												style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} regenerate-response-button"
												on:click={() => {
													showDeleteConfirm = true;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													stroke="currentColor"
													aria-hidden="true"
													style="--w:1rem; --h:1rem"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									{#if isLastMessage}
										{#each model?.actions ?? [] as action}
											<Tooltip content={action.name} placement="bottom">
												<button
													type="button"
													aria-label={action.name}
													style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'}"
													on:click={() => {
														actionMessage(action.id, message);
													}}
												>
													{#if action?.icon}
														<div style="--w:1rem; --h:1rem">
															<img
																src={action.icon}
																class="{action.icon.includes('svg')
																	? 'dark:invert-[80%]'
																	: ''}"
																style="--w:1rem; --h:1rem; fill: currentColor;"
																alt={action.name}
															/>
														</div>
													{:else}
														<Icon name="sparkles" strokeWidth="2.1" className="size-4" />
													{/if}
												</button>
											</Tooltip>
										{/each}
									{/if}
								{/if}
							{/if}
						{/if}
					</div>

					{#if message.done && showRateComment}
						<RateComment
							bind:message
							bind:show={showRateComment}
							on:save={async (e) => {
								await feedbackHandler(null, {
									...e.detail
								});
							}}
						/>
					{/if}

					{#if (isLastMessage || ($settings?.keepFollowUpPrompts ?? false)) && message.done && !readOnly && (message?.followUps ?? []).length > 0}
						<div style="--mt:0.625rem" in:fade={{ duration: 100 }}>
							<FollowUps
								followUps={message?.followUps}
								onClick={(prompt) => {
									if ($settings?.insertFollowUpPrompt ?? false) {
										// Insert the follow-up prompt into the input box
										setInputText(prompt);
									} else {
										// Submit the follow-up prompt directly
										submitMessage(message?.id, prompt);
									}
								}}
							/>
						</div>
					{/if}
				{/if}
			</div>

			{#if message?.done}
				<div aria-live="polite" class="sr-only">
					{message?.content ?? ''}
				</div>
			{/if}
		</div>
	</div>
{/key}

<style>
	.buttons::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.buttons {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	button{
		margin: 0 0.2rem 0 0;
	}
</style>
