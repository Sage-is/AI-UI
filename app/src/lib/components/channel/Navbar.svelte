<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { DropdownMenu } from 'bits-ui';
	import { goto } from '$app/navigation';

	import { showArchivedChats, showSidebar, user } from '$lib/stores';
	import { deleteSpaceById } from '$lib/apis/spaces';
	import { flyAndScale } from '$lib/utils/transitions';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import SpaceAgentsModal from './SpaceAgentsModal.svelte';
	import SpaceMembersModal from './SpaceMembersModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	export let space;
	export let onRefresh: () => void = () => {};

	let showMenu = false;
	let showAgentsModal = false;
	let showMembersModal = false;
	let showDeleteConfirm = false;

	$: spaceAgents = space?.data?.agents ?? [];
</script>

<SpaceAgentsModal bind:show={showAgentsModal} {space} onSave={onRefresh} />
<SpaceMembersModal bind:show={showMembersModal} {space} onSave={onRefresh} />

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Space')}
	message={$i18n.t('Are you sure you want to delete this space? This action cannot be undone.')}
	onConfirm={async () => {
		if (space) {
			await deleteSpaceById(localStorage.token, space.id).catch((e) => {
				toast.error(`${e}`);
			});
			goto('/');
		}
	}}
/>

<nav style="--pos:sticky; --top:0; --z:30; --w:100%; --px:0.4rem; --py:0.4rem; --mb:-2rem; --d:flex; --ai:center"
	class="drag-region">
	<div
		style="--bgi:linear-gradient(180deg, var(--tw-gradient-stops)); --tw-gradient-from:#fff; --tw-gradient-via:#fff; --tw-gradient-to:transparent; --dark-tw-gradient-from:var(--color-gray-900); --dark-tw-gradient-via:var(--color-gray-900); --dark-tw-gradient-to:transparent; --pe:none; --pos:absolute; --inset:0; --bottom:-1.75rem; --z:-1"
	class="via-50%"
	></div>

	<div style="--d:flex; --maxw:100%; --w:100%; --mx:auto; --px:0.2rem; --pt:0.125rem; --grad:0deg; --grad-color: hsl(273, 99%, 100%);">
		<div style="--d:flex; --ai:center; --w:100%; --maxw:100%">
			<div
				style="--mr:0.2rem;
					--as:flex-start;
					--d:flex;
					--fx:none;
					--ai:center;
					--c:var(--color-gray-600);
					--dark-c:var(--color-gray-400);
					{$showSidebar
					? '--d:none;'
					: ''}
					"
	class=""
			>
				<button
					id="sidebar-toggle-button"
					style="--cur:pointer; --px:0.5rem; --py:0.5rem; --d:flex; --radius:0.6rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<div style="--m:auto; --as:center">
						<Icon name="menu-lines" />
					</div>
				</button>
			</div>

			<div
				style="--fx:1 1 0%; --of:hidden; --maxw:100%; --py:0.125rem; --d:flex; --ai:center; --g:0.5rem"
	class="{$showSidebar ? 'ml-1' : ''}"
			>
				{#if space}
					<div style="--line-clamp:1; --tt:capitalize; --weight:500; --size:1.125rem"
	class="font-primary">
						{space.name}
					</div>

					{#if spaceAgents.length > 0}
						<div style="--d:flex; --ai:center; --g:-0.25rem">
							{#each spaceAgents as agent}
								<Tooltip content={agent.name}>
									<button
										style="--d:flex; --ai:center"
										on:click={() => (showAgentsModal = true)}
									>
										<img
											src={agent.profile_image_url || '/static/icons/favicon.png'}
											alt={agent.name}
											style="--w:1.25rem; --h:1.25rem; --radius:9999px; --objf:cover;  --bw:2px; --bc:#fff; --dark-bc:var(--color-gray-900)"
										/>
									</button>
								</Tooltip>
							{/each}
						</div>
					{/if}
				{/if}
			</div>

			<div style="--as:flex-start; --d:flex; --fx:none; --ai:center; --g:0.125rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)">
				{#if space && ($user?.role === 'admin' || $user?.role === 'facilitator')}
					<DropdownMenu.Root bind:open={showMenu} closeFocus={false} typeahead={false}>
						<DropdownMenu.Trigger>
							<button
								style="--d:flex; --radius:0.6rem; --p:0.4rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								aria-label="Space Menu"
							>
								<Icon name="ellipsis-vertical" className="size-4" />
							</button>
						</DropdownMenu.Trigger>

						<DropdownMenu.Content
							style="--w:12rem; --radius:0.5rem; --px:0.25rem; --py:0.25rem;  --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --shadow:5"
							sideOffset={8}
							side="bottom"
							align="end"
							transition={flyAndScale}
						>
							<DropdownMenu.Item
								style="--d:flex; --ai:center; --g:0.5rem; --px:0.75rem; --py:0.5rem; --size:0.85rem; --weight:500; --radius:0.375rem; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800)"
								on:click={() => {
									showMenu = false;
									showAgentsModal = true;
								}}
							>
								<Icon name="users-fill-20" className="size-4" />
								{$i18n.t('Manage Agents')}
							</DropdownMenu.Item>

							<!-- Manage Members — add/remove users from this space (admin/facilitator) -->
							<DropdownMenu.Item
								style="--d:flex; --ai:center; --g:0.5rem; --px:0.75rem; --py:0.5rem; --size:0.85rem; --weight:500; --radius:0.375rem; --cur:pointer; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800)"
								on:click={() => {
									showMenu = false;
									showMembersModal = true;
								}}
							>
								<Icon name="user-group-fill-20" className="size-4" />
								{$i18n.t('Manage Members')}
							</DropdownMenu.Item>

							{#if $user?.role === 'admin'}
								<DropdownMenu.Separator style="--my:0.25rem; --h:1px; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)" />
								<DropdownMenu.Item
									style="--d:flex; --ai:center; --g:0.5rem; --px:0.75rem; --py:0.5rem; --size:0.85rem; --weight:500; --radius:0.375rem; --cur:pointer; --c:var(--color-red-500); --hvr-bgc:var(--color-red-50); --hvr-dark-bgc:var(--color-red-900)"
									on:click={() => {
										showMenu = false;
										showDeleteConfirm = true;
									}}
								>
									<Icon name="bell-fill-20" className="size-4" />
									{$i18n.t('Delete Space')}
								</DropdownMenu.Item>
							{/if}
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}

				{#if $user !== undefined}
					<UserMenu
						className="max-w-[240px]"
						role={$user?.role}
						help={true}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<button
							style="--us:none; --d:flex; --radius:0.6rem; --p:0.4rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							aria-label="User Menu"
						>
							<div style="--as:center">
								<img
									src={$user?.profile_image_url}
									style="--w:1.5rem; --h:1.5rem; --objf:cover; --radius:9999px"
									alt="User profile"
									draggable="false"
								/>
							</div>
						</button>
					</UserMenu>
				{/if}
			</div>
		</div>
	</div>
</nav>
