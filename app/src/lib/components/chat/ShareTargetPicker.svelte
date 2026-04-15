<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { getGroups } from '$lib/apis/groups';
	import { getUsers, getUserById } from '$lib/apis/users';
	import { user } from '$lib/stores';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	export let selectedTargets: Array<{ type: string; id: string; mode: string }> = [];
	export let globalMode: string = 'live';

	let groups: Array<{ id: string; name: string; user_ids: string[] }> = [];
	let coMembers: Array<{ id: string; name: string; email: string }> = [];
	let searchQuery = '';
	let loading = true;

	onMount(async () => {
		try {
			const allGroups = await getGroups(localStorage.token);
			groups = allGroups;

			const currentUserId = $user?.id;
			const isAdmin = $user?.role === 'admin';

			if (isAdmin) {
				// Admin sees all users
				const result = await getUsers(localStorage.token);
				const allUsers = result?.users ?? result ?? [];
				coMembers = allUsers
					.filter((u) => u.id !== currentUserId)
					.map((u) => ({ id: u.id, name: u.name, email: u.email }));
			} else {
				// Non-admin: extract unique user IDs from visible groups
				const userIds = new Set<string>();
				for (const group of allGroups) {
					if (group.user_ids) {
						for (const uid of group.user_ids) {
							if (uid !== currentUserId) {
								userIds.add(uid);
							}
						}
					}
				}

				// Fetch details for each user
				const userDetails = await Promise.all(
					Array.from(userIds).map((uid) =>
						getUserById(localStorage.token, uid).catch(() => null)
					)
				);
				coMembers = userDetails
					.filter((u) => u && u.name)
					.map((u) => ({ id: u.id, name: u.name, email: u.email }));
			}
		} catch (err) {
			console.error('Failed to load groups/members:', err);
		}
		loading = false;
	});

	function isSelected(type: string, id: string): boolean {
		return selectedTargets.some((t) => t.type === type && t.id === id);
	}

	function toggleTarget(type: string, id: string) {
		if (isSelected(type, id)) {
			selectedTargets = selectedTargets.filter((t) => !(t.type === type && t.id === id));
		} else {
			selectedTargets = [...selectedTargets, { type, id, mode: globalMode }];
		}
	}

	$: filteredGroups = groups.filter(
		(g) =>
			!searchQuery || g.name.toLowerCase().includes(searchQuery.toLowerCase())
	);

	$: filteredMembers = coMembers.filter(
		(m) =>
			!searchQuery ||
			m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
			m.email.toLowerCase().includes(searchQuery.toLowerCase())
	);

	$: {
		// Update mode on all selected targets when globalMode changes
		selectedTargets = selectedTargets.map((t) => ({ ...t, mode: globalMode }));
	}
</script>

<div style="--d:flex; --fd:column; --g:0.6rem">
	<!-- Search -->
	<div style="--d:flex; --ai:center; --g:0.5rem; --px:0.5rem; --py:0.4rem; --radius:0.5rem; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800)">
		<Icon name="search" className="size-4 text-gray-400" />
		<input
			bind:value={searchQuery}
			placeholder={$i18n.t('Search people and groups...')}
			style="--bgc:transparent; --oe:none; --w:100%; --size:0.8125rem; --b:none; --c:inherit"
		/>
	</div>

	<!-- Mode toggle -->
	<div style="--d:flex; --ai:center; --jc:space-between; --size:0.8125rem">
		<span style="--c:var(--color-gray-500); --dark-c:var(--color-gray-400)">{$i18n.t('Share mode')}</span>
		<div style="--d:flex; --g:0.2rem">
			<button
				style="--px:0.5rem; --py:0.125rem; --radius:0.2rem; --size:0.6rem; --weight:500; --tn:all 150ms ease; {globalMode === 'live' ? '--bgc:#000; --c:#fff; --dark-bgc:#fff; --dark-c:#000' : '--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --c:var(--color-gray-600); --dark-c:var(--color-gray-400)'}"
				on:click={() => { globalMode = 'live'; }}
				type="button"
			>
				{$i18n.t('Live')}
			</button>
			<button
				style="--px:0.5rem; --py:0.125rem; --radius:0.2rem; --size:0.6rem; --weight:500; --tn:all 150ms ease; {globalMode === 'snapshot' ? '--bgc:#000; --c:#fff; --dark-bgc:#fff; --dark-c:#000' : '--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --c:var(--color-gray-600); --dark-c:var(--color-gray-400)'}"
				on:click={() => { globalMode = 'snapshot'; }}
				type="button"
			>
				{$i18n.t('Snapshot')}
			</button>
		</div>
	</div>

	{#if loading}
		<div style="--d:flex; --jc:center; --py:1rem; --c:var(--color-gray-400)">
			<span style="--size:0.8125rem">{$i18n.t('Loading...')}</span>
		</div>
	{:else}
		<div style="--maxh:16rem; --ofy:auto; --d:flex; --fd:column; --g:0.2rem">
			<!-- Groups section -->
			{#if filteredGroups.length > 0}
				<div style="--size:0.6875rem; --weight:600; --tt:uppercase; --ls:0.05em; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --px:0.2rem; --pt:0.2rem">
					{$i18n.t('Groups')}
				</div>
				{#each filteredGroups as group (group.id)}
					<button
						style="--d:flex; --ai:center; --g:0.5rem; --px:0.5rem; --py:0.4rem; --radius:0.4rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:background-color 150ms ease; --w:100%; --ta:left"
						type="button"
						on:click={() => toggleTarget('group', group.id)}
					>
						<Checkbox state={isSelected('group', group.id) ? 'checked' : 'unchecked'} />
						<div style="--d:flex; --fd:column; --g:0.0625rem">
							<span style="--size:0.8125rem; --weight:500">{group.name}</span>
							<span style="--size:0.6875rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
								{group.user_ids?.length ?? 0} {$i18n.t('members')}
							</span>
						</div>
					</button>
				{/each}
			{/if}

			<!-- People section -->
			{#if filteredMembers.length > 0}
				<div style="--size:0.6875rem; --weight:600; --tt:uppercase; --ls:0.05em; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --px:0.2rem; --pt:0.5rem">
					{$i18n.t('People')}
				</div>
				{#each filteredMembers as member (member.id)}
					<button
						style="--d:flex; --ai:center; --g:0.5rem; --px:0.5rem; --py:0.4rem; --radius:0.4rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:background-color 150ms ease; --w:100%; --ta:left"
						type="button"
						on:click={() => toggleTarget('user', member.id)}
					>
						<Checkbox state={isSelected('user', member.id) ? 'checked' : 'unchecked'} />
						<div style="--d:flex; --fd:column; --g:0.0625rem">
							<span style="--size:0.8125rem; --weight:500">{member.name}</span>
							<span style="--size:0.6875rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
								{member.email}
							</span>
						</div>
					</button>
				{/each}
			{/if}

			{#if filteredGroups.length === 0 && filteredMembers.length === 0}
				<div style="--d:flex; --jc:center; --py:1rem; --c:var(--color-gray-400); --size:0.8125rem">
					{#if searchQuery}
						{$i18n.t('No results found')}
					{:else}
						{$i18n.t('No groups or people available')}
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>
