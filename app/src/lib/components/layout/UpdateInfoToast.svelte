<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { WEBUI_VERSION } from '$lib/constants';
	import Icon from '$lib/components/Icon.svelte';

	export let version = {
		current: WEBUI_VERSION,
		latest: WEBUI_VERSION
	};
</script>

<div
	style="--d:flex; --ai:flex-start; --bgc:#F1F8FE; --dark-bgc:#020C1D;  --bc:3371D5; --dark-bc:#03113B; --size:#2B6CD4; --dark-size:#6795EC; --radius:0.5rem; --px:0.8rem; --py:0.6rem; --size:0.6rem; --maxw:20rem; --pr:0.5rem; --w:100%; --shadow:4"
>
	<div style="--fx:1 1 0%; --weight:500">
		<div>
			{$i18n.t(`A new version (v{{LATEST_VERSION}}) is now available.`, {
				LATEST_VERSION: version.latest
			})}
		</div>
		<div style="--mt:0.4rem">
			{$i18n.t('Auto-updating deployments pull this automatically. Manual installs:')}
		</div>
		<code
			style="--d:block; --mt:0.3rem; --mb:0.4rem; --bgc:#E5EEFB; --dark-bgc:#03113B; --px:0.5rem; --py:0.3rem; --radius:0.3rem; --size:0.7rem"
			>ai-ui update --tag {version.latest}</code
		>
		<a
			href="https://sage.education/getting_started/updating/"
			target="_blank"
			style="--td:underline"
			>{$i18n.t('Configure auto-updates')} ↗</a
		>
		&nbsp;&nbsp;
		<a
			href={`https://github.com/Sage-is/AI-UI/releases/tag/v${version.latest}`}
			target="_blank"
			style="--td:underline">{$i18n.t('Release Notes')} ↗</a
		>
	</div>

	<div style="--fs:0; --pr:0.2rem">
		<button
			style="--hvr-c:#1e3a8a; --hvr-dark-c:#93c5fd; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			on:click={() => {
				dispatch('close');
			}}
		>
			<Icon name="x-mark" />
		</button>
	</div>
</div>
