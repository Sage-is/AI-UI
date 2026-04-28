<script lang="ts">
	import { getContext, tick } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
		import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let pipeline = false;

	export let url = '';
	export let key = '';
	export let config = {};

	let showConfigModal = false;
	let showDeleteConfirmDialog = false;
</script>

<AddConnectionModal
	edit
	direct
	bind:show={showConfigModal}
	connection={{
		url,
		key,
		config
	}}
	onDelete={() => {
		showDeleteConfirmDialog = true;
	}}
	onSubmit={(connection) => {
		url = connection.url;
		key = connection.key;
		config = connection.config;
		onSubmit(connection);
	}}
/>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		onDelete();
		showConfigModal = false;
	}}
/>

<div style="--d:flex; --w:100%; --g:0.5rem; --ai:center">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`AI-UI will make requests to "{{url}}/chat/completions"`, {
			url
		})}
		placement="top-start"
	>
		{#if !(config?.enable ?? true)}
			<div
				style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --op:0.6; --bgc:#fff; --dark-bgc:var(--color-gray-900); --z:10"
			></div>
		{/if}
		<div style="--d:flex; --w:100%; --g:0.5rem">
			<div style="--fx:1 1 0%; --pos:relative">
				<input
					class={`w-full bg-transparent ${($settings?.highContrastMode ?? false) ? '' : 'outline-hidden'} ${pipeline ? 'pr-8' : ''}`}
					placeholder={$i18n.t('API Base URL')}
					bind:value={url}
					autocomplete="off"
				/>
			</div>

			<SensitiveInput
				inputClassName="bg-transparent w-full"
				placeholder={$i18n.t('API Key')}
				bind:value={key}
			/>
		</div>
	</Tooltip>

	<div style="--d:flex; --g:0.2rem">
		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				aria-label={$i18n.t('Open modal to configure connection')}
				style="--as:center; --p:0.2rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					showConfigModal = true;
				}}
				type="button"
			>
				<Icon name="cog6" />
			</button>
		</Tooltip>
	</div>
</div>
