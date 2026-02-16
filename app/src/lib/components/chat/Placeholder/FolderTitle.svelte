<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import DOMPurify from 'dompurify';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';

	import { selectedFolder } from '$lib/stores';

	import { deleteFolderById, updateFolderById } from '$lib/apis/folders';
	import { getChatsByFolderId } from '$lib/apis/chats';

	import FolderModal from '$lib/components/layout/Sidebar/Folders/FolderModal.svelte';

	import Folder from '$lib/components/icons/Folder.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import FolderMenu from '$lib/components/layout/Sidebar/Folders/FolderMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let folder = null;

	export let onUpdate: Function = (folderId) => {};
	export let onDelete: Function = (folderId) => {};

	let showFolderModal = false;
	let showDeleteConfirm = false;

	const updateHandler = async ({ name, data }) => {
		if (name === '') {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const currentName = folder.name;

		name = name.trim();
		folder.name = name;

		const res = await updateFolderById(localStorage.token, folder.id, {
			name,
			...(data ? { data } : {})
		}).catch((error) => {
			toast.error(`${error}`);

			folder.name = currentName;
			return null;
		});

		if (res) {
			folder.name = name;
			if (data) {
				folder.data = data;
			}

			toast.success($i18n.t('Folder updated successfully'));
			selectedFolder.set(folder);
			onUpdate(folder);
		}
	};

	const deleteHandler = async () => {
		const res = await deleteFolderById(localStorage.token, folder.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Folder deleted successfully'));
			onDelete(folder);
		}
	};

	const exportHandler = async () => {
		const chats = await getChatsByFolderId(localStorage.token, folder.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!chats) {
			return;
		}

		const blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});

		saveAs(blob, `folder-${folder.name}-export-${Date.now()}.json`);
	};
</script>

{#if folder}
	<FolderModal bind:show={showFolderModal} edit={true} {folder} onSubmit={updateHandler} />

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete folder?')}
		on:confirm={() => {
			deleteHandler();
		}}
	>
		<div style="--size:0.875rem; --c:var(--color-gray-700, #4e4e4e); --dark-c:var(--color-gray-300, #cdcdcd); --fx:1 1 0%; --line-clamp:3">
			{@html DOMPurify.sanitize(
				$i18n.t(
					'This will delete <strong>{{NAME}}</strong> and <strong>all its contents</strong>.',
					{
						NAME: folder.name
					}
				)
			)}
		</div>
	</DeleteConfirmDialog>

	<div style="--mb:0.75rem; --px:1.5rem; --jc:space-between; --w:100%; --d:flex; --pos:relative; --ai:center"
	class="@md:max-w-3xl group">
		<div style="--ta:center; --d:flex; --g:0.875rem; --ai:center">
			<div style="--radius:9999px; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-800, #333); --p:0.75rem; --w:fit-content">
				<Folder className="size-4.5" strokeWidth="2" />
			</div>

			<div style="--size:1.875rem">
				{folder.name}
			</div>
		</div>

		<div style="--d:flex; --ai:center; --translatex:0.625rem">
			<FolderMenu
				align="end"
				onEdit={() => {
					showFolderModal = true;
				}}
				onDelete={() => {
					showDeleteConfirm = true;
				}}
				onExport={() => {
					exportHandler();
				}}
			>
				<button style="--p:0.375rem; --hvr-dark-bgc:var(--color-gray-850, #262626); --radius:9999px; touch-action:auto" on:click={(e) => {}}>
					<EllipsisHorizontal className="size-4" strokeWidth="2.5" />
				</button>
			</FolderMenu>
		</div>
	</div>
{/if}
