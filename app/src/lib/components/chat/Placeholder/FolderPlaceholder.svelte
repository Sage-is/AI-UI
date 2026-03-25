<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { fade } from 'svelte/transition';

	import ChatList from './ChatList.svelte';
	import FolderKnowledge from './FolderKnowledge.svelte';

	export let folder = null;

	let selectedTab = 'chats';
</script>

<div>
	<!-- <div style="--mb:0.2rem">
		<div
			style="--d:flex; --g:0.2rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.8rem; --weight:500; --radius:9999px; --bgc:transparent; --py:0.2rem; touch-action:auto; --pe:auto"
	class="scrollbar-none"
		>
			<button
				style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedTab === 'knowledge'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				type="button"
				on:click={() => {
					selectedTab = 'knowledge';
				}}>{$i18n.t('Knowledge')}</button
			>

			<button
				style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedTab === 'chats'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				type="button"
				on:click={() => {
					selectedTab = 'chats';
				}}
			>
				{$i18n.t('Chats')}
			</button>
		</div>
	</div> -->

	<div class="">
		{#if selectedTab === 'knowledge'}
			<FolderKnowledge />
		{:else if selectedTab === 'chats'}
			<ChatList chats={folder?.items?.chats ?? []} />
		{/if}
	</div>
</div>
