<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { formatFileSize } from '$lib/utils';
	import Icon from '$lib/components/Icon.svelte';

	import FileItemModal from './FileItemModal.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Spinner from './Spinner.svelte';
	import Tooltip from './Tooltip.svelte';
		import { settings } from '$lib/stores';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let className = 'w-60';
	export let colorClassName = 'bg-white dark:bg-gray-850 border border-gray-50 dark:border-white/5';
	export let url: string | null = null;

	export let dismissible = false;
	export let modal = false;
	export let loading = false;

	export let item = null;
	export let edit = false;
	export let small = false;

	export let name: string;
	export let type: string;
	export let size: number;

	import { deleteFileById } from '$lib/apis/files';

	let showModal = false;

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

{#if item}
	<FileItemModal bind:show={showModal} bind:item {edit} />
{/if}

<button
	style="--pos:relative; --p:0.4rem; --d:flex; --ai:center; --g:0.2rem; --ta:left"
	class="group {className} {colorClassName} {small
		? 'rounded-xl'
		: 'rounded-2xl'}"
	type="button"
	on:click={async () => {
		if (item?.file?.data?.content || modal) {
			showModal = !showModal;
		} else {
			if (url) {
				if (type === 'file') {
					window.open(`${url}/content`, '_blank').focus();
				} else {
					window.open(`${url}`, '_blank').focus();
				}
			}
		}

		dispatch('click');
	}}
>
	{#if !small}
		<div style="--p:0.6rem; --bgc:rgb(0 0 0 / 0.2); --dark-bgc:rgb(255 255 255 / 0.1); --c:#fff; --radius:0.6rem">
			{#if !loading}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="currentColor"
					aria-hidden="true"
					style="--w:1.2rem; --h:1.2rem"
				>
					<path
						fill-rule="evenodd"
						d="M5.625 1.5c-1.036 0-1.875.84-1.875 1.875v17.25c0 1.035.84 1.875 1.875 1.875h12.75c1.035 0 1.875-.84 1.875-1.875V12.75A3.75 3.75 0 0 0 16.5 9h-1.875a1.875 1.875 0 0 1-1.875-1.875V5.25A3.75 3.75 0 0 0 9 1.5H5.625ZM7.5 15a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 7.5 15Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H8.25Z"
						clip-rule="evenodd"
					/>
					<path
						d="M12.971 1.816A5.23 5.23 0 0 1 14.25 5.25v1.875c0 .207.168.375.375.375H16.5a5.23 5.23 0 0 1 3.434 1.279 9.768 9.768 0 0 0-6.963-6.963Z"
					/>
				</svg>
			{:else}
				<Spinner />
			{/if}
		</div>
	{/if}

	{#if !small}
		<div style="--d:flex; --fd:column; --jc:center; --g:-0.125rem; --px:0.625rem; --w:100%">
			<div style="--dark-c:var(--color-gray-100); --size:0.8rem; --weight:500; --line-clamp:1; --mb:0.2rem">
				{decodeString(name)}
			</div>

			<div
				style="--d:flex; --jc:space-between; --size:0.6rem; --line-clamp:1"
	class="{($settings?.highContrastMode ?? false)
					? 'text-gray-800 dark:text-gray-100'
					: 'text-gray-500'}"
			>
				{#if type === 'file'}
					{$i18n.t('File')}
				{:else if type === 'doc'}
					{$i18n.t('Document')}
				{:else if type === 'collection'}
					{$i18n.t('Collection')}
				{:else}
					<span style="--tt:capitalize; --line-clamp:1">{type}</span>
				{/if}
				{#if size}
					<span style="--tt:capitalize">{formatFileSize(size)}</span>
				{/if}
			</div>
		</div>
	{:else}
		<Tooltip content={decodeString(name)} className="flex flex-col w-full" placement="top-start">
			<div style="--d:flex; --fd:column; --jc:center; --g:-0.125rem; --px:0.625rem; --w:100%">
				<div style="--dark-c:var(--color-gray-100); --size:0.8rem; --d:flex; --jc:space-between; --ai:center">
					{#if loading}
						<div style="--fs:0; --mr:0.5rem">
							<Spinner className="size-4" />
						</div>
					{/if}
					<div style="--weight:500; --line-clamp:1; --fx:1 1 0%">{decodeString(name)}</div>
					<div style="--c:var(--color-gray-500); --size:0.6rem; --tt:capitalize; --fs:0">{formatFileSize(size)}</div>
				</div>
			</div>
		</Tooltip>
	{/if}

	{#if dismissible}
		<div style="--pos:absolute; --top:-0.2rem; --right:-0.2rem">
			<button
				aria-label={$i18n.t('Remove File')}
				style="--bgc:#fff; --c:#000;  --bc:var(--color-gray-50); --radius:9999px"
	class="{($settings?.highContrastMode ??
				false)
					? ''
					: 'outline-hidden focus:outline-hidden group-hover:visible invisible transition'}"
				type="button"
				on:click|stopPropagation={() => {
					dispatch('dismiss');
				}}
			>
				<Icon name="x-mark" strokeWidth="2" className={'size-4'} />
			</button>

			<!-- <button
				style="--p:0.2rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:9999px; --v:hidden; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover:visible"
				type="button"
				on:click={() => {
				}}
			>
				<GarbageBin />
			</button> -->
		</div>
	{/if}
</button>
