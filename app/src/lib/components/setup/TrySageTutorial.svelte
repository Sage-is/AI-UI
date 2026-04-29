<script lang="ts">
	/**
	 * TrySageTutorial — first-run tutorial modal for try.sage personas.
	 *
	 * Behavior:
	 *   - Reads steps from `$config.try_sage.tutorial_steps_json` (a JSON
	 *     string the backend ships through /api/config). Parsed defensively.
	 *   - When the JSON is unset, malformed, or empty, falls back to a
	 *     baked-in 6-step default. WHY placeholders not broken iframes:
	 *     the team picks videos out of the working playlist progressively.
	 *     Shipping fake YouTube IDs would render blank frames in production
	 *     until each video is shot. The placeholder card with the step
	 *     description keeps the tutorial useful before any video lands.
	 *   - Auto-opens once per browser when:
	 *       1. enable_try_sage feature flag is true,
	 *       2. localStorage.try_sage_tutorial_seen_v1 is unset,
	 *       3. the user is signed in (not anonymous on /auth).
	 *   - "Don't show again" sets the localStorage flag. Admin "Replay
	 *     tutorial" button (in TrialMode panel) clears the flag and bumps
	 *     the `tutorialReopen` store to force this modal back open.
	 */

	import { onMount, getContext } from 'svelte';
	import { config, user, tutorialReopen } from '$lib/stores';
	import type { TutorialStep } from '$lib/apis/sage-runtime';
	import Modal from '$lib/components/common/Modal.svelte';
	import VideoEmbed from '$lib/components/common/VideoEmbed.svelte';

	const i18n = getContext<any>('i18n');

	const STORAGE_KEY = 'try_sage_tutorial_seen_v1';

	// WHY baked-in default: the backend default in A1 is the source of
	// truth, but if the operator never sets TRY_SAGE_TUTORIAL_STEPS_JSON
	// the frontend still needs *something* to render. These titles match
	// the default sequence in the plan (welcome / model-switching /
	// chat-map / artifacts / bialik-sage / done).
	const DEFAULT_STEPS: TutorialStep[] = [
		{
			id: 'welcome',
			title: 'Welcome to try.sage.is AI',
			dismissible: true,
			description: 'A workshop-friendly trial of Sage.is AI.'
		},
		{
			id: 'model-switching',
			title: 'Switching models',
			dismissible: true,
			description: 'How to pick the right agent for your task.'
		},
		{
			id: 'chat-map',
			title: 'Chat Overview',
			dismissible: true,
			description: 'See where your conversation goes.'
		},
		{
			id: 'artifacts',
			title: 'Artifacts',
			dismissible: true,
			description: 'Reusable outputs from your conversations.'
		},
		{
			id: 'bialik-sage',
			title: 'Building a Bialik Sage agent',
			dismissible: true,
			description: 'Make your own teaching assistant.'
		},
		{
			id: 'done',
			title: 'Everything',
			dismissible: true,
			description: 'Have fun and try.sage.is! Everything resets every 24 hours.'
		}
	];

	let show = false;
	let currentIndex = 0;
	let dontShowAgain = false;

	// Parse the steps JSON defensively. WHY inline ~10 lines (DRY/KISS):
	// no other component reads this string, and a separate util would
	// hide the fallback decision from the only caller that cares.
	$: steps = (() => {
		const raw = $config?.try_sage?.tutorial_steps_json;
		if (!raw) return DEFAULT_STEPS;
		try {
			const parsed = JSON.parse(raw);
			if (Array.isArray(parsed) && parsed.length > 0) {
				return parsed as TutorialStep[];
			}
		} catch (e) {
			console.warn('TrySageTutorial: tutorial_steps_json parse failed, using defaults', e);
		}
		return DEFAULT_STEPS;
	})();

	$: currentStep = steps[currentIndex];
	$: isLast = currentIndex >= steps.length - 1;
	$: isFirst = currentIndex === 0;
	$: isDismissible = currentStep?.dismissible !== false;

	function markSeen() {
		try {
			localStorage.setItem(STORAGE_KEY, 'true');
		} catch {
			// localStorage may be blocked in some workshop environments.
			// Failing silently is fine — the modal will reopen next visit.
		}
	}

	function next() {
		if (isLast) {
			finish();
		} else {
			currentIndex++;
		}
	}

	function back() {
		if (currentIndex > 0) currentIndex--;
	}

	function skip() {
		// Skip == treat the rest as seen.
		markSeen();
		show = false;
	}

	function finish() {
		if (dontShowAgain) markSeen();
		show = false;
	}

	function openTutorial() {
		currentIndex = 0;
		dontShowAgain = false;
		show = true;
	}

	onMount(() => {
		// Auto-open conditions: feature flag on, never seen before, signed in.
		const enabled = $config?.features?.enable_try_sage === true;
		let seen = false;
		try {
			seen = localStorage.getItem(STORAGE_KEY) === 'true';
		} catch {
			// If localStorage is blocked, treat as unseen so the tutorial runs once.
		}
		if (enabled && !seen && $user) {
			openTutorial();
		}
	});

	// Subscribe to the replay trigger. The TrialMode admin panel
	// increments this to re-open the tutorial after clearing localStorage.
	// Skip the initial value (0) so we don't re-open on every mount.
	let lastReopenValue = 0;
	$: if ($tutorialReopen > lastReopenValue) {
		lastReopenValue = $tutorialReopen;
		openTutorial();
	}
</script>

<Modal bind:show size="lg">
	<div style="--p:1.5rem; --d:flex; --fd:column; --g:1rem">
		<!-- Step indicator -->
		<div style="--d:flex; --jc:space-between; --ai:center">
			<div style="--size:0.7rem; --c:var(--color-gray-500)">
				{$i18n?.t('Step')} {currentIndex + 1} / {steps.length}
			</div>
			<button
				type="button"
				on:click={() => (show = false)}
				style="--size:0.75rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700)"
				aria-label="Close tutorial"
			>
				&times;
			</button>
		</div>

		<!-- Title -->
		<div style="--size:1.2rem; --weight:600; --dark-c:#fff">
			{currentStep?.title ?? ''}
		</div>

		<!-- Video or placeholder -->
		{#if currentStep?.video_url}
			<VideoEmbed url={currentStep.video_url} title={currentStep.title} />
		{:else}
			<!-- WHY placeholder: see header comment. Real videos drop in via
			     TRY_SAGE_TUTORIAL_STEPS_JSON without a redeploy. -->
			<div
				class="aspect-video w-full overflow-hidden rounded-lg"
				style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --d:flex; --fd:column; --ai:center; --jc:center; --g:0.6rem; --p:1rem; --ta:center"
			>
				<div style="--size:1rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)">
					<!--{$i18n?.t('Video coming soon')}-->
					<a href="mailto:support@sage.is">Schedule a workshop</a> to see {currentStep?.title ?? ''} in action.
				</div>
				{#if currentStep?.description}
					<div
						style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --maxw:32rem"
					>
						{currentStep.description}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Description below the embed when both video and description exist -->
		{#if currentStep?.video_url && currentStep?.description}
			<div style="--size:0.8rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)">
				{currentStep.description}
			</div>
		{/if}

		<!-- Don't show again checkbox (only on dismissible steps) -->
		{#if isDismissible}
			<label style="--d:flex; --ai:center; --g:0.5rem; --size:0.75rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); cursor:pointer">
				<input type="checkbox" bind:checked={dontShowAgain} />
				<span>{$i18n?.t("Don't show again")}</span>
			</label>
		{/if}

		<!-- Navigation -->
		<div style="--d:flex; --jc:space-between; --ai:center; --pt:0.5rem">
			<button
				type="button"
				on:click={back}
				disabled={isFirst}
				style="--px:1rem; --py:0.4rem; --radius:0.4rem; --size:0.8rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --c:var(--color-gray-700); --dark-c:var(--color-gray-200); cursor:pointer"
			>
				{$i18n?.t('Back')}
			</button>

			<div style="--d:flex; --g:0.5rem">
				<button
					type="button"
					on:click={skip}
					disabled={!isDismissible}
					style="--px:1rem; --py:0.4rem; --radius:0.4rem; --size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); cursor:pointer"
					title={!isDismissible ? 'This step cannot be skipped' : ''}
				>
					{$i18n?.t('Skip')}
				</button>
				<button
					type="button"
					on:click={next}
					style="--px:1.2rem; --py:0.4rem; --radius:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --dark-bgc:#fff; --c:#fff; --dark-c:#000; cursor:pointer"
				>
					{isLast ? $i18n?.t('Finish') : $i18n?.t('Next')}
				</button>
			</div>
		</div>
	</div>
</Modal>
