<!--
  TrySageBanner.svelte — top-of-app workshop banner for try.sage trials.

  Renders only when `$config?.features?.enable_try_sage` is true. Anonymous
  and authenticated users both see it. Mounted from `routes/(app)/+layout.svelte`
  so it sits above the app shell on every gated route.

  Layout has two parts:

    1. Always-visible row (projection-safe). Shows the trial countdown and,
       when the current user is admin, "Extend reset" + "Reset now" CTAs.
       The countdown ticks every second — yes that's a 1Hz timer, but the
       UX feedback during a live workshop is worth it. We clean up onDestroy.

    2. Collapsible <details> labeled "Persona links" (closed by default).
       Holding the persona magic links behind a closed <details> means the
       facilitator has to consciously expand the block before any login URL
       hits the projector. That keeps the JWTs off-screen until intended.

  Admin actions are intentionally co-located with the countdown rather
  than buried in the user menu (the parallel B-persona-switcher agent
  owns user-menu real estate). Admin extending or resetting the trial
  affects the countdown immediately above the buttons — placement matches
  cause and effect.

  Sign-in clicks are *hard navigation* (`window.location.assign`), not
  SvelteKit `goto`. The auth-token swap via `/auth#magic_token=...` needs
  a clean page load to invalidate stores; client-side routing would leave
  stale state from the previous persona's session.
-->

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { config, user, tryPersonas } from '$lib/stores';
	import {
		extendReset,
		forceReset,
		getStatus,
		type Persona
	} from '$lib/apis/sage-runtime';
	import { getBackendConfig } from '$lib/apis';
	import { loadPersonas, invalidatePersonas } from '$lib/utils/sage-runtime';

	import Icon from '$lib/components/Icon.svelte';
	import QRCode from '$lib/components/common/QRCode.svelte';

	// ─────────────────────────────────────────────────────────────────
	// Countdown state
	// ─────────────────────────────────────────────────────────────────

	let now = Date.now();
	let tickTimer: ReturnType<typeof setInterval> | null = null;
	// Local override when the config store doesn't yet have reset_at
	// (e.g., anonymous user on /auth where the gated `try_sage` block
	// is filtered out). We fetch from /status in that case.
	let resetAtOverride: string | null = null;

	// Reactive: the source-of-truth ISO8601 reset deadline.
	$: resetAtIso = $config?.try_sage?.reset_at ?? resetAtOverride ?? null;
	$: resetAtMs = resetAtIso ? Date.parse(resetAtIso) : null;
	$: msRemaining = resetAtMs ? Math.max(0, resetAtMs - now) : null;
	$: hoursRemaining = msRemaining !== null ? msRemaining / 3_600_000 : null;
	$: countdownLabel = formatCountdown(msRemaining);

	function formatCountdown(ms: number | null): string {
		if (ms === null) return '--:--:--';
		const total = Math.floor(ms / 1000);
		const h = Math.floor(total / 3600);
		const m = Math.floor((total % 3600) / 60);
		const s = total % 60;
		const pad = (n: number) => n.toString().padStart(2, '0');
		return `${pad(h)}:${pad(m)}:${pad(s)}`;
	}

	// ─────────────────────────────────────────────────────────────────
	// Visibility
	// ─────────────────────────────────────────────────────────────────

	$: enabled = $config?.features?.enable_try_sage === true;
	$: isAdmin = $user?.role === 'admin';
	// Color shifts to warning amber when reset is < 1 hour away, so the
	// facilitator gets a passive "wrap up soon" cue without any pop-up.
	$: warning = hoursRemaining !== null && hoursRemaining < 1;

	// ─────────────────────────────────────────────────────────────────
	// Lifecycle
	// ─────────────────────────────────────────────────────────────────

	onMount(async () => {
		if (!enabled) return;

		// Tick once a second. 1Hz is overkill for a 24h deadline but the
		// "HH:MM:SS" UI feels dead without it during a live workshop.
		tickTimer = setInterval(() => {
			now = Date.now();
		}, 1000);

		// Anonymous fallback: if the gated try_sage.reset_at didn't ride
		// the /api/config payload (anonymous users get a redacted block),
		// pull it from the public /sage/runtime/status endpoint.
		if (!$config?.try_sage?.reset_at) {
			try {
				const status = await getStatus(localStorage.token ?? '');
				if (status?.reset_at) resetAtOverride = status.reset_at;
			} catch {
				// 404 → try mode is off backend-side. Leave countdown blank.
			}
		}

		// Hydrate personas for the collapsible block. Cheap on first mount;
		// invalidatePersonas() forces re-fetch after admin actions.
		if ($tryPersonas === null) {
			try {
				await loadPersonas(localStorage.token ?? '');
			} catch (err) {
				console.error('TrySageBanner: failed to load personas', err);
			}
		}
	});

	onDestroy(() => {
		if (tickTimer) clearInterval(tickTimer);
	});

	// ─────────────────────────────────────────────────────────────────
	// Admin actions
	// ─────────────────────────────────────────────────────────────────

	let busy = false;

	async function refreshAfterAdminAction() {
		// Re-pull /api/config so the new reset_at lands in the store.
		try {
			const cfg = await getBackendConfig();
			if (cfg) config.set(cfg);
		} catch (err) {
			console.error('TrySageBanner: failed to refresh config', err);
		}
		// Force the personas store to re-fetch on next access — the
		// reset rotates magic-link JWTs, so cached URLs would be stale.
		invalidatePersonas();
		await loadPersonas(localStorage.token ?? '');
	}

	async function onExtend() {
		if (busy) return;
		busy = true;
		try {
			const r = await extendReset(localStorage.token);
			toast.success(`Reset extended by ${r.extended_by_hours}h`);
			await refreshAfterAdminAction();
		} catch (err: any) {
			if (err?.status === 409) {
				toast.error('Already extended this window');
			} else {
				toast.error(err?.detail ?? err?.message ?? 'Extend failed');
			}
		} finally {
			busy = false;
		}
	}

	async function onReset() {
		if (busy) return;
		// Destructive: wipes persona chats. confirm() is the lightest
		// possible UI guard; the action lives behind admin role anyway.
		if (!confirm('Reset try.sage trial now? Persona chats and uploads will be wiped.')) {
			return;
		}
		busy = true;
		try {
			await forceReset(localStorage.token);
			toast.success('Trial reset complete');
			await refreshAfterAdminAction();
		} catch (err: any) {
			toast.error(err?.detail ?? err?.message ?? 'Reset failed');
		} finally {
			busy = false;
		}
	}

	// ─────────────────────────────────────────────────────────────────
	// Persona row helpers
	// ─────────────────────────────────────────────────────────────────

	async function onCopy(p: Persona) {
		try {
			await navigator.clipboard.writeText(p.login_url);
			toast.success('Link copied');
		} catch {
			toast.error('Clipboard unavailable');
		}
	}

	function onSignInAs(p: Persona) {
		// Hard navigation: the auth-token swap at /auth#magic_token=…
		// needs a fresh page load to clear stores from the previous session.
		window.location.assign(p.login_url);
	}
</script>

{#if enabled}
	<div
		class="w-full px-4 py-2 text-xs flex flex-col gap-1 {warning
			? 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200'
			: 'bg-blue-500/20 text-blue-700 dark:text-blue-200'}"
	>
		<!-- Always-visible projection-safe row -->
		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="font-medium">
				try.sage trial — resets in
				<span class="font-mono tabular-nums ml-1">{countdownLabel}</span>
			</div>

			{#if isAdmin}
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="px-2 py-1 rounded-md bg-white/40 hover:bg-white/60 dark:bg-black/20 dark:hover:bg-black/30 disabled:opacity-50 transition"
						on:click={onExtend}
						disabled={busy}
					>
						Extend reset
					</button>
					<button
						type="button"
						class="px-2 py-1 rounded-md bg-white/40 hover:bg-white/60 dark:bg-black/20 dark:hover:bg-black/30 disabled:opacity-50 transition"
						on:click={onReset}
						disabled={busy}
					>
						Reset now
					</button>
				</div>
			{/if}
		</div>

		<!--
			Collapsible persona links. Closed by default — see component
			header comment for the projection-safety reasoning.
		-->
		{#if $tryPersonas && $tryPersonas.length > 0}
			<details class="group mt-1">
				<summary class="cursor-pointer select-none text-xs opacity-80 hover:opacity-100">
					Persona links ({$tryPersonas.length})
				</summary>

				<div class="mt-2 grid grid-cols-1 gap-2">
					{#each $tryPersonas as persona (persona.key)}
						<div
							class="grid items-center gap-2 p-2 rounded-md bg-white/40 dark:bg-black/20"
							style="grid-template-columns: minmax(0,12rem) auto minmax(0,1fr) auto;"
						>
							<button
								type="button"
								class="px-2 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium truncate text-left"
								on:click={() => onSignInAs(persona)}
								title="Sign in as {persona.label}"
							>
								Sign in as {persona.label}
							</button>

							<button
								type="button"
								class="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10"
								on:click={() => onCopy(persona)}
								title="Copy login URL"
								aria-label="Copy login URL for {persona.label}"
							>
								<Icon name="clipboard-copy-16" className="size-4" />
							</button>

							<code
								class="text-[10px] font-mono truncate text-gray-700 dark:text-gray-300"
								title={persona.login_url}>{persona.login_url}</code
							>

							<QRCode value={persona.login_url} size={64} ecc="M" />
						</div>
					{/each}
				</div>
			</details>
		{/if}
	</div>
{/if}
