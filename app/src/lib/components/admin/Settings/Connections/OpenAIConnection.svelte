<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
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

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		onDelete();
	}}
/>

<AddConnectionModal
	edit
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

<div style="--d:flex; --w:100%; --g:0.5rem; --ai:center">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}/chat/completions"`, {
			url
		})}
		placement="top-start"
	>
		{#if !(config?.enable ?? true)}
			<div
				style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --op:0.6; --bgc:#fff; --dark-bgc:var(--color-gray-900); --z:10"
			></div>
		{/if}
		<button
			type="button"
			style="--d:flex; --w:100%; --g:0.5rem; --ai:center; --cur:pointer; --bgc:transparent; --p:0; --b:none"
			on:click={() => { showConfigModal = true; }}
		>
			<div style="--fx:1 1 0%; --pos:relative; --ta:left">
				<div
					style="--w:100%; --bgc:transparent; --oe:none; --p:0.375rem 0.5rem; --size:0.875rem; --c:inherit; --of:hidden; --te:ellipsis; --ws:nowrap"
				>
					{url || $i18n.t('API Base URL')}
				</div>

				{#if pipeline}
					<div style="--pos:absolute; --top:0.125rem; --right:0.625rem">
						<Tooltip content="Pipelines">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								fill="currentColor"
								style="--w:1rem; --h:1rem"
							>
								<path
									d="M11.644 1.59a.75.75 0 0 1 .712 0l9.75 5.25a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.712 0l-9.75-5.25a.75.75 0 0 1 0-1.32l9.75-5.25Z"
								/>
								<path
									d="m3.265 10.602 7.668 4.129a2.25 2.25 0 0 0 2.134 0l7.668-4.13 1.37.739a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.71 0l-9.75-5.25a.75.75 0 0 1 0-1.32l1.37-.738Z"
								/>
								<path
									d="m10.933 19.231-7.668-4.13-1.37.739a.75.75 0 0 0 0 1.32l9.75 5.25c.221.12.489.12.71 0l9.75-5.25a.75.75 0 0 0 0-1.32l-1.37-.738-7.668 4.13a2.25 2.25 0 0 1-2.134-.001Z"
								/>
							</svg>
						</Tooltip>
					</div>
				{/if}
			</div>

			<div style="--fx:1 1 0%; --ta:left">
				<div
					style="--w:100%; --bgc:transparent; --p:0.375rem 0.5rem; --size:0.875rem; --c:var(--color-gray-400)"
				>
					{key ? '••••••••' : $i18n.t('API Key')}
				</div>
			</div>
		</button>
	</Tooltip>

	<div style="--d:flex; --g:0.25rem; --ai:center">
		<Tooltip content={$i18n.t('Configure')} className="self-center">
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
