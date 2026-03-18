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
	
	import ChartBar from '../icons/ChartBar.svelte';
	import DocumentChartBar from '../icons/DocumentChartBar.svelte';
	import Evaluations from './Settings/Evaluations.svelte';
	import CodeExecution from './Settings/CodeExecution.svelte';
	import Tools from './Settings/Tools.svelte';
	import Bridges from './Settings/Bridges.svelte';

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
			'db'
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						fill-rule="evenodd"
						d="M6.955 1.45A.5.5 0 0 1 7.452 1h1.096a.5.5 0 0 1 .497.45l.17 1.699c.484.12.94.312 1.356.562l1.321-1.081a.5.5 0 0 1 .67.033l.774.775a.5.5 0 0 1 .034.67l-1.08 1.32c.25.417.44.873.561 1.357l1.699.17a.5.5 0 0 1 .45.497v1.096a.5.5 0 0 1-.45.497l-1.699.17c-.12.484-.312.94-.562 1.356l1.082 1.322a.5.5 0 0 1-.034.67l-.774.774a.5.5 0 0 1-.67.033l-1.322-1.08c-.416.25-.872.44-1.356.561l-.17 1.699a.5.5 0 0 1-.497.45H7.452a.5.5 0 0 1-.497-.45l-.17-1.699a4.973 4.973 0 0 1-1.356-.562L4.108 13.37a.5.5 0 0 1-.67-.033l-.774-.775a.5.5 0 0 1-.034-.67l1.08-1.32a4.971 4.971 0 0 1-.561-1.357l-1.699-.17A.5.5 0 0 1 1 8.548V7.452a.5.5 0 0 1 .45-.497l1.699-.17c.12-.484.312-.94.562-1.356L2.629 4.107a.5.5 0 0 1 .034-.67l.774-.774a.5.5 0 0 1 .67-.033L5.43 3.71a4.97 4.97 0 0 1 1.356-.561l.17-1.699ZM6 8c0 .538.212 1.026.558 1.385l.057.057a2 2 0 0 0 2.828-2.828l-.058-.056A2 2 0 0 0 6 8Z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div style="--as:center">{$i18n.t('General')}</div>
		</button>

		<button
			id="theme"
			style="{selectedTab === 'theme' ? 'font-weight: 600;' : ''}"
			on:click={() => {
				goto('/admin/settings/theme');
			}}
		>
			<div style="--as:center; --mr:0.5rem">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM4.5 7.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3ZM7 8a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM9.5 5.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3ZM12 8a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						d="M1 9.5A3.5 3.5 0 0 0 4.5 13H12a3 3 0 0 0 .917-5.857 2.503 2.503 0 0 0-3.198-3.019 3.5 3.5 0 0 0-6.628 2.171A3.5 3.5 0 0 0 1 9.5Z"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						fill-rule="evenodd"
						d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z"
						clip-rule="evenodd"
					/>
				</svg>
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
				<DocumentChartBar />
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						fill-rule="evenodd"
						d="M12 6.75a5.25 5.25 0 0 1 6.775-5.025.75.75 0 0 1 .313 1.248l-3.32 3.319c.063.475.276.934.641 1.299.365.365.824.578 1.3.64l3.318-3.319a.75.75 0 0 1 1.248.313 5.25 5.25 0 0 1-5.472 6.756c-1.018-.086-1.87.1-2.309.634L7.344 21.3A3.298 3.298 0 1 1 2.7 16.657l8.684-7.151c.533-.44.72-1.291.634-2.309A5.342 5.342 0 0 1 12 6.75ZM4.117 19.125a.75.75 0 0 1 .75-.75h.008a.75.75 0 0 1 .75.75v.008a.75.75 0 0 1-.75.75h-.008a.75.75 0 0 1-.75-.75v-.008Z"
						clip-rule="evenodd"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path d="M11.625 16.5a1.875 1.875 0 1 0 0-3.75 1.875 1.875 0 0 0 0 3.75Z" />
					<path
						fill-rule="evenodd"
						d="M5.625 1.5H9a3.75 3.75 0 0 1 3.75 3.75v1.875c0 1.036.84 1.875 1.875 1.875H16.5a3.75 3.75 0 0 1 3.75 3.75v7.875c0 1.035-.84 1.875-1.875 1.875H5.625a1.875 1.875 0 0 1-1.875-1.875V3.375c0-1.036.84-1.875 1.875-1.875Zm6 16.5c.66 0 1.277-.19 1.797-.518l1.048 1.048a.75.75 0 0 0 1.06-1.06l-1.047-1.048A3.375 3.375 0 1 0 11.625 18Z"
						clip-rule="evenodd"
					/>
					<path
						d="M14.25 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 16.5 7.5h-1.875a.375.375 0 0 1-.375-.375V5.25Z"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						fill-rule="evenodd"
						d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm2.22 1.97a.75.75 0 0 0 0 1.06l.97.97-.97.97a.75.75 0 1 0 1.06 1.06l1.5-1.5a.75.75 0 0 0 0-1.06l-1.5-1.5a.75.75 0 0 0-1.06 0ZM8.75 8.5a.75.75 0 0 0 0 1.5h2.5a.75.75 0 0 0 0-1.5h-2.5Z"
						clip-rule="evenodd"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						fill-rule="evenodd"
						d="M2 4.25A2.25 2.25 0 0 1 4.25 2h7.5A2.25 2.25 0 0 1 14 4.25v5.5A2.25 2.25 0 0 1 11.75 12h-1.312c.1.128.21.248.328.36a.75.75 0 0 1 .234.545v.345a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1-.75-.75v-.345a.75.75 0 0 1 .234-.545c.118-.111.228-.232.328-.36H4.25A2.25 2.25 0 0 1 2 9.75v-5.5Zm2.25-.75a.75.75 0 0 0-.75.75v4.5c0 .414.336.75.75.75h7.5a.75.75 0 0 0 .75-.75v-4.5a.75.75 0 0 0-.75-.75h-7.5Z"
						clip-rule="evenodd"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						d="M7.557 2.066A.75.75 0 0 1 8 2.75v10.5a.75.75 0 0 1-1.248.56L3.59 11H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h1.59l3.162-2.81a.75.75 0 0 1 .805-.124ZM12.95 3.05a.75.75 0 1 0-1.06 1.06 5.5 5.5 0 0 1 0 7.78.75.75 0 1 0 1.06 1.06 7 7 0 0 0 0-9.9Z"
					/>
					<path
						d="M10.828 5.172a.75.75 0 1 0-1.06 1.06 2.5 2.5 0 0 1 0 3.536.75.75 0 1 0 1.06 1.06 4 4 0 0 0 0-5.656Z"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path
						fill-rule="evenodd"
						d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
						clip-rule="evenodd"
					/>
				</svg>
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:1rem; --h:1rem"
				>
					<path d="M8 7c3.314 0 6-1.343 6-3s-2.686-3-6-3-6 1.343-6 3 2.686 3 6 3Z" />
					<path
						d="M8 8.5c1.84 0 3.579-.37 4.914-1.037A6.33 6.33 0 0 0 14 6.78V8c0 1.657-2.686 3-6 3S2 9.657 2 8V6.78c.346.273.72.5 1.087.683C4.42 8.131 6.16 8.5 8 8.5Z"
					/>
					<path
						d="M8 12.5c1.84 0 3.579-.37 4.914-1.037.366-.183.74-.41 1.086-.684V12c0 1.657-2.686 3-6 3s-6-1.343-6-3v-1.22c.346.273.72.5 1.087.683C4.42 12.131 6.16 12.5 8 12.5Z"
					/>
				</svg>
			</div>
			<div style="--as:center">{$i18n.t('Database')}</div>
		</button>
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