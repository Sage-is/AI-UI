<script lang="ts">
	import { onMount } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding } from '$lib/apis/configs';

	let selected = '';
	let branding: { logo_url?: string; favicon_url?: string } = {};

	onMount(async () => {
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}
	});
</script>

<div style="--minw:4.5rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-950, #0d0d0d); --d:flex; --g:0.625rem; --fd:column; --pt:2rem">
	<div style="--d:flex; --jc:center; --pos:relative">
		{#if selected === 'home'}
			<div style="--pos:absolute; --top:0; --left:0; --d:flex; --h:100%">
				<div style="--my:auto; --btrr:0.5rem; --bbrr:0.5rem; --w:0.25rem; --h:2rem; --bgc:#000; --dark-bgc:#fff"></div>
			</div>
		{/if}

		<Tooltip content="Home" placement="right">
			<button
				style="--cur:pointer"
	class="{selected === 'home' ? 'rounded-2xl' : 'rounded-full'}"
				on:click={() => {
					selected = 'home';

					if (window.electronAPI) {
						window.electronAPI.load('home');
					}
				}}
			>
				<img
					src="{WEBUI_BASE_URL}/static/icons/splash.png"
					style="--w:2.75rem; --h:2.75rem; --dark-fr:invert(100%); --p:0.125rem"
					alt="logo"
					draggable="false"
				/>
			</button>
		</Tooltip>
	</div>

	<div style="--mt:-0.25rem; --bc:1.5px; --bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-900, #171717); --mx:1rem"></div>

	<div style="--d:flex; --jc:center; --pos:relative"
	class="group">
		{#if selected === ''}
			<div style="--pos:absolute; --top:0; --left:0; --d:flex; --h:100%">
				<div style="--my:auto; --btrr:0.5rem; --bbrr:0.5rem; --w:0.25rem; --h:2rem; --bgc:#000; --dark-bgc:#fff"></div>
			</div>
		{/if}
		<button
			style="--cur:pointer; --bgc:transparent"
			on:click={() => {
				selected = '';
			}}
		>
			<img
				src={branding?.logo_url || `${WEBUI_BASE_URL}/static/icons/favicon.png`}
				style="--w:2.5rem; --h:2.5rem"
	class="{selected === '' ? 'rounded-2xl' : 'rounded-full'}"
				alt="logo"
				draggable="false"
			/>
		</button>
	</div>

	<!-- <div style="--d:flex; --jc:center; --pos:relative; --c:var(--color-gray-400, #b4b4b4)"
	class="group">
		<button style="--cur:pointer; --p:0.5rem" on:click={() => {}}>
			<Plus className="size-4" strokeWidth="2" />
		</button>
	</div> -->
</div>
