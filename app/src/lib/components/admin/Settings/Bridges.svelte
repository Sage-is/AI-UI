<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import {
		getBridgeConnections,
		createBridgeConnection,
		updateBridgeConnection,
		deleteBridgeConnection,
		toggleBridgeConnection,
		restartBridgeConnection,
		getAvailablePlatforms
	} from '$lib/apis/bridges';

	import { user } from '$lib/stores';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext('i18n');

	let bridges: any[] = [];
	let platforms: any[] = [];
	let loading = true;

	// Modal state
	let showModal = false;
	let editingBridge: any = null;

	// Form fields
	let formPlatform = '';
	let formName = '';
	let formMode = 'ai_chat';
	let formConfig: Record<string, string> = {};
	let formChannelId = '';
	let formModelId = '';
	let formUserProvisioning = 'auto_create';
	let formAllowedIds = '';
	let formEnabled = true;

	const loadData = async () => {
		loading = true;
		try {
			[bridges, platforms] = await Promise.all([
				getBridgeConnections(localStorage.token),
				getAvailablePlatforms(localStorage.token)
			]);
		} catch (err: any) {
			toast.error(err);
		}
		loading = false;
	};

	onMount(loadData);

	const getStatusColor = (status: string) => {
		switch (status) {
			case 'connected':
				return 'bg-green-500';
			case 'starting':
				return 'bg-yellow-500';
			case 'error':
				return 'bg-red-500';
			default:
				return 'bg-gray-400';
		}
	};

	const getPlatformDisplayName = (platform: string) => {
		const p = platforms.find((pl: any) => pl.platform === platform);
		return p?.display_name || platform;
	};

	const getConfigSchema = (platform: string) => {
		const p = platforms.find((pl: any) => pl.platform === platform);
		return p?.config_schema || [];
	};

	const openAddModal = () => {
		editingBridge = null;
		formPlatform = platforms.length > 0 ? platforms[0].platform : '';
		formName = '';
		formMode = 'ai_chat';
		formConfig = {};
		formChannelId = '';
		formModelId = '';
		formUserProvisioning = 'auto_create';
		formAllowedIds = '';
		formEnabled = true;
		showModal = true;
	};

	const openEditModal = (bridge: any) => {
		editingBridge = bridge;
		formPlatform = bridge.platform;
		formName = bridge.name;
		formMode = bridge.mode;
		formConfig = { ...(bridge.config || {}) };
		formChannelId = bridge.channel_id || '';
		formModelId = bridge.model_id || '';
		formUserProvisioning = bridge.user_provisioning || 'auto_create';
		formAllowedIds = bridge.allowed_ids ? bridge.allowed_ids.join(', ') : '';
		formEnabled = bridge.enabled;
		showModal = true;
	};

	const handleSave = async () => {
		try {
			const data: any = {
				platform: formPlatform,
				name: formName,
				mode: formMode,
				config: formConfig,
				channel_id: formChannelId || null,
				model_id: formModelId || null,
				user_provisioning: formUserProvisioning,
				allowed_ids: formAllowedIds
					? formAllowedIds
							.split(',')
							.map((s: string) => s.trim())
							.filter(Boolean)
					: null,
				enabled: formEnabled
			};

			if (editingBridge) {
				await updateBridgeConnection(localStorage.token, editingBridge.id, data);
				toast.success($i18n.t('Bridge updated successfully'));
			} else {
				await createBridgeConnection(localStorage.token, data);
				toast.success($i18n.t('Bridge created successfully'));
			}

			showModal = false;
			await loadData();
		} catch (err: any) {
			toast.error(err);
		}
	};

	const handleDelete = async (id: string) => {
		if (!confirm($i18n.t('Are you sure you want to delete this bridge connection?'))) return;
		try {
			await deleteBridgeConnection(localStorage.token, id);
			toast.success($i18n.t('Bridge deleted'));
			await loadData();
		} catch (err: any) {
			toast.error(err);
		}
	};

	const handleToggle = async (id: string) => {
		try {
			await toggleBridgeConnection(localStorage.token, id);
			await loadData();
		} catch (err: any) {
			toast.error(err);
		}
	};

	const handleRestart = async (id: string) => {
		try {
			await restartBridgeConnection(localStorage.token, id);
			toast.success($i18n.t('Bridge restarted'));
			await loadData();
		} catch (err: any) {
			toast.error(err);
		}
	};
</script>

<div style="--d:flex; --fd:column; --g:1rem">
	<div style="--d:flex; --ai:center; --jc:space-between">
		<div>
			<div style="--weight:600; --size:1rem">{$i18n.t('Messaging Bridges')}</div>
			<div style="--size:0.8rem; --c:var(--color-gray-500)">
				{$i18n.t('Connect external messaging platforms like WhatsApp to Sage AI')}
			</div>
		</div>
		<button
			class="btn btn-primary"
			style="--d:flex; --ai:center; --g:0.25rem; --px:0.75rem; --py:0.375rem; --br:0.5rem; --bg:var(--color-gray-800); --c:white; --size:0.8rem; --dark-bg:var(--color-gray-200); --dark-c:var(--color-gray-900)"
			on:click={openAddModal}
		>
			<Plus className="size-3.5" />
			{$i18n.t('Add Bridge')}
		</button>
	</div>

	{#if loading}
		<div style="--d:flex; --jc:center; --py:2rem">
			<Spinner />
		</div>
	{:else if bridges.length === 0}
		<div
			style="--d:flex; --fd:column; --ai:center; --jc:center; --py:3rem; --c:var(--color-gray-500); --size:0.875rem"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				style="--w:3rem; --h:3rem; --mb:0.5rem; --c:var(--color-gray-400)"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
				/>
			</svg>
			<div>{$i18n.t('No bridge connections configured')}</div>
			<div style="--size:0.75rem">{$i18n.t('Click "Add Bridge" to connect a messaging platform')}</div>
		</div>
	{:else}
		<div style="--d:flex; --fd:column; --g:0.5rem">
			{#each bridges as bridge}
				<div
					style="--d:flex; --ai:center; --jc:space-between; --p:0.75rem; --br:0.5rem; --b:1px solid var(--color-gray-200); --dark-b:1px solid var(--color-gray-700)"
				>
					<div style="--d:flex; --ai:center; --g:0.75rem">
						<div
							class={`${getStatusColor(bridge.status)}`}
							style="--w:0.5rem; --h:0.5rem; --br:9999px; --fx-sh:none"
						></div>
						<div>
							<div style="--weight:500; --size:0.875rem">{bridge.name}</div>
							<div style="--size:0.75rem; --c:var(--color-gray-500); --d:flex; --g:0.5rem">
								<span>{getPlatformDisplayName(bridge.platform)}</span>
								<span>-</span>
								<span>{bridge.mode === 'ai_chat' ? 'AI Chat' : 'Channel Bridge'}</span>
								{#if bridge.status_message}
									<span>- {bridge.status_message}</span>
								{/if}
							</div>
						</div>
					</div>

					<div style="--d:flex; --ai:center; --g:0.5rem">
						<Tooltip content={$i18n.t('Restart')}>
							<button
								class="btn"
								style="--p:0.25rem; --br:0.375rem"
								on:click={() => handleRestart(bridge.id)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
									/>
								</svg>
							</button>
						</Tooltip>

						<Tooltip content={$i18n.t('Edit')}>
							<button
								class="btn"
								style="--p:0.25rem; --br:0.375rem"
								on:click={() => openEditModal(bridge)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
									/>
								</svg>
							</button>
						</Tooltip>

						<Tooltip content={$i18n.t('Delete')}>
							<button
								class="btn"
								style="--p:0.25rem; --br:0.375rem; --c:var(--color-red-500)"
								on:click={() => handleDelete(bridge.id)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
									/>
								</svg>
							</button>
						</Tooltip>

						<Switch
							bind:state={bridge.enabled}
							on:change={() => handleToggle(bridge.id)}
						/>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Add/Edit Modal -->
{#if showModal}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="modal-overlay"
		style="--pos:fixed; --inset:0; --bg:rgba(0,0,0,0.5); --d:flex; --ai:center; --jc:center; --z:50"
		on:click|self={() => (showModal = false)}
	>
		<div
			style="--bg:var(--color-gray-50); --dark-bg:var(--color-gray-900); --br:0.75rem; --p:1.5rem; --w:100%; --maxw:32rem; --maxh:90vh; --ofy:auto; --mx:1rem"
		>
			<div style="--weight:600; --size:1.1rem; --mb:1rem">
				{editingBridge ? $i18n.t('Edit Bridge') : $i18n.t('Add Bridge')}
			</div>

			<div style="--d:flex; --fd:column; --g:0.75rem">
				<!-- Platform -->
				{#if !editingBridge}
					<div>
						<label
							style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem"
							for="bridge-platform"
						>
							{$i18n.t('Platform')}
						</label>
						<select
							id="bridge-platform"
							bind:value={formPlatform}
							style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
							on:change={() => (formConfig = {})}
						>
							{#each platforms as platform}
								<option value={platform.platform}>{platform.display_name}</option>
							{/each}
						</select>
					</div>
				{/if}

				<!-- Name -->
				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem" for="bridge-name">
						{$i18n.t('Name')}
					</label>
					<input
						id="bridge-name"
						type="text"
						bind:value={formName}
						placeholder={$i18n.t('My WhatsApp Bridge')}
						style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
					/>
				</div>

				<!-- Mode -->
				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem" for="bridge-mode">
						{$i18n.t('Mode')}
					</label>
					<select
						id="bridge-mode"
						bind:value={formMode}
						style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
					>
						<option value="ai_chat">{$i18n.t('AI Chat - Direct AI conversations')}</option>
						<option value="channel_bridge"
							>{$i18n.t('Channel Bridge - Mirror to Sage channel')}</option
						>
					</select>
				</div>

				<!-- Platform Config -->
				{#each getConfigSchema(formPlatform) as field}
					<div>
						<label
							style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem"
							for="bridge-config-{field.name}"
						>
							{field.label}
							{#if field.required}<span style="--c:var(--color-red-500)">*</span>{/if}
						</label>
						{#if field.type === 'password'}
							<input
								id="bridge-config-{field.name}"
								type="password"
								bind:value={formConfig[field.name]}
								placeholder={field.placeholder || ''}
								style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
							/>
						{:else}
							<input
								id="bridge-config-{field.name}"
								type="text"
								bind:value={formConfig[field.name]}
								placeholder={field.placeholder || ''}
								style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
							/>
						{/if}
					</div>
				{/each}

				<!-- Model ID (for ai_chat mode) -->
				{#if formMode === 'ai_chat'}
					<div>
						<label
							style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem"
							for="bridge-model"
						>
							{$i18n.t('AI Model ID')}
						</label>
						<input
							id="bridge-model"
							type="text"
							bind:value={formModelId}
							placeholder={$i18n.t('e.g. gpt-4o or leave blank for default')}
							style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
						/>
					</div>
				{/if}

				<!-- Channel ID (for channel_bridge mode) -->
				{#if formMode === 'channel_bridge'}
					<div>
						<label
							style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem"
							for="bridge-channel"
						>
							{$i18n.t('Sage Channel ID')}
						</label>
						<input
							id="bridge-channel"
							type="text"
							bind:value={formChannelId}
							placeholder={$i18n.t('Channel ID to bridge messages to')}
							style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
						/>
					</div>
				{/if}

				<!-- User Provisioning -->
				<div>
					<label
						style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem"
						for="bridge-provisioning"
					>
						{$i18n.t('User Provisioning')}
					</label>
					<select
						id="bridge-provisioning"
						bind:value={formUserProvisioning}
						style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
					>
						<option value="auto_create"
							>{$i18n.t('Auto Create - Automatically create user accounts')}</option
						>
						<option value="pre_approved"
							>{$i18n.t('Pre-Approved - Only allowlisted users')}</option
						>
						<option value="disabled">{$i18n.t('Disabled - No new users')}</option>
					</select>
				</div>

				<!-- Allowed IDs -->
				<div>
					<label
						style="--d:block; --size:0.8rem; --weight:500; --mb:0.25rem"
						for="bridge-allowlist"
					>
						{$i18n.t('Allowed IDs (comma-separated, optional)')}
					</label>
					<input
						id="bridge-allowlist"
						type="text"
						bind:value={formAllowedIds}
						placeholder={$i18n.t('e.g. 1234567890@c.us, 0987654321@c.us')}
						style="--w:100%; --p:0.5rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --bg:var(--color-gray-50); --dark-bg:var(--color-gray-800)"
					/>
				</div>

				<!-- Enabled -->
				<div style="--d:flex; --ai:center; --jc:space-between">
					<label style="--size:0.8rem; --weight:500" for="bridge-enabled">
						{$i18n.t('Enabled')}
					</label>
					<Switch bind:state={formEnabled} />
				</div>
			</div>

			<!-- Actions -->
			<div style="--d:flex; --jc:flex-end; --g:0.5rem; --mt:1.25rem">
				<button
					class="btn"
					style="--px:1rem; --py:0.375rem; --br:0.375rem; --b:1px solid var(--color-gray-300); --dark-b:1px solid var(--color-gray-600); --size:0.8rem"
					on:click={() => (showModal = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="btn btn-primary"
					style="--px:1rem; --py:0.375rem; --br:0.375rem; --bg:var(--color-gray-800); --c:white; --size:0.8rem; --dark-bg:var(--color-gray-200); --dark-c:var(--color-gray-900)"
					on:click={handleSave}
					disabled={!formName || !formPlatform}
				>
					{editingBridge ? $i18n.t('Update') : $i18n.t('Create')}
				</button>
			</div>
		</div>
	</div>
{/if}
