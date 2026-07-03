<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import { user } from '$lib/stores';
	import { getSprigCatalog, graftSprig, pruneSprig } from '$lib/apis/retrieval';

	import Badge from '$lib/components/common/Badge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: any = getContext('i18n');

	let loaded = false;
	let refreshing = false;
	let busyName: string | null = null;

	let catalog: Record<string, any> = {};
	let grafted: Record<string, any> = {};

	// Supervisor lifecycle state -> operator-facing label + badge colour.
	const stateLabel: Record<string, string> = {
		rooted: 'Grafted',
		wilted: 'Wilted',
		delivered: 'Delivered'
	};
	const stateBadge: Record<string, string> = {
		rooted: 'success',
		wilted: 'error',
		delivered: 'info'
	};

	const load = async () => {
		refreshing = true;
		try {
			const res = await getSprigCatalog(localStorage.token);
			catalog = res?.catalog ?? {};
			grafted = res?.grafted ?? {};
		} catch (e) {
			toast.error($i18n.t('Failed to load Sprig catalog'));
		}
		refreshing = false;
	};

	const graft = async (name: string, capability: string) => {
		busyName = name;
		try {
			const res = await graftSprig(localStorage.token, { name, capability });
			toast.success($i18n.t('Grafted {{name}}', { name }));
			if (res?.warning) toast.warning(res.warning);
		} catch (e) {
			toast.error($i18n.t('Failed to graft {{name}}', { name }));
		}
		busyName = null;
		await load();
	};

	const prune = async (name: string) => {
		busyName = name;
		try {
			const res = await pruneSprig(localStorage.token, { name });
			toast.success($i18n.t('Pruned {{name}}', { name }));
			if (res?.embedding_reset) {
				toast.info(
					$i18n.t('Embedding dispatch reset — graft a cultivar to restore document search.')
				);
			}
		} catch (e) {
			toast.error($i18n.t('Failed to prune {{name}}', { name }));
		}
		busyName = null;
		await load();
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}
		await load();
		loaded = true;
	});

	$: entries = Object.entries(catalog) as [string, any][];
	$: graftedCount = Object.values(grafted).filter((g: any) => g?.state === 'rooted').length;
</script>

<div class="flex flex-col gap-1 my-1.5">
	<div class="flex justify-between items-start gap-3">
		<div class="min-w-0">
			<h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Sprigs')}™</h1>
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t(
					'Capabilities grafted onto the Rootstock™ at runtime — no model download, no pip install.'
				)}
			</div>
		</div>
		<button
			data-cy="sprigs-refresh"
			class="text-xs px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center gap-1.5 flex-none"
			on:click={load}
			disabled={refreshing}
		>
			{#if refreshing}<Spinner className="size-3" />{/if}
			{$i18n.t('Refresh')}
		</button>
	</div>

	{#if loaded && entries.length > 0}
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('{{grafted}} of {{total}} grafted', { grafted: graftedCount, total: entries.length })}
		</div>
	{/if}
</div>

{#if !loaded}
	<div class="flex justify-center py-10"><Spinner /></div>
{:else if entries.length === 0}
	<div class="text-sm text-gray-500 dark:text-gray-400 py-6">
		{$i18n.t('No Sprigs in the catalog.')}
	</div>
{:else}
	<div class="flex flex-col gap-2 mt-1">
		{#each entries as [name, spec]}
			{@const g = grafted[name]}
			{@const isGrafted = g && (g.state === 'rooted' || g.state === 'delivered')}
			<div
				data-cy="sprig-card"
				data-sprig={name}
				class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 flex items-start gap-3"
			>
				<div class="flex-none pt-0.5" data-cy="sprig-state" data-state={g?.state ?? 'sprouted'}>
					<Badge
						type={g ? (stateBadge[g.state] ?? 'muted') : 'muted'}
						content={g ? $i18n.t(stateLabel[g.state] ?? 'Sprouted') : $i18n.t('Sprouted')}
					/>
				</div>

				<div class="flex-1 min-w-0">
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 break-all">
						{name}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{spec.capability}{spec.model ? ` · ${spec.model}` : ''}{spec.dim
							? ` · ${spec.dim}d`
							: ''}
					</div>
					{#if g}
						<div class="text-xs text-gray-400 dark:text-gray-500 mt-1 font-mono break-all">
							{g.base_url}{g.pid ? ` · pid ${g.pid}` : ''}
						</div>
					{/if}
				</div>

				<div class="flex-none flex items-center gap-2">
					{#if isGrafted}
						{#if g?.base_url}
							<a
								href="/admin/diagnostics"
								class="text-xs px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
								title={$i18n.t('View health in Diagnostics')}
							>
								{$i18n.t('Health')}
							</a>
						{/if}
						<button
							data-cy="sprig-prune"
							class="text-xs px-3 py-1.5 rounded-full border border-red-300 text-red-600 dark:border-red-800 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50 flex items-center gap-1.5"
							on:click={() => prune(name)}
							disabled={busyName === name}
							title={$i18n.t('Terminate and remove this Sprig™')}
						>
							{#if busyName === name}<Spinner className="size-3" />{/if}
							{$i18n.t('Prune')}
						</button>
					{:else}
						<button
							data-cy="sprig-graft"
							class="text-xs px-3.5 py-1.5 rounded-full bg-black text-white dark:bg-white dark:text-black hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5"
							on:click={() => graft(name, spec.capability)}
							disabled={busyName === name}
						>
							{#if busyName === name}<Spinner className="size-3" />{/if}
							{g && g.state === 'wilted' ? $i18n.t('Revive') : $i18n.t('Graft')}
						</button>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}
