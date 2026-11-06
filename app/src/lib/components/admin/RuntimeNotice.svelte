<script lang="ts">
	// An admin on Docker Desktop or OrbStack learns how to move to Colima, the
	// runtime Sage supports (decided 2026-10-21). `ai-ui` passes SAGE_RUNTIME into
	// the container and /api/config hands it to admins only (card "Admin notice
	// when Sage runs on Docker Desktop or OrbStack"). Dismissing hides it for that
	// runtime in this browser; a move to another runtime brings it back.
	import { getContext } from 'svelte';
	import { config } from '$lib/stores';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');
	const NAMES: Record<string, string> = {
		'docker-desktop': 'Docker Desktop',
		orbstack: 'OrbStack'
	};
	const KEY = 'sage.runtimeNotice.dismissed';

	const read = (): string | null => {
		try {
			return localStorage.getItem(KEY);
		} catch {
			return null; // storage blocked: the notice shows
		}
	};

	let dismissed = read();
	$: runtime = $config?.sage_runtime ?? '';
	$: show = runtime in NAMES && dismissed !== runtime;

	const dismiss = () => {
		try {
			localStorage.setItem(KEY, runtime);
		} catch {
			// Storage blocked: hidden until the next load.
		}
		dismissed = runtime;
	};
</script>

{#if show}
	<div
		role="status"
		data-cy="runtime-notice"
		style="--d:flex; --g:0.6rem; --ai:flex-start; --jc:space-between; --my:0.5rem; --px:0.8rem; --py:0.6rem; --radius:0.6rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --size:0.875rem"
	>
		<p style="--m:0">
			{$i18n.t(
				'Sage is running on {{runtime}}. Run `ai-ui migrate` in Terminal to move it to Colima; your data comes along.',
				{ runtime: NAMES[runtime] }
			)}
		</p>
		<button
			type="button"
			data-cy="runtime-notice-dismiss"
			aria-label={$i18n.t('Dismiss')}
			style="--fx:none; --cur:pointer; --p:0.2rem"
			on:click={dismiss}
		>
			<Icon name="x-mark" className="size-3" strokeWidth="2" />
		</button>
	</div>
{/if}
