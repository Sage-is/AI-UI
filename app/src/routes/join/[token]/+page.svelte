<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { WEBUI_NAME, user, config } from '$lib/stores';
	import { redeemMagicLink } from '$lib/apis/magic-links';
	import { getBackendConfig } from '$lib/apis';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = false;
	let error = '';
	let name = '';
	let showNameInput = false;

	const redeem = async (guestName?: string) => {
		loading = true;
		error = '';

		try {
			const linkToken = $page.params.token;
			const result = await redeemMagicLink(linkToken, guestName);

			if (result?.token) {
				localStorage.token = result.token;

				// Set user from the redeem response
				await user.set(result);

				toast.success($i18n.t('Welcome!'));

				// Try to get backend config
				const backendConfig = await getBackendConfig().catch(() => null);
				if (backendConfig) {
					await config.set(backendConfig);
				}

				// Redirect to home
				window.location.href = '/';
			}
		} catch (err: any) {
			error = typeof err === 'string' ? err : err?.detail || 'Failed to redeem magic link';
			loading = false;
		}
	};

	onMount(async () => {
		// Show name input to let user choose a display name
		showNameInput = true;
	});
</script>

<svelte:head>
	<title>Join - {$WEBUI_NAME}</title>
</svelte:head>

<div style="--d:flex; --ai:center; --jc:center; --minh:100vh; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-900, #171717)">
	<div style="--w:100%; --maxw:24rem; --mx:auto; --p:2rem">
		<div style="--ta:center; --mb:2rem">
			<h1 style="--size:1.5rem; --weight:700; --c:var(--color-gray-900, #171717); --dark-c:#fff">
				{$WEBUI_NAME}
			</h1>
			<p style="--size:0.875rem; --c:var(--color-gray-500, #9b9b9b); --mt:0.5rem">
				{$i18n.t('You have been invited to join')}
			</p>
		</div>

		{#if loading}
			<div style="--d:flex; --jc:center; --py:2rem">
				<Spinner className="size-8" />
			</div>
		{:else if error}
			<div style="--ta:center; --p:1rem; --radius:0.75rem; --bgc:#fef2f2; --dark-bgc:#450a0a; --c:#ef4444; --mb:1rem">
				{error}
			</div>
			<div style="--ta:center">
				<a
					href="/"
					style="--size:0.875rem; --c:var(--color-gray-500, #9b9b9b); --tdu:underline"
				>
					{$i18n.t('Go to home page')}
				</a>
			</div>
		{:else if showNameInput}
			<div style="--d:flex; --fd:column; --g:1rem">
				<div>
					<label
						for="name"
						style="--d:block; --size:0.875rem; --weight:500; --c:var(--color-gray-700, #4e4e4e); --dark-c:var(--color-gray-300, #cdcdcd); --mb:0.25rem"
					>
						{$i18n.t('Your Name')}
					</label>
					<input
						id="name"
						type="text"
						bind:value={name}
						placeholder={$i18n.t('Enter your name (optional)')}
						style="--w:100%; --p:0.625rem; --radius:0.75rem; --bc:var(--color-gray-300, #cdcdcd); --dark-bc:var(--color-gray-600, #7a7a7a); --bgc:#fff; --dark-bgc:var(--color-gray-800, #333); --size:0.875rem; --oe:none"
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								redeem(name || undefined);
							}
						}}
					/>
				</div>

				<button
					style="--w:100%; --p:0.625rem; --radius:0.75rem; --bgc:var(--color-gray-900, #171717); --dark-bgc:#fff; --c:#fff; --dark-c:var(--color-gray-900, #171717); --weight:500; --size:0.875rem; --cur:pointer; --tn:opacity 150ms"
					on:click={() => redeem(name || undefined)}
				>
					{$i18n.t('Join')}
				</button>
			</div>
		{/if}
	</div>
</div>
