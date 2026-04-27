<script>
	console.log('[Settings] Component script loaded!');
	import { getContext, tick, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { config } from '$lib/stores';
	import { getBackendConfig } from '$lib/apis';
	import Database from './Settings/Database.svelte';
	import Theme from './Settings/Theme.svelte';

	import General from './Settings/General.svelte';
	import Pipelines from './Settings/Pipelines.svelte';
	import Audio from './Settings/Audio.svelte';
	import Images from './Settings/Images.svelte';
	import Interface from './Settings/Interface.svelte';
	import Models from './Settings/Models.svelte';
	import Connections from './Settings/Connections.svelte';
	import Documents from './Settings/Documents.svelte';

	import Evaluations from './Settings/Evaluations.svelte';
	import CodeExecution from './Settings/CodeExecution.svelte';
	import Tools from './Settings/Tools.svelte';
	import Bridges from './Settings/Bridges.svelte';
	import OAuthSettings from './Settings/OAuthSettings.svelte';
	import TrialMode from './Settings/TrialMode.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	let selectedTab = 'general';

	// Get current tab from URL pathname, default to 'general'
	$: {
		const pathParts = $page.url.pathname.split('/');
		const tabFromPath = pathParts[pathParts.length - 1];
		console.log('[Settings] URL pathname:', $page.url.pathname);
		console.log('[Settings] Path parts:', pathParts);
		console.log('[Settings] Tab from path:', tabFromPath);

		selectedTab = [
			'general',
			'auth',
			'theme',
			'connections',
			'models',
			'evaluations',
			'tools',
			'documents',
			'documents',
			'code-execution',
			'interface',
			'audio',
			'images',
			'pipelines',
			'bridges',
			'db',
			'trial-mode'
		].includes(tabFromPath)
			? tabFromPath
			: 'general';

		console.log('[Settings] Selected tab:', selectedTab);
	}

	$: if (selectedTab) {
		// scroll to selectedTab
		scrollToTab(selectedTab);
	}

	const scrollToTab = (tabId) => {
		const tabElement = document.getElementById(tabId);
		if (tabElement) {
			tabElement.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
		}
	};

	onMount(() => {
		console.log('[Settings] onMount called!');
		console.log('[Settings] Current selectedTab:', selectedTab);
		console.log('[Settings] Current page URL:', $page.url.pathname);

		const containerElement = document.getElementById('admin-settings-tabs-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}

		// Scroll to the selected tab on mount
		scrollToTab(selectedTab);
	});
</script>

<div style="--d:flex; --fd:column; --fd-lg:row; --w:100%; --h:100%;  --g-lg:1rem">
	<div
		id="admin-settings-tabs-container"
		style="--d:flex; --fd:row; --ofx:auto; --g:0.625rem; --maxw:100%; --g-lg:0.2rem; --fd-lg:column; --fx-lg:none; --w-lg:10rem; --dark-c:var(--color-gray-200); --size:0.8rem; --weight:500; --ta:left"
	class="tabs scrollbar-none"
	>
		<button
			id="general"
			style="{selectedTab === 'general' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/general');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="settings-gear-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('General')}</div>
		</button>

		<button
			id="auth"
			style="{selectedTab === 'auth' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/auth');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<!-- Shield/lock icon -->
				<Icon name="shield-lock-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Auth')} (Beta)</div>
		</button>

		<button
			id="theme"
			style="{selectedTab === 'theme' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/theme');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="circle-target-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Theme')}  (Beta)</div>
		</button>

		<button
			id="connections"
			style="{selectedTab === 'connections' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/connections');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="cloud-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Connections')}</div>
		</button>

		<button
			id="models"
			style="{selectedTab === 'models' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/models');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="database-fill-20" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Models')}</div>
		</button>

		<button
			id="evaluations"
			style="{selectedTab === 'evaluations' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/evaluations');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="document-chart-bar" />
			</div>
			<div style="--as:center">{$i18n.t('Evaluations')}</div>
		</button>

		<button
			id="tools"
			style="{selectedTab === 'tools' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/tools');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="wrench-solid" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Tools')}</div>
		</button>

		<button
			id="documents"
			style="{selectedTab === 'documents' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/documents');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="search-doc-fill-24" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Documents')}</div>
		</button>

		<button
			id="code-execution"
			style="{selectedTab === 'code-execution' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/code-execution');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="code-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Code Execution')}</div>
		</button>

		<button
			id="interface"
			style="{selectedTab === 'interface' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/interface');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="monitor-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Interface')}</div>
		</button>

		<button
			id="audio"
			style="{selectedTab === 'audio' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/audio');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="settingsmodal-icon-abc849" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Audio')}</div>
		</button>

		<button
			id="images"
			style="{selectedTab === 'images' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/images');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="code-fill-16-ac49" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Images')}</div>
		</button>

		<button
			id="pipelines"
			style="{selectedTab === 'pipelines' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/pipelines');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="pyramid-fill-24" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Pipelines')}</div>
		</button>

		<button
			id="bridges"
			style="{selectedTab === 'bridges' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/bridges');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 495 390"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path d="M495,237.199v-30H383.75v-86.075c24.992,31.105,63.335,51.048,106.25,51.048v-30c-58.586,0-106.25-47.664-106.25-106.25h-30c0,58.586-47.664,106.25-106.25,106.25S141.25,94.509,141.25,35.923h-30c0,58.586-47.664,106.25-106.25,106.25v30c42.915,0,81.258-19.943,106.25-51.048v86.075H0v30h111.25v100.101c-10.643,2.41-17.7,7.139-23.697,11.178c-6.839,4.607-11.356,7.651-21.931,7.651c-10.574,0-15.092-3.043-21.93-7.651C35.247,342.79,24.737,335.708,5,335.708v30c10.574,0,15.092,3.043,21.93,7.651c8.445,5.689,18.955,12.771,38.692,12.771s30.248-7.081,38.693-12.771c6.839-4.607,11.357-7.651,21.932-7.651s15.092,3.044,21.931,7.651c8.445,5.689,18.955,12.771,38.692,12.771s30.247-7.081,38.692-12.771c6.838-4.607,11.355-7.651,21.929-7.651c10.575,0,15.093,3.044,21.932,7.651c8.445,5.689,18.956,12.771,38.693,12.771c19.738,0,30.249-7.081,38.694-12.771c6.839-4.607,11.357-7.651,21.932-7.651c10.576,0,15.095,3.044,21.934,7.651c8.445,5.689,18.957,12.77,38.695,12.77s30.25-7.081,38.695-12.77c6.839-4.607,11.358-7.651,21.934-7.651v-30c-19.738,0-30.25,7.081-38.695,12.77c-6.839,4.607-11.358,7.651-21.934,7.651s-15.095-3.044-21.934-7.651c-5.995-4.039-13.049-8.765-23.687-11.176V237.199H495z M353.75,121.125v86.075H262.5v-35.852C299.285,167.3,331.71,148.555,353.75,121.125z M141.25,121.125c22.04,27.431,54.465,46.176,91.25,50.222v35.852h-91.25V121.125z M353.75,337.3c-10.646,2.409-17.704,7.139-23.702,11.179c-6.839,4.607-11.357,7.651-21.932,7.651c-10.575,0-15.092-3.043-21.931-7.651c-8.445-5.689-18.956-12.771-38.693-12.771c-19.737,0-30.247,7.081-38.692,12.771c-6.838,4.607-11.355,7.651-21.93,7.651s-15.092-3.043-21.93-7.651c-5.995-4.039-13.051-8.767-23.69-11.177V237.199h212.5V337.3z" />
				</svg>
			</div>
			<div style="--as:center">{$i18n.t('Bridges')}</div>
		</button>

		<button
			id="db"
			style="{selectedTab === 'db' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/db');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<Icon name="data-stack-fill-16" className="size-4" />
			</div>
			<div style="--as:center">{$i18n.t('Database')}</div>
		</button>

		<!-- WHY this tab is gated on enable_try_sage: in non-trial deploys
		     the panel has nothing to show — the limits/llm-status endpoints
		     404, the readouts would be empty, and the "Reopen setup wizard"
		     button is redundant with the changelog flow. -->
		{#if $config?.features?.enable_try_sage}
			<button
				id="trial-mode"
				style="{selectedTab === 'trial-mode' ? 'font-weight: 600;' : ''}"
				on:click={() => {
					goto('/admin/settings/trial-mode');
				}}
			>
				<div style="--as:center; --mr:0.5rem">
					<Icon name="settings-gear-fill-16" className="size-4" />
				</div>
				<div style="--as:center">{$i18n.t('Trial Mode')}</div>
			</button>
		{/if}
	</div>

	<div style="--fx:1 1 0%; --mt:0.6rem; --mt-lg:0; --ofy:scroll; --pr:0.2rem"
	class="scrollbar-hidden">
		{#if selectedTab === 'general'}
			<General
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'auth'}
			<OAuthSettings />
		{:else if selectedTab === 'theme'}
			<Theme
				on:save={async () => {
					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'connections'}
			<Connections
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'models'}
			<Models />
		{:else if selectedTab === 'evaluations'}
			<Evaluations />
		{:else if selectedTab === 'tools'}
			<Tools />
		{:else if selectedTab === 'documents'}
			<Documents
				on:save={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'code-execution'}
			<CodeExecution
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'interface'}
			<Interface
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'audio'}
			<Audio
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'images'}
			<Images
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'bridges'}
			<Bridges />
		{:else if selectedTab === 'db'}
			<Database
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'trial-mode' && $config?.features?.enable_try_sage}
			<TrialMode />
		{:else if selectedTab === 'pipelines'}
			<Pipelines
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{/if}
	</div>
</div>

<style>
	button {
		padding: 0.6em 0.6em;
	}
</style>