<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { mobile, showSidebar, chatId } from '$lib/stores';

	const i18n = getContext('i18n');

	export let items = [];
</script>

{#if items.length > 0}
	<div style="--d:flex; --fd:column">
		{#each items as item (item.chat_id)}
			<button
				style="--d:flex; --ai:center; --g:0.5rem; --w:100%; --px:0.625rem; --py:0.4rem; --radius:0.4rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --tn:background-color 150ms ease; --ta:left"
				on:click={() => {
					goto(`/c/${item.chat_id}`);
					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div style="--d:flex; --fd:column; --g:0.0625rem; --fx:1 1 0%; --miw:0">
					<div style="--size:0.8125rem; --line-clamp:1; --weight:400">{item.chat_title}</div>
					<div style="--d:flex; --ai:center; --g:0.4rem; --size:0.6875rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
						{#if item.share_type === 'link'}
							<span
								style="--px:0.2rem; --py:0; --radius:0.2rem; --size:0.5625rem; --weight:500; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700); --c:var(--color-gray-600); --dark-c:var(--color-gray-300)"
							>
								{$i18n.t('link')}
							</span>
						{:else if item.share_type === 'both'}
							<span>{item.share_count} {$i18n.t('recipients')}</span>
							<span
								style="--px:0.2rem; --py:0; --radius:0.2rem; --size:0.5625rem; --weight:500; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700); --c:var(--color-gray-600); --dark-c:var(--color-gray-300)"
							>
								+ {$i18n.t('link')}
							</span>
						{:else}
							<span>{item.share_count} {$i18n.t('recipients')}</span>
						{/if}
					</div>
				</div>
			</button>
		{/each}
	</div>
{/if}
