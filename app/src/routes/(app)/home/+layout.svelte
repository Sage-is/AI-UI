<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar } from '$lib/stores';
		import { page } from '$app/stores';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');
</script>

<svelte:head>
	<title>
		{$i18n.t('Home')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<div
	style="--d:flex; --fd:column; --w:100%; --h:100vh; --maxh:100dvh; --tdn:200ms; --ttf:cubic-bezier(0.4, 0, 0.2, 1); --maxw:100%; --transition:max-width var(--tdn) var(--ttf); {$showSidebar
		? '--maxw:calc(100% - 280px)'
		: ''}"
>
	<nav
		style="--px:0.625rem; --pt:0.2rem; backdrop-filter:blur(24px); --w:100%"
		class="drag-region"
	>
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
					<a
						style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						class={['/home', '/home/'].includes($page.url.pathname)
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
						href="/home">{$i18n.t('Dashboard')}</a
					>

					<a
						style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						class={$page.url.pathname.includes('/notes')
							? ''
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
						href="/notes">{$i18n.t('Notes')}</a
					>

					<a
						style="--minw:fit-content; --p:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						class="text-gray-300 dark:text-gray-600 cursor-default"
						href="/home"
						on:click|preventDefault
					>
						{$i18n.t('Calendar')}
						<span style="--size:0.625rem; --op:0.6; --ml:0.125rem">{$i18n.t('Soon')}</span>
					</a>
				</div>
			</div>
		</div>
	</nav>

	<div style="--fx:1 1 0%; --maxh:100%; --ofy:auto">
		<slot />
	</div>
</div>
