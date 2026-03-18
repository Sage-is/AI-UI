<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { fade, slide } from 'svelte/transition';

	import { showSettings, mobile, showSidebar, user } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import Link from '$lib/components/icons/Link.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[180px]';

	export let onDownload = (type) => {};
	export let onDelete = () => {};

	export let onCopyLink = null;
	export let onCopyToClipboard = null;

	export let onChange = () => {};
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		onChange(state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			style="--w:100%; --size:0.875rem; --radius:0.6rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
	class="{className} font-primary"
			sideOffset={6}
			side="bottom"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				>
					<Download strokeWidth="2" />

					<div style="--d:flex; --ai:center">{$i18n.t('Download')}</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					style="--w:100%; --radius:0.6rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
					transition={flyAndScale}
					sideOffset={8}
					align="end"
				>
					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
						on:click={() => {
							onDownload('txt');
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Plain text (.txt)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
						on:click={() => {
							onDownload('md');
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Plain text (.md)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
						on:click={() => {
							onDownload('pdf');
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('PDF document (.pdf)')}</div>
					</DropdownMenu.Item>
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>

			{#if onCopyLink || onCopyToClipboard}
				<DropdownMenu.Sub>
					<DropdownMenu.SubTrigger
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
					>
						<Share strokeWidth="2" />

						<div style="--d:flex; --ai:center">{$i18n.t('Share')}</div>
					</DropdownMenu.SubTrigger>
					<DropdownMenu.SubContent
						style="--w:100%; --radius:0.6rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
						transition={flyAndScale}
						sideOffset={8}
						align="end"
					>
						{#if onCopyLink}
							<DropdownMenu.Item
								style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
								on:click={() => {
									onCopyLink();
								}}
							>
								<Link />
								<div style="--d:flex; --ai:center">{$i18n.t('Copy link')}</div>
							</DropdownMenu.Item>
						{/if}

						{#if onCopyToClipboard}
							<DropdownMenu.Item
								style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
								on:click={() => {
									onCopyToClipboard();
								}}
							>
								<DocumentDuplicate strokeWidth="2" />
								<div style="--d:flex; --ai:center">{$i18n.t('Copy to clipboard')}</div>
							</DropdownMenu.Item>
						{/if}
					</DropdownMenu.SubContent>
				</DropdownMenu.Sub>
			{/if}

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.375rem"
				on:click={() => {
					onDelete();
				}}
			>
				<GarbageBin strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
