<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { settings, playingNotificationSound, isLastActiveTab } from '$lib/stores';
	import { getBranding } from '$lib/apis/configs';
	import DOMPurify from 'dompurify';

	import { marked } from 'marked';
	import { createEventDispatcher, onMount } from 'svelte';

	const dispatch = createEventDispatcher();

	export let onClick: Function = () => {};
	export let title: string = 'HI';
	export let content: string;

	let branding: { logo_url?: string; favicon_url?: string } = {};

	onMount(async () => {
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}

		if (!navigator.userActivation.hasBeenActive) {
			return;
		}

		if ($settings?.notificationSound ?? true) {
			if (!$playingNotificationSound && $isLastActiveTab) {
				playingNotificationSound.set(true);

				const audio = new Audio(`/audio/notification.mp3`);
				audio.play().finally(() => {
					// Ensure the global state is reset after the sound finishes
					playingNotificationSound.set(false);
				});
			}
		}
	});
</script>

<button
	style="--d:flex; --g:0.625rem; --ta:left; --minw:var(--width); --w:100%; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --bgc:#fff; --c:#000; --b:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --radius:0.75rem; --px:0.875rem; --py:0.875rem"
	on:click={() => {
		onClick();
		dispatch('closeToast');
	}}
>
	<div style="--fs:0; --translatey:-0.125rem"
	class="self-top">
		<img src={branding?.favicon_url || branding?.logo_url || `${WEBUI_BASE_URL}/static/icons/favicon.png`} alt="favicon" style="--w:1.75rem; --h:1.75rem; --radius:9999px" />
	</div>

	<div>
		{#if title}
			<div style="--size:13px; --weight:500; --mb:0.125rem; --line-clamp:1; --tt:capitalize">{title}</div>
		{/if}

		<div style="--line-clamp:2; --size:0.75rem; --as:center; --dark-c:var(--color-gray-300); --weight:400">
			{@html DOMPurify.sanitize(marked(content))}
		</div>
	</div>
</button>
