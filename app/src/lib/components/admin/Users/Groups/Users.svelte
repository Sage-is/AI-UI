<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	export let users = [];
	export let userIds = [];

	let filteredUsers = [];

	$: filteredUsers = users
		.filter((user) => {
			if (query === '') {
				return true;
			}

			return (
				user.name.toLowerCase().includes(query.toLowerCase()) ||
				user.email.toLowerCase().includes(query.toLowerCase())
			);
		})
		.sort((a, b) => {
			const aUserIndex = userIds.indexOf(a.id);
			const bUserIndex = userIds.indexOf(b.id);

			// Compare based on userIds or fall back to alphabetical order
			if (aUserIndex !== -1 && bUserIndex === -1) return -1; // 'a' has valid userId -> prioritize
			if (bUserIndex !== -1 && aUserIndex === -1) return 1; // 'b' has valid userId -> prioritize

			// Both a and b are either in the userIds array or not, so we'll sort them by their indices
			if (aUserIndex !== -1 && bUserIndex !== -1) return aUserIndex - bUserIndex;

			// If both are not in the userIds, fallback to alphabetical sorting by name
			return a.name.localeCompare(b.name);
		});

	let query = '';
</script>

<div>
	<div style="--d:flex; --w:100%">
		<div style="--d:flex; --fx:1 1 0%">
			<div style="--as:center; --mr:0.6rem">
				<Search />
			</div>
			<input
				style="--w:100%; --size:0.8rem; --pr:1rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
				bind:value={query}
				placeholder={$i18n.t('Search')}
			/>
		</div>
	</div>

	<div style="--mt:0.6rem"
	class="scrollbar-hidden">
		<div style="--d:flex; --fd:column; --g:0.625rem">
			{#if filteredUsers.length > 0}
				{#each filteredUsers as user, userIdx (user.id)}
					<div style="--d:flex; --fd:row; --ai:center; --g:0.6rem; --w:100%; --size:0.8rem">
						<div style="--d:flex; --ai:center">
							<Checkbox
								state={userIds.includes(user.id) ? 'checked' : 'unchecked'}
								on:change={(e) => {
									if (e.detail === 'checked') {
										userIds = [...userIds, user.id];
									} else {
										userIds = userIds.filter((id) => id !== user.id);
									}
								}}
							/>
						</div>

						<div style="--d:flex; --w:100%; --ai:center; --jc:space-between">
							<Tooltip content={user.email} placement="top-start">
								<div style="--d:flex">
									<div style="--weight:500; --as:center">{user.name}</div>
								</div>
							</Tooltip>

							{#if userIds.includes(user.id)}
								<Badge type="success" content="member" />
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div style="--c:var(--color-gray-500); --size:0.6rem; --ta:center; --py:0.5rem; --px:2.5rem">
					{$i18n.t('No users were found.')}
				</div>
			{/if}
		</div>
	</div>
</div>
