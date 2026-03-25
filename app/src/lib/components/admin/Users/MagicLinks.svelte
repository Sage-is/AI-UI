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
		deleteMagicLink,
		sendMagicLink
	} from '$lib/apis/magic-links';
	import { getGroups } from '$lib/apis/groups';
	import { getBridgeConnections } from '$lib/apis/bridges';

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

	// Send-on-create fields
	let createBridgeId = '';
	let createRecipients = '';
	let createMessage = '';

	// Send modal state
	let showSendModal = false;
	let sendLinkId = '';
	let sendBridgeId = '';
	let sendRecipients = '';
	let sendMessage = '';
	let sending = false;
	let bridgeConnections = [];

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

	const loadBridges = async () => {
		try {
			bridgeConnections = await getBridgeConnections(localStorage.token);
		} catch (err) {
			console.error('Failed to load bridges:', err);
		}
	};

	const openSendModal = (linkId) => {
		sendLinkId = linkId;
		sendBridgeId = bridgeConnections.length > 0 ? bridgeConnections[0].id : '';
		sendRecipients = '';
		sendMessage = '';
		showSendModal = true;
	};

	const handleSend = async (linkId, bridgeId, recipientsText, message = '') => {
		const recipients = recipientsText
			.split(/[,\n]/)
			.map((r) => r.trim())
			.filter(Boolean);
		if (!bridgeId || recipients.length === 0) {
			toast.error('Please select a bridge and enter at least one recipient');
			return;
		}
		sending = true;
		try {
			const result = await sendMagicLink(localStorage.token, linkId, {
				bridge_connection_id: bridgeId,
				recipients,
				message: message || undefined
			});
			if (result.failed > 0) {
				toast.warning(`Sent to ${result.sent}, failed ${result.failed}`);
			} else {
				toast.success(`Sent to ${result.sent} recipient${result.sent !== 1 ? 's' : ''}`);
			}
			showSendModal = false;
		} catch (err) {
			toast.error(`Failed to send: ${err}`);
		}
		sending = false;
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

				// Auto-send if recipients were provided
				if (createBridgeId && createRecipients.trim()) {
					await handleSend(result.id, createBridgeId, createRecipients, createMessage);
				}

				showCreateForm = false;
				selectedGroupIds = [];
				maxUses = 10;
				accountDurationHours = 24;
				linkExpiresHours = 168;
				webhookUrl = '';
				createBridgeId = '';
				createRecipients = '';
				createMessage = '';
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
		await Promise.all([loadLinks(), loadGroups(), loadBridges()]);
	});
</script>

<div>
	<div style="--d:flex; --jc:space-between; --ai:center; --mb:1rem">
		<div style="--size:1.125rem; --weight:500">
			{$i18n.t('Magic Links')}
		</div>
		<Tooltip content={$i18n.t('Create Magic Link')}>
			<button
				style="--p:0.5rem; --radius:0.6rem; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --tn:all 150ms; --d:flex; --ai:center; --cur:pointer"
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
			style="--p:1rem; --mb:1rem; --radius:0.6rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --d:flex; --fd:column; --g:0.6rem"
		>
			<div style="--weight:500; --size:0.8rem">{$i18n.t('Create New Magic Link')}</div>

			{#if groups.length > 0}
				<div>
					<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Assign to Groups')}</label
					>
					<div style="--d:flex; --fd:column; --g:0.2rem; --maxh:8rem; --ofy:auto">
						{#each groups as group}
							<label style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem; --cur:pointer">
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

			<div style="--d:flex; --g:0.6rem; --fw:wrap">
				<div style="--fx:1 1 0%">
					<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Max Uses')}</label
					>
					<input
						type="number"
						bind:value={maxUses}
						min="1"
						style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem"
					/>
				</div>

				<div style="--fx:1 1 0%">
					<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Account Duration (hours)')}</label
					>
					<input
						type="number"
						bind:value={accountDurationHours}
						min="1"
						style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem"
					/>
				</div>

				<div style="--fx:1 1 0%">
					<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Link Expires (hours)')}</label
					>
					<input
						type="number"
						bind:value={linkExpiresHours}
						min="1"
						style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem"
					/>
				</div>
			</div>

			<div>
				<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
					>{$i18n.t('Webhook URL (optional)')}</label
				>
				<input
					type="url"
					bind:value={webhookUrl}
					placeholder="https://..."
					style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem"
				/>
			</div>

			{#if bridgeConnections.length > 0}
				<details>
					<summary style="cursor:pointer; font-size:0.8rem; font-weight:500; color:var(--color-gray-600)"
						>{$i18n.t('Send to recipients (optional)')}</summary
					>
					<div style="--d:flex; --fd:column; --g:0.5rem; --mt:0.5rem">
						<div>
							<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
								>{$i18n.t('Bridge')}</label
							>
							<select
								bind:value={createBridgeId}
								style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem"
							>
								<option value="">{$i18n.t('Select a bridge...')}</option>
								{#each bridgeConnections as bc}
									<option value={bc.id}>{bc.name} ({bc.platform})</option>
								{/each}
							</select>
						</div>
						<div>
							<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
								>{$i18n.t('Recipients (one per line or comma-separated)')}</label
							>
							<textarea
								bind:value={createRecipients}
								rows="3"
								placeholder={$i18n.t('e.g. 1234567890@c.us')}
								style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem; resize:vertical"
							></textarea>
						</div>
						<div>
							<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
								>{$i18n.t('Message (optional)')}</label
							>
							<textarea
								bind:value={createMessage}
								rows="2"
								placeholder={$i18n.t('Custom message to include with the link')}
								style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem; resize:vertical"
							></textarea>
						</div>
					</div>
				</details>
			{/if}

			<div style="--d:flex; --g:0.5rem; --jc:flex-end">
				<button
					style="--px:0.6rem; --py:0.4rem; --radius:0.5rem; --size:0.8rem; --cur:pointer; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)"
					on:click={() => {
						showCreateForm = false;
					}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					style="--px:0.6rem; --py:0.4rem; --radius:0.5rem; --size:0.8rem; --cur:pointer; --bgc:var(--color-gray-900); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900); --weight:500"
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
		<div style="--ta:center; --py:2rem; --c:var(--color-gray-500); --size:0.8rem">
			{$i18n.t('No magic links created yet')}
		</div>
	{:else}
		<div style="--d:flex; --fd:column; --g:0.5rem">
			{#each links as link}
				<div
					style="--p:0.6rem; --radius:0.6rem; --bgc:#fff; --dark-bgc:var(--color-gray-850); --d:flex; --fd:column; --g:0.5rem; --bw:1px; --bs:solid; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700)"
				>
					<div style="--d:flex; --jc:space-between; --ai:center">
						<div style="--d:flex; --ai:center; --g:0.5rem">
							<Badge
								type={link.is_active ? 'success' : 'muted'}
								content={link.is_active ? $i18n.t('Active') : $i18n.t('Inactive')}
							/>
							<span style="--size:0.6rem; --c:var(--color-gray-500)">
								{link.use_count}/{link.max_uses} {$i18n.t('uses')}
							</span>
						</div>

						<div style="--d:flex; --g:0.2rem">
							{#if link.is_active}
								<Tooltip content={$i18n.t('Copy Link')}>
									<button
										style="--px:0.5rem; --py:0.2rem; --radius:0.5rem; --size:0.6rem; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-700)"
										on:click={() => copyLink(link.token)}
									>
										{$i18n.t('Copy')}
									</button>
								</Tooltip>
								{#if bridgeConnections.length > 0}
									<Tooltip content={$i18n.t('Send via Bridge')}>
										<button
											style="--px:0.5rem; --py:0.2rem; --radius:0.5rem; --size:0.6rem; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-700); --c:#3b82f6"
											on:click={() => openSendModal(link.id)}
										>
											{$i18n.t('Send')}
										</button>
									</Tooltip>
								{/if}
								<button
									style="--px:0.5rem; --py:0.2rem; --radius:0.5rem; --size:0.6rem; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-700); --c:#f59e0b"
									on:click={() => handleDeactivate(link.id)}
								>
									{$i18n.t('Deactivate')}
								</button>
							{/if}
							<button
								style="--px:0.5rem; --py:0.2rem; --radius:0.5rem; --size:0.6rem; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-700); --c:#ef4444"
								on:click={() => handleDelete(link.id)}
							>
								{$i18n.t('Delete')}
							</button>
						</div>
					</div>

					<div style="--size:0.6rem; --c:var(--color-gray-500); --d:flex; --g:1rem; --fw:wrap">
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

<!-- Send Modal -->
{#if showSendModal}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		style="--pos:fixed; --inset:0; --bgc:rgba(0,0,0,0.5); --d:flex; --ai:center; --jc:center; --z:50"
		on:click|self={() => (showSendModal = false)}
	>
		<div
			style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-900); --radius:0.6rem; --p:1.5rem; --w:100%; --maxw:28rem; --mx:1rem"
		>
			<div style="--weight:600; --size:1rem; --mb:1rem">{$i18n.t('Send Magic Link')}</div>

			<div style="--d:flex; --fd:column; --g:0.6rem">
				<div>
					<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Bridge')}</label
					>
					<select
						bind:value={sendBridgeId}
						style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem"
					>
						{#each bridgeConnections as bc}
							<option value={bc.id}>{bc.name} ({bc.platform})</option>
						{/each}
					</select>
				</div>

				<div>
					<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Recipients (one per line or comma-separated)')}</label
					>
					<textarea
						bind:value={sendRecipients}
						rows="4"
						placeholder={$i18n.t('e.g. 1234567890@c.us')}
						style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem; resize:vertical"
					></textarea>
				</div>

				<div>
					<label style="--d:block; --size:0.6rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Message (optional)')}</label
					>
					<textarea
						bind:value={sendMessage}
						rows="3"
						placeholder={$i18n.t('Custom message to include with the link')}
						style="--w:100%; --p:0.4rem; --radius:0.5rem; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bgc:#fff; --dark-bgc:var(--color-gray-800); --size:0.8rem; resize:vertical"
					></textarea>
				</div>
			</div>

			<div style="--d:flex; --g:0.5rem; --jc:flex-end; --mt:1rem">
				<button
					style="--px:0.6rem; --py:0.4rem; --radius:0.5rem; --size:0.8rem; --cur:pointer; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)"
					on:click={() => (showSendModal = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					style="--px:0.6rem; --py:0.4rem; --radius:0.5rem; --size:0.8rem; --cur:pointer; --bgc:var(--color-gray-900); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900); --weight:500"
					disabled={sending}
					on:click={() => handleSend(sendLinkId, sendBridgeId, sendRecipients, sendMessage)}
				>
					{sending ? $i18n.t('Sending...') : $i18n.t('Send')}
				</button>
			</div>
		</div>
	</div>
{/if}
