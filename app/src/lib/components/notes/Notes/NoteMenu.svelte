<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { getContext, onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { fade, slide } from 'svelte/transition';

	import { showSettings, mobile, showSidebar, user } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

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
			style="--w:100%; --size:0.8rem; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
	class="{className} font-primary"
			sideOffset={6}
			side="bottom"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				>
					<Icon name="download" strokeWidth="2" />

					<div style="--d:flex; --ai:center">{$i18n.t('Download')}</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					style="--w:100%; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
					transition={flyAndScale}
					sideOffset={8}
					align="end"
				>
					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
						on:click={() => {
							onDownload('txt');
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Plain text (.txt)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
						on:click={() => {
							onDownload('md');
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Plain text (.md)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
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
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
					>
						<Icon name="share" strokeWidth="2" />

						<div style="--d:flex; --ai:center">{$i18n.t('Share')}</div>
					</DropdownMenu.SubTrigger>
					<DropdownMenu.SubContent
						style="--w:100%; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
						transition={flyAndScale}
						sideOffset={8}
						align="end"
					>
						{#if onCopyLink}
							<DropdownMenu.Item
								style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
								on:click={() => {
									onCopyLink();
								}}
							>
								<Icon name="link" />
								<div style="--d:flex; --ai:center">{$i18n.t('Copy link')}</div>
							</DropdownMenu.Item>
						{/if}

						{#if onCopyToClipboard}
							<DropdownMenu.Item
								style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
								on:click={() => {
									onCopyToClipboard();
								}}
							>
								<Icon name="document-duplicate" strokeWidth="2" />
								<div style="--d:flex; --ai:center">{$i18n.t('Copy to clipboard')}</div>
							</DropdownMenu.Item>
						{/if}
					</DropdownMenu.SubContent>
				</DropdownMenu.Sub>
			{/if}

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.4rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={() => {
					onDelete();
				}}
			>
				<Icon name="garbage-bin" strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
