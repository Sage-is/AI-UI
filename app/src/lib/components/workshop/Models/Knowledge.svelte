<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { config, knowledge, settings, user } from '$lib/stores';

	import Selector from './Knowledge/Selector.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';

	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { uploadFile } from '$lib/apis/files';

	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let selectedItems = [];
	const i18n = getContext('i18n');

	let loaded = false;

	let filesInputElement = null;
	let inputFiles = [];

	const uploadFileHandler = async (file, fullContext: boolean = false) => {
		if ($user?.role !== 'admin' && !($user?.permissions?.chat?.file_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload files.'));
			return null;
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId: tempItemId,
			...(fullContext ? { context: 'full' } : {})
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		selectedItems = [...selectedItems, fileItem];

		try {
			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			// During the file upload, file content is automatically extracted.
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (uploadedFile) {
				console.log('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
				}

				fileItem.status = 'uploaded';
				fileItem.file = uploadedFile;
				fileItem.id = uploadedFile.id;
				fileItem.collection_name =
					uploadedFile?.meta?.collection_name || uploadedFile?.collection_name;
				fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

				selectedItems = selectedItems;
			} else {
				selectedItems = selectedItems.filter((item) => item?.itemId !== tempItemId);
			}
		} catch (e) {
			toast.error(`${e}`);
			selectedItems = selectedItems.filter((item) => item?.itemId !== tempItemId);
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);

		if (
			($config?.file?.max_count ?? null) !== null &&
			files.length + inputFiles.length > $config?.file?.max_count
		) {
			toast.error(
				$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
					maxCount: $config?.file?.max_count
				})
			);
			return;
		}

		inputFiles.forEach(async (file) => {
			console.log('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.log('File exceeds max size limit:', {
					fileSize: file.size,
					maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
				});
				toast.error(
					$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
						maxSize: $config?.file?.max_size
					})
				);
				return;
			}

			if (!file['type'].startsWith('image/')) {
				uploadFileHandler(file);
			} else {
				toast.error($i18n.t(`Unsupported file type.`));
			}
		});
	};

	onMount(async () => {
		if (!$knowledge) {
			knowledge.set(await getKnowledgeBases(localStorage.token));
		}
		loaded = true;
	});
</script>

<input
	bind:this={filesInputElement}
	bind:files={inputFiles}
	type="file"
	hidden
	multiple
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			const _inputFiles = Array.from(inputFiles);
			inputFilesHandler(_inputFiles);
		} else {
			toast.error($i18n.t(`File not found.`));
		}

		filesInputElement.value = '';
	}}
/>

<div>
	<slot name="label">
		<div style="--mb:0.5rem">
			<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.25rem">
				<div style="--as:center; --size:0.875rem; --weight:600">
					{$i18n.t('Knowledge')}
				</div>
			</div>

			<div style="--size:0.75rem; --dark-c:var(--color-gray-500)">
				{$i18n.t('To attach knowledge base here, add them to the "Knowledge" workshop first.')}
			</div>
		</div>
	</slot>

	<div style="--d:flex; --fd:column">
		{#if selectedItems?.length > 0}
			<div style="--d:flex; --fw:wrap; --ai:center; --g:0.5rem; --mb:0.625rem">
				{#each selectedItems as file, fileIdx}
					<FileItem
						{file}
						item={file}
						name={file.name}
						modal={true}
						edit={true}
						type={file?.legacy
							? `Legacy${file.type ? ` ${file.type}` : ''}`
							: (file?.type ?? 'Collection')}
						dismissible
						on:dismiss={(e) => {
							selectedItems = selectedItems.filter((_, idx) => idx !== fileIdx);
						}}
					/>
				{/each}
			</div>
		{/if}

		{#if loaded}
			<div style="--d:flex; --fw:wrap; --fd:row; --size:0.875rem; --g:0.25rem">
				<Selector
					knowledgeItems={$knowledge || []}
					on:select={(e) => {
						const item = e.detail;

						if (!selectedItems.find((k) => k.id === item.id)) {
							selectedItems = [
								...selectedItems,
								{
									...item
								}
							];
						}
					}}
				>
					<div
						style="--px:0.875rem; --py:0.375rem; --weight:500; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); outline-style:solid; outline-width:1px; outline-color:var(--color-gray-100); outline-color:var(--color-gray-850); --radius:1.5rem"
					>
						{$i18n.t('Select Knowledge')}
					</div>
				</Selector>

				{#if $user?.role === 'admin' || $user?.permissions?.chat?.file_upload}
					<button
						style="--px:0.875rem; --py:0.375rem; --weight:500; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); outline-style:solid; outline-width:1px; outline-color:var(--color-gray-100); outline-color:var(--color-gray-850); --radius:1.5rem"
						type="button"
						on:click={() => {
							filesInputElement.click();
						}}>{$i18n.t('Upload Files')}</button
					>
				{/if}
			</div>
		{/if}
		<!-- {knowledge} -->
	</div>
</div>
