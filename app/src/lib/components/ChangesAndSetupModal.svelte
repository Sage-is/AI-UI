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
	import StepChooser from './setup/StepChooser.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	type PanelId = 'changelog' | 'chooser' | 'welcome' | 'connection' | 'users' | 'complete';

	let currentIndex = 0;
	let connectionAdded = false;
	let usersAdded = false;
	let workingAloneSelected = false;

	// Manual panel override from StepChooser — null means use auto-computed panels
	let manualPanels: PanelId[] | null = null;

	// Pure function: compute panels from trigger reason
	function computePanels(reason: SetupTriggerReason): PanelId[] {
		const p: PanelId[] = [];

		if (reason.manualTrigger) {
			p.push('chooser');
		} else {
			if (reason.hasChangelog) {
				p.push('changelog');
			}
			if (reason.needsModels || reason.needsUsers) {
				p.push('welcome');
				if (reason.needsModels) p.push('connection');
				if (reason.needsUsers) p.push('users');
				p.push('complete');
			}
		}

		if (p.length === 0) {
			p.push('changelog');
		}

		return p;
	}

	// All panel state derived via direct $: assignments so Svelte can track them
	$: autoPanels = show ? computePanels($setupTriggerReason) : [];
	$: panels = manualPanels ?? autoPanels;
	$: currentPanel = panels[currentIndex] ?? null;
	$: isWizardMode = panels.some((p) => p !== 'changelog');
	$: wizardPanels = panels.filter((p) => p !== 'changelog');
	$: wizardIndex = isWizardMode ? wizardPanels.indexOf(currentPanel) : -1;

	// Reset state when modal opens
	$: if (show) {
		currentIndex = 0;
		manualPanels = null;
		connectionAdded = false;
		usersAdded = false;
		workingAloneSelected = false;
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

	function handleChooserStart(steps: string[]) {
		const p: PanelId[] = [];
		if (steps.includes('connection')) p.push('connection');
		if (steps.includes('users')) p.push('users');
		p.push('complete');
		manualPanels = p;
		currentIndex = 0;
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

	function handleWorkingAlone() {
		workingAloneSelected = true;
		settings.set({ ...$settings, workingAlone: true });
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

	<!-- Step Progress Indicator (wizard mode only, not for changelog) -->
	{#if isWizardMode && wizardPanels.length > 1 && currentPanel !== 'changelog'}
		<div style="--d:flex; --jc:center; --g:0.4rem; --px:1.2rem; --pb:0.5rem">
			{#each wizardPanels as panel, i}
				<div
					style="--w:0.5rem; --h:0.5rem; --radius:9999px; --tn:background-color 200ms ease; --bgc:{i <= wizardIndex ? '#000' : 'var(--color-gray-300)'}; --dark-bgc:{i <= wizardIndex ? '#fff' : 'var(--color-gray-600)'}"
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
	{:else if currentPanel === 'chooser'}
		<StepChooser onStart={handleChooserStart} />
	{:else if currentPanel === 'welcome'}
		<WelcomeStep
			onNext={next}
			hasConnectionStep={panels.includes('connection')}
			hasUsersStep={panels.includes('users')}
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
