<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';

	import { getUsage } from '$lib/apis';
	import { userSignOut } from '$lib/apis/auths';

	import { showSettings, mobile, showSidebar, showShortcuts, user } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import Keyboard from '$lib/components/icons/Keyboard.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import Code from '$lib/components/icons/Code.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import SignOut from '$lib/components/icons/SignOut.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();

	let usage = null;
	const getUsageInfo = async () => {
		const res = await getUsage(localStorage.token).catch((error) => {
			console.error('Error fetching usage info:', error);
		});

		if (res) {
			usage = res;
		} else {
			usage = null;
		}
	};

	$: if (show) {
		getUsageInfo();
	}
</script>

<ShortcutsModal bind:show={$showShortcuts} />

<!-- svelte-ignore a11y-no-static-element-interactions -->
<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			style="--w:100%; --size:0.875rem; --radius:0.75rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --shadow:4"
	class="{className} font-primary"
			sideOffset={4}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<DropdownMenu.Item
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.75rem; --w:100%; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={async () => {
					await showSettings.set(true);
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div style="--as:center; --mr:0.75rem">
					<Settings className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Settings')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.75rem; --w:100%; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={() => {
					dispatch('show', 'archived-chat');
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div style="--as:center; --mr:0.75rem">
					<ArchiveBox className="size-5" strokeWidth="1.5" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Archived Chats')}</div>
			</DropdownMenu.Item>

			{#if role === 'admin'}
				<DropdownMenu.Item
					style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.75rem; --w:100%; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --us:none"
					on:click={() => {
						show = false;
						if ($mobile) {
							showSidebar.set(false);
						}
						goto('/playground');
					}}
				>
					<div style="--as:center; --mr:0.75rem">
						<Code className="size-5" strokeWidth="1.5" />
					</div>
					<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Playground')}</div>
				</DropdownMenu.Item>
		{/if}

		{#if role === 'admin' || role === 'facilitator'}

				<DropdownMenu.Item
					style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.75rem; --w:100%; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --us:none"
					on:click={() => {
						show = false;
						if ($mobile) {
							showSidebar.set(false);
						}
						goto(role === 'admin' ? '/admin/settings' : '/admin');
					}}
				>
					<div style="--as:center; --mr:0.75rem">
						<UserGroup className="w-5 h-5" strokeWidth="1.5" />
					</div>
					<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Admin Panel')}</div>
				</DropdownMenu.Item>
			{/if}

			{#if help}
				<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-800, #333); --my:0.25rem; --p:0" />

				<!-- {$i18n.t('Help')} -->
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --py:0.375rem; --px:0.75rem; --size:0.875rem; --us:none; --w:100%; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					id="chat-share-button"
					on:click={() => {
						window.open('https://docs.sage.is', '_blank');
						show = false;
					}}
				>
					<QuestionMarkCircle className="size-5" />
					<div style="--d:flex; --ai:center">{$i18n.t('Documentation')}</div>
				</DropdownMenu.Item>

				<!-- Releases -->
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --py:0.375rem; --px:0.75rem; --size:0.875rem; --us:none; --w:100%; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					id="menu-item-releases"
					on:click={() => {
						window.open('https://github.com/Sage-is/AI-UI/releases', '_blank');
						show = false;
					}}
				>
					<Map className="size-5" />
					<div style="--d:flex; --ai:center">{$i18n.t('Releases')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --py:0.375rem; --px:0.75rem; --size:0.875rem; --us:none; --w:100%; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					id="chat-share-button"
					on:click={() => {
						showShortcuts.set(!$showShortcuts);
						show = false;
					}}
				>
					<Keyboard className="size-5" />
					<div style="--d:flex; --ai:center">{$i18n.t('Keyboard shortcuts')}</div>
				</DropdownMenu.Item>
			{/if}

			<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-800, #333); --my:0.25rem; --p:0" />

			<DropdownMenu.Item
				style="--d:flex; --radius:0.375rem; --py:0.375rem; --px:0.75rem; --w:100%; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<div style="--as:center; --mr:0.75rem">
					<SignOut className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">{$i18n.t('Sign Out')}</div>
			</DropdownMenu.Item>

			{#if usage}
				{#if usage?.user_ids?.length > 0}
					<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-800, #333); --my:0.25rem; --p:0" />

					<Tooltip
						content={usage?.model_ids && usage?.model_ids.length > 0
							? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
							: ''}
					>
						<div
							style="--d:flex; --radius:0.375rem; --py:0.25rem; --px:0.75rem; --size:0.75rem; --g:0.625rem; --ai:center"
							on:mouseenter={() => {
								getUsageInfo();
							}}
						>
							<div style="--d:flex; --ai:center">
								<span style="--pos:relative; --d:flex; --w:0.5rem; --h:0.5rem">
									<span
										style="animation:ping 1s cubic-bezier(0, 0, 0.2, 1) infinite; --pos:absolute; --d:inline-flex; --h:100%; --w:100%; --radius:9999px; --bgc:#4ade80; --op:0.75"
									/>
									<span style="--pos:relative; --d:inline-flex; --radius:9999px; --w:0.5rem; --h:0.5rem; --bgc:#22c55e" />
								</span>
							</div>

							<div class=" ">
								<span class="">
									{$i18n.t('Active Users')}:
								</span>
								<span style="--weight:600">
									{usage?.user_ids?.length}
								</span>
							</div>
						</div>
					</Tooltip>
				{/if}
			{/if}

			<!-- <DropdownMenu.Item style="--d:flex; --ai:center; --py:0.375rem; --px:0.75rem; --size:0.875rem">
				<div style="--d:flex; --ai:center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
