<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto, invalidate, invalidateAll } from '$app/navigation';
	import { onMount, getContext, createEventDispatcher, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	import {
		archiveChatById,
		cloneChatById,
		deleteChatById,
		getAllTags,
		getChatById,
		getChatList,
		getChatListByTagName,
		getPinnedChatList,
		updateChatById
	} from '$lib/apis/chats';
	import {
		chatId,
		chatTitle as _chatTitle,
		chats,
		mobile,
		pinnedChats,
		showSidebar,
		currentChatPage,
		tags,
		selectedFolder
	} from '$lib/stores';

	import ChatMenu from './ChatMenu.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ShareChatModal from '$lib/components/chat/ShareChatModal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import { generateTitle } from '$lib/apis';

	export let className = '';

	export let id;
	export let title;

	export let selected = false;
	export let shiftKey = false;

	let chat = null;

	let mouseOver = false;
	let draggable = false;
	$: if (mouseOver) {
		loadChat();
	}

	const loadChat = async () => {
		if (!chat) {
			draggable = false;
			chat = await getChatById(localStorage.token, id);
			draggable = true;
		}
	};

	let showShareChatModal = false;
	let confirmEdit = false;

	let chatTitle = title;

	const editChatTitle = async (id, title) => {
		if (title === '') {
			toast.error($i18n.t('Title cannot be an empty string.'));
		} else {
			await updateChatById(localStorage.token, id, {
				title: title
			});

			if (id === $chatId) {
				_chatTitle.set(title);
			}

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await pinnedChats.set(await getPinnedChatList(localStorage.token));

			dispatch('change');
		}
	};

	const cloneChatHandler = async (id) => {
		const res = await cloneChatById(
			localStorage.token,
			id,
			$i18n.t('Clone of {{TITLE}}', {
				TITLE: title
			})
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			await pinnedChats.set(await getPinnedChatList(localStorage.token));
		}
	};

	const deleteChatHandler = async (id) => {
		const res = await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			tags.set(await getAllTags(localStorage.token));
			if ($chatId === id) {
				await goto('/');

				await chatId.set('');
				await tick();
			}

			dispatch('change');
		}
	};

	const archiveChatHandler = async (id) => {
		await archiveChatById(localStorage.token, id);
		dispatch('change');
	};

	let itemElement;

	let generating = false;
	let doubleClicked = false;
	let dragged = false;
	let x = 0;
	let y = 0;

	const dragImage = new Image();
	dragImage.src =
		'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

	const onDragStart = (event) => {
		event.stopPropagation();

		event.dataTransfer.setDragImage(dragImage, 0, 0);

		// Set the data to be transferred
		event.dataTransfer.setData(
			'text/plain',
			JSON.stringify({
				type: 'chat',
				id: id,
				item: chat
			})
		);

		dragged = true;
		itemElement.style.opacity = '0.4';
		document.body.style.cursor = 'grabbing';
	};

	const onDrag = (event) => {
		event.stopPropagation();

		x = event.clientX;
		y = event.clientY;
	};

	const onDragEnd = (event) => {
		event.stopPropagation();

		itemElement.style.opacity = '';
		document.body.style.cursor = '';
		dragged = false;
	};

	onMount(() => {
		if (itemElement) {
			// Event listener for when dragging starts
			itemElement.addEventListener('dragstart', onDragStart);
			// Event listener for when dragging occurs (optional)
			itemElement.addEventListener('drag', onDrag);
			// Event listener for when dragging ends
			itemElement.addEventListener('dragend', onDragEnd);
		}
	});

	onDestroy(() => {
		if (itemElement) {
			itemElement.removeEventListener('dragstart', onDragStart);
			itemElement.removeEventListener('drag', onDrag);
			itemElement.removeEventListener('dragend', onDragEnd);
		}
	});

	let showDeleteConfirm = false;

	const chatTitleInputKeydownHandler = (e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			setTimeout(() => {
				const input = document.getElementById(`chat-title-input-${id}`);
				if (input) input.blur();
			}, 0);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			confirmEdit = false;
			chatTitle = '';
		}
	};

	const renameHandler = async () => {
		chatTitle = title;
		confirmEdit = true;

		await tick();

		setTimeout(() => {
			const input = document.getElementById(`chat-title-input-${id}`);
			if (input) input.focus();
		}, 0);
	};

	const generateTitleHandler = async () => {
		generating = true;
		if (!chat) {
			chat = await getChatById(localStorage.token, id);
		}

		const messages = (chat.chat?.messages ?? []).map((message) => {
			return {
				role: message.role,
				content: message.content
			};
		});

		const model = chat.chat.models.at(0) ?? chat.models.at(0) ?? '';

		chatTitle = '';

		const generatedTitle = await generateTitle(localStorage.token, model, messages).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (generatedTitle) {
			if (generatedTitle !== title) {
				editChatTitle(id, generatedTitle);
			}

			confirmEdit = false;
		} else {
			chatTitle = title;
		}

		generating = false;
	};
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={id} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		deleteChatHandler(id);
	}}
>
	<div style="--size:0.8rem; --c:var(--color-gray-500); --fx:1 1 0%; --line-clamp:3">
		{$i18n.t('This will delete')} <span style="--weight:600">{title}</span>.
	</div>
</DeleteConfirmDialog>

{#if dragged && x && y}
	<DragGhost {x} {y}>
		<div
			style="--bgc:rgb(0 0 0 / 0.8); backdrop-filter:blur(40px); --px:0.5rem; --py:0.2rem; --radius:0.5rem; --w:fit-content; --maxw:10rem"
		>
			<div style="--d:flex; --ai:center; --g:0.2rem">
				<Document className=" size-[18px]" strokeWidth="2" />
				<div style="--size:0.6rem; --c:#fff; --line-clamp:1">
					{title}
				</div>
			</div>
		</div>
	</DragGhost>
{/if}

<div
	bind:this={itemElement}
	style="--w:100%; --pos:relative"
	class="{className} group"
	draggable={draggable && !confirmEdit}
>
	{#if confirmEdit}
		<div
			id="chat-title-input-container-{id}"
			style="--radius:9999px; --w:100%; --m:0; {id === $chatId || confirmEdit
				? '--bg: var(--color-gray-100); --dark-bg: var(--color-gray-900);'
				: selected
					? '--bg: var(--color-gray-100); --dark-bg: var(--color-gray-950);'
					: '--bg: transparent; --dark-bg: transparent;'}"
		>
			<input
				id="chat-title-input-{id}"
				bind:value={chatTitle}
				style="--bgc:transparent; --w:100%; --oe:none; --mr:2.5rem"
				placeholder={generating ? $i18n.t('Generating...') : ''}
				on:keydown={chatTitleInputKeydownHandler}
				on:blur={async (e) => {
					// check if target is generate button
					if (e.relatedTarget?.id === 'generate-title-button') {
						return;
					}

					if (doubleClicked) {
						e.preventDefault();
						e.stopPropagation();

						await tick();
						setTimeout(() => {
							const input = document.getElementById(`chat-title-input-${id}`);
							if (input) input.focus();
						}, 0);

						doubleClicked = false;
						return;
					}

					if (chatTitle !== title) {
						editChatTitle(id, chatTitle);
					}

					confirmEdit = false;
					chatTitle = '';
				}}
			/>
		</div>
	{:else}
		<a
			style="--w:100%; --d:flex; --jc:space-between; --radius:0.5rem; --px:11px; --py:6px; --ws:nowrap; text-overflow:ellipsis"
			class={id === $chatId || confirmEdit
				? 'bg-gray-100 dark:bg-gray-900'
				: selected
					? 'bg-gray-100 dark:bg-gray-950'
					: ' group-hover:bg-gray-100 dark:group-hover:bg-gray-950'}
			href="/c/{id}"
			on:click={() => {
				dispatch('select');

				if (
					$selectedFolder &&
					!($selectedFolder?.items?.chats.map((chat) => chat.id) ?? []).includes(id)
				) {
					selectedFolder.set(null); // Reset selected folder if the chat is not in it
				}

				if ($mobile) {
					showSidebar.set(false);
				}
			}}
			on:dblclick={async (e) => {
				e.preventDefault();
				e.stopPropagation();

				doubleClicked = true;
				renameHandler();
			}}
			on:mouseenter={(e) => {
				mouseOver = true;
			}}
			on:mouseleave={(e) => {
				mouseOver = false;
			}}
			on:focus={(e) => {}}
			draggable="false"
		>
			<div style="--d:flex; --as:center; --fx:1 1 0%; --w:100%">
				<div dir="auto" style="--ta:left; --as:center; --of:hidden; --w:100%; --h:20px">
					{title}
				</div>
			</div>
		</a>
	{/if}

	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		style="--pos:absolute; --top:50%; --translatey:-50%; --py:0.2rem; --pr:0.125rem;
			--mr:0.4rem; --pl:1.2rem;
			--bgi:linear-gradient(270deg, var(--tw-gradient-stops));
			--tw-gradient-to:transparent;"
		class="{id === $chatId || confirmEdit
			? 'from-gray-100 dark:from-gray-900'
			: selected
				? 'from-gray-100 dark:from-gray-950'
				: 'invisible group-hover:visible from-gray-100 dark:from-gray-950'} {className === 'pr-2'
			? 'right-[8px]'
			: 'right-1'} from-80%"
		on:mouseenter={(e) => {
			mouseOver = true;
		}}
		on:mouseleave={(e) => {
			mouseOver = false;
		}}
		>
		{#if confirmEdit}
			<div
				style="--d:flex; --as:center; --ai:center; --g:0.4rem; --z:10; --translatex:-0.5px"
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
						}}
					>
						<Sparkles strokeWidth="2" />
					</button>
				</Tooltip>
			</div>
		{:else if shiftKey && mouseOver}
			<div style="--d:flex; --ai:center; --as:center; --g:0.4rem">
				<Tooltip content={$i18n.t('Archive')} className="flex items-center">
					<button
						style="--as:center; --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							archiveChatHandler(id);
						}}
						type="button"
					>
						<ArchiveBox className="size-4  translate-y-[0.5px]" strokeWidth="2" />
					</button>
				</Tooltip>

				<Tooltip content={$i18n.t('Delete')}>
					<button
						style="--as:center; --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							deleteChatHandler(id);
						}}
						type="button"
					>
						<GarbageBin strokeWidth="2" />
					</button>
				</Tooltip>
			</div>
		{:else}
			<div style="--d:flex; --as:center; --z:10; --ai:flex-end">
				<ChatMenu
					chatId={id}
					cloneChatHandler={() => {
						cloneChatHandler(id);
					}}
					shareHandler={() => {
						showShareChatModal = true;
					}}
					archiveChatHandler={() => {
						archiveChatHandler(id);
					}}
					{renameHandler}
					deleteHandler={() => {
						showDeleteConfirm = true;
					}}
					onClose={() => {
						dispatch('unselect');
					}}
					on:change={async () => {
						dispatch('change');
					}}
					on:tag={(e) => {
						dispatch('tag', e.detail);
					}}
				>
					<button
						aria-label="Chat Menu"
						style="--as:center; --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --m:0"
						on:click={() => {
							dispatch('select');
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
							/>
						</svg>
					</button>
				</ChatMenu>

				{#if id === $chatId}
					<!-- Shortcut support using "delete-chat-button" id -->
					<button
						style="--d:none"
						id="delete-chat-button"
						on:click={() => {
							showDeleteConfirm = true;
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
							/>
						</svg>
					</button>
				{/if}
			</div>
		{/if}
	</div>
</div>
