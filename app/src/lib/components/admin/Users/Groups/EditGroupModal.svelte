<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Display from './Display.svelte';
	import Permissions from './Permissions.svelte';
	import Users from './Users.svelte';
	import UserPlusSolid from '$lib/components/icons/UserPlusSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let onSubmit: Function = () => {};
	export let onDelete: Function = () => {};

	export let show = false;
	export let edit = false;

	export let users = [];
	export let group = null;

	export let custom = true;

	export let tabs = ['general', 'permissions', 'users'];

	let selectedTab = 'general';
	let loading = false;
	let showDeleteConfirmDialog = false;

	export let name = '';
	export let description = '';

	export let permissions = {
		workshop: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false
		},
		sharing: {
			public_models: false,
			public_knowledge: false,
			public_prompts: false,
			public_tools: false
		},
		chat: {
			controls: true,
			file_upload: true,
			delete: true,
			edit: true,
			temporary: true
		},
		features: {
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true
		}
	};
	export let userIds = [];

	const submitHandler = async () => {
		loading = true;

		const group = {
			name,
			description,
			permissions,
			user_ids: userIds
		};

		await onSubmit(group);

		loading = false;
		show = false;
	};

	const init = () => {
		if (group) {
			name = group.name;
			description = group.description;
			permissions = group?.permissions ?? {};

			userIds = group?.user_ids ?? [];
		}
	};

	$: if (show) {
		init();
	}

	onMount(() => {
		selectedTab = tabs[0];
		init();
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		onDelete();
		show = false;
	}}
/>

<Modal size="md" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.25rem; --pt:1rem; --mb:0.375rem">
			<div style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{#if custom}
					{#if edit}
						{$i18n.t('Edit User Group')}
					{:else}
						{$i18n.t('Add User Group')}
					{/if}
				{:else}
					{$i18n.t('Edit Default Permissions')}
				{/if}
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem; --shadow: 6">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div style="--d:flex; --fd:column; --fd-lg:row; --w:100%; --h:100%;  --g-lg:1rem">
						<div
							id="admin-settings-tabs-container"
							style="--d:flex; --fd:row; --ofx:auto; --g:0.625rem; --maxw:100%; --g-lg:0.25rem; --fd-lg:column; --fx-lg:none; --w-lg:10rem; --dark-c:var(--color-gray-200); --size:0.875rem; --weight:500; --ta:left"
	class="tabs scrollbar-none"
						>
							{#if tabs.includes('general')}
								<button
									style="--p:0.25rem; --w:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="max-w-fit {selectedTab ===
									'general'
										? ''
										: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'general';
									}}
									type="button"
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
							{/if}

							{#if tabs.includes('permissions')}
								<button
									style="--p:0.25rem; --w:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="max-w-fit {selectedTab ===
									'permissions'
										? ''
										: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'permissions';
									}}
									type="button"
								>
									<div style="--as:center; --mr:0.5rem">
										<WrenchSolid />
									</div>
									<div style="--as:center">{$i18n.t('Permissions')}</div>
								</button>
							{/if}

							{#if tabs.includes('users')}
								<button
									style="--p:0.25rem; --w:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-lg:none; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="max-w-fit {selectedTab ===
									'users'
										? ''
										: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'users';
									}}
									type="button"
								>
									<div style="--as:center; --mr:0.5rem">
										<UserPlusSolid />
									</div>
									<div style="--as:center">{$i18n.t('Users')} ({userIds.length})</div>
								</button>
							{/if}
						</div>

						<div
							style="--fx:1 1 0%; --mt:0.25rem; --mt-lg:0.25rem; --h-lg:22rem; --maxh-lg:22rem; --ofy:auto"
	class="scrollbar-hidden"
						>
							{#if selectedTab == 'general'}
								<Display bind:name bind:description />
							{:else if selectedTab == 'permissions'}
								<Permissions bind:permissions />
							{:else if selectedTab == 'users'}
								<Users bind:userIds {users} />
							{/if}
						</div>
					</div>

					<!-- <div
						style="--d:flex; --fd:row; --ofx:auto; --g:0.625rem; --size:0.875rem; --weight:500; --bb:1px solid; border-bottom-color:var(--color-gray-800)"
	class="tabs scrollbar-hidden"
					>
						{#if tabs.includes('display')}
							<button
								style="--px:0.125rem; --pb:0.375rem; --minw:fit-content; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); border-bottom-width:2px"
	class="{selectedTab ===
								'display'
									? ' dark:border-white'
									: 'border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'display';
								}}
								type="button"
							>
								{$i18n.t('Display')}
							</button>
						{/if}

						{#if tabs.includes('permissions')}
							<button
								style="--px:0.125rem; --pb:0.375rem; --minw:fit-content; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); border-bottom-width:2px"
	class="{selectedTab ===
								'permissions'
									? '  dark:border-white'
									: 'border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'permissions';
								}}
								type="button"
							>
								{$i18n.t('Permissions')}
							</button>
						{/if}

						{#if tabs.includes('users')}
							<button
								style="--px:0.125rem; --pb:0.375rem; --minw:fit-content; --d:flex; --ta:right; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); border-bottom-width:2px"
	class="{selectedTab ===
								'users'
									? ' dark:border-white'
									: ' border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'users';
								}}
								type="button"
							>
								{$i18n.t('Users')} ({userIds.length})
							</button>
						{/if}
					</div> -->

					<div style="--d:flex; --jc:space-between; --pt:0.75rem; --size:0.875rem; --weight:500; --g:0.375rem">
						{#if edit}
							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --dark-bgc:#000; --hvr-dark-bgc:var(--color-gray-900); --dark-c:#fff; --bgc:#fff; --c:#000; --hvr-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{:else}
							<div></div>
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
