<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { sharedByMeChats, sharedWithMeChats } from '$lib/stores';
	import { removeChatShareTarget, getChatsSharedByMe, getChatsSharedWithMe } from '$lib/apis/chat-shares';
		import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	export let chatId: string;
	export let targets: Array<{
		id: string;
		chat_id: string;
		target_type: string;
		target_id: string;
		target_name: string | null;
		share_mode: string;
		created_at: number;
	}> = [];

	async function removeTarget(shareId: string) {
		try {
			await removeChatShareTarget(localStorage.token, chatId, shareId);
			targets = targets.filter((t) => t.id !== shareId);
			toast.success($i18n.t('Share removed'));
			// Refresh sidebar stores
			try { sharedByMeChats.set(await getChatsSharedByMe(localStorage.token)); } catch {}
			try { sharedWithMeChats.set(await getChatsSharedWithMe(localStorage.token)); } catch {}
		} catch (err) {
			toast.error($i18n.t('Failed to remove share'));
		}
	}
</script>

{#if targets.length > 0}
	<div style="--d:flex; --fd:column; --g:0.2rem">
		<div style="--size:0.6875rem; --weight:600; --tt:uppercase; --ls:0.05em; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --px:0.2rem">
			{$i18n.t('Currently shared with')}
		</div>
		{#each targets as target (target.id)}
			<div
				style="--d:flex; --ai:center; --jc:space-between; --px:0.5rem; --py:0.4rem; --radius:0.4rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800)"
			>
				<div style="--d:flex; --ai:center; --g:0.5rem">
					<span style="--size:0.8125rem; --weight:500">
						{target.target_name ?? target.target_id}
					</span>
					<span
						style="--px:0.4rem; --py:0.0625rem; --radius:9999px; --size:0.625rem; --weight:500; --tt:uppercase; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700); --c:var(--color-gray-600); --dark-c:var(--color-gray-300)"
					>
						{target.target_type}
					</span>
					<span
						style="--px:0.4rem; --py:0.0625rem; --radius:9999px; --size:0.625rem; --weight:500; {target.share_mode === 'live' ? '--bgc:var(--color-green-100); --c:var(--color-green-700); --dark-bgc:var(--color-green-900); --dark-c:var(--color-green-300)' : '--bgc:var(--color-blue-100); --c:var(--color-blue-700); --dark-bgc:var(--color-blue-900); --dark-c:var(--color-blue-300)'}"
					>
						{target.share_mode}
					</span>
				</div>
				<Tooltip content={$i18n.t('Remove')}>
					<button
						style="--p:0.125rem; --radius:0.2rem; --c:var(--color-gray-400); --hvr-c:var(--color-red-500); --tn:color 150ms ease"
						type="button"
						on:click={() => removeTarget(target.id)}
					>
						<Icon name="x-mark" strokeWidth="2" className="size-3.5" />
					</button>
				</Tooltip>
			</div>
		{/each}
	</div>
{/if}
