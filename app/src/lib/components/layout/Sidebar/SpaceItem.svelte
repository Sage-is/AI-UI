<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	const i18n = getContext('i18n');

	import { page } from '$app/stores';
	import { mobile, showSidebar, user } from '$lib/stores';
	import { updateSpaceById } from '$lib/apis/spaces';

		import SpaceModal from './SpaceModal.svelte';

	export let onUpdate: Function = () => {};

	export let className = '';
	/** Space data object for this sidebar item. */
	export let space;

	let showEditSpaceModal = false;

	let itemElement;
</script>

<SpaceModal
	bind:show={showEditSpaceModal}
	{space}
	edit={true}
	{onUpdate}
	onSubmit={async ({ name, access_control }) => {
		const res = await updateSpaceById(localStorage.token, space.id, {
			name,
			access_control
		}).catch((error) => {
			toast.error(error.message);
		});

		if (res) {
			toast.success('Space updated successfully');
		}

		onUpdate();
	}}
/>

<div
	bind:this={itemElement}
	style="--w:100%; --radius:0.5rem; --d:flex; --pos:relative; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --px:0.625rem; --py:0.2rem"
	class="{className} group {$page
		.url.pathname === `/space/${space.id}`
		? 'bg-gray-100 dark:bg-gray-900'
		: ''}"
>
	<a
		style="--w:100%; --d:flex; --jc:space-between"
		href="/space/{space.id}"
		on:click={() => {
			if ($mobile) {
				showSidebar.set(false);
			}
		}}
		draggable="false"
	>
		<div style="--d:flex; --ai:center; --g:0.2rem">
			<Icon name="hashtag-fill-16" className="size-[1.2rem]" />

			<div style="--ta:left; --as:center; --of:hidden; --w:100%; --line-clamp:1">
				{space.name}
			</div>
		</div>
	</a>

	{#if $user?.role === 'admin'}
		<button
			style="--pos:absolute; --z:10; --right:0.5rem; --v:hidden; --as:center; --d:flex; --ai:center; --dark-c:var(--color-gray-300)"
	class="group-hover:visible"
			on:click={(e) => {
				e.stopPropagation();
				showEditSpaceModal = true;
			}}
		>
			<button style="--p:0.125rem; --hvr-dark-bgc:var(--color-gray-850); --radius:0.5rem; touch-action:auto" on:click={(e) => {}}>
				<Icon name="cog6" className="size-3.5" />
			</button>
		</button>
	{/if}
</div>
