<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tags from './common/Tags.svelte';
	import { getToolServerData } from '$lib/apis';
	import { verifyToolServerConnection } from '$lib/apis/configs';
	import AccessControl from './workshop/common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let direct = false;
	export let connection = null;

	let url = '';
	let path = 'openapi.json';

	let auth_type = 'bearer';
	let key = '';

	let accessControl = {};

	let name = '';
	let description = '';

	let enable = true;

	let loading = false;

	const verifyHandler = async () => {
		if (url === '') {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		if (path === '') {
			toast.error($i18n.t('Please enter a valid path'));
			return;
		}

		if (direct) {
			const res = await getToolServerData(
				auth_type === 'bearer' ? key : localStorage.token,
				path.includes('://') ? path : `${url}${path.startsWith('/') ? '' : '/'}${path}`
			).catch((err) => {
				toast.error($i18n.t('Connection failed'));
			});

			if (res) {
				toast.success($i18n.t('Connection successful'));
				console.debug('Connection successful', res);
			}
		} else {
			const res = await verifyToolServerConnection(localStorage.token, {
				url,
				path,
				auth_type,
				key,
				config: {
					enable: enable,
					access_control: accessControl
				},
				info: {
					name,
					description
				}
			}).catch((err) => {
				toast.error($i18n.t('Connection failed'));
			});

			if (res) {
				toast.success($i18n.t('Connection successful'));
				console.debug('Connection successful', res);
			}
		}
	};

	const submitHandler = async () => {
		loading = true;

		// remove trailing slash from url
		url = url.replace(/\/$/, '');

		const connection = {
			url,
			path,
			auth_type,
			key,
			config: {
				enable: enable,
				access_control: accessControl
			},
			info: {
				name: name,
				description: description
			}
		};

		await onSubmit(connection);

		loading = false;
		show = false;

		url = '';
		path = 'openapi.json';
		key = '';
		auth_type = 'bearer';

		name = '';
		description = '';

		enable = true;
		accessControl = null;
	};

	const init = () => {
		if (connection) {
			url = connection.url;
			path = connection?.path ?? 'openapi.json';

			auth_type = connection?.auth_type ?? 'bearer';
			key = connection?.key ?? '';

			name = connection.info?.name ?? '';
			description = connection.info?.description ?? '';

			enable = connection.config?.enable ?? true;
			accessControl = connection.config?.access_control ?? null;
		}
	};

	$: if (show) {
		init();
	}

	onMount(() => {
		init();
	});
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<h1 style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{#if edit}
					{$i18n.t('Edit Connection')}
				{:else}
					{$i18n.t('Add Connection')}
				{/if}
			</h1>
			<button
				style="--as:center"
				aria-label={$i18n.t('Close Configure Connection Modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div style="--px:0.25rem">
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--d:flex; --jc:space-between; --mb:0.125rem">
									<label
										for="api-base-url"
										class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('URL')}</label
									>
								</div>

								<div style="--d:flex; --fx:1 1 0%; --ai:center">
									<input
										id="api-base-url"
										class={`w-full flex-1 text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={url}
										placeholder={$i18n.t('API Base URL')}
										autocomplete="off"
										required
									/>

									<Tooltip
										content={$i18n.t('Verify Connection')}
										className="shrink-0 flex items-center mr-1"
									>
										<button
											style="--as:center; --p:0.25rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												verifyHandler();
											}}
											aria-label={$i18n.t('Verify Connection')}
											type="button"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												style="--w:1rem; --h:1rem"
												aria-hidden="true"
											>
												<path
													fill-rule="evenodd"
													d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
													clip-rule="evenodd"
												/>
											</svg>
										</button>
									</Tooltip>

									<Tooltip content={enable ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
										<Switch bind:state={enable} />
									</Tooltip>
								</div>

								<div style="--fx:1 1 0%; --d:flex; --ai:center">
									<label for="url-or-path" class="sr-only"
										>{$i18n.t('openapi.json URL or Path')}</label
									>
									<input
										class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										id="url-or-path"
										bind:value={path}
										placeholder={$i18n.t('openapi.json URL or Path')}
										autocomplete="off"
										required
									/>
								</div>
							</div>
						</div>

						<div
							class={`text-xs mt-1 ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
						>
							{$i18n.t(`WebUI will make requests to "{{url}}"`, {
								url: path.includes('://') ? path : `${url}${path.startsWith('/') ? '' : '/'}${path}`
							})}
						</div>

						<div style="--d:flex; --g:0.5rem; --mt:0.5rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<label
									for="select-bearer-or-session"
									class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
									>{$i18n.t('Auth')}</label
								>

								<div style="--d:flex; --g:0.5rem">
									<div style="--as:flex-start"
	class="flex-shrink-0">
										<select
											id="select-bearer-or-session"
											class={`w-full text-sm bg-transparent pr-5 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											bind:value={auth_type}
										>
											<option value="bearer">Bearer</option>
											<option value="session">Session</option>
										</select>
									</div>

									<div style="--d:flex; --fx:1 1 0%; --ai:center">
										{#if auth_type === 'bearer'}
											<SensitiveInput
												bind:value={key}
												placeholder={$i18n.t('API Key')}
												required={false}
											/>
										{:else if auth_type === 'session'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						{#if !direct}
							<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

							<div style="--d:flex; --g:0.5rem">
								<div style="--d:flex; --fd:column; --w:100%">
									<label
										for="enter-name"
										class={`mb-0.5 text-xs" ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('Name')}</label
									>

									<div style="--fx:1 1 0%">
										<input
											id="enter-name"
											class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={name}
											placeholder={$i18n.t('Enter name')}
											autocomplete="off"
											required
										/>
									</div>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%; --mt:0.5rem">
								<label
									for="description"
									class={`mb-1 text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100 placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 text-gray-500'}`}
									>{$i18n.t('Description')}</label
								>

								<div style="--fx:1 1 0%">
									<input
										id="description"
										class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={description}
										placeholder={$i18n.t('Enter description')}
										autocomplete="off"
									/>
								</div>
							</div>

							<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

							<div style="--my:0.5rem; --mx:-0.5rem">
								<div style="--px:0.6rem; --py:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-950); --radius:0.5rem">
									<AccessControl bind:accessControl />
								</div>
							</div>
						{/if}
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.875rem; --weight:500; --g:0.375rem">
						{#if edit}
							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --dark-bgc:#000; --hvr-dark-bgc:var(--color-gray-900); --dark-c:#fff; --bgc:#fff; --c:#000; --hvr-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
								type="button"
								on:click={() => {
									onDelete();
									show = false;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div style="--ml:0.5rem; --as:center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
