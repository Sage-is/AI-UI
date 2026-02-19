<script>
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import {
		createMagicLink,
		getMagicLinks,
		deactivateMagicLink,
		deleteMagicLink
	} from '$lib/apis/magic-links';
	import { getGroups } from '$lib/apis/groups';

	const i18n = getContext('i18n');

	let links = null;
	let groups = [];
	let showCreateForm = false;

	// Create form fields
	let selectedGroupIds = [];
	let maxUses = 10;
	let accountDurationHours = 24;
	let linkExpiresHours = 168; // 7 days
	let webhookUrl = '';

	const loadLinks = async () => {
		try {
			links = await getMagicLinks(localStorage.token);
		} catch (err) {
			toast.error('Failed to load magic links');
		}
	};

	const loadGroups = async () => {
		try {
			groups = await getGroups(localStorage.token);
		} catch (err) {
			console.error('Failed to load groups:', err);
		}
	};

	const handleCreate = async () => {
		try {
			const data = {
				group_ids: selectedGroupIds.length > 0 ? selectedGroupIds : null,
				max_uses: maxUses,
				account_duration: accountDurationHours * 3600,
				expires_at: Math.floor(Date.now() / 1000) + linkExpiresHours * 3600,
				webhook_url: webhookUrl || null
			};

			const result = await createMagicLink(localStorage.token, data);
			if (result) {
				toast.success('Magic link created');
				showCreateForm = false;
				selectedGroupIds = [];
				maxUses = 10;
				accountDurationHours = 24;
				linkExpiresHours = 168;
				webhookUrl = '';
				await loadLinks();
			}
		} catch (err) {
			toast.error(`Failed to create magic link: ${err}`);
		}
	};

	const handleDeactivate = async (id) => {
		try {
			await deactivateMagicLink(localStorage.token, id);
			toast.success('Magic link deactivated');
			await loadLinks();
		} catch (err) {
			toast.error(`Failed to deactivate: ${err}`);
		}
	};

	const handleDelete = async (id) => {
		try {
			await deleteMagicLink(localStorage.token, id);
			toast.success('Magic link deleted');
			await loadLinks();
		} catch (err) {
			toast.error(`Failed to delete: ${err}`);
		}
	};

	const copyLink = (token) => {
		const url = `${window.location.origin}/join/${token}`;
		navigator.clipboard.writeText(url);
		toast.success('Link copied to clipboard');
	};

	const getGroupName = (id) => {
		const group = groups.find((g) => g.id === id);
		return group ? group.name : id;
	};

	onMount(async () => {
		await Promise.all([loadLinks(), loadGroups()]);
	});
</script>

<div>
	<div style="--d:flex; --jc:space-between; --ai:center; --mb:1rem">
		<div style="--size:1.125rem; --weight:500">
			{$i18n.t('Magic Links')}
		</div>
		<Tooltip content={$i18n.t('Create Magic Link')}>
			<button
				style="--p:0.5rem; --radius:0.75rem; --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-900, #171717); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:all 150ms; --d:flex; --ai:center; --cur:pointer"
				on:click={() => {
					showCreateForm = !showCreateForm;
				}}
			>
				<Plus className="size-3.5" />
			</button>
		</Tooltip>
	</div>

	{#if showCreateForm}
		<div
			style="--p:1rem; --mb:1rem; --radius:0.75rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-850, #262626); --d:flex; --fd:column; --g:0.75rem"
		>
			<div style="--weight:500; --size:0.875rem">{$i18n.t('Create New Magic Link')}</div>

			{#if groups.length > 0}
				<div>
					<label style="--d:block; --size:0.75rem; --weight:500; --mb:0.25rem; --c:var(--color-gray-600, #7a7a7a); --dark-c:var(--color-gray-400, #b4b4b4)"
						>{$i18n.t('Assign to Groups')}</label
					>
					<div style="--d:flex; --fd:column; --g:0.25rem; --maxh:8rem; --ofy:auto">
						{#each groups as group}
							<label style="--d:flex; --ai:center; --g:0.5rem; --size:0.875rem; --cur:pointer">
								<input
									type="checkbox"
									bind:group={selectedGroupIds}
									value={group.id}
								/>
								{group.name}
							</label>
						{/each}
					</div>
				</div>
			{/if}

			<div style="--d:flex; --g:0.75rem; --fw:wrap">
				<div style="--fx:1 1 0%">
					<label style="--d:block; --size:0.75rem; --weight:500; --mb:0.25rem; --c:var(--color-gray-600, #7a7a7a); --dark-c:var(--color-gray-400, #b4b4b4)"
						>{$i18n.t('Max Uses')}</label
					>
					<input
						type="number"
						bind:value={maxUses}
						min="1"
						style="--w:100%; --p:0.375rem; --radius:0.5rem; --bc:var(--color-gray-300, #cdcdcd); --dark-bc:var(--color-gray-600, #7a7a7a); --bgc:#fff; --dark-bgc:var(--color-gray-800, #333); --size:0.875rem"
					/>
				</div>

				<div style="--fx:1 1 0%">
					<label style="--d:block; --size:0.75rem; --weight:500; --mb:0.25rem; --c:var(--color-gray-600, #7a7a7a); --dark-c:var(--color-gray-400, #b4b4b4)"
						>{$i18n.t('Account Duration (hours)')}</label
					>
					<input
						type="number"
						bind:value={accountDurationHours}
						min="1"
						style="--w:100%; --p:0.375rem; --radius:0.5rem; --bc:var(--color-gray-300, #cdcdcd); --dark-bc:var(--color-gray-600, #7a7a7a); --bgc:#fff; --dark-bgc:var(--color-gray-800, #333); --size:0.875rem"
					/>
				</div>

				<div style="--fx:1 1 0%">
					<label style="--d:block; --size:0.75rem; --weight:500; --mb:0.25rem; --c:var(--color-gray-600, #7a7a7a); --dark-c:var(--color-gray-400, #b4b4b4)"
						>{$i18n.t('Link Expires (hours)')}</label
					>
					<input
						type="number"
						bind:value={linkExpiresHours}
						min="1"
						style="--w:100%; --p:0.375rem; --radius:0.5rem; --bc:var(--color-gray-300, #cdcdcd); --dark-bc:var(--color-gray-600, #7a7a7a); --bgc:#fff; --dark-bgc:var(--color-gray-800, #333); --size:0.875rem"
					/>
				</div>
			</div>

			<div>
				<label style="--d:block; --size:0.75rem; --weight:500; --mb:0.25rem; --c:var(--color-gray-600, #7a7a7a); --dark-c:var(--color-gray-400, #b4b4b4)"
					>{$i18n.t('Webhook URL (optional)')}</label
				>
				<input
					type="url"
					bind:value={webhookUrl}
					placeholder="https://..."
					style="--w:100%; --p:0.375rem; --radius:0.5rem; --bc:var(--color-gray-300, #cdcdcd); --dark-bc:var(--color-gray-600, #7a7a7a); --bgc:#fff; --dark-bgc:var(--color-gray-800, #333); --size:0.875rem"
				/>
			</div>

			<div style="--d:flex; --g:0.5rem; --jc:flex-end">
				<button
					style="--px:0.75rem; --py:0.375rem; --radius:0.5rem; --size:0.875rem; --cur:pointer; --bgc:var(--color-gray-200, #e3e3e3); --dark-bgc:var(--color-gray-700, #4e4e4e)"
					on:click={() => {
						showCreateForm = false;
					}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					style="--px:0.75rem; --py:0.375rem; --radius:0.5rem; --size:0.875rem; --cur:pointer; --bgc:var(--color-gray-900, #171717); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900, #171717); --weight:500"
					on:click={handleCreate}
				>
					{$i18n.t('Create')}
				</button>
			</div>
		</div>
	{/if}

	{#if links === null}
		<div style="--d:flex; --jc:center; --py:2rem">
			<Spinner className="size-5" />
		</div>
	{:else if links.length === 0}
		<div style="--ta:center; --py:2rem; --c:var(--color-gray-500, #9b9b9b); --size:0.875rem">
			{$i18n.t('No magic links created yet')}
		</div>
	{:else}
		<div style="--d:flex; --fd:column; --g:0.5rem">
			{#each links as link}
				<div
					style="--p:0.75rem; --radius:0.75rem; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --d:flex; --fd:column; --g:0.5rem; --bw:1px; --bs:solid; --bc:var(--color-gray-200, #e3e3e3); --dark-bc:var(--color-gray-700, #4e4e4e)"
				>
					<div style="--d:flex; --jc:space-between; --ai:center">
						<div style="--d:flex; --ai:center; --g:0.5rem">
							<Badge
								type={link.is_active ? 'success' : 'muted'}
								content={link.is_active ? $i18n.t('Active') : $i18n.t('Inactive')}
							/>
							<span style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">
								{link.use_count}/{link.max_uses} {$i18n.t('uses')}
							</span>
						</div>

						<div style="--d:flex; --g:0.25rem">
							{#if link.is_active}
								<Tooltip content={$i18n.t('Copy Link')}>
									<button
										style="--px:0.5rem; --py:0.25rem; --radius:0.5rem; --size:0.75rem; --cur:pointer; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-700, #4e4e4e)"
										on:click={() => copyLink(link.token)}
									>
										{$i18n.t('Copy')}
									</button>
								</Tooltip>
								<button
									style="--px:0.5rem; --py:0.25rem; --radius:0.5rem; --size:0.75rem; --cur:pointer; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-700, #4e4e4e); --c:#f59e0b"
									on:click={() => handleDeactivate(link.id)}
								>
									{$i18n.t('Deactivate')}
								</button>
							{/if}
							<button
								style="--px:0.5rem; --py:0.25rem; --radius:0.5rem; --size:0.75rem; --cur:pointer; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-700, #4e4e4e); --c:#ef4444"
								on:click={() => handleDelete(link.id)}
							>
								{$i18n.t('Delete')}
							</button>
						</div>
					</div>

					<div style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --d:flex; --g:1rem; --fw:wrap">
						{#if link.group_ids && link.group_ids.length > 0}
							<span>
								{$i18n.t('Groups')}: {link.group_ids.map(getGroupName).join(', ')}
							</span>
						{/if}
						{#if link.account_duration}
							<span>
								{$i18n.t('Duration')}: {Math.round(link.account_duration / 3600)}h
							</span>
						{/if}
						{#if link.expires_at}
							<span>
								{$i18n.t('Expires')}: {dayjs(link.expires_at * 1000).fromNow()}
							</span>
						{/if}
						<span>
							{$i18n.t('Created')}: {dayjs(link.created_at * 1000).fromNow()}
						</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
