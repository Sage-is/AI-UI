<script lang="ts">
	import dayjs from 'dayjs';
	import { onMount, tick, getContext } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	import { mobile, settings } from '$lib/stores';

	import { generateMoACompletion } from '$lib/apis';
	import { updateChatById } from '$lib/apis/chats';
	import { createOpenAITextStream } from '$lib/apis/streaming';

	import ResponseMessage from './ResponseMessage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Merge from '$lib/components/icons/Merge.svelte';

	import Markdown from './Markdown.svelte';
	import Name from './Name.svelte';
	import Skeleton from './Skeleton.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	export let chatId;
	export let history;
	export let messageId;
	export let selectedModels = [];

	export let isLastMessage;
	export let readOnly = false;

	export let setInputText: Function = () => {};
	export let updateChat: Function;
	export let editMessage: Function;
	export let saveMessage: Function;
	export let rateMessage: Function;
	export let actionMessage: Function;

	export let submitMessage: Function;
	export let deleteMessage: Function;

	export let continueResponse: Function;
	export let regenerateResponse: Function;
	export let mergeResponses: Function;

	export let addMessages: Function;

	export let triggerScroll: Function;

	const dispatch = createEventDispatcher();

	let currentMessageId;
	let parentMessage;
	let groupedMessageIds = {};
	let groupedMessageIdsIdx = {};

	let message = JSON.parse(JSON.stringify(history.messages[messageId]));
	$: if (history.messages) {
		if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
			message = JSON.parse(JSON.stringify(history.messages[messageId]));
		}
	}

	const gotoMessage = async (modelIdx, messageIdx) => {
		// Clamp messageIdx to ensure it's within valid range
		groupedMessageIdsIdx[modelIdx] = Math.max(
			0,
			Math.min(messageIdx, groupedMessageIds[modelIdx].messageIds.length - 1)
		);

		// Get the messageId at the specified index
		let messageId = groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]];
		console.log(messageId);

		// Traverse the branch to find the deepest child message
		let messageChildrenIds = history.messages[messageId].childrenIds;
		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		// Update the current message ID in history
		history.currentId = messageId;

		// Await UI updates
		await tick();
		await updateChat();

		// Trigger scrolling after navigation
		triggerScroll();
	};

	const showPreviousMessage = async (modelIdx) => {
		groupedMessageIdsIdx[modelIdx] = Math.max(0, groupedMessageIdsIdx[modelIdx] - 1);

		let messageId = groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]];
		console.log(messageId);

		let messageChildrenIds = history.messages[messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		history.currentId = messageId;

		await tick();
		await updateChat();
		triggerScroll();
	};

	const showNextMessage = async (modelIdx) => {
		groupedMessageIdsIdx[modelIdx] = Math.min(
			groupedMessageIds[modelIdx].messageIds.length - 1,
			groupedMessageIdsIdx[modelIdx] + 1
		);

		let messageId = groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]];
		console.log(messageId);

		let messageChildrenIds = history.messages[messageId].childrenIds;

		while (messageChildrenIds.length !== 0) {
			messageId = messageChildrenIds.at(-1);
			messageChildrenIds = history.messages[messageId].childrenIds;
		}

		history.currentId = messageId;

		await tick();
		await updateChat();
		triggerScroll();
	};

	const initHandler = async () => {
		console.log('multiresponse:initHandler');
		await tick();

		currentMessageId = messageId;
		parentMessage = history.messages[messageId].parentId
			? history.messages[history.messages[messageId].parentId]
			: null;

		groupedMessageIds = parentMessage?.models.reduce((a, model, modelIdx) => {
			// Find all messages that are children of the parent message and have the same model
			let modelMessageIds = parentMessage?.childrenIds
				.map((id) => history.messages[id])
				.filter((m) => m?.modelIdx === modelIdx)
				.map((m) => m.id);

			// Legacy support for messages that don't have a modelIdx
			// Find all messages that are children of the parent message and have the same model
			if (modelMessageIds.length === 0) {
				let modelMessages = parentMessage?.childrenIds
					.map((id) => history.messages[id])
					.filter((m) => m?.model === model);

				modelMessages.forEach((m) => {
					m.modelIdx = modelIdx;
				});

				modelMessageIds = modelMessages.map((m) => m.id);
			}

			return {
				...a,
				[modelIdx]: { messageIds: modelMessageIds }
			};
		}, {});

		groupedMessageIdsIdx = parentMessage?.models.reduce((a, model, modelIdx) => {
			const idx = groupedMessageIds[modelIdx].messageIds.findIndex((id) => id === messageId);
			if (idx !== -1) {
				return {
					...a,
					[modelIdx]: idx
				};
			} else {
				return {
					...a,
					[modelIdx]: groupedMessageIds[modelIdx].messageIds.length - 1
				};
			}
		}, {});

		console.log(groupedMessageIds, groupedMessageIdsIdx);

		await tick();
	};

	const mergeResponsesHandler = async () => {
		const responses = Object.keys(groupedMessageIds).map((modelIdx) => {
			const { messageIds } = groupedMessageIds[modelIdx];
			const messageId = messageIds[groupedMessageIdsIdx[modelIdx]];

			return history.messages[messageId].content;
		});
		mergeResponses(messageId, responses, chatId);
	};

	onMount(async () => {
		await initHandler();
		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			const messageElement = document.getElementById(`message-${messageId}`);
			if (messageElement) {
				messageElement.scrollIntoView({ block: 'start' });
			}
		}
	});
</script>

{#if parentMessage}
	<div>
		<div
			style="--d:flex; scroll-snap-type:x var(--tw-scroll-snap-strictness, proximity); --tw-scroll-snap-strictness:mandatory; --ofx:auto"
	class="scrollbar-hidden"
			id="responses-container-{chatId}-{parentMessage.id}"
		>
			{#each Object.keys(groupedMessageIds) as modelIdx}
				{#if groupedMessageIdsIdx[modelIdx] !== undefined && groupedMessageIds[modelIdx].messageIds.length > 0}
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					{@const _messageId =
						groupedMessageIds[modelIdx].messageIds[groupedMessageIdsIdx[modelIdx]]}

					<div
						style="scroll-snap-align:center; --w:100%; --maxw:100%; --m:0.25rem;  --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --p:1.25rem; --radius:1rem"
	class="{history.messages[messageId]
							?.modelIdx == modelIdx
							? `bg-gray-50 dark:bg-gray-850 border-gray-100 dark:border-gray-800 border-2 ${
									$mobile ? 'min-w-full' : 'min-w-80'
								}`
							: `border-gray-100 dark:border-gray-850 border-dashed ${
									$mobile ? 'min-w-full' : 'min-w-80'
								}`}"
						on:click={async () => {
							if (messageId != _messageId) {
								let currentMessageId = _messageId;
								let messageChildrenIds = history.messages[currentMessageId].childrenIds;
								while (messageChildrenIds.length !== 0) {
									currentMessageId = messageChildrenIds.at(-1);
									messageChildrenIds = history.messages[currentMessageId].childrenIds;
								}
								history.currentId = currentMessageId;
								// await tick();
								// await updateChat();
								// triggerScroll();
							}
						}}
					>
						{#key history.currentId}
							{#if message}
								<ResponseMessage
									{chatId}
									{history}
									messageId={_messageId}
									{selectedModels}
									isLastMessage={true}
									siblings={groupedMessageIds[modelIdx].messageIds}
									gotoMessage={(message, messageIdx) => gotoMessage(modelIdx, messageIdx)}
									showPreviousMessage={() => showPreviousMessage(modelIdx)}
									showNextMessage={() => showNextMessage(modelIdx)}
									{setInputText}
									{updateChat}
									{editMessage}
									{saveMessage}
									{rateMessage}
									{deleteMessage}
									{actionMessage}
									{submitMessage}
									{continueResponse}
									regenerateResponse={async (message) => {
										regenerateResponse(message);
										await tick();
										groupedMessageIdsIdx[modelIdx] =
											groupedMessageIds[modelIdx].messageIds.length - 1;
									}}
									{addMessages}
									{readOnly}
								/>
							{/if}
						{/key}
					</div>
				{/if}
			{/each}
		</div>

		{#if !readOnly}
			{#if !Object.keys(groupedMessageIds).find((modelIdx) => {
				const { messageIds } = groupedMessageIds[modelIdx];
				const _messageId = messageIds[groupedMessageIdsIdx[modelIdx]];
				return !history.messages[_messageId]?.done ?? false;
			})}
				<div style="--d:flex; --jc:flex-end">
					<div style="--w:100%">
						{#if history.messages[messageId]?.merged?.status}
							{@const message = history.messages[messageId]?.merged}

							<div style="--w:100%; --radius:0.75rem; --pl:1.25rem; --pr:0.5rem; --py:0.5rem">
								<Name>
									{$i18n.t('Merged Response')}

									{#if message.timestamp}
										<span
											style="--as:center; --v:hidden; --c:var(--color-gray-400); --size:0.75rem; --weight:500; --tt:uppercase; --ml:0.125rem; --mt:-0.125rem"
	class="group-hover:visible"
										>
											{dayjs(message.timestamp * 1000).format('LT')}
										</span>
									{/if}
								</Name>

								<div style="--mt:0.25rem; --w:100%; --minw:100%"
	class="markdown-prose">
									{#if (message?.content ?? '') === ''}
										<Skeleton />
									{:else}
										<Markdown id={`merged`} content={message.content ?? ''} />
									{/if}
								</div>
							</div>
						{/if}
					</div>

					{#if isLastMessage}
						<div style="--fs:0; --c:var(--color-gray-600); --dark-c:var(--color-gray-500); --mt:0.25rem">
							<Tooltip content={$i18n.t('Merge Responses')} placement="bottom">
								<button
									type="button"
									id="merge-response-button"
									style="--p:0.25rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{true
										? 'visible'
										: 'invisible group-hover:visible'} regenerate-response-button"
									on:click={() => {
										mergeResponsesHandler();
									}}
								>
									<Merge className=" size-5 " />
								</button>
							</Tooltip>
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
{/if}
