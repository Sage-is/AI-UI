<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getModels as _getModels } from '$lib/apis';
	import { getConnectionsConfig, setConnectionsConfig } from '$lib/apis/configs';

	import { config, models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';

	const i18n = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
			false,
			true
		);
		return models;
	};

	// External
	let OLLAMA_BASE_URLS = [''];
	let OLLAMA_API_CONFIGS = {};

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];
	let OPENAI_API_CONFIGS = {};

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;

	let connectionsConfig = null;

	let pipelineUrls = {};
	let showAddOpenAIConnectionModal = false;
	let showAddOllamaConnectionModal = false;

	const updateOpenAIHandler = async () => {
		if (ENABLE_OPENAI_API !== null) {
			// Remove trailing slashes
			OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			// Check if API KEYS length is same than API URLS length
			if (OPENAI_API_KEYS.length !== OPENAI_API_BASE_URLS.length) {
				// if there are more keys than urls, remove the extra keys
				if (OPENAI_API_KEYS.length > OPENAI_API_BASE_URLS.length) {
					OPENAI_API_KEYS = OPENAI_API_KEYS.slice(0, OPENAI_API_BASE_URLS.length);
				}

				// if there are more urls than keys, add empty keys
				if (OPENAI_API_KEYS.length < OPENAI_API_BASE_URLS.length) {
					const diff = OPENAI_API_BASE_URLS.length - OPENAI_API_KEYS.length;
					for (let i = 0; i < diff; i++) {
						OPENAI_API_KEYS.push('');
					}
				}
			}

			const res = await updateOpenAIConfig(localStorage.token, {
				ENABLE_OPENAI_API: ENABLE_OPENAI_API,
				OPENAI_API_BASE_URLS: OPENAI_API_BASE_URLS,
				OPENAI_API_KEYS: OPENAI_API_KEYS,
				OPENAI_API_CONFIGS: OPENAI_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				toast.success($i18n.t('OpenAI Compatible API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateOllamaHandler = async () => {
		if (ENABLE_OLLAMA_API !== null) {
			// Remove trailing slashes
			OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			const res = await updateOllamaConfig(localStorage.token, {
				ENABLE_OLLAMA_API: ENABLE_OLLAMA_API,
				OLLAMA_BASE_URLS: OLLAMA_BASE_URLS,
				OLLAMA_API_CONFIGS: OLLAMA_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				toast.success($i18n.t('Ollama API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateConnectionsHandler = async () => {
		const res = await setConnectionsConfig(localStorage.token, connectionsConfig).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Connections settings updated'));
			await models.set(await getModels());
		}
	};

	const addOpenAIConnectionHandler = async (connection) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key];
		OPENAI_API_CONFIGS[OPENAI_API_BASE_URLS.length - 1] = connection.config;

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[OLLAMA_BASE_URLS.length - 1] = {
			...connection.config,
			key: connection.key
		};

		await updateOllamaHandler();
	};

	onMount(async () => {
		console.log('[Connections] onMount called');
		console.log('[Connections] User role:', $user?.role);
		console.log('[Connections] Is admin?', $user?.role === 'admin');
		
		if ($user?.role === 'admin') {
			console.log('[Connections] Starting admin connections initialization');
			let ollamaConfig = {};
			let openaiConfig = {};

			try {
				console.log('[Connections] About to call Promise.all with 3 API calls...');
				
				await Promise.all([
					(async () => {
						console.log('[Connections] Fetching Ollama config...');
						try {
							ollamaConfig = await getOllamaConfig(localStorage.token);
							console.log('[Connections] Ollama config loaded:', ollamaConfig);
						} catch (err) {
							console.error('[Connections] Ollama config failed:', err);
							throw err;
						}
					})(),
					(async () => {
						console.log('[Connections] Fetching OpenAI config...');
						try {
							openaiConfig = await getOpenAIConfig(localStorage.token);
							console.log('[Connections] OpenAI config loaded:', openaiConfig);
						} catch (err) {
							console.error('[Connections] OpenAI config failed:', err);
							throw err;
						}
					})(),
					(async () => {
						console.log('[Connections] Fetching connections config...');
						try {
							connectionsConfig = await getConnectionsConfig(localStorage.token);
							console.log('[Connections] Connections config loaded:', connectionsConfig);
						} catch (err) {
							console.error('[Connections] Connections config failed:', err);
							throw err;
						}
					})()
				]);

				console.log('[Connections] Promise.all completed successfully');

				ENABLE_OPENAI_API = openaiConfig.ENABLE_OPENAI_API;
				ENABLE_OLLAMA_API = ollamaConfig.ENABLE_OLLAMA_API;

				OPENAI_API_BASE_URLS = openaiConfig.OPENAI_API_BASE_URLS;
				OPENAI_API_KEYS = openaiConfig.OPENAI_API_KEYS;
				OPENAI_API_CONFIGS = openaiConfig.OPENAI_API_CONFIGS;

				OLLAMA_BASE_URLS = ollamaConfig.OLLAMA_BASE_URLS;
				OLLAMA_API_CONFIGS = ollamaConfig.OLLAMA_API_CONFIGS;

				console.log('[Connections] All configs loaded successfully');
				console.log('[Connections] ENABLE_OPENAI_API:', ENABLE_OPENAI_API);
				console.log('[Connections] ENABLE_OLLAMA_API:', ENABLE_OLLAMA_API);
				console.log('[Connections] connectionsConfig:', connectionsConfig);

				if (ENABLE_OPENAI_API) {
					console.log('[Connections] Processing OpenAI connections...');
					// get url and idx
					for (const [idx, url] of OPENAI_API_BASE_URLS.entries()) {
						if (!OPENAI_API_CONFIGS[idx]) {
							// Legacy support, url as key
							OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[url] || {};
						}
					}

					OPENAI_API_BASE_URLS.forEach(async (url, idx) => {
						OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[idx] || {};
						if (!(OPENAI_API_CONFIGS[idx]?.enable ?? true)) {
							return;
						}
						try {
							console.log(`[Connections] Fetching OpenAI models for URL ${idx}: ${url}`);
							const res = await getOpenAIModels(localStorage.token, idx);
							if (res.pipelines) {
								pipelineUrls[url] = true;
							}
							console.log(`[Connections] OpenAI models loaded for URL ${idx}`);
						} catch (error) {
							console.error(`[Connections] Failed to load OpenAI models for URL ${idx}:`, error);
						}
					});
				}

				if (ENABLE_OLLAMA_API) {
					console.log('[Connections] Processing Ollama connections...');
					for (const [idx, url] of OLLAMA_BASE_URLS.entries()) {
						if (!OLLAMA_API_CONFIGS[idx]) {
							OLLAMA_API_CONFIGS[idx] = OLLAMA_API_CONFIGS[url] || {};
						}
					}
				}
				
				console.log('[Connections] Initialization complete - component should render');
			} catch (error) {
				console.error('[Connections] Failed to load admin connections:', error);
				toast.error('Failed to load connections settings: ' + String(error));
				
				// Set fallback values to prevent infinite spinner
				ENABLE_OPENAI_API = false;
				ENABLE_OLLAMA_API = false;
				connectionsConfig = {
					ENABLE_DIRECT_CONNECTIONS: false,
					ENABLE_BASE_MODELS_CACHE: false
				};
				
				console.log('[Connections] Fallback values set - component should render with defaults');
			}
		} else {
			console.log('[Connections] User is not admin, skipping initialization');
		}
	});

	const submitHandler = async () => {
		updateOpenAIHandler();
		updateOllamaHandler();
		updateConnectionsHandler();

		dispatch('save');
	};
</script>

<AddConnectionModal
	bind:show={showAddOpenAIConnectionModal}
	onSubmit={addOpenAIConnectionHandler}
/>

<AddConnectionModal
	ollama
	bind:show={showAddOllamaConnectionModal}
	onSubmit={addOllamaConnectionHandler}
/>

<form style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.875rem" on:submit|preventDefault={submitHandler}>
	<div style="--ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && connectionsConfig !== null}
			<div style="--mb:0.875rem">
				<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Connections')}</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

				<div style="--my:0.5rem">
					<div style="--mt:0.5rem; --g:0.5rem">
						<div style="--d:flex; --jc:space-between; --ai:center; --size:0.875rem">
							<div style="--weight:500">{$i18n.t('OpenAI Compatible API')}</div>

							<div style="--d:flex; --ai:center">
								<div class="">
									<Switch
										bind:state={ENABLE_OPENAI_API}
										on:change={async () => {
											updateOpenAIHandler();
										}}
									/>
								</div>
							</div>
						</div>

						{#if ENABLE_OPENAI_API}
							<div class="">
								<div style="--d:flex; --jc:space-between; --ai:center">
									<div style="--weight:500; --size:0.6rem">{$i18n.t('Manage OpenAI Compatible API Connections')}</div>

									<Tooltip content={$i18n.t(`Add Connection`)}>
										<button
											style="--px:0.25rem"
											on:click={() => {
												showAddOpenAIConnectionModal = true;
											}}
											type="button"
										>
											<Plus />
										</button>
									</Tooltip>
								</div>

								<div style="--d:flex; --fd:column; --g:0.375rem; --mt:0.375rem">
									{#each OPENAI_API_BASE_URLS as url, idx}
										<OpenAIConnection
											pipeline={pipelineUrls[url] ? true : false}
											bind:url
											bind:key={OPENAI_API_KEYS[idx]}
											bind:config={OPENAI_API_CONFIGS[idx]}
											onSubmit={() => {
												updateOpenAIHandler();
											}}
											onDelete={() => {
												OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
													(url, urlIdx) => idx !== urlIdx
												);
												OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);

												let newConfig = {};
												OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] =
														OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OPENAI_API_CONFIGS = newConfig;
												updateOpenAIHandler();
											}}
										/>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>

				<div style="--my:0.5rem">
					<div style="--d:flex; --jc:space-between; --ai:center; --size:0.875rem; --mb:0.5rem">
						<div style="--weight:500">{$i18n.t('Ollama API')}</div>

						<div style="--mt:0.25rem">
							<Switch
								bind:state={ENABLE_OLLAMA_API}
								on:change={async () => {
									updateOllamaHandler();
								}}
							/>
						</div>
					</div>

					{#if ENABLE_OLLAMA_API}
						<div class="">
							<div style="--d:flex; --jc:space-between; --ai:center">
								<div style="--weight:500; --size:0.6rem">{$i18n.t('Manage Ollama API Connections')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										style="--px:0.25rem"
										on:click={() => {
											showAddOllamaConnectionModal = true;
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div style="--d:flex; --w:100%; --g:0.375rem">
								<div style="--fx:1 1 0%; --d:flex; --fd:column; --g:0.375rem; --mt:0.375rem">
									{#each OLLAMA_BASE_URLS as url, idx}
										<OllamaConnection
											bind:url
											bind:config={OLLAMA_API_CONFIGS[idx]}
											{idx}
											onSubmit={() => {
												updateOllamaHandler();
											}}
											onDelete={() => {
												OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);

												let newConfig = {};
												OLLAMA_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] =
														OLLAMA_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OLLAMA_API_CONFIGS = newConfig;
											}}
										/>
									{/each}
								</div>
							</div>

							<div style="--mt:0.25rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
								{$i18n.t('Trouble accessing Ollama?')}
								<a
									style="--c:var(--color-gray-300); --weight:500; --td:underline"
									href="https://github.com/Sage-is/AI-UI#troubleshooting"
									target="_blank"
								>
									{$i18n.t('Click here for help.')}
								</a>
							</div>
						</div>
					{/if}
				</div>

				<div style="--my:0.5rem">
					<div style="--d:flex; --jc:space-between; --ai:center; --size:0.875rem">
						<div style="--weight:500">{$i18n.t('Direct Connections')}</div>

						<div style="--d:flex; --ai:center">
							<div class="">
								<Switch
									bind:state={connectionsConfig.ENABLE_DIRECT_CONNECTIONS}
									on:change={async () => {
										updateConnectionsHandler();
									}}
								/>
							</div>
						</div>
					</div>

					<div style="--mt:0.25rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
						{$i18n.t(
							'Direct Connections allow users to connect to their own OpenAI compatible API endpoints.'
						)}
					</div>
				</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

				<div style="--my:0.5rem">
					<div style="--d:flex; --jc:space-between; --ai:center; --size:0.875rem">
						<div style="--size:0.6rem; --weight:500">{$i18n.t('Cache Base Model List')}</div>

						<div style="--d:flex; --ai:center">
							<div class="">
								<Switch
									bind:state={connectionsConfig.ENABLE_BASE_MODELS_CACHE}
									on:change={async () => {
										updateConnectionsHandler();
									}}
								/>
							</div>
						</div>
					</div>

					<div style="--mt:0.25rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
						{$i18n.t(
							'Base Model List Cache speeds up access by fetching base models only at startup or on settings save—faster, but may not show recent base model changes.'
						)}
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
