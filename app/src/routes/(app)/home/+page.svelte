<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { user, chats, pinnedChats } from '$lib/stores';
	import { getChatList, getPinnedChatList } from '$lib/apis/chats';
	import { formatDate } from '$lib/utils';

	const i18n = getContext('i18n');

	const RECENT_LIMIT = 5;
	const PINNED_LIMIT = 5;

	let recentChats: any[] = [];
	let pinned: any[] = [];

	$: recentChats = ($chats ?? []).slice(0, RECENT_LIMIT);
	$: pinned = ($pinnedChats ?? []).slice(0, PINNED_LIMIT);

	onMount(async () => {
		if (!$chats?.length) {
			chats.set(await getChatList(localStorage.token, 1));
		}
		if (!$pinnedChats?.length) {
			pinnedChats.set(await getPinnedChatList(localStorage.token));
		}
	});

	function getGreeting(): string {
		const h = new Date().getHours();
		if (h < 12) return 'Good morning';
		if (h < 17) return 'Good afternoon';
		return 'Good evening';
	}

	const soonWidgets = [
		{
			icon: '📅',
			title: 'Calendar',
			desc: 'Your schedule at a glance. Meetings, deadlines, and reminders.'
		},
		{
			icon: '📊',
			title: 'Usage',
			desc: 'Track your activity, token usage, and model performance over time.'
		},
		{
			icon: '⚡',
			title: 'Quick Actions',
			desc: 'One-tap shortcuts to your most-used prompts and workflows.'
		}
	];

	const cardStyle =
		'--d:flex; --fd:column; --radius:0.6rem; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --bw:1px; --bs:solid; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-900)';

	const chatItemStyle =
		'--d:flex; --ai:center; --jc:space-between; --px:0.6rem; --py:0.5rem; --radius:0.375rem; --tn:background-color 150ms ease; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850)';
</script>

<div style="--maxw:56rem; --mx:auto; --px:1.5rem; --py:2rem">
	<!-- Greeting -->
	<div style="--mb:2rem">
		<h1 style="--size:1.75rem; --weight:700; --lh:1.2; --mb:0.25rem">
			{$i18n.t(getGreeting())}, {$user?.name?.split(' ')[0] ?? ''}
		</h1>
		<p
			style="--size:0.9375rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
		>
			{$i18n.t("Welcome to your personal space. Here's what's happening.")}
		</p>
	</div>

	<!-- Live Sections -->
	<div style="--d:grid; --g:0.6rem; --mb:1.5rem" class="grid-cols-1 lg:grid-cols-2">
		<!-- Recent Chats -->
		<div style="{cardStyle}; --p:1rem">
			<div style="--d:flex; --ai:center; --jc:space-between; --mb:0.6rem">
				<h2 style="--size:0.9375rem; --weight:600; --d:flex; --ai:center; --g:0.5rem">
					<span>💬</span> {$i18n.t('Recent Chats')}
				</h2>
				{#if recentChats.length > 0}
					<a
						href="/c/{recentChats[0]?.id}"
						style="--size:0.6rem; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --dark-hvr-c:var(--color-gray-200); --tn:color 150ms ease"
					>
						{$i18n.t('View all')} &rarr;
					</a>
				{/if}
			</div>

			{#if recentChats.length > 0}
				<div style="--d:flex; --fd:column; --g:0.125rem">
					{#each recentChats as chat}
						<a href="/c/{chat.id}" style={chatItemStyle} class="no-underline">
							<span
								style="--size:0.8125rem; overflow:hidden; text-overflow:ellipsis; --ws:nowrap; --fx:1; --mr:0.6rem"
							>
								{chat.title}
							</span>
							<span
								style="--size:0.6875rem; --c:var(--color-gray-400); --ws:nowrap; --fx:none"
							>
								{formatDate(chat.updated_at * 1000)}
							</span>
						</a>
					{/each}
				</div>
			{:else}
				<p
					style="--size:0.8125rem; --c:var(--color-gray-400); --ta:center; --py:1.5rem; --m:0"
				>
					{$i18n.t('No chats yet. Start a conversation!')}
				</p>
			{/if}
		</div>

		<!-- Pinned Chats -->
		<div style="{cardStyle}; --p:1rem">
			<div style="--d:flex; --ai:center; --jc:space-between; --mb:0.6rem">
				<h2 style="--size:0.9375rem; --weight:600; --d:flex; --ai:center; --g:0.5rem">
					<span>🔖</span> {$i18n.t('Pinned')}
				</h2>
			</div>

			{#if pinned.length > 0}
				<div style="--d:flex; --fd:column; --g:0.125rem">
					{#each pinned as chat}
						<a href="/c/{chat.id}" style={chatItemStyle} class="no-underline">
							<span
								style="--size:0.8125rem; overflow:hidden; text-overflow:ellipsis; --ws:nowrap; --fx:1; --mr:0.6rem"
							>
								{chat.title}
							</span>
							<span
								style="--size:0.6875rem; --c:var(--color-gray-400); --ws:nowrap; --fx:none"
							>
								{formatDate(chat.updated_at * 1000)}
							</span>
						</a>
					{/each}
				</div>
			{:else}
				<p
					style="--size:0.8125rem; --c:var(--color-gray-400); --ta:center; --py:1.5rem; --m:0"
				>
					{$i18n.t('Pin a chat from the sidebar to see it here.')}
				</p>
			{/if}
		</div>

		<!-- Notes -->
		<a
			href="/notes"
			style="{cardStyle}; --p:1.25rem; --tn:background-color 150ms ease, border-color 150ms ease; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850)"
			class="no-underline"
		>
			<div style="--d:flex; --ai:center; --g:0.5rem; --mb:0.5rem">
				<span style="--size:1.5rem">📝</span>
				<h3 style="--size:0.9375rem; --weight:600">{$i18n.t('Notes')}</h3>
			</div>
			<p
				style="--size:0.8125rem; --lh:1.4; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --m:0"
			>
				{$i18n.t('Quick-capture ideas, meeting notes, and thoughts. Always in reach.')}
			</p>
		</a>

		<!-- Coming Soon Widgets -->
		{#each soonWidgets as w}
			<div style="{cardStyle}; --p:1.25rem; --op:0.55">
				<div style="--d:flex; --ai:center; --jc:space-between; --mb:0.5rem">
					<div style="--d:flex; --ai:center; --g:0.5rem">
						<span style="--size:1.5rem">{w.icon}</span>
						<h3 style="--size:0.9375rem; --weight:600">{$i18n.t(w.title)}</h3>
					</div>
					<span
						style="--size:0.625rem; --weight:500; --px:0.375rem; --py:0.125rem; --radius:9999px; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800); --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
					>
						{$i18n.t('Coming Soon')}
					</span>
				</div>
				<p
					style="--size:0.8125rem; --lh:1.4; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --m:0"
				>
					{$i18n.t(w.desc)}
				</p>
			</div>
		{/each}
	</div>

	<!-- Vision -->
	<div style="{cardStyle}; --p:1.5rem">
		<h2 style="--size:1.125rem; --weight:600; --mb:0.6rem">
			{$i18n.t('Your AI, Your Way')}
		</h2>
		<div
			style="--size:0.875rem; --lh:1.6; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
		>
			<p style="--mb:0.6rem">
				{$i18n.t(
					"This is your dashboard — a personal space that adapts to how you work. Instead of jumping between pages to find what matters, everything lives here."
				)}
			</p>
			<p style="--mb:0.6rem">
				{$i18n.t(
					"We're building toward a widget-based home where you choose what to see: recent conversations, pinned notes, calendar events, usage stats, quick-launch prompts — arranged your way."
				)}
			</p>
			<p style="--m:0">
				{$i18n.t(
					"Think of it as mission control for your AI workflow. Minimal by default, powerful when you need it."
				)}
			</p>
		</div>
	</div>
</div>
