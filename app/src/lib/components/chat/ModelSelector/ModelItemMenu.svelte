<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import Icon from '$lib/components/Icon.svelte';

	import { getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
				import { settings } from '$lib/stores';

	const i18n = getContext('i18n');

	export let show = false;
	export let model;

	export let pinModelHandler: (modelId: string) => void = () => {};
	export let copyLinkHandler: Function = () => {};

	export let onClose: Function = () => {};
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<Tooltip content={$i18n.t('More')} className=" group-hover/item:opacity-100  opacity-0">
			<slot />
		</Tooltip>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		strategy="fixed"
		style="--w:100%; --maxw:180px; --size:0.8rem; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:9999999; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
		sideOffset={-2}
		side="bottom"
		align="end"
		transition={flyAndScale}
	>
		<button
			type="button"
			style="--d:flex; --radius:0.4rem; --py:0.4rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --ai:center; --g:0.5rem"
			on:click={(e) => {
				e.stopPropagation();
				e.preventDefault();

				pinModelHandler(model?.id);
				show = false;
			}}
		>
			{#if ($settings?.pinnedModels ?? []).includes(model?.id)}
				<Icon name="eye-slash" />
			{:else}
				<Icon name="eye" />
			{/if}

			<div style="--d:flex; --ai:center">
				{#if ($settings?.pinnedModels ?? []).includes(model?.id)}
					{$i18n.t('Hide from Sidebar')}
				{:else}
					{$i18n.t('Keep in Sidebar')}
				{/if}
			</div>
		</button>

		<button
			type="button"
			style="--d:flex; --radius:0.4rem; --py:0.4rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --ai:center; --g:0.5rem"
			on:click={(e) => {
				e.stopPropagation();
				e.preventDefault();

				copyLinkHandler();
				show = false;
			}}
		>
			<Icon name="link" />

			<div style="--d:flex; --ai:center">{$i18n.t('Copy Link')}</div>
		</button>
	</DropdownMenu.Content>
</DropdownMenu.Root>
