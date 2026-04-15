<script lang="ts">
	console.log('[Tools] Component being rendered - THIS IS THE TOOLS COMPONENT!');
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { getModels as _getModels } from '$lib/apis';
	import Icon from '$lib/components/Icon.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
		import Connection from '$lib/components/chat/Settings/Tools/Connection.svelte';

	import AddServerModal from '$lib/components/AddServerModal.svelte';
	import { getToolServerConnections, setToolServerConnections } from '$lib/apis/configs';

	let servers = null;
	let showConnectionModal = false;

	const addConnectionHandler = async (server) => {
		servers = [...servers, server];
		await updateHandler();
	};

	const updateHandler = async () => {
		const res = await setToolServerConnections(localStorage.token, {
			TOOL_SERVER_CONNECTIONS: servers
		}).catch((err) => {
			toast.error($i18n.t('Failed to save connections'));

			return null;
		});

		if (res) {
			toast.success($i18n.t('Connections saved successfully'));
		}
	};

	onMount(async () => {
		const res = await getToolServerConnections(localStorage.token);
		servers = res.TOOL_SERVER_CONNECTIONS;
	});
</script>

<AddServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.8rem"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div style="--ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if servers !== null}
			<div class="">
				<div style="--mb:0.6rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('General')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem; --d:flex; --fd:column; --w:100%; --jc:space-between">
						<!-- {$i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, {
							URL: 'server?.url'
						})} -->
						<div style="--d:flex; --jc:space-between; --ai:center; --mb:0.125rem">
							<div style="--weight:500">{$i18n.t('Manage Tool Servers')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									style="--px:0.2rem"
									on:click={() => {
										showConnectionModal = true;
									}}
									type="button"
								>
									<Icon name="plus" strokeWidth="2" />
								</button>
							</Tooltip>
						</div>

						<div style="--d:flex; --fd:column; --g:0.4rem">
							{#each servers as server, idx}
								<Connection
									bind:connection={server}
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

						<div style="--my:0.4rem">
							<div style="--size:0.6rem; --c:var(--color-gray-500)">
								{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
							</div>
						</div>
					</div>

					<!-- <div style="--mb:0.625rem; --d:flex; --w:100%; --jc:space-between">
						<div style="--size:0.6rem; --weight:500">{$i18n.t('Arena Models')}</div>

						<Tooltip content={$i18n.t(`Message rating should be enabled to use this feature`)}>
							<Switch bind:state={evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS} />
						</Tooltip>
					</div> -->
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

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
		<button
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
