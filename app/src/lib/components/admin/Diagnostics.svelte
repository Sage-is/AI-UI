<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import dayjs from '$lib/dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { user } from '$lib/stores';
	import { getDiagnosticsHealth, probeEndpoint } from '$lib/apis/diagnostics';

	import Badge from '$lib/components/common/Badge.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import DiagnosticRow from '$lib/components/admin/Diagnostics/DiagnosticRow.svelte';
	import HowToFixModal from '$lib/components/admin/Diagnostics/HowToFixModal.svelte';
	import CommandLibrary from '$lib/components/admin/Diagnostics/CommandLibrary.svelte';
	import type { DeploymentShape } from '$lib/components/admin/Diagnostics/fixRegistry';

	const i18n: any = getContext('i18n');

	let health: any = null;
	let lastRefreshed: number = 0;
	let loaded = false;
	let refreshing = false;
	let tickKey = 0;
	let tickInterval: ReturnType<typeof setInterval> | null = null;

	// HowToFixModal state
	let fixModalShow = false;
	let fixModalIssueType: string | null = null;

	$: deploymentShape = (health?.deployment_shape?.shape ?? 'unknown') as DeploymentShape;
	$: deploymentConfidence = (health?.deployment_shape?.confidence ?? 'unknown') as
		| 'high'
		| 'low'
		| 'unknown';

	const openFixModal = (issueType: string) => {
		fixModalIssueType = issueType;
		fixModalShow = true;
	};

	// tickKey is referenced so this re-evaluates when the ticker fires.
	$: lastRefreshedLabel =
		tickKey >= 0 && lastRefreshed ? dayjs(lastRefreshed * 1000).fromNow() : '';

	const statusRank: Record<string, number> = {
		unreachable: 0,
		degraded: 1,
		unknown: 2,
		ok: 3
	};

	const statusToBadgeType: Record<string, string> = {
		ok: 'success',
		degraded: 'warning',
		unreachable: 'error',
		unknown: 'muted'
	};

	const loadHealth = async () => {
		loaded = false;
		try {
			health = await getDiagnosticsHealth(localStorage.token);
			lastRefreshed = Math.floor(Date.now() / 1000);
		} catch (e) {
			console.error('[Diagnostics] load failed', e);
			toast.error($i18n.t('Failed to load diagnostics.'));
		} finally {
			loaded = true;
		}
	};

	const reprobeAll = async () => {
		refreshing = true;
		try {
			await loadHealth();
		} finally {
			refreshing = false;
		}
	};

	const probeOne = async (probeUrl: string, capability: string) => {
		const tid = toast.loading($i18n.t('Probing...'));
		try {
			await probeEndpoint(localStorage.token, probeUrl, capability);
			toast.dismiss(tid);
			toast.success($i18n.t('Probe succeeded'));
		} catch (e) {
			console.error('[Diagnostics] probe failed', e);
			toast.dismiss(tid);
			toast.error($i18n.t('Probe failed'));
		}
		await loadHealth();
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}
		await loadHealth();
		tickInterval = setInterval(() => {
			tickKey += 1;
		}, 30000);
	});

	onDestroy(() => {
		if (tickInterval) {
			clearInterval(tickInterval);
			tickInterval = null;
		}
	});

	// --- Section data derivers ---
	$: endpointsObj = health?.endpoints ?? {};
	$: endpointEntries = Object.entries(endpointsObj) as [string, any][];
	$: activeEndpoints = endpointEntries.filter(([, row]) => row?.in_config !== false);
	$: ghostEndpoints = endpointEntries.filter(([, row]) => row?.in_config === false);

	$: bootProbes = health?.boot_probes ?? null;
	$: bootInFlight = (bootProbes?.in_flight ?? 0) > 0;

	// Aggregate "Issues" — every row across every section whose status is not ok.
	$: issues = collectIssues(health);

	function collectIssues(h: any): Array<{ label: string; row: any; section: string }> {
		if (!h) return [];
		const out: Array<{ label: string; row: any; section: string }> = [];

		// Endpoints
		const eps = h.endpoints ?? {};
		for (const [url, row] of Object.entries(eps) as [string, any][]) {
			if (row?.status && row.status !== 'ok') {
				out.push({ label: url, row, section: 'endpoints' });
			}
		}

		// Boot status
		const boot = h.boot_status ?? {};
		for (const [key, row] of Object.entries(boot) as [string, any][]) {
			if (row?.status && row.status !== 'ok') {
				out.push({ label: key, row, section: 'boot_status' });
			}
		}

		// Static assets
		const assets = h.static_assets ?? {};
		for (const [path, row] of Object.entries(assets) as [string, any][]) {
			if (row?.status && row.status !== 'ok') {
				out.push({ label: path, row, section: 'static_assets' });
			}
		}

		// Browser headers
		const headers = h.browser_headers ?? {};
		for (const [key, entry] of Object.entries(headers) as [string, any][]) {
			const row = entry?.configured ?? entry;
			if (row?.status && row.status !== 'ok') {
				out.push({ label: key, row, section: 'browser_headers' });
			}
		}

		// Worst-first sort (unreachable < degraded < unknown < ok)
		out.sort((a, b) => {
			const ra = statusRank[a.row.status] ?? 99;
			const rb = statusRank[b.row.status] ?? 99;
			return ra - rb;
		});
		return out;
	}
</script>

<div class="w-full">
	<!-- Header -->
	<div class="flex items-center justify-between mb-4 gap-3 flex-wrap">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">
			{$i18n.t('Diagnostics')}
		</h1>

		<div class="flex items-center gap-3">
			{#if lastRefreshedLabel}
				<span class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Last refreshed {{TIME}}', { TIME: lastRefreshedLabel })}
				</span>
			{/if}
			<button
				type="button"
				class="text-sm px-3 py-1.5 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 flex items-center gap-2"
				on:click={reprobeAll}
				disabled={refreshing || !loaded}
				aria-label={$i18n.t('Re-probe all endpoints')}
				title={$i18n.t('Re-probe all endpoints')}
			>
				{#if refreshing}
					<Spinner className="size-4" />
				{:else}
					<Icon name="refresh-fill-20-ca63" className="size-4" />
				{/if}
				<span>{$i18n.t('Re-probe all')}</span>
			</button>
		</div>
	</div>

	{#if !loaded && !health}
		<div class="py-8 text-center text-gray-500 dark:text-gray-400">
			{$i18n.t('Loading diagnostics...')}
		</div>
	{:else if loaded && !health}
		<div
			role="alert"
			class="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950 p-4 mb-4"
		>
			<div class="font-semibold text-red-900 dark:text-red-200 mb-2">
				{$i18n.t('Failed to load diagnostics.')}
			</div>
			<div class="text-sm text-red-800 dark:text-red-300 mb-3">
				{$i18n.t(
					'The diagnostics endpoint did not respond. Check your network connection or server logs and try again.'
				)}
			</div>
			<button
				type="button"
				class="text-sm px-3 py-1.5 rounded border border-red-300 dark:border-red-700 hover:bg-red-100 dark:hover:bg-red-900 disabled:opacity-50 flex items-center gap-2"
				on:click={loadHealth}
				disabled={refreshing}
				aria-label={$i18n.t('Retry loading diagnostics')}
			>
				{#if refreshing}
					<Spinner className="size-4" />
				{:else}
					<Icon name="refresh-fill-20-ca63" className="size-4" />
				{/if}
				<span>{$i18n.t('Retry')}</span>
			</button>
		</div>
	{:else if health}
		<!-- Boot-probe banner -->
		{#if bootInFlight}
			<div
				class="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950 p-4 mb-4"
			>
				<div class="font-semibold text-blue-900 dark:text-blue-200">
					{$i18n.t('Boot probes still running')}
				</div>
				<div class="text-sm text-blue-800 dark:text-blue-300">
					{$i18n.t('{{COMPLETED}} of {{TOTAL}} complete', {
						COMPLETED: bootProbes?.completed ?? 0,
						TOTAL: bootProbes?.total ?? 0
					})}
				</div>
			</div>
		{/if}

		<!-- Issues banner -->
		{#if issues.length > 0 && !bootInFlight}
			<div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-4">
				<h2 id="diagnostics-issues-heading" class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
					{$i18n.t('Issues')}
				</h2>
				<ul
					role="list"
					aria-labelledby="diagnostics-issues-heading"
					class="flex flex-col gap-2 list-none p-0 m-0"
				>
					{#each issues as issue}
						{@const issueBadgeLabel = $i18n.t(
							issue.row.status === 'unreachable'
								? 'Unreachable'
								: issue.row.status === 'degraded'
									? 'Degraded'
									: issue.row.status === 'unknown'
										? 'Unknown'
										: 'OK'
						)}
						<li
							class="flex items-start gap-3 p-2 rounded bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800"
						>
							<div class="flex-none pt-1">
								<Badge
									type={statusToBadgeType[issue.row.status] ?? 'muted'}
									content={issueBadgeLabel}
									ariaLabel={$i18n.t('Status: {{STATUS}}', { STATUS: issueBadgeLabel })}
								/>
							</div>
							<div class="flex-1 min-w-0">
								<div
									class="text-sm font-semibold text-gray-900 dark:text-gray-100 break-all"
								>
									{issue.label}
								</div>
								<div class="text-sm text-gray-700 dark:text-gray-300">
									{issue.row.summary_key
										? $i18n.t(issue.row.summary_key, issue.row.summary_params ?? {})
										: ''}
								</div>
							</div>
							{#if issue.row.issue_type}
								<button
									type="button"
									class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 flex-none"
									on:click={() => openFixModal(issue.row.issue_type)}
									aria-label={$i18n.t('Show me how to fix this')}
									title={$i18n.t('Show me how to fix this')}
								>
									{$i18n.t('Show me how to fix this')}
								</button>
							{/if}
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Endpoints -->
		<div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-4">
			<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
				{$i18n.t('Endpoints')}
			</h2>
			{#if activeEndpoints.length === 0 && ghostEndpoints.length === 0}
				<div class="text-sm text-gray-500 dark:text-gray-400">—</div>
			{:else}
				{#each activeEndpoints as [url, row]}
					<DiagnosticRow
						label={url}
						record={row}
						onProbe={probeOne}
						onFix={openFixModal}
						capability={row?.technical?.capability ?? ''}
						{url}
					/>
				{/each}

				{#if ghostEndpoints.length > 0}
					<div class="mt-3">
						<Collapsible chevron={true} title={$i18n.t('Previously configured')}>
							<div slot="content" class="pt-2">
								{#each ghostEndpoints as [url, row]}
									<DiagnosticRow label={url} record={row} onFix={openFixModal} />
								{/each}
							</div>
						</Collapsible>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Boot status -->
		<div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-4">
			<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
				{$i18n.t('Boot status')}
			</h2>
			{#each ['data_dir_writable', 'secret_key_persisted', 'alembic_head'] as key}
				{#if health?.boot_status?.[key]}
					<DiagnosticRow label={key} record={health.boot_status[key]} onFix={openFixModal} />
				{/if}
			{/each}
		</div>

		<!-- Static assets -->
		<div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-4">
			<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
				{$i18n.t('Static assets')}
			</h2>
			{#each ['/assets/loader.js', '/assets/custom.css', '/manifest.json', '/favicon.ico'] as path}
				{#if health?.static_assets?.[path]}
					<DiagnosticRow label={path} record={health.static_assets[path]} onFix={openFixModal} />
				{/if}
			{/each}
		</div>

		<!-- Browser headers -->
		<div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-4">
			<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">
				{$i18n.t('Browser headers')}
			</h2>
			{#each ['permissions_policy', 'content_security_policy'] as key}
				{#if health?.browser_headers?.[key]}
					<DiagnosticRow
						label={key}
						record={health.browser_headers[key]?.configured ?? health.browser_headers[key]}
						onFix={openFixModal}
					/>
				{/if}
			{/each}
		</div>

		<!-- Command library (Phase 3d) -->
		<CommandLibrary />
	{/if}
</div>

<!-- How-to-fix modal (Phase 3c) -->
<HowToFixModal
	bind:show={fixModalShow}
	issueType={fixModalIssueType}
	defaultShape={deploymentShape}
	shapeConfidence={deploymentConfidence}
/>
