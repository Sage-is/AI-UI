<script lang="ts">
	// The chrome the dashboard surfaces share: the sidebar toggle, the top menu,
	// and a scrolling body.
	//
	// EXTRACTED 2026-08-09, when Calendar became a real page. Until then the nav
	// lived inside `home/+layout.svelte` and there was only one of it. Copying it
	// into a second layout would have been two navs that must stay in step, and a
	// nav that drifts is one where the current page stops being highlighted on
	// half the routes and nobody notices for a month.
	//
	// The `LINKS` list is the whole nav. Adding a surface is one entry.
	import { getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar } from '$lib/stores';
	import { page } from '$app/stores';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	/** Browser tab title for the surface using this shell. */
	export let title = '';

	const LINK_S =
		'--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)';
	const IDLE = 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white';

	// `match` decides the highlight. Kept beside the href so the two cannot drift
	// — the bug that shape produces is a nav where nothing looks current.
	const LINKS = [
		{ href: '/home', label: 'Dashboard', match: (p: string) => ['/home', '/home/'].includes(p) },
		{ href: '/notes', label: 'Notes', match: (p: string) => p.includes('/notes') },
		{ href: '/calendar', label: 'Calendar', match: (p: string) => p.includes('/calendar') }
	];
</script>

<svelte:head>
	<title>
		{$i18n.t(title)} • {$WEBUI_NAME}
	</title>
</svelte:head>

<div
	style="--d:flex; --fd:column; --w:100%; --h:100vh; --maxh:100dvh; --tdn:200ms; --ttf:cubic-bezier(0.4, 0, 0.2, 1); --maxw:100%; --transition:max-width var(--tdn) var(--ttf); {$showSidebar
		? '--maxw:calc(100% - 280px)'
		: ''}"
>
	<nav style="--px:0.625rem; --pt:0.2rem; backdrop-filter:blur(24px); --w:100%" class="drag-region">
		<div style="--d:flex; --ai:center">
			<div
				style="--d:flex; --fx:none; --ai:center; --as:flex-end; {$showSidebar ? '--d:none' : ''}"
				class={$showSidebar ? 'md:hidden' : ''}
			>
				<button
					id="sidebar-toggle-button"
					style="--cur:pointer; --p:0.4rem; --d:flex; --radius:0.6rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<div style="--m:auto; --as:center">
						<Icon name="menu-lines" className="size-5" strokeWidth="2" />
					</div>
				</button>
			</div>

			<div style="--d:flex; --w:100%">
				<div
					style="--d:flex; --g:0.2rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.8rem; --weight:500; --radius:9999px; --bgc:transparent; --pt:0.2rem"
					class="scrollbar-none"
				>
					{#each LINKS as link}
						<a
							data-cy="dash-nav-{link.label.toLowerCase()}"
							style={LINK_S}
							class={link.match($page.url.pathname) ? '' : IDLE}
							href={link.href}>{$i18n.t(link.label)}</a
						>
					{/each}
				</div>
			</div>
		</div>
	</nav>

	<div style="--fx:1 1 0%; --maxh:100%; --ofy:auto">
		<slot />
	</div>
</div>
