<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { showSettings, mobile, showSidebar, user } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';

	import Mic from '../icons/Mic.svelte';
	import CursorArrowRays from '../icons/CursorArrowRays.svelte';
	import DocumentArrowUp from '../icons/DocumentArrowUp.svelte';
	import CloudArrowUp from '../icons/CloudArrowUp.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let className = 'max-w-[170px]';

	export let onRecord = () => {};
	export let onCaptureAudio = () => {};
	export let onUpload = () => {};

	const dispatch = createEventDispatcher();
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			style="--w:100%; --size:0.875rem; --radius:0.6rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
	class="{className} font-primary"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={async () => {
					onRecord();
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<Mic className="size-4" strokeWidth="2" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Record')}</div>
			</button>

			<button
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					onCaptureAudio();
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<CursorArrowRays className="size-4" strokeWidth="2" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Capture Audio')}</div>
			</button>

			<button
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					onUpload();
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<CloudArrowUp className="size-4" strokeWidth="2" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Upload Audio')}</div>
			</button>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
