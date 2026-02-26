<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import { models } from '$lib/stores';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Image from '$lib/components/common/Image.svelte';

	export let show = false;
	export let selectedModelId = '';
	export let files = [];

	export let onUpdate = (files: any[]) => {
		// Default no-op function
	};
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
			{$i18n.t('Controls')}
		</div>
	</div>
</div>

<div style="--mt:0.25rem">
	<div style="--pb:2.5rem">
		{#if files.length > 0}
			<div style="--size:0.75rem; --weight:500; --pb:0.25rem">Files</div>

			<div style="--d:flex; --fd:column; --g:0.25rem">
				{#each files.filter((file) => file.type !== 'image') as file, fileIdx}
					<FileItem
						className="w-full"
						item={file}
						small={true}
						edit={true}
						dismissible={true}
						url={file.url}
						name={file.name}
						type={file.type}
						size={file?.size}
						loading={file.status === 'uploading'}
						on:dismiss={() => {
							// Remove the file from the files array
							files = files.filter((item) => item.id !== file.id);
							files = files;

							onUpdate(files);
						}}
						on:click={() => {
							console.log(file);
						}}
					/>
				{/each}

				<div style="--d:flex; --ai:center; --fw:wrap; --g:0.5rem; --mt:0.375rem">
					{#each files.filter((file) => file.type === 'image') as file, fileIdx}
						<Image
							src={file.url}
							imageClassName=" size-14 rounded-xl object-cover"
							dismissible={true}
							onDismiss={() => {
								files = files.filter((item) => item.id !== file.id);
								files = files;

								onUpdate(files);
							}}
						/>
					{/each}
				</div>
			</div>

			<hr style="--my:0.5rem; --bc:var(--color-gray-50); --dark-bc:rgb(78 78 78 / 0.1)" />
		{/if}

		<div style="--size:0.75rem; --weight:500; --mb:0.25rem">Model</div>

		<div style="--w:100%">
			<select style="--w:100%; --bgc:transparent; --size:0.875rem; --oe:none" bind:value={selectedModelId}>
				<option value="" style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)" disabled>
					{$i18n.t('Select a model')}
				</option>
				{#each $models.filter((model) => !(model?.info?.meta?.hidden ?? false)) as model}
					<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)">{model.name}</option>
				{/each}
			</select>
		</div>
	</div>
</div>
