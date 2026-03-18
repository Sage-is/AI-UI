<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		user,
		mobile,
		models,
		prompts,
		knowledge,
		tools
	} from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import MenuLines from '$lib/components/icons/MenuLines.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			if ($page.url.pathname.includes('/models') && !$user?.permissions?.workshop?.models) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/knowledge') &&
				!$user?.permissions?.workshop?.knowledge
			) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/prompts') &&
				!$user?.permissions?.workshop?.prompts
			) {
				goto('/');
			} else if ($page.url.pathname.includes('/tools') && !$user?.permissions?.workshop?.tools) {
				goto('/');
			}
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workshop')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		style="--pos:relative; --d:flex; --fd:column; --w:100%; --h:100vh; --maxh:100dvh; --tdn:200ms; --ttf:cubic-bezier(0.4, 0, 0.2, 1); --maxw:100%; --transition:max-width var(--tdn) var(--ttf); {$showSidebar
			? '--maxw:calc(100% - 280px)'
			: ''}"
	>
		<nav style="--px:0.625rem; --pt:0.25rem; backdrop-filter:blur(24px)" class="drag-region">
			<div style="--d:flex; --ai:center; --g:0.25rem">
				<div
					style="--as:center; --d:flex; --fx:none; --ai:center; {$showSidebar ? '--d:none' : ''}"
					class={$showSidebar ? 'md:hidden' : ''}
				>
					<button
						id="sidebar-toggle-button"
						style="--cur:pointer; --p:0.375rem; --d:flex; --radius:0.6rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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

				<div class="">
					<div
						style="--d:flex; --g:0.25rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.875rem; --weight:500; --radius:9999px; --bgc:transparent; --py:0.25rem; touch-action:auto; --pe:auto"
						class="scrollbar-none"
					>
						{#if $user?.role === 'admin' || $user?.permissions?.workshop?.models}
							<a
								style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								class={$page.url.pathname.includes('/workshop/models')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
								href="/workshop/models">{$i18n.t('Agents')}</a
							>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workshop?.knowledge}
							<a
								style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								class={$page.url.pathname.includes('/workshop/knowledge')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
								href="/workshop/knowledge"
							>
								{$i18n.t('Knowledge')}
							</a>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workshop?.prompts}
							<a
								style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								class={$page.url.pathname.includes('/workshop/prompts')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
								href="/workshop/prompts">{$i18n.t('Prompts')}</a
							>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workshop?.tools}
							<a
								style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								class={$page.url.pathname.includes('/workshop/tools')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
								href="/workshop/tools"
							>
								{$i18n.t('Tools')}
							</a>
						{/if}
					</div>
				</div>

				<!-- <div style="--d:flex; --ai:center; --size:1.25rem; --weight:600">{$i18n.t('Workshop')}</div> -->
			</div>
		</nav>

		<div
			style="--pb:0.25rem; --px:18px; --fx:1 1 0%; --maxh:100%; --ofy:auto"
			id="workshop-container"
		>
			<slot />
		</div>
	</div>
{/if}
