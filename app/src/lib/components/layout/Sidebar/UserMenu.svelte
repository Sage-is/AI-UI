<script lang="ts">
	import { createEventDispatcher, getContext, onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { fade } from 'svelte/transition';
	import Icon from '$lib/components/Icon.svelte';

	import { getUsage } from '$lib/apis';
	import { userSignOut } from '$lib/apis/auths';

	import { showSettings, mobile, showSidebar, showShortcuts, user } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
					import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import TryPersonaSwitcher from '$lib/components/TryPersonaSwitcher.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();

	let triggerEl: HTMLElement;
	let menuEl: HTMLElement;
	let menuStyle = '';

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

	function toggle() {
		show = !show;
		if (show) {
			updatePosition();
			getUsageInfo();
		}
		dispatch('change', show);
	}

	function close() {
		if (show) {
			show = false;
			dispatch('change', false);
		}
	}

	function updatePosition() {
		if (!triggerEl) return;
		const rect = triggerEl.getBoundingClientRect();
		const vH = window.innerHeight;
		const vW = window.innerWidth;

		let style = 'position:fixed;';

		// Vertical: bottom half → open upward, top half → open downward
		if (rect.top > vH / 2) {
			style += ` bottom:${vH - rect.top + 4}px;`;
		} else {
			style += ` top:${rect.bottom + 4}px;`;
		}

		// Horizontal: right half → align right edge, left half → align left edge
		if (rect.left > vW / 2) {
			style += ` right:${vW - rect.right}px;`;
		} else {
			style += ` left:${rect.left}px;`;
		}

		menuStyle = style;
	}

	function handleWindowPointerdown(e: PointerEvent) {
		if (!show) return;
		const target = e.target as Node;
		if (menuEl?.contains(target) || triggerEl?.contains(target)) return;
		close();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') close();
	}

	const itemStyle =
		'--d:flex; --radius:0.4rem; --py:0.4rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)';

	const helpItemStyle =
		'--d:flex; --g:0.5rem; --ai:center; --py:0.4rem; --px:0.6rem; --size:0.8rem; --us:none; --w:100%; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)';
</script>

<svelte:window on:pointerdown={handleWindowPointerdown} on:keydown={handleKeydown} />

<ShortcutsModal bind:show={$showShortcuts} />

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div bind:this={triggerEl} on:click={toggle}>
	<slot />
</div>

{#if show}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={menuEl}
		transition:fade={{ duration: 100 }}
		style="{menuStyle} --w:100%; --size:0.8rem; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:999; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
		class="{className} font-primary"
		on:click|stopPropagation
	>
		<button
			style={itemStyle}
			on:click={async () => {
				await showSettings.set(true);
				close();
				if ($mobile) showSidebar.set(false);
			}}
		>
			<div style="--as:center; --mr:0.6rem">
				<Icon name="settings" className="w-5 h-5" strokeWidth="1.5" />
			</div>
			<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
				{$i18n.t('Settings')}
			</div>
		</button>

		<button
			style={itemStyle}
			on:click={() => {
				dispatch('show', 'archived-chat');
				close();
				if ($mobile) showSidebar.set(false);
			}}
		>
			<div style="--as:center; --mr:0.6rem">
				<Icon name="archive-box" className="size-5" strokeWidth="1.5" />
			</div>
			<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
				{$i18n.t('Archived Chats')}
			</div>
		</button>

		{#if role === 'admin' || role === 'facilitator'}
			<button
				style="{itemStyle}; --us:none"
				on:click={() => {
					close();
					if ($mobile) showSidebar.set(false);
					goto(role === 'admin' ? '/admin/settings' : '/admin');
				}}
			>
				<div style="--as:center; --mr:0.6rem">
					<Icon name="user-group" className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
					{$i18n.t('Admin Panel')}
				</div>
			</button>
		{/if}

		<!--
			try.sage persona switcher (B3). Self-gated by
			`$config?.features?.enable_try_sage`; renders nothing in
			production deployments. Sibling banner agent (B-banner-admin)
			owns admin reset/extend controls — those live in
			`+layout.svelte`, not here.
		-->
		<!--<TryPersonaSwitcher />-->

		{#if help}
			<hr
				style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-800); --my:0.2rem; --p:0"
			/>

			<button
				style={helpItemStyle}
				on:click={() => {
					window.open('https://docs.sage.is', '_blank');
					close();
				}}
			>
				<Icon name="question-mark-circle" strokeWidth="2" className="size-5" />
				<div style="--d:flex; --ai:center">{$i18n.t('Documentation')}</div>
			</button>

			<button
				style={helpItemStyle}
				on:click={() => {
					window.open('https://github.com/Sage-is/AI-UI/releases', '_blank');
					close();
				}}
			>
				<Icon name="map" strokeWidth="2" className="size-5" />
				<div style="--d:flex; --ai:center">{$i18n.t('Releases')}</div>
			</button>

			<button
				style={helpItemStyle}
				on:click={() => {
					showShortcuts.set(!$showShortcuts);
					close();
				}}
			>
				<Icon name="keyboard" strokeWidth="2" className="size-5" />
				<div style="--d:flex; --ai:center">{$i18n.t('Keyboard shortcuts')}</div>
			</button>
		{/if}

		<hr
			style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-800); --my:0.2rem; --p:0"
		/>

		<button
			style={itemStyle}
			on:click={async () => {
				const res = await userSignOut();
				user.set(null);
				localStorage.removeItem('token');
				location.href = res?.redirect_url ?? '/auth';
				close();
			}}
		>
			<div style="--as:center; --mr:0.6rem">
				<Icon name="sign-out" className="w-5 h-5" strokeWidth="1.5" />
			</div>
			<div style="--as:center; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
				{$i18n.t('Sign Out')}
			</div>
		</button>

		{#if usage}
			{#if usage?.user_ids?.length > 0}
				<hr
					style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-800); --my:0.2rem; --p:0"
				/>

				<Tooltip
					content={usage?.model_ids && usage?.model_ids.length > 0
						? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
						: ''}
				>
					<div
						style="--d:flex; --radius:0.4rem; --py:0.2rem; --px:0.6rem; --size:0.6rem; --g:0.625rem; --ai:center"
						on:mouseenter={() => {
							getUsageInfo();
						}}
					>
						<div style="--d:flex; --ai:center">
							<span style="--pos:relative; --d:flex; --w:0.5rem; --h:0.5rem">
								<span
									style="animation:ping 1s cubic-bezier(0, 0, 0.2, 1) infinite; --pos:absolute; --d:inline-flex; --h:100%; --w:100%; --radius:9999px; --bgc:#4ade80; --op:0.75"
								/>
								<span
									style="--pos:relative; --d:inline-flex; --radius:9999px; --w:0.5rem; --h:0.5rem; --bgc:#22c55e"
								/>
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
	</div>
{/if}
