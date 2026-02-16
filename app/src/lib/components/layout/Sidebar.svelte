<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';

	import { goto } from '$app/navigation';
	import {
		user,
		chats,
		settings,
		showSettings,
		chatId,
		tags,
		showSidebar,
		showSearch,
		mobile,
		showArchivedChats,
		pinnedChats,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		channels,
		socket,
		config,
		isApp,
		models,
		selectedFolder
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import {
		getChatList,
		getAllTags,
		getPinnedChatList,
		toggleChatPinnedStatusById,
		getChatById,
		updateChatFolderIdById,
		importChat
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { getBranding } from '$lib/apis/configs';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import ArchivedChatsModal from './ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import AddFilesPlaceholder from '../AddFilesPlaceholder.svelte';
	import Folder from '../common/Folder.svelte';
	import Plus from '../icons/Plus.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/spaces';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Home from '../icons/Home.svelte';
	import Search from '../icons/Search.svelte';
	import SearchModal from './SearchModal.svelte';
	import FolderModal from './Sidebar/Folders/FolderModal.svelte';

	const BREAKPOINT = 768;

	let navElement;
	let shiftKey = false;

	let branding: { logo_url?: string; logo_dark_url?: string } = {};
	let selectedChatId = null;
	let showDropdown = false;
	let showPinnedChat = true;

	let showCreateChannel = false;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let showCreateFolderModal = false;
	let folders = {};
	let newFolderId = null;

	const initFolders = async () => {
		const folderList = await getFolders(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [];
		});

		folders = {};

		// First pass: Initialize all folder entries
		for (const folder of folderList) {
			// Ensure folder is added to folders with its data
			folders[folder.id] = { ...(folders[folder.id] || {}), ...folder };

			if (newFolderId && folder.id === newFolderId) {
				folders[folder.id].new = true;
				newFolderId = null;
			}
		}

		// Second pass: Tie child folders to their parents
		for (const folder of folderList) {
			if (folder.parent_id) {
				// Ensure the parent folder is initialized if it doesn't exist
				if (!folders[folder.parent_id]) {
					folders[folder.parent_id] = {}; // Create a placeholder if not already present
				}

				// Initialize childrenIds array if it doesn't exist and add the current folder id
				folders[folder.parent_id].childrenIds = folders[folder.parent_id].childrenIds
					? [...folders[folder.parent_id].childrenIds, folder.id]
					: [folder.id];

				// Sort the children by updated_at field
				folders[folder.parent_id].childrenIds.sort((a, b) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
	};

	const createFolder = async ({ name, data }) => {
		if (name === '') {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const rootFolders = Object.values(folders).filter((folder) => folder.parent_id === null);
		if (rootFolders.find((folder) => folder.name.toLowerCase() === name.toLowerCase())) {
			// If a folder with the same name already exists, append a number to the name
			let i = 1;
			while (
				rootFolders.find((folder) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase())
			) {
				i++;
			}

			name = `${name} ${i}`;
		}

		// Add a dummy folder to the list to show the user that the folder is being created
		const tempId = uuidv4();
		folders = {
			...folders,
			tempId: {
				id: tempId,
				name: name,
				created_at: Date.now(),
				updated_at: Date.now()
			}
		};

		const res = await createNewFolder(localStorage.token, {
			name,
			data
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// newFolderId = res.id;
			await initFolders();
		}
	};

	const initChannels = async () => {
		await channels.set(await getChannels(localStorage.token));
	};

	const initChatList = async () => {
		// Reset pagination variables
		tags.set(await getAllTags(localStorage.token));
		pinnedChats.set(await getPinnedChatList(localStorage.token));
		initFolders();

		currentChatPage.set(1);
		allChatsLoaded = false;

		await chats.set(await getChatList(localStorage.token, $currentChatPage));

		// Enable pagination
		scrollPaginationEnabled.set(true);
	};

	const loadMoreChats = async () => {
		chatListLoading = true;

		currentChatPage.set($currentChatPage + 1);

		let newChatList = [];

		newChatList = await getChatList(localStorage.token, $currentChatPage);

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;
		await chats.set([...($chats ? $chats : []), ...newChatList]);

		chatListLoading = false;
	};

	const importChatHandler = async (items, pinned = false, folderId = null) => {
		console.log('importChatHandler', items, pinned, folderId);
		for (const item of items) {
			console.log(item);
			if (item.chat) {
				await importChat(
					localStorage.token,
					item.chat,
					item?.meta ?? {},
					pinned,
					folderId,
					item?.created_at ?? null,
					item?.updated_at ?? null
				);
			}
		}

		initChatList();
	};

	const inputFilesHandler = async (files) => {
		console.log(files);

		for (const file of files) {
			const reader = new FileReader();
			reader.onload = async (e) => {
				const content = e.target.result;

				try {
					const chatItems = JSON.parse(content);
					importChatHandler(chatItems);
				} catch {
					toast.error($i18n.t(`Invalid file format.`));
				}
			};

			reader.readAsText(file);
		}
	};

	const tagEventHandler = async (type, tagName, chatId) => {
		console.log(type, tagName, chatId);
		if (type === 'delete') {
			initChatList();
		} else if (type === 'add') {
			initChatList();
		}
	};

	let draggedOver = false;

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
		console.log(e); // Log the drop event

		// Perform file drop check and handle it accordingly
		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);

			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles); // Log the dropped files
				inputFilesHandler(inputFiles); // Handle the dropped files
			}
		}

		draggedOver = false; // Reset draggedOver status after drop
	};

	let touchstart;
	let touchend;

	function checkDirection() {
		const screenWidth = window.innerWidth;
		const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
		if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
			if (touchend.screenX < touchstart.screenX) {
				showSidebar.set(false);
			}
			if (touchend.screenX > touchstart.screenX) {
				showSidebar.set(true);
			}
		}
	}

	const onTouchStart = (e) => {
		touchstart = e.changedTouches[0];
		console.log(touchstart.clientX);
	};

	const onTouchEnd = (e) => {
		touchend = e.changedTouches[0];
		checkDirection();
	};

	const onKeyDown = (e) => {
		if (e.key === 'Shift') {
			shiftKey = true;
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
		selectedChatId = null;
	};

	onMount(async () => {
		showPinnedChat = localStorage?.showPinnedChat ? localStorage.showPinnedChat === 'true' : true;

		// Load branding for sidebar logo
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}

		mobile.subscribe((value) => {
			if ($showSidebar && value) {
				showSidebar.set(false);
			}

			if ($showSidebar && !value) {
				const navElement = document.getElementsByTagName('nav')[0];
				if (navElement) {
					navElement.style['-webkit-app-region'] = 'drag';
				}
			}

			if (!$showSidebar && !value) {
				showSidebar.set(true);
			}
		});

		showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);
		showSidebar.subscribe((value) => {
			localStorage.sidebar = value;

			// nav element is not available on the first render
			const navElement = document.getElementsByTagName('nav')[0];

			if (navElement) {
				if ($mobile) {
					if (!value) {
						navElement.style['-webkit-app-region'] = 'drag';
					} else {
						navElement.style['-webkit-app-region'] = 'no-drag';
					}
				} else {
					navElement.style['-webkit-app-region'] = 'drag';
				}
			}
		});

		chats.subscribe((value) => {
			initFolders();
		});

		await initChannels();
		await initChatList();

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		const dropZone = document.getElementById('sidebar');

		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);

		window.removeEventListener('touchstart', onTouchStart);
		window.removeEventListener('touchend', onTouchEnd);

		window.removeEventListener('focus', onFocus);
		window.removeEventListener('blur', onBlur);

		const dropZone = document.getElementById('sidebar');

		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});
</script>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	onUpdate={async () => {
		await initChatList();
	}}
/>

<ChannelModal
	bind:show={showCreateChannel}
	onSubmit={async ({ name, access_control }) => {
		const res = await createNewChannel(localStorage.token, {
			name: name,
			access_control: access_control
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			$socket.emit('join-channels', { auth: { token: $user?.token } });
			await initChannels();
			showCreateChannel = false;
		}
	}}
/>

<FolderModal
	bind:show={showCreateFolderModal}
	onSubmit={async (folder) => {
		await createFolder(folder);
		showCreateFolderModal = false;
	}}
/>

<!-- svelte-ignore a11y-no-static-element-interactions -->

{#if $showSidebar}
	<div
		style="--pos:fixed; --d-md:none; --z:40; --top:0; --right:0; --left:0; --bottom:0; --bgc:rgb(0 0 0 / 0.6); --w:100%; --minh:100vh; --h:100vh; --d:flex; --jc:center; --of:hidden; overscroll-behavior:contain"
	class="{$isApp
			? ' ml-[4.5rem] md:ml-0'
			: ''}"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

<SearchModal
	bind:show={$showSearch}
	onClose={() => {
		if ($mobile) {
			showSidebar.set(false);
		}
	}}
/>

<div
	bind:this={navElement}
	id="sidebar"
	style="--h:100vh; --maxh:100dvh; --minh:100vh; --us:none; --fs:0; --bgc:var(--color-gray-50, #f9f9f9); --c:var(--color-gray-900, #171717); --dark-bgc:var(--color-gray-950, #0d0d0d); --dark-c:var(--color-gray-200, #e3e3e3); --size:0.875rem; --pos:fixed; --z:50; --top:0; --left:0; --ofx:hidden"
	class="{$showSidebar
		? 'md:relative w-[260px] max-w-[260px]'
		: '-translate-x-[260px] w-[0px]'} {$isApp
		? `ml-[4.5rem] md:ml-0 `
		: 'transition-width duration-200 ease-in-out'}"
	data-state={$showSidebar}
>
	<div
		style="--py:0.5rem; --my:auto; --d:flex; --fd:column; --jc:space-between; --h:100vh; --maxh:100dvh; --w:260px; --ofx:hidden; --z:50"
	class="{$showSidebar
			? ''
			: 'invisible'}"
	>
		<div style="--px:0.375rem; --d:flex; --jc:space-between; --g:0.25rem; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4)">
			<button
				style="--cur:pointer; --p:7px; --d:flex; --radius:0.75rem; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-900, #171717); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					showSidebar.set(!$showSidebar);
				}}
			>
				<div style="--m:auto; --as:center">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						style="--w:1.25rem; --h:1.25rem"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"
						/>
					</svg>
				</div>
			</button>

			<a
				id="sidebar-new-chat-button"
				style="--d:flex; --jc:space-between; --ai:center; --fx:1 1 0%; --radius:0.5rem; --px:0.5rem; --py:0.25rem; --h:100%; --ta:right; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-900, #171717); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="no-drag-region"
				href="/"
				draggable="false"
				on:click={async () => {
					selectedChatId = null;
					selectedFolder.set(null);

					if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
						await temporaryChatEnabled.set(true);
					} else {
						await temporaryChatEnabled.set(false);
					}

					setTimeout(() => {
						if ($mobile) {
							showSidebar.set(false);
						}
					}, 0);
				}}
			>
				<div style="--d:flex; --ai:center">
					<div style="--as:center; --mx:0.375rem">
						<img
							crossorigin="anonymous"
							src={branding?.logo_url || `${WEBUI_BASE_URL}/static/icons/favicon.png`}
							style="--w:1.25rem; --h:1.25rem; --translatex:-0.375rem; --radius:9999px"
	class="sidebar-new-chat-icon"
							alt="logo"
						/>
					</div>
					<div style="--as:center; --size:0.875rem; --c:var(--color-gray-850, #262626); --dark-c:#fff"
	class="font-primary">
						{$i18n.t('New Chat')}
					</div>
				</div>

				<div>
					<PencilSquare className=" size-5" strokeWidth="2" />
				</div>
			</a>
		</div>

		<!-- {#if $user?.role === 'admin'}
			<div style="--px:0.375rem; --d:flex; --jc:center; --c:var(--color-gray-800, #333); --dark-c:var(--color-gray-200, #e3e3e3)">
				<a
					style="--fg:1; --d:flex; --ai:center; --g:0.75rem; --radius:0.5rem; --px:0.5rem; --py:7px; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-900, #171717); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					href="/home"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
					draggable="false"
				>
					<div style="--as:center">
						<Home strokeWidth="2" className="size-[1.1rem]" />
					</div>

					<div style="--d:flex; --as:center; --translatey:0.5px">
						<div style="--as:center; --weight:500; --size:0.875rem"
	class="font-primary">{$i18n.t('Home')}</div>
					</div>
				</a>
			</div>
		{/if} -->

		<div style="--px:0.375rem; --d:flex; --jc:center; --c:var(--color-gray-800, #333); --dark-c:var(--color-gray-200, #e3e3e3)">
			<button
				style="--fg:1; --d:flex; --ai:center; --g:0.75rem; --radius:0.5rem; --px:0.5rem; --py:7px; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-900, #171717); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --oe:2px solid transparent"
				on:click={() => {
					showSearch.set(true);
				}}
				draggable="false"
			>
				<div style="--as:center">
					<Search strokeWidth="2" className="size-[1.1rem]" />
				</div>

				<div style="--d:flex; --as:center; --translatey:0.5px">
					<div style="--as:center; --size:0.875rem"
	class="font-primary">{$i18n.t('Search')}</div>
				</div>
			</button>
		</div>

		{#if ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))}
			<div style="--px:0.375rem; --d:flex; --jc:center; --c:var(--color-gray-800, #333); --dark-c:var(--color-gray-200, #e3e3e3)">
				<a
					style="--fg:1; --d:flex; --ai:center; --g:0.75rem; --radius:0.5rem; --px:0.5rem; --py:7px; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-900, #171717); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					href="/notes"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
					draggable="false"
				>
					<div style="--as:center">
						<svg
							style="--w:1rem; --h:1rem"
							aria-hidden="true"
							xmlns="http://www.w3.org/2000/svg"
							width="24"
							height="24"
							fill="none"
							viewBox="0 0 24 24"
						>
							<path
								stroke="currentColor"
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 3v4a1 1 0 0 1-1 1H5m4 8h6m-6-4h6m4-8v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7.914a1 1 0 0 1 .293-.707l3.914-3.914A1 1 0 0 1 9.914 3H18a1 1 0 0 1 1 1Z"
							/>
						</svg>
					</div>

					<div style="--d:flex; --as:center; --translatey:0.5px">
						<div style="--as:center; --size:0.875rem"
	class="font-primary">{$i18n.t('Notes')}</div>
					</div>
				</a>
			</div>
		{/if}

		{#if $user?.role === 'admin' || $user?.permissions?.workshop?.models || $user?.permissions?.workshop?.knowledge || $user?.permissions?.workshop?.prompts || $user?.permissions?.workshop?.tools}
			<div style="--px:0.375rem; --d:flex; --jc:center; --c:var(--color-gray-800, #333); --dark-c:var(--color-gray-200, #e3e3e3)">
				<a
					style="--fg:1; --d:flex; --ai:center; --g:0.75rem; --radius:0.5rem; --px:0.5rem; --py:7px; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-900, #171717); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					href="/workshop"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
					draggable="false"
				>
					<div style="--as:center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							style="--w:1.1rem; --h:1.1rem"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
							/>
						</svg>
					</div>

					<div style="--d:flex; --as:center; --translatey:0.5px">
						<div style="--as:center; --size:0.875rem"
	class="font-primary">{$i18n.t('Workshop')}</div>
					</div>
				</a>
			</div>
		{/if}

		<div style="--pos:relative; --d:flex; --fd:column; --fx:1 1 0%; --ofy:auto; --ofx:hidden">
			{#if ($models ?? []).length > 0 && ($settings?.pinnedModels ?? []).length > 0}
				<div style="--mt:0.125rem">
					{#each $settings.pinnedModels as modelId (modelId)}
						{@const model = $models.find((model) => model.id === modelId)}
						{#if model}
							<div style="--px:0.375rem; --d:flex; --jc:center; --c:var(--color-gray-800, #333); --dark-c:var(--color-gray-200, #e3e3e3)">
								<a
									style="--fg:1; --d:flex; --ai:center; --g:0.625rem; --radius:0.5rem; --px:0.5rem; --py:7px; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-900, #171717); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									href="/?model={modelId}"
									on:click={() => {
										selectedChatId = null;
										chatId.set('');

										if ($mobile) {
											showSidebar.set(false);
										}
									}}
									draggable="false"
								>
									<div style="--as:center; --fs:0">
										<img
											crossorigin="anonymous"
											src={model?.info?.meta?.profile_image_url ??
												branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
											style="--w:1.25rem; --h:1.25rem; --radius:9999px; --translatex:-0.5px"
											alt="logo"
										/>
									</div>

									<div style="--d:flex; --as:center; --translatey:0.5px">
										<div style="--as:center; --size:0.875rem; --line-clamp:1"
	class="font-primary">
											{model?.name ?? modelId}
										</div>
									</div>
								</a>
							</div>
						{/if}
					{/each}
				</div>
			{/if}

			{#if $config?.features?.enable_channels && ($user?.role === 'admin' || $channels.length > 0)}
				<Folder
					className="px-2 mt-0.5"
					name={$i18n.t('Spaces')}
					dragAndDrop={false}
					onAdd={async () => {
						if ($user?.role === 'admin') {
							await tick();

							setTimeout(() => {
								showCreateChannel = true;
							}, 0);
						}
					}}
					onAddLabel={$i18n.t('Create Channel')}
				>
					{#each $channels as channel}
						<ChannelItem
							{channel}
							onUpdate={async () => {
								await initChannels();
							}}
						/>
					{/each}
				</Folder>
			{/if}

			<Folder
				className="px-2 mt-0.5"
				name={$i18n.t('Chats')}
				onAdd={() => {
					showCreateFolderModal = true;
				}}
				onAddLabel={$i18n.t('New Folder')}
				on:change={async (e) => {
					selectedFolder.set(null);
					await goto('/');
				}}
				on:import={(e) => {
					importChatHandler(e.detail);
				}}
				on:drop={async (e) => {
					const { type, id, item } = e.detail;

					if (type === 'chat') {
						let chat = await getChatById(localStorage.token, id).catch((error) => {
							return null;
						});
						if (!chat && item) {
							chat = await importChat(
								localStorage.token,
								item.chat,
								item?.meta ?? {},
								false,
								null,
								item?.created_at ?? null,
								item?.updated_at ?? null
							);
						}

						if (chat) {
							console.log(chat);
							if (chat.folder_id) {
								const res = await updateChatFolderIdById(localStorage.token, chat.id, null).catch(
									(error) => {
										toast.error(`${error}`);
										return null;
									}
								);
							}

							if (chat.pinned) {
								const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
							}

							initChatList();
						}
					} else if (type === 'folder') {
						if (folders[id].parent_id === null) {
							return;
						}

						const res = await updateFolderParentIdById(localStorage.token, id, null).catch(
							(error) => {
								toast.error(`${error}`);
								return null;
							}
						);

						if (res) {
							await initFolders();
						}
					}
				}}
			>
				{#if $pinnedChats.length > 0}
					<div style="--d:flex; --fd:column; --g:0.25rem; --radius:0.75rem">
						<Folder
							className=""
							bind:open={showPinnedChat}
							on:change={(e) => {
								localStorage.setItem('showPinnedChat', e.detail);
								console.log(e.detail);
							}}
							on:import={(e) => {
								importChatHandler(e.detail, true);
							}}
							on:drop={async (e) => {
								const { type, id, item } = e.detail;

								if (type === 'chat') {
									let chat = await getChatById(localStorage.token, id).catch((error) => {
										return null;
									});
									if (!chat && item) {
										chat = await importChat(
											localStorage.token,
											item.chat,
											item?.meta ?? {},
											false,
											null,
											item?.created_at ?? null,
											item?.updated_at ?? null
										);
									}

									if (chat) {
										console.log(chat);
										if (chat.folder_id) {
											const res = await updateChatFolderIdById(
												localStorage.token,
												chat.id,
												null
											).catch((error) => {
												toast.error(`${error}`);
												return null;
											});
										}

										if (!chat.pinned) {
											const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
										}

										initChatList();
									}
								}
							}}
							name={$i18n.t('Pinned')}
						>
							<div
								style="--ml:0.75rem; --pl:0.25rem; --mt:1px; --d:flex; --fd:column; --ofy:auto; --bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-900, #171717)"
	class="scrollbar-hidden border-s"
							>
								{#each $pinnedChats as chat, idx (`pinned-chat-${chat?.id ?? idx}`)}
									<ChatItem
										className=""
										id={chat.id}
										title={chat.title}
										{shiftKey}
										selected={selectedChatId === chat.id}
										on:select={() => {
											selectedChatId = chat.id;
										}}
										on:unselect={() => {
											selectedChatId = null;
										}}
										on:change={async () => {
											initChatList();
										}}
										on:tag={(e) => {
											const { type, name } = e.detail;
											tagEventHandler(type, name, chat.id);
										}}
									/>
								{/each}
							</div>
						</Folder>
					</div>
				{/if}

				{#if folders}
					<Folders
						{folders}
						{shiftKey}
						onDelete={(folderId) => {
							selectedFolder.set(null);
							initChatList();
						}}
						on:update={() => {
							initChatList();
						}}
						on:import={(e) => {
							const { folderId, items } = e.detail;
							importChatHandler(items, false, folderId);
						}}
						on:change={async () => {
							initChatList();
						}}
					/>
				{/if}

				<div style="--fx:1 1 0%; --d:flex; --fd:column; --ofy:auto"
	class="scrollbar-hidden">
					<div style="--pt:0.375rem">
						{#if $chats}
							{#each $chats as chat, idx (`chat-${chat?.id ?? idx}`)}
								{#if idx === 0 || (idx > 0 && chat.time_range !== $chats[idx - 1].time_range)}
									<div
										style="--w:100%; --pl:0.625rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-500, #9b9b9b); --weight:500; --pb:0.375rem"
	class="{idx ===
										0
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

								<ChatItem
									className=""
									id={chat.id}
									title={chat.title}
									{shiftKey}
									selected={selectedChatId === chat.id}
									on:select={() => {
										selectedChatId = chat.id;
									}}
									on:unselect={() => {
										selectedChatId = null;
									}}
									on:change={async () => {
										initChatList();
									}}
									on:tag={(e) => {
										const { type, name } = e.detail;
										tagEventHandler(type, name, chat.id);
									}}
								/>
							{/each}

							{#if $scrollPaginationEnabled && !allChatsLoaded}
								<Loader
									on:visible={(e) => {
										if (!chatListLoading) {
											loadMoreChats();
										}
									}}
								>
									<div
										style="--w:100%; --d:flex; --jc:center; --py:0.25rem; --size:0.75rem; animation:pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; --ai:center; --g:0.5rem"
									>
										<Spinner className=" size-4" />
										<div class=" ">Loading...</div>
									</div>
								</Loader>
							{/if}
						{:else}
							<div style="--w:100%; --d:flex; --jc:center; --py:0.25rem; --size:0.75rem; animation:pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; --ai:center; --g:0.5rem">
								<Spinner className=" size-4" />
								<div class=" ">Loading...</div>
							</div>
						{/if}
					</div>
				</div>
			</Folder>
		</div>

		<div style="--px:0.5rem">
			<div style="--d:flex; --fd:column"
	class="font-primary">
				{#if $user !== undefined && $user !== null}
					<UserMenu
						role={$user?.role}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<button
							style="--radius: 1em; --w:100%"
							on:click={() => {
								showDropdown = !showDropdown;
							}}
						>
							<div style="--as:center; --mr:0.75rem">
								<img
									src={$user?.profile_image_url}
									style="--maxw:30px; --objf:cover; --radius:9999px"
									alt="User profile"
								/>
							</div>
							<div style="--as:center; --weight:500">{$user?.name}</div>
						</button>
					</UserMenu>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
