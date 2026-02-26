<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { showArchivedChats, showSidebar, user } from '$lib/stores';

	import { slide } from 'svelte/transition';
	import { page } from '$app/stores';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';

	const i18n = getContext('i18n');

	export let channel;
</script>

<nav style="--pos:sticky; --top:0; --z:30; --w:100%; --px:0.375rem; --py:0.375rem; --mb:-2rem; --d:flex; --ai:center"
	class="drag-region">
	<div
		style="--bgi:linear-gradient(180deg, var(--tw-gradient-stops)); --tw-gradient-from:#fff; --tw-gradient-via:#fff; --tw-gradient-to:transparent; --dark-tw-gradient-from:var(--color-gray-900); --dark-tw-gradient-via:var(--color-gray-900); --dark-tw-gradient-to:transparent; --pe:none; --pos:absolute; --inset:0; --bottom:-1.75rem; --z:-1"
	class="via-50%"
	></div>

	<div style="--d:flex; --maxw:100%; --w:100%; --mx:auto; --px:0.25rem; --pt:0.125rem; --grad:0deg; --grad-color: hsl(273, 99%, 100%);">
		<div style="--d:flex; --ai:center; --w:100%; --maxw:100%">
			<div
				style="--mr:0.25rem; 
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
					style="--cur:pointer; --px:0.5rem; --py:0.5rem; --d:flex; --radius:0.75rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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
				style="--fx:1 1 0%; --of:hidden; --maxw:100%; --py:0.125rem"
	class="{$showSidebar ? 'ml-1' : ''}"
			>
				{#if channel}
					<div style="--line-clamp:1; --tt:capitalize; --weight:500; --size:1.125rem"
	class="font-primary">
						{channel.name}
					</div>
				{/if}
			</div>

			<div style="--as:flex-start; --d:flex; --fx:none; --ai:center; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)">
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
							style="--us:none; --d:flex; --radius:0.75rem; --p:0.375rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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
