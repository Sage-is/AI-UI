<script>
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { toast } from 'svelte-sonner';

	import { updateUserRole, getUsers, getManagedUsers, deleteUserById } from '$lib/apis/users';

	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import EditUserModal from '$lib/components/admin/Users/UserList/EditUserModal.svelte';
	import UserChatsModal from '$lib/components/admin/Users/UserList/UserChatsModal.svelte';
	import AddUserModal from '$lib/components/admin/Users/UserList/AddUserModal.svelte';

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import RoleUpdateConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Badge from '$lib/components/common/Badge.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import About from '$lib/components/chat/Settings/About.svelte';
	import Banner from '$lib/components/common/Banner.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	$: isAdmin = $user?.role === 'admin';

	let page = 1;

	let users = null;
	let total = null;

	let query = '';
	let orderBy = 'created_at'; // default sort key
	let direction = 'asc'; // default sort order

	let selectedUser = null;

	let showDeleteConfirmDialog = false;
	let showAddUserModal = false;

	let showUserChatsModal = false;
	let showEditUserModal = false;

	const deleteUserHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		// if the user is deleted and the current page has only one user, go back to the previous page
		if (users.length === 1 && page > 1) {
			page -= 1;
		}

		if (res) {
			getUserList();
		}
	};

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	const getUserList = async () => {
		try {
			const fetchFn = $user?.role === 'facilitator' ? getManagedUsers : getUsers;
			const res = await fetchFn(localStorage.token, query, orderBy, direction, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				users = res.users;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		}
	};

	$: if (page) {
		getUserList();
	}

	$: if (query !== null && orderBy && direction) {
		getUserList();
	}
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		deleteUserHandler(selectedUser.id);
	}}
/>

{#key selectedUser}
	<EditUserModal
		bind:show={showEditUserModal}
		{selectedUser}
		sessionUser={$user}
		on:save={async () => {
			getUserList();
		}}
	/>
{/key}

<AddUserModal
	bind:show={showAddUserModal}
	on:save={async () => {
		getUserList();
	}}
/>

{#if selectedUser}
	<UserChatsModal bind:show={showUserChatsModal} user={selectedUser} />
{/if}

{#if ($config?.license_metadata?.seats ?? null) !== null && total && total > $config?.license_metadata?.seats}
	<div style="--mt:0.2rem; --mb:0.5rem; --size:0.6rem; --c:#ef4444">
		<Banner
			className="mx-0"
			banner={{
				type: 'error',
				title: 'License Error',
				content:
					'Exceeded the number of seats in your license. Please contact support to increase the number of seats.',
				dismissable: true
			}}
		/>
	</div>
{/if}

{#if users === null || total === null}
	<div style="--my:2.5rem">
		<Spinner className="size-5" />
	</div>
{:else}
	<div style="--mt:0.125rem; --mb:0.5rem; --g:0.2rem; --d:flex; --fd:column; --fd-md:row; --jc:space-between">
		<div style="--d:flex; --as-md:center; --size:1.125rem; --weight:500; --px:0.125rem">
			<div class="flex-shrink-0">
				{$i18n.t('Users')}
			</div>
			<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />

			{#if ($config?.license_metadata?.seats ?? null) !== null}
				{#if total > $config?.license_metadata?.seats}
					<span style="--size:1.125rem; --weight:500; --c:#ef4444"
						>{total} of {$config?.license_metadata?.seats}
						<span style="--size:0.8rem; --weight:400">available users</span></span
					>
				{:else}
					<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)"
						>{total} of {$config?.license_metadata?.seats}
						<span style="--size:0.8rem; --weight:400">available users</span></span
					>
				{/if}
			{:else}
				<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)">{total}</span>
			{/if}
		</div>

		<div style="--d:flex; --g:0.2rem">
			<div style="--d:flex; --w:100%; --g:0.5rem">
				<div style="--d:flex; --fx:1 1 0%">
					<div style="--as:center; --ml:0.2rem; --mr:0.6rem">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<input
						style="--w:100%; --size:0.8rem; --pr:1rem; --py:0.2rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
						bind:value={query}
						placeholder={$i18n.t('Search')}
					/>
				</div>

				<div>
					<Tooltip content={$i18n.t('Add User')}>
						<button
							style="--p:0.5rem; --radius:0.6rem; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.8rem; --d:flex; --ai:center; --g:0.2rem"
							on:click={() => {
								showAddUserModal = !showAddUserModal;
							}}
						>
							<Plus className="size-3.5" />
						</button>
					</Tooltip>
				</div>
			</div>
		</div>
	</div>

	<div
		style="--pos:relative; --ws:nowrap; --ofx:auto; --maxw:100%; --radius:0.125rem; --pt:0.125rem"
	class="scrollbar-hidden"
	>
		<table
			style="--w:100%; --size:0.8rem; --ta:left; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); table-layout:auto; --maxw:100%; --radius:0.125rem"
		>
			<thead
				style="--size:0.6rem; --c:var(--color-gray-700); --tt:uppercase; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-400); --translatey:-0.125rem"
			>
				<tr class="">
					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('role')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center">
							{$i18n.t('Role')}

							{#if orderBy === 'role'}
								<span style="--weight:400"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('name')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center">
							{$i18n.t('Name')}

							{#if orderBy === 'name'}
								<span style="--weight:400"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('email')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center">
							{$i18n.t('Email')}

							{#if orderBy === 'email'}
								<span style="--weight:400"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('last_active_at')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center">
							{$i18n.t('Last Active')}

							{#if orderBy === 'last_active_at'}
								<span style="--weight:400"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('created_at')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center">
							{$i18n.t('Created at')}
							{#if orderBy === 'created_at'}
								<span style="--weight:400"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('oauth_sub')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center">
							{$i18n.t('OAuth ID')}

							{#if orderBy === 'oauth_sub'}
								<span style="--weight:400"
									>{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th scope="col" style="--px:0.6rem; --py:0.5rem; --ta:right" />
				</tr>
			</thead>
			<tbody>
				{#each users as user, userIdx}
					<tr style="--bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-bc:var(--color-gray-850); --size:0.6rem">
						<td style="--d:table;--px:0.6rem; --py:0.2rem; --minw:7rem; --w:7rem">
							<button
								style="--translatey:0.125rem"
								on:click={() => {
									selectedUser = user;
									showEditUserModal = !showEditUserModal;
								}}
							>
								<Badge
									type={user.role === 'admin' ? 'info' : user.role === 'facilitator' ? 'warning' : user.role === 'user' ? 'success' : user.role === 'temporary' ? 'muted' : 'muted'}
									content={$i18n.t(user.role)}
								/>
							</button>
						</td>
						<td style="--d:table;--px:0.6rem; --py:0.2rem; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --w:max-content">
							<div style="--d:flex; --fd:row; --w:max-content">
								<img
									style="--radius:9999px; --w:1.5rem; --h:1.5rem; --objf:cover; --mr:0.625rem"
									src={user?.profile_image_url?.startsWith(WEBUI_BASE_URL) ||
									user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
									user.profile_image_url.startsWith('data:')
										? user.profile_image_url
										: `${WEBUI_BASE_URL}/user.png`}
									alt="user"
								/>

								<div style="--weight:500; --as:center">{user.name}</div>
							</div>
						</td>
						<td style="--d:table;--px:0.6rem; --py:0.2rem"> {user.email} </td>

						<td style="--d:table;--px:0.6rem; --py:0.2rem">
							{dayjs(user.last_active_at * 1000).fromNow()}
						</td>

						<td style="--d:table;--px:0.6rem; --py:0.2rem">
							{dayjs(user.created_at * 1000).format('LL')}
						</td>

						<td style="--d:table;--px:0.6rem; --py:0.2rem">
							{#if user.role === 'temporary' && user.info?.temporary?.expires_at}
								<span style="{dayjs(user.info.temporary.expires_at * 1000).isBefore(dayjs()) ? '--c:#ef4444' : '--c:var(--color-gray-500)'}">
									{dayjs(user.info.temporary.expires_at * 1000).fromNow()}
								</span>
							{:else}
								{user.oauth_sub ?? ''}
							{/if}
						</td>

						<td style="--d:table;--px:0.6rem; --py:0.2rem; --ta:right">
							<div style="--d:flex; --jc:flex-end; --w:100%">
								{#if $config.features.enable_admin_chat_access && user.role !== 'admin'}
									<Tooltip content={$i18n.t('Chats')}>
										<button
											style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
											on:click={async () => {
												showUserChatsModal = !showUserChatsModal;
												selectedUser = user;
											}}
										>
											<ChatBubbles />
										</button>
									</Tooltip>
								{/if}

								<Tooltip content={$i18n.t('Edit User')}>
									<button
										style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
										on:click={async () => {
											showEditUserModal = !showEditUserModal;
											selectedUser = user;
										}}
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
												d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
											/>
										</svg>
									</button>
								</Tooltip>

								{#if isAdmin && user.role !== 'admin'}
									<Tooltip content={$i18n.t('Delete User')}>
										<button
											style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
											on:click={async () => {
												showDeleteConfirmDialog = true;
												selectedUser = user;
											}}
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
								{/if}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div style="--c:var(--color-gray-500); --size:0.6rem; --mt:0.4rem; --ta:right">
		ⓘ {$i18n.t("Click on the user role button to change a user's role.")}
	</div>

	<Pagination bind:page count={total} perPage={30} />
{/if}

{#if !$config?.license_metadata}
	{#if total > 50}
		<div style="--size:0.8rem">
			<Markdown
				content={`
> [!NOTE]
> # **Hey there! 👋**
>
> It looks like you have over 50 users — that usually falls under organizational usage.
> 
> Sage.is AI is proudly open source and completely free, with no hidden limits — and we'd love to keep it that way. 🌱  
>
> By supporting the project through sponsorship or an enterprise license, you’re not only helping us stay independent, you’re also helping us ship new features faster, improve stability, and grow the project for the long haul. With an *enterprise license*, you also get additional perks like dedicated support, customization options, and more — all at a fraction of what it would cost to build and maintain internally.  
> 
> Your support helps us stay independent and continue building great tools for everyone. 💛
> 
> - 👉 **[Click here to learn more about enterprise licensing](https://docs.sage.is/license)**
> - 👉 *[Click here to sponsor the project on GitHub](https://github.com/sponsors/Sage-is/)*
`}
			/>
		</div>
	{/if}
{/if}
