<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { showSettings, mobile, showSidebar, user } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';
	import Sparkles from '../icons/Sparkles.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[170px]';

	export let onEdit = () => {};
	export let onChat = () => {};

	export let onChange = () => {};
</script>

<DropdownMenu.Root bind:open={show} onOpenChange={onChange}>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			style="--w:100%; --size:0.875rem; --radius:0.75rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
	class="{className} font-primary"
			sideOffset={8}
			side="bottom"
			align="end"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.75rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={async () => {
					onEdit();
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<Sparkles className="size-4" strokeWidth="2" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Enhance')}</div>
			</button>

			<button
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.75rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					onChat();
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<ChatBubbleOval className="size-4" strokeWidth="2" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Chat')}</div>
			</button>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
