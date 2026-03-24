<!--
  AuthStep.svelte — Wizard step for OAuth provider setup (Beta)
  Thin wrapper around OAuthSettings in compact mode.
-->
<script lang="ts">
	import { getContext } from 'svelte';
	import OAuthSettings from '$lib/components/admin/Settings/OAuthSettings.svelte';

	const i18n = getContext('i18n');

	export let onNext: () => void = () => {};
	export let onBack: () => void = () => {};

	let oauthSettings: OAuthSettings;
	let saving = false;

	const saveAndNext = async () => {
		saving = true;
		await oauthSettings.save();
		saving = false;
		onNext();
	};
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	<div style="--d:flex; --ai:center; --g:0.5rem; --mb:0.2rem">
		<div style="--size:1.2rem; --weight:600; --dark-c:#fff">
			{$i18n.t('Authentication')}
		</div>
		<span style="--size:0.55rem; --c:var(--color-amber-600); --weight:600; --px:0.3rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-amber-100); --dark-bgc:var(--color-amber-900); --dark-c:var(--color-amber-400)">{$i18n.t('Beta')}</span>
	</div>
	<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
		{$i18n.t('Let users sign in with their Google or GitHub accounts.')}
	</div>

	<div style="--mb:1.5rem">
		<OAuthSettings bind:this={oauthSettings} compact={true} />
	</div>

	<div style="--d:flex; --jc:space-between; --ai:center">
		<button
			on:click={onBack}
			style="--px:0.6rem; --py:0.3rem; --size:0.75rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --dark-hvr-c:var(--color-gray-200)"
		>
			{$i18n.t('Back')}
		</button>

		<div style="--d:flex; --ai:center; --g:0.6rem">
			<button
				on:click={onNext}
				style="--px:0.6rem; --py:0.3rem; --size:0.7rem; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --td:underline"
			>
				{$i18n.t('Skip')}
			</button>

			<button
				on:click={saveAndNext}
				disabled={saving}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:{!saving ? '#000' : 'var(--color-gray-300)'}; --hvr-bgc:{!saving ? 'var(--color-gray-900)' : 'var(--color-gray-300)'}; --c:#fff; --dark-bgc:{!saving ? '#fff' : 'var(--color-gray-600)'}; --dark-c:{!saving ? '#000' : 'var(--color-gray-400)'}; --hvr-dark-bgc:{!saving ? 'var(--color-gray-100)' : 'var(--color-gray-600)'}; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{saving ? $i18n.t('Saving...') : $i18n.t('Save & Next')}
			</button>
		</div>
	</div>
</div>
