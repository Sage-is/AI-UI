<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { formatFileSize, getLineCount } from '$lib/utils';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Info from '../icons/Info.svelte';
	import Switch from './Switch.svelte';
	import Tooltip from './Tooltip.svelte';
	import dayjs from 'dayjs';

	export let item;
	export let show = false;
	export let edit = false;

	let enableFullContent = false;

	let isPdf = false;
	let isAudio = false;

	$: isPDF =
		item?.meta?.content_type === 'application/pdf' ||
		(item?.name && item?.name.toLowerCase().endsWith('.pdf'));

	$: isAudio =
		(item?.meta?.content_type ?? '').startsWith('audio/') ||
		(item?.name && item?.name.toLowerCase().endsWith('.mp3')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.wav')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.ogg')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.m4a')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.webm'));

	onMount(() => {
		console.log(item);
		if (item?.context === 'full') {
			enableFullContent = true;
		}
	});
</script>

<Modal bind:show size="lg">
	<div style="--px:1.5rem; --py:1.25rem; --w:100%; --d:flex; --fd:column; --jc:center; --dark-c:var(--color-gray-400)"
	class="font-primary">
		<div style="--pb:0.5rem">
			<div style="--d:flex; --ai:flex-start; --jc:space-between">
				<div>
					<div style="--weight:500; --size:1.125rem; --dark-c:var(--color-gray-100)">
						<a
							href="#"
							style="--hvr-td:underline; --line-clamp:1"
							on:click|preventDefault={() => {
								if (!isPDF && item.url) {
									window.open(
										item.type === 'file' ? `${item.url}/content` : `${item.url}`,
										'_blank'
									);
								}
							}}
						>
							{item?.name ?? 'File'}
						</a>
					</div>
				</div>

				<div>
					<button
						on:click={() => {
							show = false;
						}}
					>
						<XMark />
					</button>
				</div>
			</div>

			<div>
				<div style="--d:flex; --fd:column; --ai:center; --fd-md:row; --g:0.25rem; --jc:space-between; --w:100%">
					<div style="--d:flex; --fw:wrap; --size:0.875rem; --g:0.25rem; --c:var(--color-gray-500)">
						{#if item?.type === 'collection'}
							{#if item?.type}
								<div style="--tt:capitalize; --fs:0">{item.type}</div>
								•
							{/if}

							{#if item?.description}
								<div style="--line-clamp:1">{item.description}</div>
								•
							{/if}

							{#if item?.created_at}
								<div style="--tt:capitalize; --fs:0">
									{dayjs(item.created_at * 1000).format('LL')}
								</div>
							{/if}
						{/if}

						{#if item.size}
							<div style="--tt:capitalize; --fs:0">{formatFileSize(item.size)}</div>
							•
						{/if}

						{#if item?.file?.data?.content}
							<div style="--tt:capitalize; --fs:0">
								{getLineCount(item?.file?.data?.content ?? '')} extracted lines
							</div>

							<div style="--d:flex; --ai:center; --g:0.25rem; --fs:0">
								<Info />

								Formatting may be inconsistent from source.
							</div>
						{/if}

						{#if item?.knowledge}
							<div style="--tt:capitalize; --fs:0">
								{$i18n.t('Knowledge Base')}
							</div>
						{/if}
					</div>

					{#if edit}
						<div>
							<Tooltip
								content={enableFullContent
									? $i18n.t(
											'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
										)
									: $i18n.t(
											'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
										)}
							>
								<div style="--d:flex; --ai:center; --g:0.375rem; --size:0.6rem">
									{#if enableFullContent}
										{$i18n.t('Using Entire Document')}
									{:else}
										{$i18n.t('Using Focused Retrieval')}
									{/if}
									<Switch
										bind:state={enableFullContent}
										on:change={(e) => {
											item.context = e.detail ? 'full' : undefined;
										}}
									/>
								</div>
							</Tooltip>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div style="--maxh:75vh; --of:auto">
			{#if item?.type === 'collection'}
				<div>
					{#each item?.files as file}
						<div style="--d:flex; --ai:center; --g:0.5rem; --mb:0.5rem">
							<div style="--size:0.6rem"
	class="flex-shrink-0">
								{file?.meta?.name}
							</div>
						</div>
					{/each}
				</div>
			{:else if isPDF}
				<iframe
					title={item?.name}
					src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
					style="--w:100%; --h:70vh; --bw:0; --radius:0.5rem; --mt:1rem"
				/>
			{:else}
				{#if isAudio}
					<audio
						src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
						style="--w:100%; --bw:0; --radius:0.5rem; --mb:0.5rem"
						controls
						playsinline
					/>
				{/if}

				{#if item?.file?.data}
					<div style="--maxh:24rem; --of:scroll; --size:0.6rem; --ws:pre-wrap"
	class="scrollbar-hidden">
						{item?.file?.data?.content ?? 'No content'}
					</div>
				{/if}
			{/if}
		</div>
	</div>
</Modal>
