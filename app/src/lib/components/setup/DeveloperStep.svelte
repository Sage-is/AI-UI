<script lang="ts">
	import { getContext } from 'svelte';
	import { config, settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	const i18n = getContext('i18n');

	export let onNext: () => void = () => {};
	export let onBack: () => void = () => {};

	$: isDevMode = $config?.dev_mode ?? false;

	let devMissionSignup = $settings?.devMissionSignup ?? false;

	async function handleNext() {
		if (!isDevMode && devMissionSignup !== ($settings?.devMissionSignup ?? false)) {
			settings.set({ ...$settings, devMissionSignup });
			await updateUserSettings(localStorage.token, { ui: $settings });
		}
		onNext();
	}
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	{#if isDevMode}
		<!-- Dev Mode: Celebration -->
		<div style="--ta:center; --mb:1rem">
			<div style="--size:3rem; --mb:0.4rem">
				&#129497;
			</div>
			<div style="--size:1.4rem; --weight:600; --dark-c:#fff; --mb:0.3rem">
				{$i18n.t('Welcome to Dev Mode!')}
			</div>
			<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
				{$i18n.t('Live source mounted. Changes reload automatically.')}
			</div>
		</div>

		<div style="--d:flex; --fd:column; --g:0.6rem; --mb:1.5rem">
			<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
				<span style="--c:var(--color-green-600)">&#10003;</span>
				<span>{$i18n.t('Source code mounted')}</span>
			</div>
			<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
				<span style="--c:var(--color-green-600)">&#10003;</span>
				<span>{$i18n.t('Hot reload active')}</span>
			</div>
		</div>

		<div style="--d:flex; --fd:column; --g:0.4rem; --mb:1.5rem">
			<a
				href="https://github.com/Sage-is/AI-UI"
				target="_blank"
				rel="noopener"
				style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --td:underline"
			>
				{$i18n.t('GitHub Repository')}
			</a>
			<a
				href="https://github.com/Sage-is/AI-UI/blob/master/docs/contributing.md"
				target="_blank"
				rel="noopener"
				style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --td:underline"
			>
				{$i18n.t('Contributing Guide')}
			</a>
		</div>
	{:else}
		<!-- Production: Guide to setting up dev -->
		<div style="--ta:center; --mb:1rem">
			<div style="--size:2.5rem; --mb:0.3rem">
				&#128187;
			</div>
			<div style="--size:1.2rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
				{$i18n.t('Developer Mode')}
			</div>
			<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:0.3rem">
				{$i18n.t('Time to dust off that terminal. Yes, the black screen with the blinking cursor.')}
			</div>
			<div style="--size:0.7rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --mb:1rem">
				{$i18n.t('Two commands and you are hacking on AI UI with hot reload. No PhD required.')}
			</div>
		</div>

		<div style="--d:flex; --fd:column; --g:0.8rem; --mb:1.2rem">
			<!-- Step 1 -->
			<div style="--d:flex; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid">
				<div style="--size:1.2rem; --weight:600; --c:var(--color-gray-300); --dark-c:var(--color-gray-600); --shrink:0; --w:1.5rem; --ta:center">1</div>
				<div>
					<div style="--size:0.85rem; --weight:500; --mb:0.2rem">{$i18n.t('Install the CLI')}</div>
					<code style="--size:0.7rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --px:0.4rem; --py:0.2rem; --radius:0.25rem; --d:inline-block">
						brew tap sage-is/apps && brew install ai-ui
					</code>
					<div style="--size:0.65rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --mt:0.25rem">
						{$i18n.t('One tap, one install. Homebrew does the heavy lifting.')}
					</div>
				</div>
			</div>

			<!-- Step 2 -->
			<div style="--d:flex; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid">
				<div style="--size:1.2rem; --weight:600; --c:var(--color-gray-300); --dark-c:var(--color-gray-600); --shrink:0; --w:1.5rem; --ta:center">2</div>
				<div>
					<div style="--size:0.85rem; --weight:500; --mb:0.2rem">{$i18n.t('Launch dev mode')}</div>
					<code style="--size:0.7rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --px:0.4rem; --py:0.2rem; --radius:0.25rem; --d:inline-block">
						ai-ui dev
					</code>
					<div style="--size:0.65rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --mt:0.25rem">
						{$i18n.t('Clones the repo, mounts source, fires up hot reload. Grab a coffee while it downloads ~1 GB of Node goodness the first time.')}
					</div>
				</div>
			</div>

			<!-- Step 3 -->
			<div style="--d:flex; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid">
				<div style="--size:1.2rem; --weight:600; --c:var(--color-gray-300); --dark-c:var(--color-gray-600); --shrink:0; --w:1.5rem; --ta:center">3</div>
				<div>
					<div style="--size:0.85rem; --weight:500; --mb:0.2rem">{$i18n.t('Break things (then fix them)')}</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Edit code, save, watch it reload. That is the whole loop. Ship it when you are proud of it.')}
					</div>
				</div>
			</div>
		</div>

		<!-- Mission signup -->
		<label
			style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --mb:1.2rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
		>
			<input type="checkbox" bind:checked={devMissionSignup} style="--w:1rem; --h:1rem; --shrink:0" />
			<div>
				<div style="--size:0.85rem; --weight:500">
					{$i18n.t('Sign me up for the mission')}
				</div>
				<div style="--size:0.65rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
					{$i18n.t("I solemnly swear I will open a terminal. Remind me next time I log in until I do.")}
				</div>
			</div>
		</label>

		<div style="--d:flex; --fd:column; --g:0.4rem; --mb:1.5rem">
			<div style="--size:0.7rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:0.2rem">
				{$i18n.t('Read the fine manual')}
			</div>
			<a
				href="https://docs.sage.is/docs/contribute"
				target="_blank"
				rel="noopener"
				style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --td:underline"
			>
				{$i18n.t('Contributing Guide')}
			</a>
			<a
				href="https://docs.sage.is/docs/getting_started"
				target="_blank"
				rel="noopener"
				style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --td:underline"
			>
				{$i18n.t('Getting Started Docs')}
			</a>
			<a
				href="https://github.com/Sage-is/AI-UI"
				target="_blank"
				rel="noopener"
				style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --td:underline"
			>
				{$i18n.t('GitHub Repository')}
			</a>
		</div>
	{/if}

	<div style="--d:flex; --jc:space-between; --ai:center">
		<button
			on:click={onBack}
			style="--px:0.6rem; --py:0.3rem; --size:0.75rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --dark-hvr-c:var(--color-gray-200)"
		>
			{$i18n.t('Back')}
		</button>

		<button
			on:click={handleNext}
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
		>
			{$i18n.t('Next')}
		</button>
	</div>
</div>
