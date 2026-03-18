<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { page } from '$app/stores';
	import { mobile, showSidebar, user } from '$lib/stores';
	import { updateChannelById } from '$lib/apis/spaces';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ChannelModal from './ChannelModal.svelte';

	export let onUpdate: Function = () => {};

	export let className = '';
	export let channel;

	let showEditChannelModal = false;

	let itemElement;
</script>

<ChannelModal
	bind:show={showEditChannelModal}
	{channel}
	edit={true}
	{onUpdate}
	onSubmit={async ({ name, access_control }) => {
		const res = await updateChannelById(localStorage.token, channel.id, {
			name,
			access_control
		}).catch((error) => {
			toast.error(error.message);
		});

		if (res) {
			toast.success('Channel updated successfully');
		}

		onUpdate();
	}}
/>

<div
	bind:this={itemElement}
	style="--w:100%; --radius:0.5rem; --d:flex; --pos:relative; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --px:0.625rem; --py:0.2rem"
	class="{className} group {$page
		.url.pathname === `/space/${channel.id}`
		? 'bg-gray-100 dark:bg-gray-900'
		: ''}"
>
	<a
		style="--w:100%; --d:flex; --jc:space-between"
		href="/space/{channel.id}"
		on:click={() => {
			if ($mobile) {
				showSidebar.set(false);
			}
		}}
		draggable="false"
	>
		<div style="--d:flex; --ai:center; --g:0.2rem">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				style="--w:1.2rem; --h:1.2rem"
			>
				<path
					fill-rule="evenodd"
					d="M7.487 2.89a.75.75 0 1 0-1.474-.28l-.455 2.388H3.61a.75.75 0 0 0 0 1.5h1.663l-.571 2.998H2.75a.75.75 0 0 0 0 1.5h1.666l-.403 2.114a.75.75 0 0 0 1.474.28l.456-2.394h2.973l-.403 2.114a.75.75 0 0 0 1.474.28l.456-2.394h1.947a.75.75 0 0 0 0-1.5h-1.661l.57-2.998h1.95a.75.75 0 0 0 0-1.5h-1.664l.402-2.108a.75.75 0 0 0-1.474-.28l-.455 2.388H7.085l.402-2.108ZM6.8 6.498l-.571 2.998h2.973l.57-2.998H6.8Z"
					clip-rule="evenodd"
				/>
			</svg>

			<div style="--ta:left; --as:center; --of:hidden; --w:100%; --line-clamp:1">
				{channel.name}
			</div>
		</div>
	</a>

	{#if $user?.role === 'admin'}
		<button
			style="--pos:absolute; --z:10; --right:0.5rem; --v:hidden; --as:center; --d:flex; --ai:center; --dark-c:var(--color-gray-300)"
	class="group-hover:visible"
			on:click={(e) => {
				e.stopPropagation();
				showEditChannelModal = true;
			}}
		>
			<button style="--p:0.125rem; --hvr-dark-bgc:var(--color-gray-850); --radius:0.5rem; touch-action:auto" on:click={(e) => {}}>
				<Cog6 className="size-3.5" />
			</button>
		</button>
	{/if}
</div>
