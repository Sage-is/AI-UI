<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { getModels as _getModels } from '$lib/apis';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Connections/Connection.svelte';

	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';

	export let saveSettings: Function;

	let config = null;

	let showConnectionModal = false;

	const addConnectionHandler = async (connection) => {
		config.OPENAI_API_BASE_URLS.push(connection.url);
		config.OPENAI_API_KEYS.push(connection.key);
		config.OPENAI_API_CONFIGS[config.OPENAI_API_BASE_URLS.length - 1] = connection.config;

		await updateHandler();
	};

	const updateHandler = async () => {
		// Remove trailing slashes
		config.OPENAI_API_BASE_URLS = config.OPENAI_API_BASE_URLS.map((url) => url.replace(/\/$/, ''));

		// Check if API KEYS length is same than API URLS length
		if (config.OPENAI_API_KEYS.length !== config.OPENAI_API_BASE_URLS.length) {
			// if there are more keys than urls, remove the extra keys
			if (config.OPENAI_API_KEYS.length > config.OPENAI_API_BASE_URLS.length) {
				config.OPENAI_API_KEYS = config.OPENAI_API_KEYS.slice(
					0,
					config.OPENAI_API_BASE_URLS.length
				);
			}

			// if there are more urls than keys, add empty keys
			if (config.OPENAI_API_KEYS.length < config.OPENAI_API_BASE_URLS.length) {
				const diff = config.OPENAI_API_BASE_URLS.length - config.OPENAI_API_KEYS.length;
				for (let i = 0; i < diff; i++) {
					config.OPENAI_API_KEYS.push('');
				}
			}
		}

		await saveSettings({
			directConnections: config
		});
	};

	onMount(async () => {
		config = $settings?.directConnections ?? {
			OPENAI_API_BASE_URLS: [],
			OPENAI_API_KEYS: [],
			OPENAI_API_CONFIGS: {}
		};
	});
</script>

<AddConnectionModal direct bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<form
	id="tab-connections"
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.8rem"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div style="--ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if config !== null}
			<div class="">
				<div style="--pr:0.4rem">
					<div class="">
						<div style="--d:flex; --jc:space-between; --ai:center; --mb:0.125rem">
							<div style="--weight:500">{$i18n.t('Manage Direct Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									style="--px:0.2rem"
									on:click={() => {
										showConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div style="--d:flex; --fd:column; --g:0.4rem">
							{#each config?.OPENAI_API_BASE_URLS ?? [] as url, idx}
								<Connection
									bind:url
									bind:key={config.OPENAI_API_KEYS[idx]}
									bind:config={config.OPENAI_API_CONFIGS[idx]}
									onSubmit={() => {
										updateHandler();
									}}
									onDelete={() => {
										config.OPENAI_API_BASE_URLS = config.OPENAI_API_BASE_URLS.filter(
											(url, urlIdx) => idx !== urlIdx
										);
										config.OPENAI_API_KEYS = config.OPENAI_API_KEYS.filter(
											(key, keyIdx) => idx !== keyIdx
										);

										let newConfig = {};
										config.OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
											newConfig[newIdx] =
												config.OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
										});
										config.OPENAI_API_CONFIGS = newConfig;
									}}
								/>
							{/each}
						</div>
					</div>

					<div style="--my:0.4rem">
						<div
							style="--size:0.6rem"
	class="{($settings?.highContrastMode ?? false)
								? 'text-gray-800 dark:text-gray-100'
								: 'text-gray-500'}"
						>
							{$i18n.t('Connect to your own OpenAI compatible API endpoints.')}
							<br />
							{$i18n.t(
								'CORS must be properly configured by the provider to allow requests from Sage.is AI.'
							)}
						</div>
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

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
		<button
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
