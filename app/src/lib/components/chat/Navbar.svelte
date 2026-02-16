<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		WEBUI_NAME,
		banners,
		chatId,
		config,
		mobile,
		settings,
		showArchivedChats,
		showControls,
		showSidebar,
		temporaryChatEnabled,
		user
	} from '$lib/stores';

	import { slide } from 'svelte/transition';
	import { page } from '$app/stores';

	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Menu from '$lib/components/layout/Navbar/Menu.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import Banner from '../common/Banner.svelte';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let chat;
	export let history;
	export let selectedModels;
	export let showModelSelector = true;
	export let showBanners = true;

	let closedBannerIds = [];

	let showShareChatModal = false;
	let showDownloadChatModal = false;
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />

<button
	id="new-chat-button"
	style="--d:none"
	on:click={() => {
		initNewChat();
	}}
	aria-label="New Chat"
/>

<nav style="--pos:sticky; --top:0; --z:30; --w:100%; --py:0.25rem; --mb:-2rem; --d:flex; --fd:column; --ai:center"
	class="drag-region">
	<div style="--d:flex; --ai:center; --w:100%; --pl:0.375rem; --pr:0.25rem">
		<div
			style="--bgi:linear-gradient(180deg, var(--tw-gradient-stops)); --tw-gradient-from:#fff; --tw-gradient-via:#fff; --tw-gradient-to:transparent; --dark-tw-gradient-from:var(--color-gray-900, #171717); --dark-tw-gradient-via:var(--color-gray-900, #171717); --dark-tw-gradient-to:transparent; --pe:none; --pos:absolute; --inset:0; --bottom:-1.75rem; --z:-1"
	class="via-50%"
		></div>

		<div style="--d:flex; --maxw:100%; --w:100%; --mx:auto; --p:0.25rem; --pt:0.125rem; --grad:0deg; --grad-color: hsl(273, 99%, 100%)">
			<div style="--d:flex; --ai:center; --w:100%; --maxw:100%">
				<div
					style="--mr:0.25rem; 
					--as:flex-start; 
					--d:flex; --fx:none; 
					--ai:center; 
					--c:var(--color-gray-600, #676767);
					{$showSidebar
					? '--d:none;'
					: ''}
					"
	class="{$showSidebar
						? 'md:hidden'
						: ''}"
				>
					<button
						id="sidebar-toggle-button"
						style="--cur:pointer; --px:0.5rem; --py:0.5rem; --d:flex; --radius:0.75rem; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<div style="--m:auto; --as:center">
							<MenuLines />
						</div>
					</button>

					{#if !$mobile}
						<Tooltip content={$i18n.t('New Chat')}>
							<button
								style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.75rem; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4); --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$showSidebar
									? 'md:hidden'
									: ''}"
								on:click={() => {
									initNewChat();
								}}
								aria-label="New Chat"
							>
								<div style="--m:auto; --as:center">
									<PencilSquare className=" size-5" strokeWidth="2" />
								</div>
							</button>
						</Tooltip>
					{/if}
				</div>

				<div
					style="--fx:1 1 0%; --of:hidden; --maxw:100%; --py:0.125rem"
	class="{$showSidebar ? 'ml-1' : ''}"
				>
					{#if showModelSelector}
						<ModelSelector bind:selectedModels showSetDefault={!shareEnabled} />
					{/if}
				</div>

				<div style="--as:flex-start; --d:flex; --fx:none; --ai:center; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4)">
					<!-- <div style="--d-md:none; --d:flex; --as:center; --w:1px; --h:1.25rem; --mx:0.5rem; --bgc:var(--color-gray-300, #cdcdcd); --dark-bgc:#44403c" /> -->
					{#if shareEnabled && chat && (chat.id || $temporaryChatEnabled)}
						<Menu
							{chat}
							{shareEnabled}
							shareHandler={() => {
								showShareChatModal = !showShareChatModal;
							}}
							downloadHandler={() => {
								showDownloadChatModal = !showDownloadChatModal;
							}}
						>
							<button
								style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.75rem; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								id="chat-context-menu-button"
							>
								<div style="--m:auto; --as:center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										style="--w:1.25rem; --h:1.25rem"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
										/>
									</svg>
								</div>
							</button>
						</Menu>
					{/if}

					<Tooltip content={$i18n.t('Controls')}>
						<button
							style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.75rem; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={async () => {
								await showControls.set(!$showControls);
							}}
							aria-label="Controls"
						>
							<div style="--m:auto; --as:center">
								<AdjustmentsHorizontal className=" size-5" strokeWidth="0.5" />
							</div>
						</button>
					</Tooltip>

					{#if $mobile}
						<Tooltip content={$i18n.t('New Chat')}>
							<button
								style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.75rem; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-400, #b4b4b4); --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$showSidebar
									? 'md:hidden'
									: ''}"
								on:click={() => {
									initNewChat();
								}}
								aria-label="New Chat"
							>
								<div style="--m:auto; --as:center">
									<PencilSquare className=" size-5" strokeWidth="2" />
								</div>
							</button>
						</Tooltip>
					{/if}

					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<div
								style="--us:none; --d:flex; --radius:0.75rem; --p:0.375rem; --w:100%; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							>
								<div style="--as:center">
									<span class="sr-only">{$i18n.t('User menu')}</span>
									<img
										src={$user?.profile_image_url}
										style="--w:1.5rem; --h:1.5rem; --objf:cover; --radius:9999px"
										alt=""
										draggable="false"
									/>
								</div>
							</div>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if $temporaryChatEnabled && $chatId === 'local'}
		<div style="--w:100%; --z:30; --ta:center">
			<div style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Temporary Chat')}</div>
		</div>
	{/if}

	<div style="--pos:absolute; --top:100%; --left:0; --right:0; --h:fit-content">
		{#if !history.currentId && !$chatId && ($banners.length > 0 || ($config?.license_metadata?.type ?? null) === 'trial' || (($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats))}
			<div style="--w:100%; --z:30; --mt:1.25rem">
				<div style="--d:flex; --fd:column; --g:0.25rem; --w:100%">
					{#if ($config?.license_metadata?.type ?? null) === 'trial'}
						<Banner
							banner={{
								type: 'info',
								title: 'Trial License',
								content: $i18n.t(
									'You are currently using a trial license. Please contact support to upgrade your license.'
								)
							}}
						/>
					{/if}

					{#if ($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats}
						<Banner
							banner={{
								type: 'error',
								title: 'License Error',
								content: $i18n.t(
									'Exceeded the number of seats in your license. Please contact support to increase the number of seats.'
								)
							}}
						/>
					{/if}

					{#if showBanners}
						{#each $banners.filter((b) => ![...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]'), ...closedBannerIds].includes(b.id)) as banner}
							<Banner
								{banner}
								on:dismiss={(e) => {
									const bannerId = e.detail;

									if (banner.dismissible) {
										localStorage.setItem(
											'dismissedBannerIds',
											JSON.stringify(
												[
													bannerId,
													...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]')
												].filter((id) => $banners.find((b) => b.id === id))
											)
										);
									} else {
										closedBannerIds = [...closedBannerIds, bannerId];
									}
								}}
							/>
						{/each}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</nav>
