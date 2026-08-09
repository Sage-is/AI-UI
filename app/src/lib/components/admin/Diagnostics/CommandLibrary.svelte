<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { copyToClipboard } from '$lib/utils';

	import { commandLibrary } from './commandLibrary';

	const i18n: any = getContext('i18n');

	const openMap: Record<string, boolean> = {};
	commandLibrary.forEach((e) => (openMap[e.id] = false));

	const handleCopy = async (text: string) => {
		await copyToClipboard(text);
		toast.success($i18n.t('Copied to clipboard'));
	};
</script>

<div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-4" data-cy="diag-command-library">
	<h2 class="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
		{$i18n.t('Command library')}
	</h2>
	<p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
		{$i18n.t(
			'Recovery snippets. Copy and paste into your own terminal. The library never runs commands for you.'
		)}
	</p>

	<ul role="list" class="flex flex-col gap-2 list-none p-0 m-0">
		{#each commandLibrary as entry (entry.id)}
			<li>
				<Collapsible bind:open={openMap[entry.id]} chevron={true} title={$i18n.t(entry.title_key)}>
					<div slot="content" class="pt-2 pb-1 space-y-2">
						<div class="text-sm text-gray-700 dark:text-gray-300">
							{$i18n.t(entry.description_key)}
						</div>

						{#if entry.warning_key}
							<div
								role="alert"
								class="rounded border border-yellow-300 dark:border-yellow-700 bg-yellow-50 dark:bg-yellow-950 p-2 text-xs text-yellow-900 dark:text-yellow-200 flex items-start gap-2"
							>
								<Icon name="warning-fill-20-ca63" className="size-4 flex-none mt-0.5" />
								<span>{$i18n.t(entry.warning_key)}</span>
							</div>
						{/if}

						<div class="flex items-start gap-2">
							<pre
								class="text-xs bg-gray-100 dark:bg-gray-800 rounded p-2 overflow-x-auto flex-1 text-gray-800 dark:text-gray-200">{entry.command}</pre>
							<button
								type="button"
								class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 flex-none"
								on:click={() => handleCopy(entry.command)}
								aria-label={$i18n.t('Copy {{TITLE}} command', {
									TITLE: $i18n.t(entry.title_key)
								})}
								title={$i18n.t('Copy')}
							>
								{$i18n.t('Copy')}
							</button>
						</div>
					</div>
				</Collapsible>
			</li>
		{/each}
	</ul>
</div>
