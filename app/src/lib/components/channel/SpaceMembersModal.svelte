<!--
  SpaceMembersModal.svelte — Manage space members (add/remove users).

  Follows the same pattern as SpaceAgentsModal.svelte.
  Members are stored in space.access_control.read.user_ids.
  Only admin and facilitator roles can open this modal (enforced by Navbar.svelte).

  Props:
    show   — boolean to show/hide modal
    space  — the space object with access_control
    onSave — callback after saving (triggers refresh)
-->
<script lang="ts">
	import { getContext } from 'svelte';
	import { updateSpaceById } from '$lib/apis/spaces';
	import { getAllUsers } from '$lib/apis/users';
	import Modal from '$lib/components/common/Modal.svelte';
		import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let space;
	export let onSave: () => void = () => {};

	/** All users in the system (fetched when modal opens) */
	let allUsers: any[] = [];
	/** User IDs currently in this space's access control */
	let memberIds: string[] = [];
	/** Selected user ID from the add dropdown */
	let selectedUserId = '';

	// Fetch users and sync state when the modal opens
	$: if (show && space) {
		memberIds = [...(space?.access_control?.read?.user_ids ?? [])];
		loadUsers();
	}

	async function loadUsers() {
		try {
			const result = await getAllUsers(localStorage.token);
			allUsers = Array.isArray(result) ? result : [];
		} catch (err) {
			console.error('[SpaceMembersModal] Failed to load users:', err);
			allUsers = [];
		}
	}

	// Resolve user objects from IDs for display
	$: members = (allUsers ?? []).length > 0
		? memberIds.map((id) => allUsers.find((u) => u.id === id)).filter(Boolean)
		: [];

	// Available users = all users minus already-added members
	$: availableUsers = (allUsers ?? []).filter((u) => !memberIds.includes(u.id));

	const addMember = () => {
		if (!selectedUserId) return;
		memberIds = [...memberIds, selectedUserId];
		selectedUserId = '';
	};

	const removeMember = (userId: string) => {
		memberIds = memberIds.filter((id) => id !== userId);
	};

	/**
	 * Save updated member list to space.access_control.read.user_ids.
	 * Preserves existing group_ids and other access_control fields.
	 */
	const saveHandler = async () => {
		const currentAC = space.access_control || {};
		const updatedAC = {
			...currentAC,
			read: {
				...(currentAC.read || {}),
				user_ids: memberIds
			}
		};
		await updateSpaceById(localStorage.token, space.id, {
			name: space.name,
			data: space.data,
			meta: space.meta,
			access_control: updatedAC
		});
		show = false;
		onSave();
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<!-- Header -->
		<div style="--d:flex; --jc:space-between; --ai:center; --mb:1rem">
			<h3 style="--weight:600; --size:1.1rem">{$i18n.t('Manage Members')}</h3>
			<button
				style="--c:var(--color-gray-500); --hvr-c:var(--color-gray-700)"
				on:click={() => (show = false)}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					style="--w:1.25rem; --h:1.25rem"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<!-- Current members list -->
		{#if members.length > 0}
			<div style="--d:flex; --fd:column; --g:0.5rem; --mb:1rem">
				{#each members as member (member.id)}
					<div
						style="--d:flex; --ai:center; --jc:space-between; --px:0.75rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800)"
					>
						<div style="--d:flex; --ai:center; --g:0.5rem">
							<img
								src={member.profile_image_url || '/static/icons/favicon.png'}
								alt={member.name}
								style="--w:1.5rem; --h:1.5rem; --radius:9999px; --objf:cover"
							/>
							<span style="--weight:500; --size:0.9rem">{member.name}</span>
							<!-- Show role badge -->
							{#if member.role === 'admin'}
								<span
									style="--size:0.6rem; --px:0.35rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-red-100); --dark-bgc:var(--color-red-900); --c:var(--color-red-700); --dark-c:var(--color-red-300); --weight:600"
								>
									ADMIN
								</span>
							{:else if member.role === 'facilitator'}
								<span
									style="--size:0.6rem; --px:0.35rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-green-100); --dark-bgc:var(--color-green-900); --c:var(--color-green-700); --dark-c:var(--color-green-300); --weight:600"
								>
									FACILITATOR
								</span>
							{/if}
						</div>
						<Tooltip content={$i18n.t('Remove')}>
							<button
								style="--c:var(--color-gray-500); --hvr-c:var(--color-red-500); --tn:color 150ms"
								on:click={() => removeMember(member.id)}
							>
								<Icon name="garbage-bin" className="size-4" />
							</button>
						</Tooltip>
					</div>
				{/each}
			</div>
		{:else}
			<div
				style="--py:2rem; --ta:center; --c:var(--color-gray-400); --size:0.85rem; --mb:1rem"
			>
				{$i18n.t('No members added yet')}
			</div>
		{/if}

		<!-- Add member dropdown -->
		<div style="--d:flex; --g:0.5rem; --mb:1rem">
			<select
				bind:value={selectedUserId}
				style="--fx:1 1 0%; --px:0.75rem; --py:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bgc:#fff; --dark-bgc:var(--color-gray-850); --size:0.85rem"
			>
				<option value="">{$i18n.t('Select a user...')}</option>
				{#each availableUsers as user (user.id)}
					<option value={user.id}>{user.name} ({user.email})</option>
				{/each}
			</select>
			<button
				style="--px:1rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-900); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900); --weight:500; --size:0.85rem; --hvr-opacity:0.9; --tn:opacity 150ms"
				disabled={!selectedUserId}
				on:click={addMember}
			>
				{$i18n.t('Add')}
			</button>
		</div>

		<!-- Action buttons -->
		<div style="--d:flex; --jc:flex-end; --g:0.5rem">
			<button
				style="--px:1rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --weight:500; --size:0.85rem"
				on:click={() => (show = false)}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				style="--px:1rem; --py:0.5rem; --radius:0.5rem; --bgc:var(--color-gray-900); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900); --weight:500; --size:0.85rem; --hvr-opacity:0.9; --tn:opacity 150ms"
				on:click={saveHandler}
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</div>
</Modal>
