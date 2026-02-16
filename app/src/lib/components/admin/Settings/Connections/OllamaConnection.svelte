<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import ManageOllamaModal from './ManageOllamaModal.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let url = '';
	export let idx = 0;
	export let config = {};

	let showManageModal = false;
	let showConfigModal = false;
	let showDeleteConfirmDialog = false;
</script>

<AddConnectionModal
	ollama
	edit
	bind:show={showConfigModal}
	connection={{
		url,
		key: config?.key ?? '',
		config: config
	}}
	onDelete={() => {
		showDeleteConfirmDialog = true;
	}}
	onSubmit={(connection) => {
		url = connection.url;
		config = { ...connection.config, key: connection.key };
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

<ManageOllamaModal bind:show={showManageModal} urlIdx={idx} />

<div style="--d:flex; --g:0.375rem">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}/api/chat"`, {
			url
		})}
		placement="top-start"
	>
		{#if !(config?.enable ?? true)}
			<div
				style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --op:0.6; --bgc:#fff; --dark-bgc:var(--color-gray-900, #171717); --z:10"
			></div>
		{/if}

		<input
			style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
			placeholder={$i18n.t('Enter URL (e.g. http://localhost:11434)')}
			bind:value={url}
		/>
	</Tooltip>

	<div style="--d:flex; --g:0.25rem">
		<Tooltip content={$i18n.t('Manage')} className="self-start">
			<button
				style="--as:center; --p:0.25rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-900, #171717); --hvr-dark-bgc:var(--color-gray-850, #262626); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					showManageModal = true;
				}}
				type="button"
			>
				<ArrowDownTray />
			</button>
		</Tooltip>

		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				style="--as:center; --p:0.25rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-900, #171717); --hvr-dark-bgc:var(--color-gray-850, #262626); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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
