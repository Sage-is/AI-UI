<script>
	import { showArchivedChats, showSidebar, user } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Notes from '$lib/components/notes/Notes.svelte';
</script>

<nav style="--px:0.5rem; --pt:0.25rem; backdrop-filter:blur(24px); --w:100%"
	class="drag-region">
	<div style="--d:flex; --ai:center">
		<div style="--d:flex; --fx:none; --ai:center; {$showSidebar ? '--d:none' : ''}"
	class="{$showSidebar ? 'md:hidden' : ''}">
			<button
				id="sidebar-toggle-button"
				style="--cur:pointer; --p:0.375rem; --d:flex; --radius:0.75rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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

		<div style="--ml:0.5rem; --py:0.125rem; --as:center; --d:flex; --ai:center; --jc:space-between; --w:100%">
			<div class="">
				<div
					style="--d:flex; --g:0.25rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.875rem; --weight:500; --bgc:transparent; --py:0.25rem; touch-action:auto; --pe:auto"
	class="scrollbar-none"
				>
					<a style="--minw:fit-content; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)" href="/notes">
						{$i18n.t('Notes')}
					</a>
				</div>
			</div>

			<div style="--as:center; --d:flex; --ai:center; --g:0.25rem">
				{#if $user !== undefined && $user !== null}
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

<div style="--pb:0.25rem; --fx:1 1 0%; --maxh:100%; --ofy:auto"
	class="@container">
	<Notes />
</div>
