<script lang="ts">
	import { getContext } from 'svelte';
	import { settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	import Modal from './common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	async function dismiss() {
		show = false;
	}

	async function optOut() {
		settings.set({ ...$settings, devMissionSignup: false });
		await updateUserSettings(localStorage.token, { ui: $settings });
		show = false;
	}
</script>

<Modal bind:show size="lg">
	<!-- Close button -->
	<div style="--d:flex; --jc:flex-end; --px:0.5rem; --pt:0.5rem">
		<button on:click={dismiss} aria-label={$i18n.t('Close')}>
			<XMark className={'size-5'}>
				<p class="sr-only">{$i18n.t('Close')}</p>
			</XMark>
		</button>
	</div>

	<div style="--px:1.2rem; --pt:0.5rem; --pb:1.5rem">
		<!-- Header -->
		<div style="--ta:center; --mb:1rem">
			<div style="--size:2.5rem; --mb:0.3rem">
				&#128075;
			</div>
			<div style="--size:1.3rem; --weight:600; --dark-c:#fff; --mb:0.3rem">
				{$i18n.t("Hey recruit, you are still in production mode.")}
			</div>
			<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:0.2rem">
				{$i18n.t('You signed up for the dev mission. That terminal is not going to open itself.')}
			</div>
		</div>

		<!-- Quick steps recap -->
		<div style="--d:flex; --fd:column; --g:0.6rem; --mb:1.2rem">
			<div style="--d:flex; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid">
				<div style="--size:1.2rem; --weight:600; --c:var(--color-gray-300); --dark-c:var(--color-gray-600); --shrink:0; --w:1.5rem; --ta:center">1</div>
				<div>
					<div style="--size:0.85rem; --weight:500; --mb:0.2rem">{$i18n.t('Install the CLI')}</div>
					<code style="--size:0.7rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --px:0.4rem; --py:0.2rem; --radius:0.25rem; --d:inline-block">
						brew tap sage-is/apps && brew install ai-ui
					</code>
				</div>
			</div>

			<div style="--d:flex; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid">
				<div style="--size:1.2rem; --weight:600; --c:var(--color-gray-300); --dark-c:var(--color-gray-600); --shrink:0; --w:1.5rem; --ta:center">2</div>
				<div>
					<div style="--size:0.85rem; --weight:500; --mb:0.2rem">{$i18n.t('Launch dev mode')}</div>
					<code style="--size:0.7rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --px:0.4rem; --py:0.2rem; --radius:0.25rem; --d:inline-block">
						ai-ui dev
					</code>
				</div>
			</div>
		</div>

		<!-- Links -->
		<div style="--d:flex; --fd:column; --g:0.4rem; --mb:1.5rem">
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
		</div>

		<!-- Actions -->
		<div style="--d:flex; --jc:space-between; --ai:center">
			<button
				on:click={optOut}
				style="--px:0.6rem; --py:0.3rem; --size:0.7rem; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --dark-hvr-c:var(--color-gray-300)"
			>
				{$i18n.t('Stop reminding me')}
			</button>

			<button
				on:click={dismiss}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{$i18n.t("I'm on it, I swear")}
			</button>
		</div>
	</div>
</Modal>
