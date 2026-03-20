<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { DropdownMenu } from 'bits-ui';
	import { goto } from '$app/navigation';

	import { showArchivedChats, showSidebar, user } from '$lib/stores';
	import { deleteChannelById } from '$lib/apis/spaces';
	import { flyAndScale } from '$lib/utils/transitions';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import ChannelAgentsModal from './ChannelAgentsModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let channel;
	export let onRefresh: () => void = () => {};

	let showMenu = false;
	let showAgentsModal = false;
	let showDeleteConfirm = false;

	$: channelAgents = channel?.data?.agents ?? [];
</script>

<ChannelAgentsModal bind:show={showAgentsModal} {channel} onSave={onRefresh} />

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Channel')}
	message={$i18n.t('Are you sure you want to delete this channel? This action cannot be undone.')}
	onConfirm={async () => {
		if (channel) {
			await deleteChannelById(localStorage.token, channel.id).catch((e) => {
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
						<MenuLines />
					</div>
				</button>
			</div>

			<div
				style="--fx:1 1 0%; --of:hidden; --maxw:100%; --py:0.125rem; --d:flex; --ai:center; --g:0.5rem"
	class="{$showSidebar ? 'ml-1' : ''}"
			>
				{#if channel}
					<div style="--line-clamp:1; --tt:capitalize; --weight:500; --size:1.125rem"
	class="font-primary">
						{channel.name}
					</div>

					{#if channelAgents.length > 0}
						<div style="--d:flex; --ai:center; --g:-0.25rem">
							{#each channelAgents as agent}
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
				{#if channel && ($user?.role === 'admin' || $user?.role === 'facilitator')}
					<DropdownMenu.Root bind:open={showMenu} closeFocus={false} typeahead={false}>
						<DropdownMenu.Trigger>
							<button
								style="--d:flex; --radius:0.6rem; --p:0.4rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								aria-label="Channel Menu"
							>
								<EllipsisVertical className="size-4" />
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
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" style="--w:1rem; --h:1rem">
									<path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />
								</svg>
								{$i18n.t('Manage Agents')}
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
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" style="--w:1rem; --h:1rem">
										<path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clip-rule="evenodd" />
									</svg>
									{$i18n.t('Delete Channel')}
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
