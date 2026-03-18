<script lang="ts">
	import { getContext } from 'svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { marked } from 'marked';

	const i18n = getContext('i18n');

	const capabilityLabels = {
		vision: {
			label: $i18n.t('Vision'),
			description: $i18n.t('Model accepts image inputs')
		},
		file_upload: {
			label: $i18n.t('File Upload'),
			description: $i18n.t('Model accepts file inputs')
		},

		image_generation: {
			label: $i18n.t('Image Generation'),
			description: $i18n.t('Model can generate images based on text prompts')
		},
		code_interpreter: {
			label: $i18n.t('Code Interpreter'),
			description: $i18n.t('Model can execute code and perform calculations')
		},
		usage: {
			label: $i18n.t('Usage'),
			description: $i18n.t(
				'Sends `stream_options: { include_usage: true }` in the request.\nSupported providers will return token usage information in the response when set.'
			)
		},
		citations: {
			label: $i18n.t('Citations'),
			description: $i18n.t('Displays citations in the response')
		}
	};

	export let capabilities: {
		vision?: boolean;
		file_upload?: boolean;

		image_generation?: boolean;
		code_interpreter?: boolean;
		usage?: boolean;
		citations?: boolean;
	} = {};
</script>

<div>
	<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.25rem">
		<div style="--as:center; --size:0.875rem; --weight:600">{$i18n.t('Capabilities')}</div>
	</div>
	<div style="--d:flex; --ai:center; --mt:0.5rem; --fw:wrap">
		{#each Object.keys(capabilityLabels) as capability}
			<div style="--d:flex; --ai:center; --g:0.5rem; --mr:0.6rem">
				<Checkbox
					state={capabilities[capability] ? 'checked' : 'unchecked'}
					on:change={(e) => {
						capabilities[capability] = e.detail === 'checked';
					}}
				/>

				<div style="--py:0.125rem; --size:0.875rem; --tt:capitalize">
					<Tooltip content={marked.parse(capabilityLabels[capability].description)}>
						{$i18n.t(capabilityLabels[capability].label)}
					</Tooltip>
				</div>
			</div>
		{/each}
	</div>
</div>
