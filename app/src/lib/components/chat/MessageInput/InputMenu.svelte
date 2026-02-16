<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, onMount, tick } from 'svelte';

	import { config, user, tools as _tools, mobile } from '$lib/stores';
	import { createPicker } from '$lib/utils/google-drive-picker';

	import { getTools } from '$lib/apis/tools';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import CameraSolid from '$lib/components/icons/CameraSolid.svelte';
	import PhotoSolid from '$lib/components/icons/PhotoSolid.svelte';
	import CommandLineSolid from '$lib/components/icons/CommandLineSolid.svelte';

	const i18n = getContext('i18n');

	export let selectedToolIds: string[] = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let screenCaptureHandler: Function;
	export let uploadFilesHandler: Function;
	export let inputFilesHandler: Function;

	export let uploadGoogleDriveHandler: Function;
	export let uploadOneDriveHandler: Function;

	export let onClose: Function;

	let tools = {};
	let show = false;
	let showAllTools = false;

	$: if (show) {
		init();
	}

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	const init = async () => {
		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}

		tools = $_tools.reduce((a, tool, i, arr) => {
			a[tool.id] = {
				name: tool.name,
				description: tool.meta.description,
				enabled: selectedToolIds.includes(tool.id)
			};
			return a;
		}, {});
	};

	const detectMobile = () => {
		const userAgent = navigator.userAgent || navigator.vendor || window.opera;
		return /android|iphone|ipad|ipod|windows phone/i.test(userAgent);
	};

	function handleFileChange(event) {
		const inputFiles = Array.from(event.target?.files);
		if (inputFiles && inputFiles.length > 0) {
			console.log(inputFiles);
			inputFilesHandler(inputFiles);
		}
	}
</script>

<!-- Hidden file input used to open the camera on mobile -->
<input
	id="camera-input"
	type="file"
	accept="image/*"
	capture="environment"
	on:change={handleFileChange}
	style="display: none;"
/>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:200px; --radius:0.75rem; --px:0.25rem; --py:0.25rem; --b:1px solid; --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --shadow:1"
			sideOffset={10}
			alignOffset={-8}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			{#if Object.keys(tools).length > 0}
				<div style="--ofy:auto"
	class="{showAllTools ? '' : 'max-h-28'} scrollbar-thin">
					{#each Object.keys(tools) as toolId}
						<button
							style="--d:flex; --w:100%; --jc:space-between; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --radius:0.75rem"
							on:click={() => {
								tools[toolId].enabled = !tools[toolId].enabled;
							}}
						>
							<div style="--fx:1 1 0%; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
								<Tooltip
									content={tools[toolId]?.description ?? ''}
									placement="top-start"
									className="flex flex-1 gap-2 items-center"
								>
									<div style="--fs:0">
										<WrenchSolid />
									</div>

									<div style="overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{tools[toolId].name}</div>
								</Tooltip>
							</div>

							<div style="--fs:0">
								<Switch
									state={tools[toolId].enabled}
									on:change={async (e) => {
										const state = e.detail;
										await tick();
										if (state) {
											selectedToolIds = [...selectedToolIds, toolId];
										} else {
											selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
										}
									}}
								/>
							</div>
						</button>
					{/each}
				</div>
				{#if Object.keys(tools).length > 3}
					<button
						style="--d:flex; --w:100%; --jc:center; --ai:center; --size:0.875rem; --weight:500; --cur:pointer; --radius:0.5rem; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333)"
						on:click={() => {
							showAllTools = !showAllTools;
						}}
						title={showAllTools ? $i18n.t('Show Less') : $i18n.t('Show All')}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2.5"
							stroke="currentColor"
							style="--w:0.75rem; --h:0.75rem; --tn:transform 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:200ms; --c:var(--color-gray-300, #cdcdcd); --dark-c:var(--color-gray-600, #676767)"
	class="{showAllTools
								? 'rotate-180'
								: ''}"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5"
							></path>
						</svg>
					</button>
				{/if}
				<hr style="--bc:rgb(0 0 0 / 0.05); --dark-bc:rgb(255 255 255 / 0.05); --my:0.25rem" />
			{/if}

			<Tooltip
				content={fileUploadCapableModels.length !== selectedModels.length
					? $i18n.t('Model(s) do not support file upload')
					: !fileUploadEnabled
						? $i18n.t('You do not have permission to upload files.')
						: ''}
				className="w-full"
			>
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.75rem"
	class="{!fileUploadEnabled
						? 'opacity-50'
						: ''}"
					on:click={() => {
						if (fileUploadEnabled) {
							if (!detectMobile()) {
								screenCaptureHandler();
							} else {
								const cameraInputElement = document.getElementById('camera-input');

								if (cameraInputElement) {
									cameraInputElement.click();
								}
							}
						}
					}}
				>
					<CameraSolid />
					<div style="--line-clamp:1">{$i18n.t('Capture')}</div>
				</DropdownMenu.Item>
			</Tooltip>

			<Tooltip
				content={fileUploadCapableModels.length !== selectedModels.length
					? $i18n.t('Model(s) do not support file upload')
					: !fileUploadEnabled
						? $i18n.t('You do not have permission to upload files.')
						: ''}
				className="w-full"
			>
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.75rem"
	class="{!fileUploadEnabled
						? 'opacity-50'
						: ''}"
					on:click={() => {
						if (fileUploadEnabled) {
							uploadFilesHandler();
						}
					}}
				>
					<DocumentArrowUpSolid />
					<div style="--line-clamp:1">{$i18n.t('Upload Files')}</div>
				</DropdownMenu.Item>
			</Tooltip>

			{#if fileUploadEnabled}
				{#if $config?.features?.enable_google_drive_integration}
					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.75rem"
						on:click={() => {
							uploadGoogleDriveHandler();
						}}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 87.3 78" style="--w:1.25rem; --h:1.25rem">
							<path
								d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z"
								fill="#0066da"
							/>
							<path
								d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z"
								fill="#00ac47"
							/>
							<path
								d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z"
								fill="#ea4335"
							/>
							<path
								d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z"
								fill="#00832d"
							/>
							<path
								d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z"
								fill="#2684fc"
							/>
							<path
								d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z"
								fill="#ffba00"
							/>
						</svg>
						<div style="--line-clamp:1">{$i18n.t('Google Drive')}</div>
					</DropdownMenu.Item>
				{/if}

				{#if $config?.features?.enable_onedrive_integration}
					<DropdownMenu.Sub>
						<DropdownMenu.SubTrigger
							style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.75rem; --w:100%"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 32 32"
								style="--w:1.25rem; --h:1.25rem"
								fill="none"
							>
								<mask
									id="mask0_87_7796"
									style="mask-type:alpha"
									maskUnits="userSpaceOnUse"
									x="0"
									y="6"
									width="32"
									height="20"
								>
									<path
										d="M7.82979 26C3.50549 26 0 22.5675 0 18.3333C0 14.1921 3.35322 10.8179 7.54613 10.6716C9.27535 7.87166 12.4144 6 16 6C20.6308 6 24.5169 9.12183 25.5829 13.3335C29.1316 13.3603 32 16.1855 32 19.6667C32 23.0527 29 26 25.8723 25.9914L7.82979 26Z"
										fill="#C4C4C4"
									/>
								</mask>
								<g mask="url(#mask0_87_7796)">
									<path
										d="M7.83017 26.0001C5.37824 26.0001 3.18957 24.8966 1.75391 23.1691L18.0429 16.3335L30.7089 23.4647C29.5926 24.9211 27.9066 26.0001 26.0004 25.9915C23.1254 26.0001 12.0629 26.0001 7.83017 26.0001Z"
										fill="url(#paint0_linear_87_7796)"
									/>
									<path
										d="M25.5785 13.3149L18.043 16.3334L30.709 23.4647C31.5199 22.4065 32.0004 21.0916 32.0004 19.6669C32.0004 16.1857 29.1321 13.3605 25.5833 13.3337C25.5817 13.3274 25.5801 13.3212 25.5785 13.3149Z"
										fill="url(#paint1_linear_87_7796)"
									/>
									<path
										d="M7.06445 10.7028L18.0423 16.3333L25.5779 13.3148C24.5051 9.11261 20.6237 6 15.9997 6C12.4141 6 9.27508 7.87166 7.54586 10.6716C7.3841 10.6773 7.22358 10.6877 7.06445 10.7028Z"
										fill="url(#paint2_linear_87_7796)"
									/>
									<path
										d="M1.7535 23.1687L18.0425 16.3331L7.06471 10.7026C3.09947 11.0792 0 14.3517 0 18.3331C0 20.1665 0.657197 21.8495 1.7535 23.1687Z"
										fill="url(#paint3_linear_87_7796)"
									/>
								</g>
								<defs>
									<linearGradient
										id="paint0_linear_87_7796"
										x1="4.42591"
										y1="24.6668"
										x2="27.2309"
										y2="23.2764"
										gradientUnits="userSpaceOnUse"
									>
										<stop stop-color="#2086B8" />
										<stop offset="1" stop-color="#46D3F6" />
									</linearGradient>
									<linearGradient
										id="paint1_linear_87_7796"
										x1="23.8302"
										y1="19.6668"
										x2="30.2108"
										y2="15.2082"
										gradientUnits="userSpaceOnUse"
									>
										<stop stop-color="#1694DB" />
										<stop offset="1" stop-color="#62C3FE" />
									</linearGradient>
									<linearGradient
										id="paint2_linear_87_7796"
										x1="8.51037"
										y1="7.33333"
										x2="23.3335"
										y2="15.9348"
										gradientUnits="userSpaceOnUse"
									>
										<stop stop-color="#0D3D78" />
										<stop offset="1" stop-color="#063B83" />
									</linearGradient>
									<linearGradient
										id="paint3_linear_87_7796"
										x1="-0.340429"
										y1="19.9998"
										x2="14.5634"
										y2="14.4649"
										gradientUnits="userSpaceOnUse"
									>
										<stop stop-color="#16589B" />
										<stop offset="1" stop-color="#1464B7" />
									</linearGradient>
								</defs>
							</svg>
							<div style="--line-clamp:1">{$i18n.t('Microsoft OneDrive')}</div>
						</DropdownMenu.SubTrigger>
						<DropdownMenu.SubContent
							style="--w:calc(100vw-2rem); --maxw:280px; --radius:0.75rem; --px:0.25rem; --py:0.25rem; --b:1px solid; --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --shadow:1"
							side={$mobile ? 'bottom' : 'right'}
							sideOffset={$mobile ? 5 : 0}
							alignOffset={$mobile ? 0 : -8}
						>
							<DropdownMenu.Item
								style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.75rem"
								on:click={() => {
									uploadOneDriveHandler('personal');
								}}
							>
								<div style="--line-clamp:1">{$i18n.t('Microsoft OneDrive (personal)')}</div>
							</DropdownMenu.Item>
							<DropdownMenu.Item
								style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --weight:500; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.75rem"
								on:click={() => {
									uploadOneDriveHandler('organizations');
								}}
							>
								<div style="--d:flex; --fd:column">
									<div style="--line-clamp:1">{$i18n.t('Microsoft OneDrive (work/school)')}</div>
									<div style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">Includes SharePoint</div>
								</div>
							</DropdownMenu.Item>
						</DropdownMenu.SubContent>
					</DropdownMenu.Sub>
				{/if}
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
