<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { WEBUI_NAME, models } from '$lib/stores';
	import { getAllUsers } from '$lib/apis/users';

	const i18n = getContext('i18n');

	export let onStart: (steps: string[]) => void = () => {};
	export let isFirstRun = false;

	let hasModels = false;
	let hasUsers = false;
	let loading = true;

	let includeConnection = true;
	let includeUsers = true;

	onMount(async () => {
		hasModels = $models.length > 0;

		try {
			const users = await getAllUsers(localStorage.token);
			hasUsers = users ? users.filter((u: any) => u.role !== 'admin').length > 0 : false;
		} catch {
			hasUsers = false;
		}

		// Always pre-check connections (admin should review even if configured)
		includeConnection = true;
		// Pre-check users only if none exist
		includeUsers = !hasUsers;

		loading = false;
	});

	$: canStart = includeConnection || includeUsers;

	const handleStart = () => {
		const steps: string[] = [];
		if (includeConnection) steps.push('connection');
		if (includeUsers) steps.push('users');
		onStart(steps);
	};
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	{#if isFirstRun}
		<div style="--size:1.4rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
			{$i18n.t('Welcome to {{name}}!', { name: $WEBUI_NAME })}
		</div>
		<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
			{$i18n.t("Let's get you set up. Choose what you'd like to configure — you can always change these later in Settings.")}
		</div>
	{:else}
		<div style="--size:1.2rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
			{$i18n.t('Setup Wizard')}
		</div>
		<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
			{$i18n.t('Select the steps you want to run.')}
		</div>
	{/if}

	{#if loading}
		<div style="--d:flex; --jc:center; --py:2rem; --size:0.8rem; --c:var(--color-gray-400)">
			{$i18n.t('Loading...')}
		</div>
	{:else}
		<div style="--d:flex; --fd:column; --g:0.6rem; --mb:1.5rem">
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input
					type="checkbox"
					bind:checked={includeConnection}
					style="--w:1rem; --h:1rem; --shrink:0"
				/>
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Model Connections')}</span>
						{#if hasModels}
							<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('configured')}</span>
						{/if}
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Add or update API connections to model providers')}
					</div>
				</div>
			</label>

			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input
					type="checkbox"
					bind:checked={includeUsers}
					style="--w:1rem; --h:1rem; --shrink:0"
				/>
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Users')}</span>
						{#if hasUsers}
							<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('configured')}</span>
						{/if}
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Invite your team or choose to work alone')}
					</div>
				</div>
			</label>
		</div>

		<div style="--d:flex; --jc:space-between; --ai:center">
			{#if isFirstRun}
				<div style="--size:0.65rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --italic:italic; --maxw:20rem">
					{$i18n.t('Complete the setup and this wizard will not appear again.')}
				</div>
			{:else}
				<div />
			{/if}

			<button
				on:click={handleStart}
				disabled={!canStart}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --shrink:0; --bgc:{canStart ? '#000' : 'var(--color-gray-300)'}; --hvr-bgc:{canStart ? 'var(--color-gray-900)' : 'var(--color-gray-300)'}; --c:#fff; --dark-bgc:{canStart ? '#fff' : 'var(--color-gray-600)'}; --dark-c:{canStart ? '#000' : 'var(--color-gray-400)'}; --hvr-dark-bgc:{canStart ? 'var(--color-gray-100)' : 'var(--color-gray-600)'}; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{$i18n.t("Get Started")}
			</button>
		</div>
	{/if}
</div>
