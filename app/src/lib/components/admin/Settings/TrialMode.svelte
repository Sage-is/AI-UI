<script lang="ts">
	/**
	 * TrialMode admin settings panel.
	 *
	 * Lives at /admin/settings/trial-mode and is gated by
	 * `features.enable_try_sage` upstream — see Settings.svelte.
	 *
	 * Provides three escape hatches the operator might need:
	 *   - Reopen setup wizard: the wizard is suppressed for try-mode
	 *     sessions (see needsWizard guard in ChangesAndSetupModal). This
	 *     button re-opens it imperatively for diagnostic use.
	 *   - Replay tutorial: clears the seen flag and bumps the
	 *     tutorialReopen store so <TrySageTutorial> reopens.
	 *   - Read-only diagnostics: reset deadline, seat count, allowed
	 *     models (from /limits), hidden-LLM status (from /llm-status).
	 */

	import { getContext, onMount } from 'svelte';
	import { config, showChangesAndSetup, tutorialReopen, setupTriggerReason } from '$lib/stores';
	import { getLimits, getLLMStatus } from '$lib/apis/sage-runtime';
	import type { RuntimeLimits, LLMStatus } from '$lib/apis/sage-runtime';

	const i18n = getContext<any>('i18n');

	let limits: RuntimeLimits | null = null;
	let llmStatus: LLMStatus | null = null;
	let limitsError: string | null = null;
	let llmError: string | null = null;

	function reopenWizard() {
		// Force the wizard's manualTrigger path so needsWizard returns
		// true even when there's nothing pending. The needsWizard guard
		// for try_sage.enabled is bypassed by the manualTrigger flag —
		// see ChangesAndSetupModal.svelte.
		setupTriggerReason.set({
			hasChangelog: false,
			needsModels: false,
			needsUsers: false,
			manualTrigger: true
		});
		showChangesAndSetup.set(true);
	}

	function replayTutorial() {
		try {
			localStorage.removeItem('try_sage_tutorial_seen_v1');
		} catch {
			// localStorage may be blocked; the bump below still works
			// because the modal opens unconditionally on counter change.
		}
		tutorialReopen.update((n) => n + 1);
	}

	function formatResetAt(iso: string | undefined): string {
		if (!iso) return $i18n?.t('Not set') ?? 'Not set';
		try {
			return new Date(iso).toLocaleString();
		} catch {
			return iso;
		}
	}

	onMount(async () => {
		const token = localStorage.token;
		try {
			limits = await getLimits(token);
		} catch (e: any) {
			limitsError = e?.message ?? String(e);
		}
		try {
			llmStatus = await getLLMStatus(token);
		} catch (e: any) {
			llmError = e?.message ?? String(e);
		}
	});
</script>

<div style="--d:flex; --fd:column; --g:1.2rem; --size:0.8rem; --p:0.5rem">
	<div>
		<div style="--size:1rem; --weight:600; --dark-c:#fff; --mb:0.3rem">
			{$i18n?.t('Trial Mode')}
		</div>
		<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
			{$i18n?.t(
				'Operator escape hatches for the try.sage trial environment. These are diagnostics — workshop attendees never see this panel.'
			)}
		</div>
	</div>

	<!-- Action buttons -->
	<div style="--d:flex; --fd:column; --g:0.6rem">
		<button
			type="button"
			on:click={reopenWizard}
			style="--d:flex; --fd:column; --ai:flex-start; --g:0.2rem; --p:0.8rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); cursor:pointer; --ta:left"
		>
			<div style="--size:0.85rem; --weight:500; --dark-c:#fff">
				{$i18n?.t('Reopen setup wizard')}
			</div>
			<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n?.t('The wizard is suppressed in trial mode. Use this to inspect it without leaving try mode.')}
			</div>
		</button>

		<button
			type="button"
			on:click={replayTutorial}
			style="--d:flex; --fd:column; --ai:flex-start; --g:0.2rem; --p:0.8rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); cursor:pointer; --ta:left"
		>
			<div style="--size:0.85rem; --weight:500; --dark-c:#fff">
				{$i18n?.t('Replay tutorial')}
			</div>
			<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n?.t('Clear the seen flag and reopen the tutorial overlay.')}
			</div>
		</button>
	</div>

	<!-- Read-only readouts -->
	<div style="--d:flex; --fd:column; --g:0.5rem; --p:0.8rem; --radius:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)">
		<div style="--size:0.8rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
			{$i18n?.t('Trial state')}
		</div>

		<div style="--d:flex; --jc:space-between; --g:1rem">
			<span style="--c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n?.t('Reset deadline')}
			</span>
			<span style="--dark-c:var(--color-gray-200); --weight:500">
				{formatResetAt($config?.try_sage?.reset_at)}
			</span>
		</div>

		<div style="--d:flex; --jc:space-between; --g:1rem">
			<span style="--c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n?.t('Seat count')}
			</span>
			<span style="--dark-c:var(--color-gray-200); --weight:500">
				{$config?.try_sage?.seat_count ?? '—'}
			</span>
		</div>

		<div style="--d:flex; --jc:space-between; --g:1rem">
			<span style="--c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n?.t('Reset interval (hours)')}
			</span>
			<span style="--dark-c:var(--color-gray-200); --weight:500">
				{$config?.try_sage?.reset_interval_hours ?? '—'}
			</span>
		</div>

		<div style="--d:flex; --jc:space-between; --g:1rem; --ai:flex-start">
			<span style="--c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n?.t('Allowed models')}
			</span>
			<span style="--dark-c:var(--color-gray-200); --weight:500; --ta:right; --maxw:24rem; --break:break-all">
				{#if limitsError}
					<span style="--c:var(--color-red-500)">{limitsError}</span>
				{:else if limits}
					{limits.allowed_models?.length ? limits.allowed_models.join(', ') : $i18n?.t('None configured')}
				{:else}
					&hellip;
				{/if}
			</span>
		</div>

		<div style="--d:flex; --jc:space-between; --g:1rem">
			<span style="--c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n?.t('Hidden LLM connection')}
			</span>
			<span style="--dark-c:var(--color-gray-200); --weight:500">
				{#if llmError}
					<span style="--c:var(--color-red-500)">{llmError}</span>
				{:else if llmStatus}
					{llmStatus.configured ? $i18n?.t('Configured') : $i18n?.t('Not configured')} · {llmStatus.model_count}
					{$i18n?.t('models')}
				{:else}
					&hellip;
				{/if}
			</span>
		</div>
	</div>
</div>
