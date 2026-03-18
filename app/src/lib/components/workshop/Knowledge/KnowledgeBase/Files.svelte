<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import FileItem from '$lib/components/common/FileItem.svelte';

	export let selectedFileId = null;
	export let files = [];

	export let small = false;
</script>

<div style="--maxh:100%; --d:flex; --fd:column; --w:100%">
	{#each files as file}
		<div style="--mt:0.2rem; --px:0.5rem">
			<FileItem
				className="w-full"
				colorClassName="{selectedFileId === file.id
					? ' bg-gray-50 dark:bg-gray-850'
					: 'bg-transparent'} hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				{small}
				item={file}
				name={file?.name ?? file?.meta?.name}
				type="file"
				size={file?.size ?? file?.meta?.size ?? ''}
				loading={file.status === 'uploading'}
				dismissible
				on:click={() => {
					if (file.status === 'uploading') {
						return;
					}

					dispatch('click', file.id);
				}}
				on:dismiss={() => {
					if (file.status === 'uploading') {
						return;
					}

					dispatch('delete', file.id);
				}}
			/>
		</div>
	{/each}
</div>
