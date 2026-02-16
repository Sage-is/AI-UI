<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, showSidebar, user } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Admin Panel')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		style="--d:flex; --fd:column; --w:100%; --h:100vh; --maxh:100dvh; --tdn:200ms; --ttf:cubic-bezier(0.4, 0, 0.2, 1); --maxw:100%"
	class="transition-width {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''}"
	>
		<nav style="--px:0.625rem; --pt:0.25rem; backdrop-filter:blur(24px)"
	class="drag-region">
			<div style="--d:flex; --ai:center; --g:0.25rem">
				<div style="--d:flex; --fx:none; --ai:center; --as:flex-end"
	class="{$showSidebar ? 'md:hidden' : ''}">
					<button
						id="sidebar-toggle-button"
						style="--cur:pointer; --p:0.375rem; --d:flex; --radius:0.75rem; --hvr-bgc:var(--color-gray-100, #ececec); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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

				<div style="--d:flex; --w:100%">
					<div
						style="--d:flex; --g:0.25rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.875rem; --weight:500; --radius:9999px; --bgc:transparent; --pt:0.25rem"
	class="scrollbar-none"
					>
						<a
							style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$page.url.pathname.includes('/admin/settings')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
							href="/admin/settings">{$i18n.t('Settings')}</a
						>
						<a
							style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$page.url.pathname.includes('/admin/users')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
							href="/admin">{$i18n.t('Users')}</a
						>

						<a
							style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$page.url.pathname.includes('/admin/evaluations')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
							href="/admin/evaluations">{$i18n.t('Evaluations')}</a
						>

						<a
							style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$page.url.pathname.includes('/admin/functions')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
							href="/admin/functions">{$i18n.t('Functions')}</a
						>
					</div>
				</div>
			</div>
		</nav>

		<div style="--pb:0.25rem; --px:16px; --fx:1 1 0%; --maxh:100%; --ofy:auto">
			<slot />
		</div>
	</div>
{/if}
