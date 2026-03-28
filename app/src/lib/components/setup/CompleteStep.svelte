<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, models, config } from '$lib/stores';
	import { getAllUsers } from '$lib/apis/users';
	import { getAdminConfig, getOAuthConfig } from '$lib/apis/auths';
	import { getModelsStatus } from '$lib/apis/retrieval';

	const i18n = getContext('i18n');

	export let onFinish: () => void = () => {};
	export let workingAlone = false;

	let connectionAdded = false;
	let usersCount = 0;
	let featuresEnabled = 0;
	let authMethods: string[] = [];
	let embeddingStatus = 'pending';
	let whisperStatus = 'pending';
	let loading = true;
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	// Feature flags to count from admin config
	const featureKeys = [
		'ENABLE_COMMUNITY_SHARING',
		'ENABLE_MESSAGE_RATING',
		'ENABLE_NOTES',
		'ENABLE_SPACES',
		'ENABLE_USER_WEBHOOKS'
	];

	onMount(async () => {
		connectionAdded = $models.length > 0;

		try {
			const res = await getAllUsers(localStorage.token);
			// API returns { users: [...], total: N }
			const users = Array.isArray(res) ? res : (res?.users ?? []);
			usersCount = users.filter((u: any) => u.role !== 'admin').length;
		} catch {
			usersCount = 0;
		}

		try {
			const config = await getAdminConfig();
			if (config) {
				featuresEnabled = featureKeys.filter((k) => config[k]).length;
			}
		} catch {
			featuresEnabled = 0;
		}

		// Check model download status and poll if downloading
		await updateModelStatus();
		if (embeddingStatus === 'downloading' || whisperStatus === 'downloading') {
			pollTimer = setInterval(updateModelStatus, 5000);
		}

		// Check which auth methods are configured
		try {
			const oauthCfg = await getOAuthConfig();
			if (oauthCfg?.GOOGLE_CLIENT_ID && oauthCfg?.GOOGLE_CLIENT_SECRET) authMethods.push('Google');
			if (oauthCfg?.GITHUB_CLIENT_ID && oauthCfg?.GITHUB_CLIENT_SECRET) authMethods.push('GitHub');
			if (oauthCfg?.ENABLE_MAGIC_LINK_LOGIN) authMethods.push('Email Link');
		} catch {
			// ignore — auth check is best-effort
		}

		loading = false;
	});

	async function updateModelStatus() {
		try {
			const mStatus = await getModelsStatus(localStorage.token);
			if (mStatus?.models) {
				embeddingStatus = mStatus.models.embedding ?? 'pending';
				whisperStatus = mStatus.models.whisper ?? 'pending';

				// Stop polling when nothing is downloading
				if (embeddingStatus !== 'downloading' && whisperStatus !== 'downloading' && pollTimer) {
					clearInterval(pollTimer);
					pollTimer = null;
				}
			}
		} catch {
			// ignore
		}
	}

	$: readyCount = [embeddingStatus, whisperStatus].filter((s) => s === 'ready').length;
	$: downloadingCount = [embeddingStatus, whisperStatus].filter((s) => s === 'downloading').length;
	$: totalComponents = 2;
</script>

<div style="--px:1.2rem; --pt:1.5rem; --pb:1.5rem; --ta:center">
	<div style="--size:2rem; --mb:0.6rem">
		&#10003;
	</div>
	<div style="--size:1.4rem; --weight:600; --dark-c:#fff; --mb:0.4rem">
		{$i18n.t("You're all set!")}
	</div>
	<div style="--size:0.8rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.5rem">
		{$i18n.t('{{name}} is ready to use.', { name: $WEBUI_NAME })}
	</div>

	{#if loading}
		<div style="--d:flex; --jc:center; --py:1rem; --size:0.8rem; --c:var(--color-gray-400)">
			{$i18n.t('Loading...')}
		</div>
	{:else}
		<div style="--d:flex; --fd:column; --g:0.5rem; --mb:1.5rem; --ta:left; --mx:auto; --w:fit-content">
			{#if authMethods.length > 0}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-green-600)">&#10003;</span>
					<span>{$i18n.t('Auth configured: {{methods}}', { methods: authMethods.join(', ') })}</span>
				</div>
			{/if}

			{#if connectionAdded}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-green-600)">&#10003;</span>
					<span>{$i18n.t('Model connection configured')}</span>
				</div>
			{/if}


			{#if usersCount > 0}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-green-600)">&#10003;</span>
					<span>
						{usersCount === 1
							? $i18n.t('1 user configured')
							: $i18n.t('{{count}} users configured', { count: usersCount })}
					</span>
				</div>
			{/if}

			{#if workingAlone}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-green-600)">&#10003;</span>
					<span>{$i18n.t('Working alone mode enabled')}</span>
				</div>
			{/if}

			{#if readyCount === totalComponents}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-green-600)">&#10003;</span>
					<span>{$i18n.t('AI engine components installed')}</span>
				</div>
			{:else if downloadingCount > 0}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-blue-600)">&#8635;</span>
					<span>{$i18n.t('{{ready}} of {{total}} AI engine components ready...', { ready: readyCount, total: totalComponents })}</span>
				</div>
			{:else if readyCount > 0}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-green-600)">&#10003;</span>
					<span>{$i18n.t('{{ready}} of {{total}} AI engine components installed', { ready: readyCount, total: totalComponents })}</span>
				</div>
			{/if}

			{#if $config?.dev_mode}
				<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
					<span style="--c:var(--color-green-600)">&#10003;</span>
					<span>{$i18n.t('Developer mode active')}</span>
				</div>
			{/if}

			{#if !connectionAdded && featuresEnabled === 0 && usersCount === 0 && !workingAlone}
				<div style="--size:0.75rem; --c:var(--color-gray-400)">
					{$i18n.t('You can configure connections and users anytime from Settings.')}
				</div>
			{/if}


			<div style="--d:flex; --ai:center; --g:0.5rem; --size:0.8rem">
				<span style="--c:var(--color-green-600)">&#10003;</span>
				<span>
					{featuresEnabled === 1
						? $i18n.t('1 feature enabled')
						: $i18n.t('{{count}} features enabled', { count: featuresEnabled })}
				</span>
			</div>
		</div>
	{/if}

	<button
		on:click={onFinish}
		style="--px:1.2rem; --py:0.5rem; --size:0.9rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
	>
		{$i18n.t("Let's Go!")}
	</button>
</div>
