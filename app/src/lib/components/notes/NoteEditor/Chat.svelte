<script lang="ts">
	export let show = false;
	export let selectedModelId = '';

	import { marked } from 'marked';
	// Configure marked with extensions
	marked.use({
		breaks: true,
		gfm: true,
		renderer: {
			list(body, ordered, start) {
				const isTaskList = body.includes('data-checked=');

				if (isTaskList) {
					return `<ul data-type="taskList">${body}</ul>`;
				}

				const type = ordered ? 'ol' : 'ul';
				const startatt = ordered && start !== 1 ? ` start="${start}"` : '';
				return `<${type}${startatt}>${body}</${type}>`;
			},

			listitem(text, task, checked) {
				if (task) {
					const checkedAttr = checked ? 'true' : 'false';
					return `<li data-type="taskItem" data-checked="${checkedAttr}">${text}</li>`;
				}
				return `<li>${text}</li>`;
			}
		}
	});

	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import {
		OLLAMA_API_BASE_URL,
		OPENAI_API_BASE_URL,
		WEBUI_API_BASE_URL,
		WEBUI_BASE_URL
	} from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings } from '$lib/stores';

	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';

	import Messages from '$lib/components/notes/NoteEditor/Chat/Messages.svelte';
	import MessageInput from '$lib/components/channel/MessageInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import PencilSquare from '$lib/components/icons/PencilSquare.svelte';

	const i18n = getContext('i18n');

	export let editor = null;

	export let editing = false;
	export let streaming = false;
	export let stopResponseFlag = false;

	export let note = null;
	export let selectedContent = null;

	export let files = [];
	export let messages = [];

	export let onInsert = (content) => {};
	export let onStop = () => {};
	export let onEdited = () => {};

	export let insertNoteHandler = () => {};
	export let scrollToBottomHandler = () => {};

	let loaded = false;

	let loading = false;

	let messagesContainerElement: HTMLDivElement;

	let system = '';
	let editEnabled = false;
	let chatInputElement = null;

	const DEFAULT_DOCUMENT_EDITOR_PROMPT = `You are an expert document editor.

## Task
Based on the user's instruction, update and enhance the existing notes or selection by incorporating relevant and accurate information from the provided context in the content's primary language. Ensure all edits strictly follow the user’s intent.

## Input Structure
- Existing notes: Enclosed within <notes></notes> XML tags.
- Additional context: Enclosed within <context></context> XML tags.
- Current note selection: Enclosed within <selection></selection> XML tags.
- Editing instruction: Provided in the user message.

## Output Instructions
- If a selection is provided, edit **only** the content within <selection></selection>. Leave unselected parts unchanged.
- If no selection is provided, edit the entire notes.
- Deliver a single, rewritten version of the notes in markdown format.
- Integrate information from the context only if it directly supports the user's instruction.
- Use clear, organized markdown elements: headings, lists, task lists ([ ]) where tasks or checklists are strongly implied, bold and italic text as appropriate.
- Focus on improving clarity, completeness, and usefulness of the notes.
- Return only the final, fully-edited markdown notes—do not include explanations, reasoning, or XML tags.
`;

	let scrolledToBottom = true;

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			if (scrolledToBottom) {
				messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
			}
		}
	};

	const onScroll = () => {
		if (messagesContainerElement) {
			scrolledToBottom =
				messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
				messagesContainerElement.clientHeight + 10;
		}
	};

	const chatCompletionHandler = async () => {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models.find((model) => model.id === selectedModelId);
		if (!model) {
			selectedModelId = '';
			return;
		}

		let responseMessage;
		if (messages.at(-1)?.role === 'assistant') {
			responseMessage = messages.at(-1);
		} else {
			responseMessage = {
				role: 'assistant',
				content: '',
				done: false
			};
			messages.push(responseMessage);
			messages = messages;
		}

		await tick();
		scrollToBottom();

		stopResponseFlag = false;
		let enhancedContent = {
			json: null,
			html: '',
			md: ''
		};

		system = '';

		if (editEnabled) {
			system = `${DEFAULT_DOCUMENT_EDITOR_PROMPT}\n\n`;
		} else {
			system = `You are a helpful assistant. Please answer the user's questions based on the context provided.\n\n`;
		}

		system +=
			`<notes>${note?.data?.content?.md ?? ''}</notes>` +
			(files && files.length > 0
				? `\n<context>${files.map((file) => `${file.name}: ${file?.file?.data?.content ?? 'Could not extract content'}\n`).join('')}</context>`
				: '') +
			(selectedContent ? `\n<selection>${selectedContent?.text}</selection>` : '');

		const chatMessages = JSON.parse(
			JSON.stringify([
				{
					role: 'system',
					content: `${system}`
				},
				...messages
			])
		);

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: chatMessages
				// ...(files && files.length > 0 ? { files } : {}) // TODO: Decide whether to use native file handling or not
			},
			`${WEBUI_BASE_URL}/api`
		);

		await tick();
		scrollToBottom();

		let messageContent = '';

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

					if (editEnabled) {
						editing = false;
						streaming = false;
						onEdited();
					}

					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								if (editEnabled) {
									responseMessage.content = `<status title="${$i18n.t('Edited')}" done="true" />`;

									if (selectedContent && selectedContent?.text && editor) {
										editor.commands.insertContentAt(
											{
												from: selectedContent.from,
												to: selectedContent.to
											},
											enhancedContent.html || enhancedContent.md || ''
										);

										selectedContent = null;
									}
								}

								responseMessage.done = true;
								messages = messages;
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								let deltaContent = data.choices[0]?.delta?.content ?? '';
								if (responseMessage.content == '' && deltaContent == '\n') {
									continue;
								} else {
									if (editEnabled) {
										editing = true;
										streaming = true;

										enhancedContent.md += deltaContent;
										enhancedContent.html = marked.parse(enhancedContent.md);

										if (!selectedContent || !selectedContent?.text) {
											note.data.content.md = enhancedContent.md;
											note.data.content.html = enhancedContent.html;
											note.data.content.json = null;
										}

										scrollToBottomHandler();

										responseMessage.content = `<status title="${$i18n.t('Editing')}" done="false" />`;
										messages = messages;
									} else {
										messageContent += deltaContent;

										responseMessage.content = messageContent;
										messages = messages;
									}

									await tick();
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}

				scrollToBottom();
			}
		}
	};

	const submitHandler = async (e) => {
		const { content, data } = e;
		if (selectedModelId && content) {
			messages.push({
				role: 'user',
				content: content
			});
			messages = messages;

			await tick();
			scrollToBottom();

			loading = true;
			await chatCompletionHandler();
			messages = messages.map((message) => {
				message.done = true;
				return message;
			});

			loading = false;
			stopResponseFlag = false;
		}
	};

	onMount(async () => {
		editEnabled = localStorage.getItem('noteEditEnabled') === 'true';

		loaded = true;

		await tick();
		scrollToBottom();
	});
</script>

<div style="--d:flex; --ai:center; --mb:0.375rem; --pt:0.375rem">
	<div style="--translatex:-0.375rem; --d:flex; --ai:center">
		<button
			style="--p:0.125rem; --bgc:transparent; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
			on:click={() => {
				show = !show;
			}}
		>
			<XMark className="size-5" strokeWidth="2.5" />
		</button>
	</div>

	<div style="--weight:500; --size:1rem; --d:flex; --ai:center; --g:0.25rem">
		<div>
			{$i18n.t('Chat')}
		</div>

		<div>
			<Tooltip
				content={$i18n.t(
					'This feature is experimental and may be modified or discontinued without notice.'
				)}
				position="top"
				className="inline-block"
			>
				<span style="--c:var(--color-gray-500); --size:0.875rem">({$i18n.t('Experimental')})</span>
			</Tooltip>
		</div>
	</div>
</div>

<div style="--d:flex; --fd:column; --ai:center; --mb:0.5rem; --fx:1 1 0%; "
	class="@container">
	<div style="--d:flex; --fd:column; --jc:space-between; --w:100%; --ofy:auto; --h:100%">
		<div style="--mx:auto; --w:100%; --px-md:0; --h:100%; --pos:relative">
			<div style="--d:flex; --fd:column; --h:100%">
				<div
					style="--pb:0.625rem; --d:flex; --fd:column; --jc:space-between; --w:100%; --fx:1 1 auto; --of:auto; --h:0"
	class="scrollbar-hidden"
					id="messages-container"
					bind:this={messagesContainerElement}
					on:scroll={onScroll}
				>
					<div style="--h:100%; --w:100%; --d:flex; --fd:column">
						<div style="--fx:1 1 0%; --p:0.25rem">
							<Messages bind:messages {onInsert} />
						</div>
					</div>
				</div>

				<div style="--pb:0.5rem">
					{#if selectedContent}
						<div style="--size:0.75rem; --radius:0.75rem; --px:0.875rem; --py:0.75rem; --w:100%"
	class="markdown-prose-xs">
							<blockquote>
								<div style="--line-clamp:3">
									{selectedContent?.text}
								</div>
							</blockquote>
						</div>
					{/if}

					<MessageInput
						bind:chatInputElement
						acceptFiles={false}
						inputLoading={loading}
						showFormattingButtons={false}
						onSubmit={submitHandler}
						{onStop}
					>
						<div slot="menu" style="--d:flex; --ai:center; --jc:space-between; --g:0.5rem; --w:100%; --pr:0.25rem">
							<div>
								<Tooltip content={$i18n.t('Edit')} placement="top">
									<button
										on:click|preventDefault={() => {
											editEnabled = !editEnabled;

											localStorage.setItem('noteEditEnabled', editEnabled ? 'true' : 'false');
										}}
										disabled={streaming || loading}
										type="button"
										style="--px:0.5rem; --py:0.5rem; --d:flex; --g:0.375rem; --ai:center; --size:0.875rem; --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:300ms; --maxw:100%; --of:hidden; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800)"
	class="@xl:px-2.5 focus:outline-hidden {editEnabled
											? ' text-sky-500 dark:text-sky-300 bg-sky-50 dark:bg-sky-200/5'
											: 'bg-transparent text-gray-600 dark:text-gray-300 '} disabled:opacity-50 disabled:pointer-events-none"
									>
										<PencilSquare className="size-4" strokeWidth="1.75" />
										<span
											style="--d:block; --ws:nowrap; --of:hidden; text-overflow:ellipsis; --lh:1; --pr:0.125rem"
											>{$i18n.t('Edit')}</span
										>
									</button>
								</Tooltip>
							</div>

							<Tooltip content={selectedModelId}>
								<select
									style="--bgc:transparent; --radius:0.5rem; --py:0.25rem; --px:0.5rem; --mx:-0.125rem; --size:0.875rem; --oe:none; --w:100%; --ta:right; --pr:1.25rem"
									bind:value={selectedModelId}
								>
									{#each $models as model}
										<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)"
											>{model.name}</option
										>
									{/each}
								</select>
							</Tooltip>
						</div>
					</MessageInput>
				</div>
			</div>
		</div>
	</div>
</div>
