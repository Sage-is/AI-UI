<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { chats, user, settings, scrollPaginationEnabled, currentChatPage } from '$lib/stores';

	import {
		archiveAllChats,
		deleteAllChats,
		getAllChats,
		getChatList,
		importChat
	} from '$lib/apis/chats';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import ArchivedChatsModal from '$lib/components/layout/ArchivedChatsModal.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Chats
	let importFiles;

	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showArchivedChatsModal = false;

	let chatImportInputElement: HTMLInputElement;

	$: if (importFiles) {
		console.log(importFiles);

		let reader = new FileReader();
		reader.onload = (event) => {
			let chats = JSON.parse(event.target.result);
			console.log(chats);
			if (getImportOrigin(chats) == 'openai') {
				try {
					chats = convertOpenAIChats(chats);
				} catch (error) {
					console.log('Unable to import chats:', error);
				}
			}
			importChats(chats);
		};

		if (importFiles.length > 0) {
			reader.readAsText(importFiles[0]);
		}
	}

	const importChats = async (_chats) => {
		for (const chat of _chats) {
			console.log(chat);

			if (chat.chat) {
				await importChat(
					localStorage.token,
					chat.chat,
					chat.meta ?? {},
					false,
					null,
					chat?.created_at ?? null,
					chat?.updated_at ?? null
				);
			} else {
				// Legacy format
				await importChat(localStorage.token, chat, {}, false, null);
			}
		}

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const exportChats = async () => {
		let blob = new Blob([JSON.stringify(await getAllChats(localStorage.token))], {
			type: 'application/json'
		});
		saveAs(blob, `chat-export-${Date.now()}.json`);
	};

	const archiveAllChatsHandler = async () => {
		await goto('/');
		await archiveAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const deleteAllChatsHandler = async () => {
		await goto('/');
		await deleteAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const handleArchivedChatsChange = async () => {
		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));

		scrollPaginationEnabled.set(true);
	};
</script>

<ArchivedChatsModal bind:show={showArchivedChatsModal} onUpdate={handleArchivedChatsChange} />

<div id="tab-chats" style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.8rem">
	<div style="--g:0.5rem; --ofy:scroll; --maxh:28rem; --maxh-lg:100%">
		<div style="--d:flex; --fd:column">
			<input
				id="chat-import-input"
				bind:this={chatImportInputElement}
				bind:files={importFiles}
				type="file"
				accept=".json"
				hidden
			/>
			<button
				style="--d:flex; --radius:0.4rem; --py:0.5rem; --px:0.8rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					chatImportInputElement.click();
				}}
			>
				<div style="--as:center; --mr:0.6rem">
					<Icon name="clipboard-import" className="size-4" />
				</div>
				<div style="--as:center; --size:0.8rem; --weight:500">{$i18n.t('Import Chats')}</div>
			</button>

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<button
					style="--d:flex; --radius:0.4rem; --py:0.5rem; --px:0.8rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						exportChats();
					}}
				>
					<div style="--as:center; --mr:0.6rem">
						<Icon name="clipboard-import-331f" className="size-4" />
					</div>
					<div style="--as:center; --size:0.8rem; --weight:500">{$i18n.t('Export Chats')}</div>
				</button>
			{/if}
		</div>

		<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)" />

		<div style="--d:flex; --fd:column">
			<button
				style="--d:flex; --radius:0.4rem; --py:0.5rem; --px:0.8rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					showArchivedChatsModal = true;
				}}
			>
				<div style="--as:center; --mr:0.6rem">
					<Icon name="archive-box-fill" className="size-4" />
				</div>
				<div style="--as:center; --size:0.8rem; --weight:500">{$i18n.t('Archived Chats')}</div>
			</button>

			{#if showArchiveConfirm}
				<div style="--d:flex; --jc:space-between; --radius:0.4rem; --ai:center; --py:0.5rem; --px:0.8rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
					<div style="--d:flex; --ai:center; --g:0.6rem">
						<Icon name="database-fill-16" className="size-4" />
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div style="--d:flex; --g:0.4rem; --ai:center">
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								archiveAllChatsHandler();
								showArchiveConfirm = false;
							}}
						>
							<Icon name="check-fill-20" className="size-4" />
						</button>
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								showArchiveConfirm = false;
							}}
						>
							<Icon name="x-mark" className="size-4" />
						</button>
					</div>
				</div>
			{:else}
				<button
					style="--d:flex; --radius:0.4rem; --py:0.5rem; --px:0.8rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						showArchiveConfirm = true;
					}}
				>
					<div style="--as:center; --mr:0.6rem">
						<Icon name="archive-box-fill-b8ae" className="size-4" />
					</div>
					<div style="--as:center; --size:0.8rem; --weight:500">{$i18n.t('Archive All Chats')}</div>
				</button>
			{/if}

			{#if showDeleteConfirm}
				<div style="--d:flex; --jc:space-between; --radius:0.4rem; --ai:center; --py:0.5rem; --px:0.8rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
					<div style="--d:flex; --ai:center; --g:0.6rem">
						<Icon name="database-fill-16" className="size-4" />
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div style="--d:flex; --g:0.4rem; --ai:center">
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								deleteAllChatsHandler();
								showDeleteConfirm = false;
							}}
						>
							<Icon name="check-fill-20" className="size-4" />
						</button>
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								showDeleteConfirm = false;
							}}
						>
							<Icon name="x-mark" className="size-4" />
						</button>
					</div>
				</div>
			{:else}
				<button
					style="--d:flex; --radius:0.4rem; --py:0.5rem; --px:0.8rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						showDeleteConfirm = true;
					}}
				>
					<div style="--as:center; --mr:0.6rem">
						<Icon name="clipboard-import-8f4e" className="size-4" />
					</div>
					<div style="--as:center; --size:0.8rem; --weight:500">{$i18n.t('Delete All Chats')}</div>
				</button>
			{/if}
		</div>
	</div>
</div>
