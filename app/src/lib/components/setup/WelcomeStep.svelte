<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { WEBUI_NAME, models } from '$lib/stores';
	import { getAllUsers } from '$lib/apis/users';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';

	const i18n = getContext('i18n');

	export let onStart: (steps: string[]) => void = () => {};
	export let isFirstRun = false;

	let hasModels = false;
	let hasNonAdminUsers = false;
	let loading = true;

	let includeAuth = true;
	let includeConnection = true;
	let includeUsers = true;
	let includeFeatures = true;
	let includeSearchAudio = true;

	onMount(async () => {
		hasModels = $models.length > 0;

		try {
			const res = await getAllUsers(localStorage.token);
			// API returns { users: [...], total: N }
			const users = Array.isArray(res) ? res : (res?.users ?? []);
			hasNonAdminUsers = users.some((u: any) => u.role !== 'admin');
		} catch {
			hasNonAdminUsers = false;
		}

		// First run / reset: check all so admin reviews everything
		// Manual re-run: only check items not yet configured
		if (!isFirstRun) {
			includeConnection = !hasModels;
			includeUsers = !hasNonAdminUsers;
		}

		loading = false;
	});

	$: canStart = includeAuth || includeConnection || includeUsers || includeFeatures || includeSearchAudio;

	const handleStart = () => {
		const steps: string[] = [];
		// Order: auth → connection → users → features
		if (includeAuth) steps.push('auth');
		if (includeConnection) steps.push('connection');
		if (includeUsers) steps.push('users');
		if (includeFeatures) steps.push('features');
		if (includeSearchAudio) steps.push('search_audio');
		onStart(steps);
	};
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	{#if isFirstRun}
		<div style="--size:1.4rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
			{$i18n.t('Welcome to {{name}}!', { name: $WEBUI_NAME })}
		</div>
		<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
			{$i18n.t("Let's get you set up. Choose what you'd like to configure — you can always change these later in Admin > Settings.")}
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

			<!-- Authentication (Beta) -->
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-amber-100); --dark-bc:var(--color-amber-900); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-amber-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input type="checkbox" bind:checked={includeAuth} style="--w:1rem; --h:1rem; --shrink:0" />
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Authentication')}</span>
						<span style="--size:0.55rem; --c:var(--color-amber-600); --weight:600; --px:0.3rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-amber-100); --dark-bgc:var(--color-amber-900); --dark-c:var(--color-amber-400)">{$i18n.t('Beta')}</span>
						<Tooltip content={$i18n.t('Set up Google, GitHub, or email magic link sign-in so users can log in without a password.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Configure Google, GitHub, or email link sign-in for your users')}
					</div>
				</div>
			</label>

			<!-- Model Connections -->
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input type="checkbox" bind:checked={includeConnection} style="--w:1rem; --h:1rem; --shrink:0" />
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Model Connections')}</span>
						{#if hasModels}
							<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('configured')}</span>
						{/if}
						<Tooltip content={$i18n.t('Configure API endpoints for AI model providers like OpenAI or Ollama. Required for the platform to generate responses.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Add or update API connections to model providers')}
					</div>
				</div>
			</label>

			<!-- Users -->
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input type="checkbox" bind:checked={includeUsers} style="--w:1rem; --h:1rem; --shrink:0" />
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Users')}</span>
						{#if hasNonAdminUsers}
							<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('configured')}</span>
						{/if}
						<Tooltip content={$i18n.t('Add team members, assign roles, or choose to work alone. You can manage users anytime from Admin > Users.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Invite your team or choose to work alone')}
					</div>
					{#if hasNonAdminUsers}
						<a
							href="/admin/users"
							target="_blank"

							style="--size:0.65rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500); --td:underline; --mt:0.2rem; --d:inline-block"
						>
							{$i18n.t('Manage users')}
						</a>
					{/if}
				</div>
			</label>

			<!-- Features (last) -->
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input type="checkbox" bind:checked={includeFeatures} style="--w:1rem; --h:1rem; --shrink:0" />
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Features')}</span>
						<Tooltip content={$i18n.t('Toggle platform capabilities such as community sharing, notes, spaces, and message rating.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Enable or disable platform features like sharing, notes, and spaces')}
					</div>
				</div>
			</label>

			<!-- AI Engine -->
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input type="checkbox" bind:checked={includeSearchAudio} style="--w:1rem; --h:1rem; --shrink:0" />
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('AI Engine')}</span>
						<Tooltip content={$i18n.t('Install local AI components for document search, knowledge base, and audio transcription. Downloads run in the background (~2.5 GB total).')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Install local AI processing for document search and audio transcription')}
					</div>
				</div>
			</label>

		</div>

		<div style="--d:flex; --jc:space-between; --ai:center">
			{#if isFirstRun}
				<div style="--size:0.65rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --italic:italic; --maxw:22rem">
					{$i18n.t('Complete the setup and this wizard will not appear again unless you go to Admin > Settings > Wizard')}
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
