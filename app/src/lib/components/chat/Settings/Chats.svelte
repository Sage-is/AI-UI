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

<div id="tab-chats" style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.75rem; --size:0.875rem">
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
				style="--d:flex; --radius:0.375rem; --py:0.5rem; --px:0.875rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					chatImportInputElement.click();
				}}
			>
				<div style="--as:center; --mr:0.75rem">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div style="--as:center; --size:0.875rem; --weight:500">{$i18n.t('Import Chats')}</div>
			</button>

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
				<button
					style="--d:flex; --radius:0.375rem; --py:0.5rem; --px:0.875rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						exportChats();
					}}
				>
					<div style="--as:center; --mr:0.75rem">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div style="--as:center; --size:0.875rem; --weight:500">{$i18n.t('Export Chats')}</div>
				</button>
			{/if}
		</div>

		<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)" />

		<div style="--d:flex; --fd:column">
			<button
				style="--d:flex; --radius:0.375rem; --py:0.5rem; --px:0.875rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					showArchivedChatsModal = true;
				}}
			>
				<div style="--as:center; --mr:0.75rem">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path
							d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
						/>
						<path
							fill-rule="evenodd"
							d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087ZM12 10.5a.75.75 0 0 1 .75.75v4.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 1 1 1.06-1.06l1.72 1.72v-4.94a.75.75 0 0 1 .75-.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div style="--as:center; --size:0.875rem; --weight:500">{$i18n.t('Archived Chats')}</div>
			</button>

			{#if showArchiveConfirm}
				<div style="--d:flex; --jc:space-between; --radius:0.375rem; --ai:center; --py:0.5rem; --px:0.875rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
					<div style="--d:flex; --ai:center; --g:0.75rem">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
							<path
								fill-rule="evenodd"
								d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM5.72 7.47a.75.75 0 0 1 1.06 0L8 8.69l1.22-1.22a.75.75 0 1 1 1.06 1.06L9.06 9.75l1.22 1.22a.75.75 0 1 1-1.06 1.06L8 10.81l-1.22 1.22a.75.75 0 0 1-1.06-1.06l1.22-1.22-1.22-1.22a.75.75 0 0 1 0-1.06Z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div style="--d:flex; --g:0.375rem; --ai:center">
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								archiveAllChatsHandler();
								showArchiveConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								style="--w:1rem; --h:1rem"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								showArchiveConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
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
				<button
					style="--d:flex; --radius:0.375rem; --py:0.5rem; --px:0.875rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						showArchiveConfirm = true;
					}}
				>
					<div style="--as:center; --mr:0.75rem">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
							/>
							<path
								fill-rule="evenodd"
								d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087Zm6.163 3.75A.75.75 0 0 1 10 12h4a.75.75 0 0 1 0 1.5h-4a.75.75 0 0 1-.75-.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div style="--as:center; --size:0.875rem; --weight:500">{$i18n.t('Archive All Chats')}</div>
				</button>
			{/if}

			{#if showDeleteConfirm}
				<div style="--d:flex; --jc:space-between; --radius:0.375rem; --ai:center; --py:0.5rem; --px:0.875rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
					<div style="--d:flex; --ai:center; --g:0.75rem">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
							<path
								fill-rule="evenodd"
								d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM5.72 7.47a.75.75 0 0 1 1.06 0L8 8.69l1.22-1.22a.75.75 0 1 1 1.06 1.06L9.06 9.75l1.22 1.22a.75.75 0 1 1-1.06 1.06L8 10.81l-1.22 1.22a.75.75 0 0 1-1.06-1.06l1.22-1.22-1.22-1.22a.75.75 0 0 1 0-1.06Z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div style="--d:flex; --g:0.375rem; --ai:center">
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								deleteAllChatsHandler();
								showDeleteConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								style="--w:1rem; --h:1rem"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							style="--hvr-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								showDeleteConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
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
				<button
					style="--d:flex; --radius:0.375rem; --py:0.5rem; --px:0.875rem; --w:100%; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						showDeleteConfirm = true;
					}}
				>
					<div style="--as:center; --mr:0.75rem">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm7 7a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1 0-1.5h4.5A.75.75 0 0 1 11 9Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div style="--as:center; --size:0.875rem; --weight:500">{$i18n.t('Delete All Chats')}</div>
				</button>
			{/if}
		</div>
	</div>
</div>
