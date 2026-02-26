<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import SearchInput from './Sidebar/SearchInput.svelte';
	import { getChatById, getChatList, getChatListBySearchText } from '$lib/apis/chats';
	import Spinner from '../common/Spinner.svelte';

	import dayjs from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import Loader from '../common/Loader.svelte';
	import { createMessagesList } from '$lib/utils';
	import { user, searchQuery } from '$lib/stores';
	import Messages from '../chat/Messages.svelte';
	dayjs.extend(calendar);

	export let show = false;
	export let onClose = () => {};

	let query = '';
	let page = 1;

	let chatList = null;

	let chatListLoading = false;
	let allChatsLoaded = false;

	let searchDebounceTimeout;

	let selectedIdx = 0;

	let selectedChat = null;

	let selectedModels = [''];
	let history = null;
	let messages = null;

	$: if (!chatListLoading && chatList) {
		loadChatPreview(selectedIdx);
	}

	const loadChatPreview = async (selectedIdx) => {
		if (!chatList || chatList.length === 0) {
			selectedChat = null;
			messages = null;
			history = null;
			selectedModels = [''];
			return;
		}

		const chatId = chatList[selectedIdx].id;

		const chat = await getChatById(localStorage.token, chatId).catch(async (error) => {
			return null;
		});

		if (chat) {
			if (chat?.chat?.history) {
				selectedModels =
					(chat?.chat?.models ?? undefined) !== undefined
						? chat?.chat?.models
						: [chat?.chat?.models ?? ''];

				history = chat?.chat?.history;
				messages = createMessagesList(chat?.chat?.history, chat?.chat?.history?.currentId);

				// scroll to the bottom of the messages container
				await tick();
				const messagesContainerElement = document.getElementById('chat-preview');
				if (messagesContainerElement) {
					messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
				}
			} else {
				messages = [];
			}
		} else {
			toast.error($i18n.t('Failed to load chat preview'));
			selectedChat = null;
			messages = null;
			history = null;
			selectedModels = [''];
			return;
		}
	};

	const searchHandler = async () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		page = 1;
		chatList = null;
		if (query === '') {
			chatList = await getChatList(localStorage.token, page);
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				chatList = await getChatListBySearchText(localStorage.token, query, page);
			}, 500);
		}

		selectedChat = null;
		messages = null;
		history = null;
		selectedModels = [''];

		if ((chatList ?? []).length === 0) {
			allChatsLoaded = true;
		} else {
			allChatsLoaded = false;
		}
	};

	const loadMoreChats = async () => {
		chatListLoading = true;
		page += 1;

		let newChatList = [];

		if (query) {
			newChatList = await getChatListBySearchText(localStorage.token, query, page);
		} else {
			newChatList = await getChatList(localStorage.token, page);
		}

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;

		if (newChatList.length > 0) {
			chatList = [...chatList, ...newChatList];
		}

		chatListLoading = false;
	};

	const init = () => {
		if ($searchQuery) {
			query = $searchQuery;
			searchQuery.set('');
		}
		searchHandler();
	};

	const onKeyDown = (e) => {
		if (e.code === 'Escape') {
			show = false;
			onClose();
		} else if (e.code === 'Enter' && (chatList ?? []).length > 0) {
			const item = document.querySelector(`[data-arrow-selected="true"]`);
			if (item) {
				item?.click();
			}

			show = false;
			return;
		} else if (e.code === 'ArrowDown') {
			const searchInput = document.getElementById('search-input');

			if (searchInput) {
				// check if focused on the search input
				if (document.activeElement === searchInput) {
					searchInput.blur();
					selectedIdx = 0;
					return;
				}
			}

			selectedIdx = Math.min(selectedIdx + 1, (chatList ?? []).length - 1);
		} else if (e.code === 'ArrowUp') {
			if (selectedIdx === 0) {
				const searchInput = document.getElementById('search-input');

				if (searchInput) {
					// check if focused on the search input
					if (document.activeElement !== searchInput) {
						searchInput.focus();
						selectedIdx = 0;
						return;
					}
				}
			}

			selectedIdx = Math.max(selectedIdx - 1, 0);
		}

		const item = document.querySelector(`[data-arrow-selected="true"]`);
		item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
	};

	onMount(() => {
		init();

		document.addEventListener('keydown', onKeyDown);
	});

	onDestroy(() => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}
		document.removeEventListener('keydown', onKeyDown);
	});
</script>

<Modal size="xl" bind:show>
	<div style="--py:0.625rem; --dark-c:var(--color-gray-300); --c:var(--color-gray-700)">
		<div style="--px:0.875rem; --pb:0.375rem">
			<SearchInput
				bind:value={query}
				on:input={searchHandler}
				placeholder={$i18n.t('Search')}
				showClearButton={true}
				onKeydown={(e) => {
					console.log('e', e);

					if (e.code === 'Enter' && (chatList ?? []).length > 0) {
						const item = document.querySelector(`[data-arrow-selected="true"]`);
						if (item) {
							item?.click();
						}

						show = false;
						return;
					} else if (e.code === 'ArrowDown') {
						selectedIdx = Math.min(selectedIdx + 1, (chatList ?? []).length - 1);
					} else if (e.code === 'ArrowUp') {
						selectedIdx = Math.max(selectedIdx - 1, 0);
					} else {
						selectedIdx = 0;
					}

					const item = document.querySelector(`[data-arrow-selected="true"]`);
					item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
				}}
			/>
		</div>

		<!-- <hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.25rem" /> -->

		<div style="--d:flex; --px:0.75rem; --pb:0.25rem">
			<div
				style="--d:flex; --fd:column; --ofy:auto; --h:24rem; --h-md:40rem; --maxh:100%; --w:100%; --fx:1 1 0%"
	class="scrollbar-hidden"
			>
				{#if chatList}
					{#if chatList.length === 0}
						<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --ta:center; --px:1.25rem">
							{$i18n.t('No results found')}
						</div>
					{/if}

					{#each chatList as chat, idx (chat.id)}
						{#if idx === 0 || (idx > 0 && chat.time_range !== chatList[idx - 1].time_range)}
							<div
								style="--w:100%; --size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500); --weight:500;  --px:0.5rem"
	class="{idx === 0
									? ''
									: 'pt-5'}"
							>
								{$i18n.t(chat.time_range)}
								<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
							</div>
						{/if}

						<a
							style="--w:100%; --d:flex; --jc:space-between; --ai:center; --radius:0.5rem; --size:0.875rem; --py:0.5rem; --px:0.75rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850)"
	class="{selectedIdx ===
							idx
								? 'bg-gray-50 dark:bg-gray-850'
								: ''}"
							href="/c/{chat.id}"
							draggable="false"
							data-arrow-selected={selectedIdx === idx ? 'true' : undefined}
							on:mouseenter={() => {
								selectedIdx = idx;
							}}
							on:click={() => {
								show = false;
								onClose();
							}}
						>
							<div style="--fx:1 1 0%">
								<div style="text-overflow:ellipsis; --line-clamp:1; --w:100%">
									{chat?.title}
								</div>
							</div>

							<div style="--pl:0.75rem; --fs:0; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --size:0.75rem">
								{dayjs(chat?.updated_at * 1000).calendar()}
							</div>
						</a>
					{/each}

					{#if !allChatsLoaded}
						<Loader
							on:visible={(e) => {
								if (!chatListLoading) {
									loadMoreChats();
								}
							}}
						>
							<div style="--w:100%; --d:flex; --jc:center; --py:0.25rem; --size:0.75rem; animation:pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; --ai:center; --g:0.5rem">
								<Spinner className=" size-4" />
								<div class=" ">Loading...</div>
							</div>
						</Loader>
					{/if}
				{:else}
					<div style="--w:100%; --h:100%; --d:flex; --jc:center; --ai:center">
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>
			<div
				id="chat-preview"
				style="--d:none; --d-md:flex; --fx-md:2 1 0%; --w:100%; --ofy:auto; --h:24rem; --h-md:40rem"
	class="scrollbar-hidden"
			>
				{#if messages === null}
					<div
						style="--w:100%; --h:100%; --d:flex; --jc:center; --ai:center; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --size:0.875rem"
					>
						{$i18n.t('Select a conversation to preview')}
					</div>
				{:else}
					<div style="--w:100%; --h:100%; --d:flex; --fd:column">
						<Messages
							className="h-full flex pt-4 pb-8 w-full"
							user={$user}
							readOnly={true}
							{selectedModels}
							bind:history
							bind:messages
							autoScroll={true}
							sendPrompt={() => {}}
							continueResponse={() => {}}
							regenerateResponse={() => {}}
						/>
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
