<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { WEBUI_VERSION } from '$lib/constants';
	import XMark from '../icons/XMark.svelte';

	export let version = {
		current: WEBUI_VERSION,
		latest: WEBUI_VERSION
	};
</script>

<div
	style="--d:flex; --ai:flex-start; --bgc:#F1F8FE; --dark-bgc:#020C1D; --b:1px solid; --bc:3371D5; --dark-bc:#03113B; --size:#2B6CD4; --dark-size:#6795EC; --radius:0.5rem; --px:0.875rem; --py:0.75rem; --size:0.75rem; --maxw:20rem; --pr:0.5rem; --w:100%; --shadow:4"
>
	<div style="--fx:1 1 0%; --weight:500">
		{$i18n.t(`A new version (v{{LATEST_VERSION}}) is now available.`, {
			LATEST_VERSION: version.latest
		})}

		<a href="https://github.com/Sage-is/AI-UI/releases" target="_blank" style="--td:underline">
			{$i18n.t('Update for the latest features and improvements.')}</a
		>
	</div>

	<div style="--fs:0; --pr:0.25rem">
		<button
			style="--hvr-c:#1e3a8a; --hvr-dark-c:#93c5fd; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark />
		</button>
	</div>
</div>
