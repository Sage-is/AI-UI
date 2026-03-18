<script lang="ts">
	import { getContext } from 'svelte';
	import type { SetupTriggerReason } from '$lib/stores';

	import { config, settings, models, setupTriggerReason } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	import Modal from './common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChangelogPanel from './setup/ChangelogPanel.svelte';
	import WelcomeStep from './setup/WelcomeStep.svelte';
	import ConnectionStep from './setup/ConnectionStep.svelte';
	import UsersStep from './setup/UsersStep.svelte';
	import CompleteStep from './setup/CompleteStep.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	type PanelId = 'changelog' | 'welcome' | 'connection' | 'users' | 'complete';

	let currentIndex = 0;
	let connectionAdded = false;
	let usersAdded = false;
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
		connectionAdded = false;
		usersAdded = false;
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
		} else {
			finish();
		}
	}

	function back() {
		if (currentIndex > 0) {
			currentIndex--;
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

	// Called by WelcomeStep when admin clicks "Get Started" with selected steps
	function handleWelcomeStart(steps: string[]) {
		// Build full panel sequence: everything before welcome + welcome + selected steps + complete
		const beforeWelcome = panels.slice(0, panels.indexOf('welcome'));
		const p: PanelId[] = [...beforeWelcome, 'welcome'];
		if (steps.includes('connection')) p.push('connection');
		if (steps.includes('users')) p.push('users');
		p.push('complete');
		dynamicPanels = p;
		// Advance past welcome to the first real step
		currentIndex = beforeWelcome.length + 1;
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
				<button
					on:click={() => goToWizardPanel(i)}
					aria-label={panel}
					style="--w:0.6rem; --h:0.6rem; --radius:9999px; --p:0; --tn:background-color 200ms ease, transform 150ms ease; --bgc:{i <= wizardIndex ? '#000' : 'var(--color-gray-300)'}; --dark-bgc:{i <= wizardIndex ? '#fff' : 'var(--color-gray-600)'}; cursor:pointer; --hvr-transform:scale(1.3)"
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
	{:else if currentPanel === 'connection'}
		<ConnectionStep
			onNext={() => {
				connectionAdded = $models.length > 0;
				next();
			}}
			onBack={back}
		/>
	{:else if currentPanel === 'users'}
		<UsersStep
			onNext={() => {
				usersAdded = true;
				next();
			}}
			onBack={back}
			onWorkingAlone={() => {
				handleWorkingAlone();
			}}
		/>
	{:else if currentPanel === 'complete'}
		<CompleteStep
			onFinish={finish}
			{connectionAdded}
			{usersAdded}
			workingAlone={workingAloneSelected}
		/>
	{/if}
</Modal>
