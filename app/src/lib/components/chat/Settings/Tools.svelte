<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { getModels as _getModels, getToolServersData } from '$lib/apis';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { models, settings, toolServers, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Tools/Connection.svelte';

	import AddServerModal from '$lib/components/AddServerModal.svelte';

	export let saveSettings: Function;

	let servers = null;
	let showConnectionModal = false;

	const addConnectionHandler = async (server) => {
		servers = [...servers, server];
		await updateHandler();
	};

	const updateHandler = async () => {
		await saveSettings({
			toolServers: servers
		});

		toolServers.set(await getToolServersData($i18n, $settings?.toolServers ?? []));
	};

	onMount(async () => {
		servers = $settings?.toolServers ?? [];
	});
</script>

<AddServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} direct />

<form
	id="tab-tools"
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.875rem"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div style="--ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if servers !== null}
			<div class="">
				<div style="--pr:0.375rem">
					<!-- {$i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, {
						URL: 'server?.url'
					})} -->
					<div class="">
						<div style="--d:flex; --jc:space-between; --ai:center; --mb:0.125rem">
							<div style="--weight:500">{$i18n.t('Manage Tool Servers')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									aria-label={$i18n.t(`Add Connection`)}
									style="--px:0.25rem"
									on:click={() => {
										showConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div style="--d:flex; --fd:column; --g:0.375rem">
							{#each servers as server, idx}
								<Connection
									bind:connection={server}
									direct
									onSubmit={() => {
										updateHandler();
									}}
									onDelete={() => {
										servers = servers.filter((_, i) => i !== idx);
										updateHandler();
									}}
								/>
							{/each}
						</div>
					</div>

					<div style="--my:0.375rem">
						<div
							class={`text-xs 
								${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
						>
							{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
							<br />
							{$i18n.t(
								'CORS must be properly configured by the provider to allow requests from Sage.is AI.'
							)}
						</div>
					</div>

					<div style="--size:0.6rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); --mb:0.5rem">
						<a
							style="--td:underline"
							href="https://github.com/open-webui/openapi-servers"
							target="_blank">{$i18n.t('Learn more about OpenAPI tool servers.')}</a
						>
					</div>
				</div>
			</div>
		{:else}
			<div style="--d:flex; --h:100%; --jc:center">
				<div style="--my:auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.875rem; --weight:500">
		<button
			style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
