<script>
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { page } from '$app/stores';

	import UserList from './Users/UserList.svelte';
	import Groups from './Users/Groups.svelte';
	import MagicLinks from './Users/MagicLinks.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	let selectedTab;
	$: {
		const pathParts = $page.url.pathname.split('/');
		const tabFromPath = pathParts[pathParts.length - 1];
		selectedTab = ['overview', 'groups', 'magic-links'].includes(tabFromPath) ? tabFromPath : 'overview';
	}

	$: if (selectedTab) {
		// scroll to selectedTab
		scrollToTab(selectedTab);
	}

	const scrollToTab = (tabId) => {
		const tabElement = document.getElementById(tabId);
		if (tabElement) {
			tabElement.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
		}
	};

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin' && $user?.role !== 'facilitator') {
			await goto('/');
		}

		loaded = true;

		const containerElement = document.getElementById('users-tabs-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}

		// Scroll to the selected tab on mount
		scrollToTab(selectedTab);
	});
</script>

<div style="--d:flex; --fd:column; --fd-lg:row; --w:100%; --h:100%;  --g-lg:1rem">
	<div
		id="users-tabs-container"
		style="--d:flex; --fd:row; --ofx:auto; --g:0.625rem; --maxw:100%; --g-lg:0.2rem; --fd-lg:column; --fx-lg:none; --w-lg:10rem; --dark-c:var(--color-gray-200); --size:0.8rem; --weight:500; --ta:left"
	class="scrollbar-none"
	>
		<button
			id="overview"
			style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedTab ===
			'overview'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				goto('/admin/users/overview');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="users-group-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Overview')}</div>
		</button>

		<button
			id="groups"
			style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedTab ===
			'groups'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				goto('/admin/users/groups');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="user-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Groups')}</div>
		</button>

		<button
			id="magic-links"
			style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedTab ===
			'magic-links'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				goto('/admin/users/magic-links');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="link" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Magic Links')}</div>
		</button>
	</div>

	<div style="--fx:1 1 0%; --mt:0.2rem; --mt-lg:0; --ofy:scroll">
		{#if selectedTab === 'overview'}
			<UserList />
		{:else if selectedTab === 'groups'}
			<Groups />
		{:else if selectedTab === 'magic-links'}
			<MagicLinks />
		{/if}
	</div>
</div>
