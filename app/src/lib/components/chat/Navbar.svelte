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

	import { getChatShareTargets } from '$lib/apis/chat-shares';

	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Menu from '$lib/components/layout/Navbar/Menu.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';

	import Banner from '../common/Banner.svelte';
	import Icon from '$lib/components/Icon.svelte';

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
	let hasShareTargets = false;

	$: if ($chatId && shareEnabled) {
		getChatShareTargets(localStorage.token, $chatId)
			.then((targets) => { hasShareTargets = targets && targets.length > 0; })
			.catch(() => { hasShareTargets = false; });
	} else {
		hasShareTargets = false;
	}
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

<nav style="--pos:sticky; --top:0; --z:30; --w:100%; --py:0.2rem; --mb:-2rem; --d:flex; --fd:column; --ai:center"
	class="drag-region">
	<div style="--d:flex; --ai:center; --w:100%; --pl:0.4rem; --pr:0.2rem">
		<div
			style="--bgi:linear-gradient(180deg, var(--tw-gradient-stops)); --tw-gradient-from:#fff; --tw-gradient-via:#fff; --tw-gradient-to:transparent; --dark-tw-gradient-from:var(--color-gray-900); --dark-tw-gradient-via:var(--color-gray-900); --dark-tw-gradient-to:transparent; --pe:none; --pos:absolute; --inset:0; --bottom:-1.75rem; --z:-1"
	class="via-50%"
		></div>

		<div style="--d:flex; --maxw:100%; --w:100%; --mx:auto; --p:0.2rem; --pt:0.125rem; --grad:0deg; --grad-color: hsl(273, 99%, 100%)">
			<div style="--d:flex; --ai:center; --w:100%; --maxw:100%">
				<div
					style="--mr:0.2rem;
					--as:flex-start;
					--d:flex; --fx:none;
					--ai:center;
					--c:var(--color-gray-600);
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
						style="--cur:pointer; --px:0.5rem; --py:0.5rem; --d:flex; --radius:0.6rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<div style="--m:auto; --as:center">
							<Icon name="menu-lines" />
						</div>
					</button>

					{#if !$mobile}
						<Tooltip content={$i18n.t('New Chat')}>
							<button
								style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.6rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$showSidebar
									? 'md:hidden'
									: ''}"
								on:click={() => {
									initNewChat();
								}}
								aria-label="New Chat"
							>
								<div style="--m:auto; --as:center">
									<Icon name="pencil-square" className=" size-5" strokeWidth="2" />
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

				<div style="--as:flex-start; --d:flex; --fx:none; --ai:center; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)">
					<!-- <div style="--d-md:none; --d:flex; --as:center; --w:1px; --h:1.2rem; --mx:0.5rem; --bgc:var(--color-gray-300); --dark-bgc:#44403c" /> -->
					{#if shareEnabled && chat && (chat.id || $temporaryChatEnabled)}
						<Menu
							{chat}
							{shareEnabled}
							{hasShareTargets}
							shareHandler={() => {
								showShareChatModal = !showShareChatModal;
							}}
							downloadHandler={() => {
								showDownloadChatModal = !showDownloadChatModal;
							}}
						>
							<div style="--pos:relative; --d:inline-flex">
								<button
									style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.6rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
									id="chat-context-menu-button"
								>
									<div style="--m:auto; --as:center">
										<Icon name="ellipsis-horizontal" className="size-[1.2rem]" />
									</div>
								</button>
								{#if hasShareTargets}
									<div
										style="--pos:absolute; --top:0.2rem; --right:0.2rem; --w:0.5rem; --h:0.5rem; --radius:9999px; --bgc:var(--color-green-500); --dark-bgc:var(--color-green-400); --bs:solid; --bw:1.5px; --bc:#fff; --dark-bc:var(--color-gray-850)"
										title={$i18n.t('Shared with people')}
									/>
								{/if}
							</div>
						</Menu>
					{/if}

					<Tooltip content={$i18n.t('Controls')}>
						<button
							style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.6rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={async () => {
								await showControls.set(!$showControls);
							}}
							aria-label="Controls"
						>
							<div style="--m:auto; --as:center">
								<Icon name="adjustments-horizontal" className=" size-5" strokeWidth="0.5" />
							</div>
						</button>
					</Tooltip>

					{#if $mobile}
						<Tooltip content={$i18n.t('New Chat')}>
							<button
								style="--d:flex; --cur:pointer; --px:0.5rem; --py:0.5rem; --radius:0.6rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{$showSidebar
									? 'md:hidden'
									: ''}"
								on:click={() => {
									initNewChat();
								}}
								aria-label="New Chat"
							>
								<div style="--m:auto; --as:center">
									<Icon name="pencil-square" className=" size-5" strokeWidth="2" />
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
								style="--us:none; --d:flex; --radius:0.6rem; --p:0.4rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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
			<div style="--size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Temporary Chat')}</div>
		</div>
	{/if}

	<div style="--pos:absolute; --top:100%; --left:0; --right:0; --h:fit-content">
		{#if !history.currentId && !$chatId && ($banners.length > 0 || ($config?.license_metadata?.type ?? null) === 'trial' || (($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats))}
			<div style="--w:100%; --z:30; --mt:1.2rem">
				<div style="--d:flex; --fd:column; --g:0.2rem; --w:100%">
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
