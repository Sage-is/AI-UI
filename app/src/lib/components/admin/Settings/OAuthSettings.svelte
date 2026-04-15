<!--
  OAuthSettings.svelte — Shared OAuth configuration form (Beta)
  Used in both the setup wizard (compact=true) and Admin > Settings > Auth tab.
  Each provider uses <details>/<summary> to keep things clean.
-->
<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Icon from '$lib/components/Icon.svelte';

	import {
		getOAuthConfig,
		updateOAuthConfig,
		getAdminConfig,
		updateAdminConfig,
		getLdapConfig,
		getLdapServer,
		updateLdapConfig,
		updateLdapServer
	} from '$lib/apis/auths';
	import { getBackendConfig } from '$lib/apis';
	import { config } from '$lib/stores';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	/** Hide the standalone Save button when embedded in wizard */
	export let compact = false;

	let loading = true;
	let saving = false;

	// OAuth global toggles
	let enableOAuthSignup = false;
	let mergeAccountsByEmail = false;

	// Google
	let googleClientId = '';
	let googleClientSecret = '';

	// GitHub
	let githubClientId = '';
	let githubClientSecret = '';

	// Magic link email login
	let enableMagicLinkLogin = false;
	let magicLinkSmtpHost = '';
	let magicLinkSmtpPort = 587;
	let magicLinkSmtpUser = '';
	let magicLinkSmtpPassword = '';
	let magicLinkSmtpFrom = '';

	// General auth settings (only loaded/shown in full admin mode, not wizard)
	let adminConfig: any = null;
	let ENABLE_LDAP = false;
	let LDAP_SERVER: any = {
		label: '',
		host: '',
		port: '',
		attribute_for_mail: 'mail',
		attribute_for_username: 'uid',
		app_dn: '',
		app_dn_password: '',
		search_base: '',
		search_filters: '',
		use_tls: false,
		certificate_path: '',
		ciphers: ''
	};

	// Base URL for callback instructions — loaded from admin config
	let webuiUrl = '';

	onMount(async () => {
		try {
			const loads = [getOAuthConfig(), getAdminConfig()];
			// Full admin mode: also load LDAP config
			if (!compact) loads.push(getLdapConfig(), getLdapServer());
			const [oauthCfg, adminCfg, ldapCfg, ldapSrv] = await Promise.all(loads);
			enableOAuthSignup = oauthCfg.ENABLE_OAUTH_SIGNUP ?? false;
			mergeAccountsByEmail = oauthCfg.OAUTH_MERGE_ACCOUNTS_BY_EMAIL ?? false;
			googleClientId = oauthCfg.GOOGLE_CLIENT_ID ?? '';
			googleClientSecret = oauthCfg.GOOGLE_CLIENT_SECRET ?? '';
			githubClientId = oauthCfg.GITHUB_CLIENT_ID ?? '';
			githubClientSecret = oauthCfg.GITHUB_CLIENT_SECRET ?? '';
			enableMagicLinkLogin = oauthCfg.ENABLE_MAGIC_LINK_LOGIN ?? false;
			magicLinkSmtpHost = oauthCfg.MAGIC_LINK_SMTP_HOST ?? '';
			magicLinkSmtpPort = oauthCfg.MAGIC_LINK_SMTP_PORT ?? 587;
			magicLinkSmtpUser = oauthCfg.MAGIC_LINK_SMTP_USER ?? '';
			magicLinkSmtpPassword = oauthCfg.MAGIC_LINK_SMTP_PASSWORD ?? '';
			magicLinkSmtpFrom = oauthCfg.MAGIC_LINK_SMTP_FROM ?? '';
			webuiUrl = (adminCfg.WEBUI_URL ?? '').replace(/\/$/, '');
			// Always populate adminConfig (wizard needs ENABLE_SIGNUP for gating)
			if (adminCfg) {
				adminConfig = adminCfg;
			}
			if (!compact && ldapCfg) {
				ENABLE_LDAP = ldapCfg.ENABLE_LDAP ?? false;
			}
			if (!compact && ldapSrv) {
				LDAP_SERVER = ldapSrv;
			}
		} catch {
			toast.error($i18n.t('Failed to load OAuth settings'));
		}
		loading = false;
	});

	/** Save OAuth config to backend and refresh the global config store */
	export const save = async () => {
		saving = true;
		try {
			await updateOAuthConfig({
				ENABLE_OAUTH_SIGNUP: enableOAuthSignup,
				OAUTH_MERGE_ACCOUNTS_BY_EMAIL: mergeAccountsByEmail,
				GOOGLE_CLIENT_ID: googleClientId,
				GOOGLE_CLIENT_SECRET: googleClientSecret,
				GITHUB_CLIENT_ID: githubClientId,
				ENABLE_MAGIC_LINK_LOGIN: enableMagicLinkLogin,
				MAGIC_LINK_SMTP_HOST: magicLinkSmtpHost,
				MAGIC_LINK_SMTP_PORT: magicLinkSmtpPort,
				MAGIC_LINK_SMTP_USER: magicLinkSmtpUser,
				MAGIC_LINK_SMTP_PASSWORD: magicLinkSmtpPassword,
				MAGIC_LINK_SMTP_FROM: magicLinkSmtpFrom,
				GITHUB_CLIENT_SECRET: githubClientSecret
			});
			// Save general auth config (signup toggle used in both wizard and admin)
			if (adminConfig) {
				await updateAdminConfig(adminConfig);
			}
			// LDAP only saved in full admin mode
			if (!compact) {
				await updateLdapConfig(ENABLE_LDAP);
				if (ENABLE_LDAP) {
					await updateLdapServer(LDAP_SERVER);
				}
			}
			// Refresh global config so login page picks up new providers
			const updatedConfig = await getBackendConfig();
			config.set(updatedConfig);
			toast.success($i18n.t('Auth settings saved'));
			dispatch('saved');
		} catch {
			toast.error($i18n.t('Failed to save OAuth settings'));
		}
		saving = false;
	};

	$: googleConfigured = !!(googleClientId && googleClientSecret);
	$: githubConfigured = !!(githubClientId && githubClientSecret);
	$: anyOAuthConfigured = googleConfigured || githubConfigured;
	$: configuredProviders = [
		...(googleConfigured ? ['Google'] : []),
		...(githubConfigured ? ['GitHub'] : [])
	].join(' & ');

	// Auto-disable OAuth signup when general signups are turned off or no providers configured
	$: if (adminConfig && !adminConfig.ENABLE_SIGNUP) enableOAuthSignup = false;
	$: if (!anyOAuthConfigured) enableOAuthSignup = false;
</script>

{#if loading}
	<div style="--d:flex; --jc:center; --py:2rem; --size:0.8rem; --c:var(--color-gray-400)">
		{$i18n.t('Loading...')}
	</div>
{:else}
	<div style="--d:flex; --fd:column; --g:0.8rem">
		<!-- Google OAuth -->
		<details
			style="--radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --p:0"
		>
			<summary
				style="--d:flex; --ai:center; --jc:space-between; --p:0.8rem; cursor:pointer; --size:0.85rem; --weight:500; list-style:none"
			>
				<div style="--d:flex; --ai:center; --g:0.5rem">
					<!-- Google icon -->
					<svg viewBox="0 0 24 24" style="--w:1rem; --h:1rem" aria-hidden="true">
						<path
							d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
							fill="#4285F4"
						/>
						<path
							d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
							fill="#34A853"
						/>
						<path
							d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
							fill="#FBBC05"
						/>
						<path
							d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
							fill="#EA4335"
						/>
					</svg>
					<span>{$i18n.t('Google')}</span>
					{#if googleConfigured}
						<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500"
							>{$i18n.t('configured')}</span
						>
					{/if}
				</div>
				<!-- Chevron indicator -->
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:0.8rem; --h:0.8rem; --c:var(--color-gray-400); --tn:transform 150ms ease"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"
						clip-rule="evenodd"
					/>
				</svg>
			</summary>
			<div style="--px:0.8rem; --pb:0.8rem; --d:flex; --fd:column; --g:0.6rem">
				<!-- Setup instructions with direct link -->
				<div
					style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --lh:1.5"
				>
					<a
						href="https://console.cloud.google.com/apis/credentials"
						target="_blank"
						rel="noopener"
						style="--c:var(--color-blue-500); --td:underline"
						>{$i18n.t('Open Google Cloud Console')}&nbsp;&#8599;</a
					>
					&mdash; {$i18n.t(
						'create an OAuth 2.0 Client ID under Credentials > Create Credentials > OAuth client ID. Choose "Web application" as the type.'
					)}
					{#if webuiUrl}
						{$i18n.t('Set the authorized redirect URI to:')}
						<code
							style="--size:0.65rem; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --px:0.3rem; --py:0.1rem; --radius:0.25rem; word-break:break-all"
						>
							{webuiUrl}/oauth/google/callback
						</code>
					{/if}
				</div>
				<div style="--d:flex; --fd:column; --g:0.4rem">
					<label style="--size:0.75rem; --weight:500">{$i18n.t('Client ID')}</label>
					<input
						type="text"
						bind:value={googleClientId}
						placeholder="123456789.apps.googleusercontent.com"
						style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
					/>
				</div>
				<div style="--d:flex; --fd:column; --g:0.4rem">
					<label style="--size:0.75rem; --weight:500">{$i18n.t('Client Secret')}</label>
					<div
						style="--d:flex; --ai:center; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --px:0.5rem"
					>
						<SensitiveInput
							bind:value={googleClientSecret}
							placeholder="GOCSPX-..."
							required={false}
						/>
					</div>
				</div>
			</div>
		</details>

		<!-- GitHub OAuth -->
		<details
			style="--radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --p:0"
		>
			<summary
				style="--d:flex; --ai:center; --jc:space-between; --p:0.8rem; cursor:pointer; --size:0.85rem; --weight:500; list-style:none"
			>
				<div style="--d:flex; --ai:center; --g:0.5rem">
					<!-- GitHub icon -->
					<svg
						viewBox="0 0 16 16"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
						aria-hidden="true"
					>
						<path
							d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"
						/>
					</svg>
					<span>{$i18n.t('GitHub')}</span>
					{#if githubConfigured}
						<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500"
							>{$i18n.t('configured')}</span
						>
					{/if}
				</div>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:0.8rem; --h:0.8rem; --c:var(--color-gray-400); --tn:transform 150ms ease"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"
						clip-rule="evenodd"
					/>
				</svg>
			</summary>
			<div style="--px:0.8rem; --pb:0.8rem; --d:flex; --fd:column; --g:0.6rem">
				<div
					style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --lh:1.5"
				>
					<a
						href="https://github.com/settings/developers"
						target="_blank"
						rel="noopener"
						style="--c:var(--color-blue-500); --td:underline"
						>{$i18n.t('Open GitHub Developer Settings')}&nbsp;&#8599;</a
					>
					&mdash; {$i18n.t('click "New OAuth App", fill in your app name and homepage URL.')}
					{#if webuiUrl}
						{$i18n.t('Set the authorization callback URL to:')}
						<code
							style="--size:0.65rem; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --px:0.3rem; --py:0.1rem; --radius:0.25rem; word-break:break-all"
						>
							{webuiUrl}/oauth/github/callback
						</code>
					{/if}
				</div>
				<div style="--d:flex; --fd:column; --g:0.4rem">
					<label style="--size:0.75rem; --weight:500">{$i18n.t('Client ID')}</label>
					<input
						type="text"
						bind:value={githubClientId}
						placeholder="Iv1.abc123..."
						style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
					/>
				</div>
				<div style="--d:flex; --fd:column; --g:0.4rem">
					<label style="--size:0.75rem; --weight:500">{$i18n.t('Client Secret')}</label>
					<div
						style="--d:flex; --ai:center; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --px:0.5rem"
					>
						<SensitiveInput
							bind:value={githubClientSecret}
							placeholder="ghp_..."
							required={false}
						/>
					</div>
				</div>
			</div>
		</details>

		<!-- Email Magic Link Login (Beta) -->
		<details
			style="--radius:0.75rem; --bc:var(--color-amber-100); --dark-bc:var(--color-amber-900); --bw:1px; --bs:solid; --p:0"
		>
			<summary
				style="--d:flex; --ai:center; --jc:space-between; --p:0.8rem; cursor:pointer; --size:0.85rem; --weight:500; list-style:none"
			>
				<div style="--d:flex; --ai:center; --g:0.5rem">
					<!-- Email icon -->
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
						aria-hidden="true"
					>
						<path
							d="M2.5 3A1.5 1.5 0 0 0 1 4.5v.793c.026.009.051.02.076.032L7.674 8.51c.206.1.446.1.652 0l6.598-3.185A.755.755 0 0 1 15 5.293V4.5A1.5 1.5 0 0 0 13.5 3h-11Z"
						/>
						<path
							d="M15 6.954 8.978 9.86a2.25 2.25 0 0 1-1.956 0L1 6.954V11.5A1.5 1.5 0 0 0 2.5 13h11a1.5 1.5 0 0 0 1.5-1.5V6.954Z"
						/>
					</svg>
					<span>{$i18n.t('Email Magic Link')}</span>
					<span
						style="--size:0.55rem; --c:var(--color-amber-600); --weight:600; --px:0.3rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-amber-100); --dark-bgc:var(--color-amber-900); --dark-c:var(--color-amber-400)"
						>{$i18n.t('Beta')}</span
					>
					{#if enableMagicLinkLogin && magicLinkSmtpHost}
						<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500"
							>{$i18n.t('configured')}</span
						>
					{/if}
				</div>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					style="--w:0.8rem; --h:0.8rem; --c:var(--color-gray-400); --tn:transform 150ms ease"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"
						clip-rule="evenodd"
					/>
				</svg>
			</summary>
			<div style="--px:0.8rem; --pb:0.8rem; --d:flex; --fd:column; --g:0.6rem">
				<div
					style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --lh:1.5"
				>
					{$i18n.t(
						'Users with existing accounts can sign in by clicking a link sent to their email. No password needed. Requires SMTP.'
					)}
				</div>
				<!-- Enable toggle -->
				<label style="--d:flex; --ai:center; --g:0.6rem; cursor:pointer">
					<input
						type="checkbox"
						bind:checked={enableMagicLinkLogin}
						style="--w:1rem; --h:1rem; --shrink:0"
					/>
					<span style="--size:0.8rem; --weight:500">{$i18n.t('Enable Email Magic Link Login')}</span
					>
				</label>
				<!-- SMTP fields (shown when enabled) -->
				{#if enableMagicLinkLogin}
					<div style="--d:flex; --fd:column; --g:0.5rem; --mt:0.2rem">
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --g:0.3rem; --fx:1 1 0%">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('SMTP Host')}</label>
								<input
									type="text"
									bind:value={magicLinkSmtpHost}
									placeholder="smtp.gmail.com"
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
							<div style="--d:flex; --fd:column; --g:0.3rem; --w:5rem">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Port')}</label>
								<input
									type="number"
									bind:value={magicLinkSmtpPort}
									placeholder="587"
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
						</div>
						<div style="--d:flex; --fd:column; --g:0.3rem">
							<label style="--size:0.75rem; --weight:500">{$i18n.t('Username')}</label>
							<input
								type="text"
								bind:value={magicLinkSmtpUser}
								placeholder="you@gmail.com"
								style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
							/>
						</div>
						<div style="--d:flex; --fd:column; --g:0.3rem">
							<label style="--size:0.75rem; --weight:500">{$i18n.t('Password')}</label>
							<div
								style="--d:flex; --ai:center; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --px:0.5rem"
							>
								<SensitiveInput
									bind:value={magicLinkSmtpPassword}
									placeholder={$i18n.t('App password or SMTP password')}
									required={false}
								/>
							</div>
						</div>
						<div style="--d:flex; --fd:column; --g:0.3rem">
							<label style="--size:0.75rem; --weight:500">{$i18n.t('From Address')}</label>
							<input
								type="email"
								bind:value={magicLinkSmtpFrom}
								placeholder="noreply@yourdomain.com"
								style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
							/>
						</div>
					</div>
				{/if}
			</div>
		</details>

		<!-- Sage.is Login — coming soon, greyed out and non-interactive -->
		<div
			style="--radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --p:0; --opacity:0.5; pointer-events:none"
		>
			<div
				style="--d:flex; --ai:center; --jc:space-between; --p:0.8rem; --size:0.85rem; --weight:500"
			>
				<div style="--d:flex; --ai:center; --g:0.5rem">
					<!-- Sage icon -->
					<svg
						viewBox="0 0 16 16"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
						aria-hidden="true"
					>
						<path
							d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1Zm0 2.5a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5ZM6.5 7.5h3v4.5h-1V8.5h-2v-1Z"
						/>
					</svg>
					<span>{$i18n.t('Sage.is Login')}</span>
					<span
						style="--size:0.55rem; --c:var(--color-gray-500); --weight:600; --px:0.3rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700); --dark-c:var(--color-gray-400)"
						>{$i18n.t('Coming Soon')}</span
					>
				</div>
			</div>
			<div
				style="--px:0.8rem; --pb:0.8rem; --size:0.7rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --lh:1.5"
			>
				{$i18n.t(
					'Sign in with Google or GitHub through auth.sage.is. No OAuth app setup required.'
				)}
			</div>
		</div>

		<!-- OAuth merge and Signup controls — shown in both wizard and admin -->
		{#if compact && adminConfig}
			<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.6rem" />
			<div style="--d:flex; --fd:column; --g:0.5rem; --mb:0.4rem">
				<label style="--d:flex; --ai:center; --g:0.6rem; cursor:pointer">
					<input
						type="checkbox"
						bind:checked={mergeAccountsByEmail}
						style="--w:1rem; --h:1rem; --shrink:0"
					/>
					<div>
						<div style="--d:flex; --ai:center; --g:0.4rem">
							<span style="--size:0.8rem; --weight:500">{$i18n.t('Merge Accounts by Email')}</span>
							<Tooltip
								content={$i18n.t(
									'Link an OAuth login to an existing account if the email matches. Disable if you want OAuth and password accounts to stay separate.'
								)}
								placement="right"
								className="flex items-center"
							>
								<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"
									><Icon name="question-mark-circle" strokeWidth="2" className="size-3.5" /></span
								>
							</Tooltip>
						</div>
					</div>
				</label>
			</div>

			<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.6rem" />

			<div style="--d:flex; --fd:column; --g:0.5rem">
				<!-- Enable New Sign Ups -->
				<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
					<span style="--size:0.8rem; --weight:500">{$i18n.t('Enable New Sign Ups')}</span>
					<div style="--d:flex; --ai:center; --g:0.6rem">
						{#if adminConfig.ENABLE_SIGNUP}
							<span
								style="--size:0.65rem; --c:var(--color-amber-600); --dark-c:var(--color-amber-400)"
							>
								{$i18n.t('Open registration: remember to review new accounts regularly.')}
							</span>
						{/if}
						<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
					</div>
				</div>

				<!-- Allow OAuth Signup — gated behind Enable New Sign Ups + at least one provider configured -->
				{#if adminConfig.ENABLE_SIGNUP && anyOAuthConfigured}
					<label style="--d:flex; --ai:center; --g:0.6rem; cursor:pointer; --ml:auto;--mr:1rem">
						{#if enableOAuthSignup}
							<div
								style="--size:0.65rem; --c:var(--color-amber-600); --dark-c:var(--color-amber-400); --mt:0.2rem"
							>
								{$i18n.t('{{providers}} sign-up is open — review new accounts regularly.', {
									providers: configuredProviders
								})}
							</div>
						{/if}
						<input
							type="checkbox"
							bind:checked={enableOAuthSignup}
							style="--w:1rem; --h:1rem; --shrink:0"
						/>
						<div>
							<div style="--d:flex; --ai:center; --g:0.4rem;">
								<span style="--size:0.8rem; --weight:500">{$i18n.t('Allow OAuth Signup')}</span>
								<Tooltip
									content={$i18n.t(
										'When enabled, new users can create accounts by signing in with {{providers}}. When disabled, only existing users can use OAuth to sign in.',
										{ providers: configuredProviders }
									)}
									placement="right"
									className="flex items-center"
								>
									<span
										style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"
										><Icon name="question-mark-circle" strokeWidth="2" className="size-3.5" /></span
									>
								</Tooltip>
							</div>
						</div>
					</label>
				{/if}
			</div>
		{/if}
	</div>

	<!-- General auth settings (full admin mode only, not shown in wizard) -->
	{#if !compact && adminConfig}
		<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:1rem" />

		<div style="--d:flex; --fd:column; --g:0.6rem">
			<!-- Allow OAuth Signup — gated behind Enable New Sign Ups + at least one provider configured -->
			{#if adminConfig.ENABLE_SIGNUP && anyOAuthConfigured}
				<label
					style="--d:flex; --ai:center; --g:0.6rem; cursor:pointer; --pl:1rem; --ml:auto; --mr:1rem"
				>
					<input
						type="checkbox"
						bind:checked={enableOAuthSignup}
						style="--w:1rem; --h:1rem; --shrink:0"
					/>
					<div>
						<div style="--d:flex; --ai:center; --g:0.4rem">
							<span style="--size:0.8rem; --weight:500">{$i18n.t('Allow OAuth Signup')}</span>
							<Tooltip
								content={$i18n.t(
									'When enabled, new users can create accounts by signing in with {{providers}}. When disabled, only existing users can use OAuth to sign in.',
									{ providers: configuredProviders }
								)}
								placement="right"
								className="flex items-center"
							>
								<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"
									><Icon name="question-mark-circle" strokeWidth="2" className="size-3.5" /></span
								>
							</Tooltip>
						</div>
						{#if enableOAuthSignup}
							<div
								style="--size:0.65rem; --c:var(--color-amber-600); --dark-c:var(--color-amber-400); --mt:0.2rem"
							>
								{$i18n.t('{{providers}} sign-up is open — review new accounts regularly.', {
									providers: configuredProviders
								})}
							</div>
						{/if}
					</div>
				</label>
			{/if}

			<!-- Default User Role -->
			<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
				<span style="--size:0.8rem; --weight:500">{$i18n.t('Default User Role')}</span>
				<select
					style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.25rem; --px:0.5rem; --size:0.8rem; --bgc:transparent; --oe:none"
					bind:value={adminConfig.DEFAULT_USER_ROLE}
				>
					<option value="pending">{$i18n.t('pending')}</option>
					<option value="user">{$i18n.t('user')}</option>
					<option value="facilitator">{$i18n.t('facilitator')}</option>
					<option value="admin">{$i18n.t('admin')}</option>
				</select>
			</div>

			<!-- Show Admin Details in Pending Overlay -->
			<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
				<span style="--size:0.8rem; --weight:500"
					>{$i18n.t('Show Admin Details in Account Pending Overlay')}</span
				>
				<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
			</div>

			<!-- Pending Overlay customization -->
			<details
				style="--radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --p:0"
			>
				<summary
					style="--d:flex; --ai:center; --p:0.8rem; cursor:pointer; --size:0.85rem; --weight:500; list-style:none"
				>
					{$i18n.t('Pending User Overlay')}
				</summary>
				<div style="--px:0.8rem; --pb:0.8rem; --d:flex; --fd:column; --g:0.5rem">
					<div style="--d:flex; --fd:column; --g:0.3rem">
						<label style="--size:0.75rem; --weight:500">{$i18n.t('Title')}</label>
						<Textarea
							placeholder={$i18n.t(
								'Enter a title for the pending user overlay. Leave empty for default.'
							)}
							bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
						/>
					</div>
					<div style="--d:flex; --fd:column; --g:0.3rem">
						<label style="--size:0.75rem; --weight:500">{$i18n.t('Content')}</label>
						<Textarea
							placeholder={$i18n.t(
								'Enter content for the pending user overlay. Leave empty for default.'
							)}
							bind:value={adminConfig.PENDING_USER_OVERLAY_CONTENT}
						/>
					</div>
				</div>
			</details>

			<!-- Enable API Key -->
			<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
				<span style="--size:0.8rem; --weight:500">{$i18n.t('Enable API Key')}</span>
				<Switch bind:state={adminConfig.ENABLE_API_KEY} />
			</div>

			{#if adminConfig?.ENABLE_API_KEY}
				<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
					<span style="--size:0.8rem; --weight:500">{$i18n.t('API Key Endpoint Restrictions')}</span
					>
					<Switch bind:state={adminConfig.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS} />
				</div>
				{#if adminConfig?.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS}
					<div style="--d:flex; --fd:column; --g:0.3rem">
						<label style="--size:0.75rem; --weight:500">{$i18n.t('Allowed Endpoints')}</label>
						<input
							type="text"
							placeholder="/api/v1/messages, /api/v1/channels"
							bind:value={adminConfig.API_KEY_ALLOWED_ENDPOINTS}
							style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
						/>
					</div>
				{/if}
			{/if}

			<!-- JWT Expiration -->
			<div style="--d:flex; --fd:column; --g:0.3rem">
				<label style="--size:0.8rem; --weight:500">{$i18n.t('JWT Expiration')}</label>
				<input
					type="text"
					placeholder={$i18n.t('e.g. 30m, 1h, 10d, or -1 for no expiration')}
					bind:value={adminConfig.JWT_EXPIRES_IN}
					style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
				/>
				<div style="--size:0.7rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
					{$i18n.t('Valid units: s, m, h, d, w — or -1 for no expiration.')}
				</div>
			</div>

			<!-- LDAP -->
			<details
				style="--radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --p:0"
			>
				<summary
					style="--d:flex; --ai:center; --jc:space-between; --p:0.8rem; cursor:pointer; --size:0.85rem; --weight:500; list-style:none"
				>
					<span>{$i18n.t('LDAP')}</span>
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div on:click|stopPropagation>
						<Switch bind:state={ENABLE_LDAP} />
					</div>
				</summary>
				{#if ENABLE_LDAP}
					<div style="--px:0.8rem; --pb:0.8rem; --d:flex; --fd:column; --g:0.5rem">
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --g:0.3rem; --fx:1 1 0%">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Label')}</label>
								<input
									type="text"
									bind:value={LDAP_SERVER.label}
									placeholder={$i18n.t('Enter server label')}
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
						</div>
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --g:0.3rem; --fx:1 1 0%">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Host')}</label>
								<input
									type="text"
									bind:value={LDAP_SERVER.host}
									placeholder={$i18n.t('Enter server host')}
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
							<div style="--d:flex; --fd:column; --g:0.3rem; --w:5rem">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Port')}</label>
								<input
									type="number"
									bind:value={LDAP_SERVER.port}
									placeholder="389"
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
						</div>
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --g:0.3rem; --fx:1 1 0%">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Application DN')}</label>
								<input
									type="text"
									bind:value={LDAP_SERVER.app_dn}
									placeholder={$i18n.t('Enter Application DN')}
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
							<div style="--d:flex; --fd:column; --g:0.3rem; --fx:1 1 0%">
								<label style="--size:0.75rem; --weight:500"
									>{$i18n.t('Application DN Password')}</label
								>
								<div
									style="--d:flex; --ai:center; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --px:0.5rem"
								>
									<SensitiveInput
										bind:value={LDAP_SERVER.app_dn_password}
										placeholder={$i18n.t('Enter Application DN Password')}
										required={false}
									/>
								</div>
							</div>
						</div>
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --g:0.3rem; --fx:1 1 0%">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Attribute for Mail')}</label>
								<input
									type="text"
									bind:value={LDAP_SERVER.attribute_for_mail}
									placeholder="mail"
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
							<div style="--d:flex; --fd:column; --g:0.3rem; --fx:1 1 0%">
								<label style="--size:0.75rem; --weight:500"
									>{$i18n.t('Attribute for Username')}</label
								>
								<input
									type="text"
									bind:value={LDAP_SERVER.attribute_for_username}
									placeholder="uid"
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
						</div>
						<div style="--d:flex; --fd:column; --g:0.3rem">
							<label style="--size:0.75rem; --weight:500">{$i18n.t('Search Base')}</label>
							<input
								type="text"
								bind:value={LDAP_SERVER.search_base}
								placeholder="ou=users,dc=foo,dc=example"
								style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
							/>
						</div>
						<div style="--d:flex; --fd:column; --g:0.3rem">
							<label style="--size:0.75rem; --weight:500">{$i18n.t('Search Filters')}</label>
							<input
								type="text"
								bind:value={LDAP_SERVER.search_filters}
								placeholder="(&(objectClass=inetOrgPerson)(uid=%s))"
								style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
							/>
							<a
								href="https://ldap.com/ldap-filters/"
								target="_blank"
								rel="noopener"
								style="--size:0.7rem; --c:var(--color-blue-500); --td:underline"
								>{$i18n.t('LDAP filter guide')}</a
							>
						</div>
						<!-- TLS -->
						<div style="--d:flex; --jc:space-between; --ai:center">
							<span style="--size:0.8rem; --weight:500">{$i18n.t('TLS')}</span>
							<Switch bind:state={LDAP_SERVER.use_tls} />
						</div>
						{#if LDAP_SERVER.use_tls}
							<div style="--d:flex; --fd:column; --g:0.3rem">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Certificate Path')}</label>
								<input
									type="text"
									bind:value={LDAP_SERVER.certificate_path}
									placeholder={$i18n.t('Enter certificate path')}
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
							<div style="--d:flex; --jc:space-between; --ai:center">
								<span style="--size:0.75rem; --weight:500">{$i18n.t('Validate Certificate')}</span>
								<Switch bind:state={LDAP_SERVER.validate_cert} />
							</div>
							<div style="--d:flex; --fd:column; --g:0.3rem">
								<label style="--size:0.75rem; --weight:500">{$i18n.t('Ciphers')}</label>
								<input
									type="text"
									bind:value={LDAP_SERVER.ciphers}
									placeholder="ALL"
									style="--w:100%; --size:0.8rem; --p:0.5rem; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent"
								/>
							</div>
						{/if}
					</div>
				{/if}
			</details>
		</div>
	{/if}

	<!-- Save button (full admin mode only, not shown in wizard) -->
	{#if !compact}
		<div style="--d:flex; --jc:flex-end; --mt:1rem">
			<button
				on:click={save}
				disabled={saving}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:{!saving
					? '#000'
					: 'var(--color-gray-300)'}; --hvr-bgc:{!saving
					? 'var(--color-gray-900)'
					: 'var(--color-gray-300)'}; --c:#fff; --dark-bgc:{!saving
					? '#fff'
					: 'var(--color-gray-600)'}; --dark-c:{!saving
					? '#000'
					: 'var(--color-gray-400)'}; --hvr-dark-bgc:{!saving
					? 'var(--color-gray-100)'
					: 'var(--color-gray-600)'}; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{saving ? $i18n.t('Saving...') : $i18n.t('Save')}
			</button>
		</div>
	{/if}
{/if}
