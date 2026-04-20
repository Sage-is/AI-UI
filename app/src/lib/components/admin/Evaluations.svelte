<script>
	import { getContext, tick, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import Leaderboard from './Evaluations/Leaderboard.svelte';
	import Feedbacks from './Evaluations/Feedbacks.svelte';

	import { getAllFeedbacks } from '$lib/apis/evaluations';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	let selectedTab;
	$: {
		const pathParts = $page.url.pathname.split('/');
		const tabFromPath = pathParts[pathParts.length - 1];
		selectedTab = ['leaderboard', 'feedbacks'].includes(tabFromPath) ? tabFromPath : 'leaderboard';
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
	let feedbacks = [];

	onMount(async () => {
		feedbacks = await getAllFeedbacks(localStorage.token);
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

{#if loaded}
	<div style="--d:flex; --fd:column; --fd-lg:row; --w:100%; --h:100%;  --g-lg:1rem">
		<div
			id="users-tabs-container"
			style="--d:flex; --fd:row; --ofx:auto; --g:0.625rem; --maxw:100%; --g-lg:0.2rem; --fd-lg:column; --fx-lg:none; --w-lg:10rem; --dark-c:var(--color-gray-200); --size:0.8rem; --weight:500; --ta:left"
	class="tabs scrollbar-none"
		>
			<button
				id="leaderboard"
				style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedTab ===
				'leaderboard'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					goto('/admin/evaluations/leaderboard');
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<Icon name="clipboard-import-c5ce" className="size-4" />
				</div>
				<div style="--as:center">{$i18n.t('Leaderboard')}</div>
			</button>

			<button
				id="feedbacks"
				style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selectedTab ===
				'feedbacks'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					goto('/admin/evaluations/feedbacks');
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<Icon name="leaderboard-fill-16" className="size-4" />
				</div>
				<div style="--as:center">{$i18n.t('Feedbacks')}</div>
			</button>
		</div>

		<div style="--fx:1 1 0%; --mt:0.2rem; --mt-lg:0; --ofy:scroll">
			{#if selectedTab === 'leaderboard'}
				<Leaderboard {feedbacks} />
			{:else if selectedTab === 'feedbacks'}
				<Feedbacks {feedbacks} />
			{/if}
		</div>
	</div>
{/if}
