<script lang="ts">
	import { getContext } from 'svelte';

	import Badge from '$lib/components/common/Badge.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n: any = getContext('i18n');

	export let label: string = '';
	export let record: any = {};
	export let onProbe: ((url: string, capability: string) => Promise<void>) | null = null;
	export let capability: string = '';
	export let url: string = '';

	let probing = false;
	let detailsOpen = false;

	const statusToBadgeType: Record<string, string> = {
		ok: 'success',
		degraded: 'warning',
		unreachable: 'error',
		unknown: 'muted'
	};

	const statusToLabelKey: Record<string, string> = {
		ok: 'OK',
		degraded: 'Degraded',
		unreachable: 'Unreachable',
		unknown: 'Unknown'
	};

	$: badgeType = statusToBadgeType[record?.status] ?? 'muted';
	$: badgeLabel = $i18n.t(statusToLabelKey[record?.status] ?? 'Unknown');
	$: summaryText = record?.summary_key
		? $i18n.t(record.summary_key, record?.summary_params ?? {})
		: '';

	const handleProbe = async () => {
		if (!onProbe || !url || !capability) return;
		probing = true;
		try {
			await onProbe(url, capability);
		} finally {
			probing = false;
		}
	};
</script>

<div class="py-2 border-b border-gray-100 dark:border-gray-800 last:border-b-0">
	<div class="flex items-start gap-3 flex-wrap">
		<div class="flex-none pt-1">
			<Badge
				type={badgeType}
				content={badgeLabel}
				ariaLabel={$i18n.t('Status: {{STATUS}}', { STATUS: badgeLabel })}
			/>
		</div>

		<div class="flex-1 min-w-0">
			<div class="font-semibold text-sm text-gray-900 dark:text-gray-100 break-all">
				{label}
			</div>
			<div class="text-sm text-gray-700 dark:text-gray-300">
				{summaryText}
			</div>
		</div>

		<div class="flex items-center gap-2 flex-none">
			{#if onProbe && url && capability}
				<button
					type="button"
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 flex items-center gap-1"
					on:click={handleProbe}
					disabled={probing}
					aria-label={$i18n.t('Re-probe')}
					title={$i18n.t('Re-probe')}
				>
					{#if probing}
						<Spinner className="size-3" />
					{:else}
						<Icon name="refresh-fill-20-ca63" className="size-3" />
					{/if}
					<span>{$i18n.t('Re-probe')}</span>
				</button>
			{/if}

			{#if record?.issue_type}
				<button
					type="button"
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 opacity-50 cursor-not-allowed"
					disabled
					aria-disabled="true"
					title={$i18n.t('Documentation coming in 2.3.4')}
				>
					{$i18n.t('Show me how to fix this')}
				</button>
			{/if}
		</div>
	</div>

	{#if record?.technical}
		<div class="mt-2">
			<Collapsible bind:open={detailsOpen} chevron={true} title={$i18n.t('Technical detail')}>
				<div slot="content">
					<pre
						aria-label={$i18n.t('Technical details for {{LABEL}}: JSON diagnostic data', {
							LABEL: label
						})}
						class="text-xs bg-gray-50 dark:bg-gray-800 rounded p-2 overflow-x-auto text-gray-700 dark:text-gray-300">{JSON.stringify(
							record.technical,
							null,
							2
						)}</pre>
				</div>
			</Collapsible>
		</div>
	{/if}
</div>
