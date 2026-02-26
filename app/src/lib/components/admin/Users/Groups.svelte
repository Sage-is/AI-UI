<script>
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, config, user, showSidebar, knowledge } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import UsersSolid from '$lib/components/icons/UsersSolid.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import User from '$lib/components/icons/User.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import GroupModal from './Groups/EditGroupModal.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import GroupItem from './Groups/GroupItem.svelte';
	import AddGroupModal from './Groups/AddGroupModal.svelte';
	import { createNewGroup, getGroups } from '$lib/apis/groups';
	import {
		getUserDefaultPermissions,
		getAllUsers,
		updateUserDefaultPermissions
	} from '$lib/apis/users';

	const i18n = getContext('i18n');

	let loaded = false;

	let users = [];
	let total = 0;

	let groups = [];
	let filteredGroups;

	$: filteredGroups = groups.filter((user) => {
		if (search === '') {
			return true;
		} else {
			let name = user.name.toLowerCase();
			const query = search.toLowerCase();
			return name.includes(query);
		}
	});

	let search = '';
	let defaultPermissions = {
		workshop: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false
		},
		sharing: {
			public_models: false,
			public_knowledge: false,
			public_prompts: false,
			public_tools: false
		},
		chat: {
			controls: true,
			system_prompt: true,
			file_upload: true,
			delete: true,
			edit: true,
			share: true,
			export: true,
			stt: true,
			tts: true,
			call: true,
			multiple_models: true,
			temporary: true,
			temporary_enforced: false
		},
		features: {
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true,
			notes: true
		}
	};

	let showCreateGroupModal = false;
	let showDefaultPermissionsModal = false;

	const setGroups = async () => {
		groups = await getGroups(localStorage.token);
	};

	const addGroupHandler = async (group) => {
		const res = await createNewGroup(localStorage.token, group).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group created successfully'));
			groups = await getGroups(localStorage.token);
		}
	};

	const updateDefaultPermissionsHandler = async (group) => {
		console.debug(group.permissions);

		const res = await updateUserDefaultPermissions(localStorage.token, group.permissions).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			toast.success($i18n.t('Default permissions updated successfully'));
			defaultPermissions = await getUserDefaultPermissions(localStorage.token);
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin' && $user?.role !== 'facilitator') {
			await goto('/');
			return;
		}

		const res = await getAllUsers(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			users = res.users;
			total = res.total;
		}

		await setGroups();
		defaultPermissions = await getUserDefaultPermissions(localStorage.token);

		loaded = true;
	});
</script>

{#if loaded}
	<AddGroupModal bind:show={showCreateGroupModal} onSubmit={addGroupHandler} />
	<div style="--mt:0.125rem; --mb:0.5rem; --g:0.25rem; --d:flex; --fd:column; --fd-md:row; --jc:space-between">
		<div style="--d:flex; --as-md:center; --size:1.125rem; --weight:500; --px:0.125rem">
			{$i18n.t('Groups')}
			<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />

			<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)">{groups.length}</span>
		</div>

		<div style="--d:flex; --g:0.25rem">
			<div style="--d:flex; --w:100%; --g:0.5rem">
				<div style="--d:flex; --fx:1 1 0%">
					<div style="--as:center; --ml:0.25rem; --mr:0.75rem">
						<Search />
					</div>
					<input
						style="--w:100%; --size:0.875rem; --pr:1rem; --py:0.25rem; --btrr:0.75rem; --bbrr:0.75rem; --oe:none; --bgc:transparent"
						bind:value={search}
						placeholder={$i18n.t('Search')}
					/>
				</div>

				<div>
					<Tooltip content={$i18n.t('Create Group')}>
						<button
							style="--p:0.5rem; --radius:0.75rem; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem; --d:flex; --ai:center; --g:0.25rem"
							on:click={() => {
								showCreateGroupModal = !showCreateGroupModal;
							}}
						>
							<Plus className="size-3.5" />
						</button>
					</Tooltip>
				</div>
			</div>
		</div>
	</div>

	<div>
		{#if filteredGroups.length === 0}
			<div style="--d:flex; --fd:column; --ai:center; --jc:center; --h:10rem">
				<div style="--size:1.25rem; --weight:500">
					{$i18n.t('Organize your users')}
				</div>

				<div style="--mt:0.25rem; --size:0.875rem; --dark-c:var(--color-gray-300)">
					{$i18n.t('Use groups to group your users and assign permissions.')}
				</div>

				<div style="--mt:0.75rem">
					<button
						style="--px:1rem; --py:0.375rem; --size:0.875rem; --radius:9999px; --bgc:#000; --hvr-bgc:var(--color-gray-800); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --d:flex; --ai:center; --g:0.25rem"
						aria-label={$i18n.t('Create Group')}
						on:click={() => {
							showCreateGroupModal = true;
						}}
					>
						{$i18n.t('Create Group')}
					</button>
				</div>
			</div>
		{:else}
			<div>
				<div style="--d:flex; --ai:center; --g:0.75rem; --jc:space-between; --size:0.75rem; --tt:uppercase; --px:0.25rem; --weight:700">
					<div style="--w:100%; --fb:60%">Group</div>

					<div style="--w:100%; --fb:40%; --ta:right">Users</div>
				</div>

				<hr style="--mt:0.375rem; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)" />

				{#each filteredGroups as group}
					<div style="--my:0.5rem">
						<GroupItem {group} {users} {setGroups} />
					</div>
				{/each}
			</div>
		{/if}

		<hr style="--mb:0.5rem; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)" />

		{#if $user?.role === 'admin'}
			<GroupModal
				bind:show={showDefaultPermissionsModal}
				tabs={['permissions']}
				bind:permissions={defaultPermissions}
				custom={false}
				onSubmit={updateDefaultPermissionsHandler}
			/>

			<button
				style="--d:flex; --ai:center; --jc:space-between; --radius:0.5rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --pt:0.25rem"
				on:click={() => {
					showDefaultPermissionsModal = true;
				}}
			>
				<div style="--d:flex; --ai:center; --g:0.625rem">
					<div style="--p:0.375rem; --bgc:rgb(0 0 0 / 0.05); --dark-bgc:rgb(255 255 255 / 0.1); --radius:9999px">
						<UsersSolid className="size-4" />
					</div>

					<div style="--ta:left">
						<div style="--size:0.875rem; --weight:500">{$i18n.t('Default permissions')}</div>

						<div style="--d:flex; --size:0.75rem; --mt:0.125rem">
							{$i18n.t('applies to all users with the "user" role')}
						</div>
					</div>
				</div>

				<div>
					<ChevronRight strokeWidth="2.5" />
				</div>
			</button>
		{/if}
	</div>
{/if}
