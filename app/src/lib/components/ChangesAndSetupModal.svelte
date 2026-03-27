<script lang="ts">
	import { getContext } from 'svelte';
	import type { SetupTriggerReason } from '$lib/stores';

	import { config, settings, setupTriggerReason } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	import Modal from './common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChangelogPanel from './setup/ChangelogPanel.svelte';
	import WelcomeStep from './setup/WelcomeStep.svelte';
	import ConnectionStep from './setup/ConnectionStep.svelte';
	import FeaturesStep from './setup/FeaturesStep.svelte';
	import UsersStep from './setup/UsersStep.svelte';
	import AuthStep from './setup/AuthStep.svelte';
	import SearchAudioStep from './setup/SearchAudioStep.svelte';
	import CompleteStep from './setup/CompleteStep.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	type PanelId = 'changelog' | 'welcome' | 'auth' | 'connection' | 'features' | 'users' | 'search_audio' | 'complete';

	let currentIndex = 0;
	let workingAloneSelected = false;

	// Dynamic panels set by WelcomeStep's onStart callback — null means use auto-computed
	let dynamicPanels: PanelId[] | null = null;

	// Determine whether to show wizard (welcome + steps)
	function needsWizard(reason: SetupTriggerReason): boolean {
		return reason.needsModels || reason.needsUsers || reason.manualTrigger;
	}

	// Initial panel list: just changelog? + welcome
	// The welcome step lets the admin choose which steps to include
	function computeInitialPanels(reason: SetupTriggerReason): PanelId[] {
		const p: PanelId[] = [];

		if (reason.hasChangelog) {
			p.push('changelog');
		}

		if (needsWizard(reason)) {
			p.push('welcome');
		}

		// Fallback: if nothing, show changelog
		if (p.length === 0) {
			p.push('changelog');
		}

		return p;
	}

	// All panel state derived via direct $: assignments so Svelte can track them
	$: initialPanels = show ? computeInitialPanels($setupTriggerReason) : [];
	$: panels = dynamicPanels ?? initialPanels;
	$: currentPanel = panels[currentIndex] ?? null;
	$: isWizardMode = panels.some((p) => p !== 'changelog');
	$: wizardPanels = panels.filter((p) => p !== 'changelog');
	$: wizardIndex = isWizardMode ? wizardPanels.indexOf(currentPanel) : -1;
	$: isFirstRun = !$settings?.setupCompleted;

	// Reset state when modal opens
	$: if (show) {
		currentIndex = 0;
		dynamicPanels = null;
		selectedSteps = [];
		workingAloneSelected = false;
	}

	function goToWizardPanel(wizardIdx: number) {
		const targetPanel = wizardPanels[wizardIdx];
		if (targetPanel) {
			const panelIdx = panels.indexOf(targetPanel);
			if (panelIdx >= 0) {
				currentIndex = panelIdx;
			}
		}
	}

	function next() {
		if (currentIndex < panels.length - 1) {
			currentIndex++;
			skipIfNeeded();
		} else {
			finish();
		}
	}

	function back() {
		if (currentIndex > 0) {
			currentIndex--;
			// Skip backward past unchecked steps
			while (
				currentIndex > 0 &&
				allSteps.includes(panels[currentIndex]) &&
				!selectedSteps.includes(panels[currentIndex])
			) {
				currentIndex--;
			}
		}
	}

	async function finish() {
		localStorage.version = $config?.version;
		await settings.set({
			...$settings,
			version: $config?.version,
			setupCompleted: true
		});
		await updateUserSettings(localStorage.token, { ui: $settings });
		show = false;
	}

	// Track which steps the admin selected on WelcomeStep
	let selectedSteps: string[] = [];

	// All wizard steps always present (order: auth → connection → users → features)
	const allSteps: PanelId[] = ['auth', 'connection', 'users', 'features', 'search_audio'];

	// Called by WelcomeStep when admin clicks "Get Started"
	function handleWelcomeStart(steps: string[]) {
		selectedSteps = steps;
		// Always include all steps + complete in the panel sequence
		const beforeWelcome = panels.slice(0, panels.indexOf('welcome'));
		const p: PanelId[] = [...beforeWelcome, 'welcome', ...allSteps, 'complete'];
		dynamicPanels = p;
		// Advance past welcome, skipping to first selected step
		const welcomeIdx = beforeWelcome.length;
		currentIndex = welcomeIdx + 1;
		skipIfNeeded();
	}

	/** Skip current panel if it wasn't selected, advancing forward */
	function skipIfNeeded() {
		while (
			currentIndex < panels.length - 1 &&
			allSteps.includes(panels[currentIndex]) &&
			!selectedSteps.includes(panels[currentIndex])
		) {
			currentIndex++;
		}
	}

	function handleChangelogNext() {
		if (panels.length > 1) {
			next();
		} else {
			finishChangelogOnly();
		}
	}

	async function finishChangelogOnly() {
		localStorage.version = $config?.version;
		await settings.set({ ...$settings, version: $config?.version });
		await updateUserSettings(localStorage.token, { ui: $settings });
		show = false;
	}

	async function handleWorkingAlone() {
		workingAloneSelected = true;
		await settings.set({ ...$settings, workingAlone: true });
		await updateUserSettings(localStorage.token, { ui: { ...$settings, workingAlone: true } });
		next();
	}

	function handleClose() {
		if (currentPanel === 'changelog' && panels.length === 1) {
			finishChangelogOnly();
		} else {
			show = false;
		}
	}
</script>

<Modal bind:show size="lg">
	<!-- Close button -->
	<div style="--d:flex; --jc:flex-end; --px:0.5rem; --pt:0.5rem">
		<button
			on:click={handleClose}
			aria-label={$i18n.t('Close')}
		>
			<XMark className={'size-5'}>
				<p class="sr-only">{$i18n.t('Close')}</p>
			</XMark>
		</button>
	</div>

	<!-- Step Progress Indicator (wizard mode only, not for changelog or welcome) -->
	{#if isWizardMode && wizardPanels.length > 1 && currentPanel !== 'changelog' && currentPanel !== 'welcome'}
		<div style="--d:flex; --jc:center; --g:0.4rem; --px:1.2rem; --pb:0.5rem">
			{#each wizardPanels as panel, i}
				{@const isSkipped = allSteps.includes(panel) && !selectedSteps.includes(panel)}
				{@const isPastOrCurrent = i <= wizardIndex}
				<button
					on:click={() => {
						if (!isSkipped) goToWizardPanel(i);
					}}
					aria-label={panel}
					style="--w:{isSkipped ? '0.35rem' : '0.6rem'}; --h:{isSkipped ? '0.35rem' : '0.6rem'}; --radius:9999px; --p:0; --tn:background-color 200ms ease, transform 150ms ease; --bgc:{isSkipped ? 'var(--color-gray-200)' : isPastOrCurrent ? '#000' : 'var(--color-gray-300)'}; --dark-bgc:{isSkipped ? 'var(--color-gray-750)' : isPastOrCurrent ? '#fff' : 'var(--color-gray-600)'}; cursor:{isSkipped ? 'default' : 'pointer'}; --hvr-transform:{isSkipped ? 'none' : 'scale(1.3)'}"
				/>
			{/each}
		</div>
	{/if}

	<!-- Panel Content -->
	{#if currentPanel === 'changelog'}
		<ChangelogPanel
			onNext={handleChangelogNext}
			isLastPanel={panels.length === 1}
		/>
	{:else if currentPanel === 'welcome'}
		<WelcomeStep
			onStart={handleWelcomeStart}
			{isFirstRun}
		/>
	{:else if currentPanel === 'auth'}
		<AuthStep
			onNext={next}
			onBack={back}
		/>
	{:else if currentPanel === 'connection'}
		<ConnectionStep
			onNext={next}
			onBack={back}
		/>
	{:else if currentPanel === 'features'}
		<FeaturesStep
			onNext={next}
			onBack={back}
		/>
	{:else if currentPanel === 'users'}
		<UsersStep
			onNext={next}
			onBack={back}
			onWorkingAlone={() => {
				handleWorkingAlone();
			}}
		/>
	{:else if currentPanel === 'search_audio'}
		<SearchAudioStep
			onNext={next}
			onBack={back}
		/>
	{:else if currentPanel === 'complete'}
		<CompleteStep
			onFinish={finish}
			workingAlone={workingAloneSelected}
		/>
	{/if}
</Modal>
