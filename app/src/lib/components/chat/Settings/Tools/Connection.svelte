<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import AddServerModal from '$lib/components/AddServerModal.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let connection = null;
	export let direct = false;

	let showConfigModal = false;
	let showDeleteConfirmDialog = false;
</script>

<AddServerModal
	edit
	{direct}
	bind:show={showConfigModal}
	{connection}
	onDelete={() => {
		showDeleteConfirmDialog = true;
	}}
	onSubmit={(c) => {
		connection = c;
		onSubmit(c);
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
		content={$i18n.t(`WebUI will make requests to "{{url}}"`, {
			url: `${connection?.url}/${connection?.path ?? 'openapi.json'}`
		})}
		placement="top-start"
	>
		{#if !(connection?.config?.enable ?? true)}
			<div
				style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --op:0.6; --bgc:#fff; --dark-bgc:var(--color-gray-900); --z:10"
			></div>
		{/if}
		<div style="--d:flex; --w:100%">
			<div style="--fx:1 1 0%; --pos:relative">
				<input
					style="--oe:none; --w:100%; --bgc:transparent"
					placeholder={$i18n.t('API Base URL')}
					bind:value={connection.url}
					autocomplete="off"
				/>
			</div>

			{#if (connection?.auth_type ?? 'bearer') === 'bearer'}
				<SensitiveInput
					inputClassName=" outline-hidden bg-transparent w-full"
					placeholder={$i18n.t('API Key')}
					bind:value={connection.key}
					required={false}
				/>
			{/if}
		</div>
	</Tooltip>

	<div style="--d:flex; --g:0.25rem">
		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				style="--as:center; --p:0.25rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					showConfigModal = true;
				}}
				type="button"
			>
				<Cog6 />
			</button>
		</Tooltip>
	</div>
</div>
