<script lang="ts">
	import DOMPurify from 'dompurify';

	import { getVersionUpdates, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import {
		getAdminConfig,
		getLdapConfig,
		getLdapServer,
		updateAdminConfig,
		updateLdapConfig,
		updateLdapServer
	} from '$lib/apis/auths';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { config, showChangesAndSetup, setupTriggerReason } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	let adminConfig = null;
	let webhookUrl = '';

	// LDAP
	let ENABLE_LDAP = false;
	let LDAP_SERVER = {
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

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.info(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.info(updateAvailable);
	};

	const updateLdapServerHandler = async () => {
		if (!ENABLE_LDAP) return;
		const res = await updateLdapServer(LDAP_SERVER).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('LDAP server updated'));
		}
	};

	const updateHandler = async () => {
		webhookUrl = await updateWebhookUrl(localStorage.token, webhookUrl);
		const res = await updateAdminConfig(adminConfig);
		await updateLdapConfig(ENABLE_LDAP);
		await updateLdapServerHandler();

		if (res) {
			saveHandler();
		} else {
			toast.error($i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}

		await Promise.all([
			(async () => {
				adminConfig = await getAdminConfig();
			})(),

			(async () => {
				webhookUrl = await getWebhookUrl(localStorage.token);
			})(),
			(async () => {
				LDAP_SERVER = await getLdapServer();
			})()
		]);

		const ldapConfig = await getLdapConfig();
		ENABLE_LDAP = ldapConfig.ENABLE_LDAP;
	});
</script>

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.8rem"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div style="--mt:0.125rem; --g:0.6rem; --ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if adminConfig !== null}
			<div class="">
				<div style="--mb:0.8rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('General')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem">
						<div style="--mb:0.2rem; --size:0.6rem; --weight:500; --d:flex; --g:0.5rem; --ai:center">
							<div>
								{$i18n.t('Version')}
							</div>
						</div>
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--d:flex; --fd:column; --size:0.6rem; --c:var(--color-gray-700); --dark-c:var(--color-gray-200)">
								<div style="--d:flex; --g:0.2rem">
									<Tooltip content={WEBUI_BUILD_HASH}>
										v{WEBUI_VERSION}
									</Tooltip>

									{#if $config?.features?.enable_version_update_check}
										<a
											href="https://github.com/Sage-is/AI-UI/releases/tag/v{version.latest}"
											target="_blank"
										>
											{updateAvailable === null
												? $i18n.t('Checking for updates...')
												: updateAvailable
													? `(v${version.latest} ${$i18n.t('available!')})`
													: $i18n.t('(latest)')}
										</a>
									{/if}
								</div>

								<button
									style="--td:underline; --d:flex; --ai:center; --g:0.2rem; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500)"
									type="button"
									on:click={() => {
										setupTriggerReason.set({ hasChangelog: true, needsModels: false, needsUsers: false, manualTrigger: false });
										showChangesAndSetup.set(true);
									}}
								>
									<div>{$i18n.t("See what's new")}</div>
								</button>

								<button
									style="--td:underline; --d:flex; --ai:center; --g:0.2rem; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500)"
									type="button"
									on:click={() => {
										setupTriggerReason.set({ hasChangelog: false, needsModels: false, needsUsers: false, manualTrigger: true });
										showChangesAndSetup.set(true);
									}}
								>
									<div>{$i18n.t('Run Setup Wizard')}</div>
								</button>
							</div>

							{#if $config?.features?.enable_version_update_check}
								<button
									style="--size:0.6rem; --px:0.6rem; --py:0.4rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --weight:500"
									type="button"
									on:click={() => {
										checkForVersionUpdates();
									}}
								>
									{$i18n.t('Check for updates')}
								</button>
							{/if}
						</div>
					</div>

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--size:0.6rem; --pr:0.5rem">
								<div class="">
									{$i18n.t('Help')}
								</div>
								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									{$i18n.t('Discover how to use Sage.is AI and seek support from the community.')}
								</div>
							</div>

							<a
								style="--size:0.6rem; --weight:500; --td:underline"
	class="flex-shrink-0"
								href="https://docs.sage.is/"
								target="_blank"
							>
								{$i18n.t('Documentation')}
							</a>
						</div>

						<div style="--mt:0.2rem">
							<div style="--d:flex; --g:0.2rem">
								<a href="https://x.com/Sage_Is_AI" target="_blank">
									<img
										alt="X (formerly Twitter) Follow"
										src="https://img.shields.io/badge/X-Follow-black.svg?style=for-the-badge&logoColor=white"
									/>
								</a>

								<a href="http://linkedin.com/company/sage-is-ai" target="_blank">
									<a href="http://linkedin.com/company/sage-is-ai" target="_blank">
										<img
											alt="LinkedIn Follow"
											src="https://img.shields.io/badge/LinkedIn-Follow-blue.svg?style=for-the-badge&logo=linkedin&logoColor=white"
										/>
									</a>
								</a>

								<a href="https://bsky.app/profile/sage-is-ai.bsky.social" target="_blank">
									<img
										alt="Bluesky Follow"
										src="https://img.shields.io/badge/bluesky-%230A7AFF.svg?style=for-the-badge&logo=bluesky&logoColor=white&label=Follow"
									/>
								</a>

								<a href="https://github.com/Sage-is/AI-UI" target="_blank">
									<img
										alt="Github Repo"
										src="https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white&label=Star us on"
									/>
								</a>
							</div>
						</div>
					</div>

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--size:0.6rem; --pr:0.5rem">
								<div class="">
									{$i18n.t('License')}
								</div>

								{#if $config?.license_metadata}
									<a href="https://docs.sage.is/license" target="_blank" style="--c:var(--color-gray-500); --mt:0.125rem">
										<span style="--tt:capitalize; --c:#000; --dark-c:#fff"
											>{$config?.license_metadata?.type}
											license</span
										>
										registered to
										<span style="--tt:capitalize; --c:#000; --dark-c:#fff"
											>{$config?.license_metadata?.organization_name}</span
										>
										for
										<span style="--weight:500; --c:#000; --dark-c:#fff"
											>{$config?.license_metadata?.seats ?? 'Unlimited'} users.</span
										>
									</a>
									{#if $config?.license_metadata?.html}
										<div style="--mt:0.125rem">
											{@html DOMPurify.sanitize($config?.license_metadata?.html)}
										</div>
									{/if}
								{:else}
									<a
										style="--size:0.6rem; --hvr-td:underline"
										href="https://docs.sage.is/license"
										target="_blank"
									>
										<span style="--c:var(--color-gray-500)">
											{$i18n.t(
												'Sage.is AI runs on open source. Always will. No lock-in. No tricks. Full AGPL freedom. Enterprise teams please stand with us. Sponsor the future of Honest and Real Open AI.'
											)}
										</span>
									</a>
								{/if}
							</div>

							<!-- <button
								style="--size:0.6rem; --px:0.6rem; --py:0.4rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --weight:500"
	class="flex-shrink-0"
							>
								{$i18n.t('Activate')}
							</button> -->
						</div>
					</div>
				</div>

				<div style="--mb:0.6rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Authentication')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem; --d:flex; --w:100%; --jc:space-between">
						<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Default User Role')}</div>
						<div style="--d:flex; --ai:center; --pos:relative">
							<select
								style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --size:0.6rem; --bgc:transparent; --oe:none; --ta:right"
								bind:value={adminConfig.DEFAULT_USER_ROLE}
								placeholder="Select a role"
							>
								<option value="pending">{$i18n.t('pending')}</option>
								<option value="user">{$i18n.t('user')}</option>
								<option value="facilitator">{$i18n.t('facilitator')}</option>
								<option value="temporary">{$i18n.t('temporary')}</option>
								<option value="admin">{$i18n.t('admin')}</option>
							</select>
						</div>
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Enable New Sign Ups')}</div>

						<Switch bind:state={adminConfig.ENABLE_SIGNUP} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('Show Admin Details in Account Pending Overlay')}
						</div>

						<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
					</div>

					<div style="--mb:0.625rem">
						<div style="--as:center; --size:0.6rem; --weight:500; --mb:0.5rem">
							{$i18n.t('Pending User Overlay Title')}
						</div>
						<Textarea
							placeholder={$i18n.t(
								'Enter a title for the pending user info overlay. Leave empty for default.'
							)}
							bind:value={adminConfig.PENDING_USER_OVERLAY_TITLE}
						/>
					</div>

					<div style="--mb:0.625rem">
						<div style="--as:center; --size:0.6rem; --weight:500; --mb:0.5rem">
							{$i18n.t('Pending User Overlay Content')}
						</div>
						<Textarea
							placeholder={$i18n.t(
								'Enter content for the pending user info overlay. Leave empty for default.'
							)}
							bind:value={adminConfig.PENDING_USER_OVERLAY_CONTENT}
						/>
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Enable API Key')}</div>

						<Switch bind:state={adminConfig.ENABLE_API_KEY} />
					</div>

					{#if adminConfig?.ENABLE_API_KEY}
						<div style="--mb:0.625rem; --d:flex; --w:100%; --jc:space-between; --pr:0.5rem">
							<div style="--as:center; --size:0.6rem; --weight:500">
								{$i18n.t('API Key Endpoint Restrictions')}
							</div>

							<Switch bind:state={adminConfig.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS} />
						</div>

						{#if adminConfig?.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS}
							<div style="--d:flex; --w:100%; --fd:column; --pr:0.5rem">
								<div style="--size:0.6rem; --weight:500">
									{$i18n.t('Allowed Endpoints')}
								</div>

								<input
									style="--w:100%; --mt:0.2rem; --radius:0.5rem; --size:0.8rem; --dark-c:var(--color-gray-300); --bgc:transparent; --oe:none"
									type="text"
									placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
									bind:value={adminConfig.API_KEY_ALLOWED_ENDPOINTS}
								/>

								<div style="--mt:0.5rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
									<!-- https://docs.sage.is/getting-started/advanced-topics/api-endpoints -->
									<a
										href="https://docs.sage.is/getting-started/api-endpoints"
										target="_blank"
										style="--c:var(--color-gray-300); --weight:500; --td:underline"
									>
										{$i18n.t('To learn more about available endpoints, visit our documentation.')}
									</a>
								</div>
							</div>
						{/if}
					{/if}

					<div style="--mb:0.625rem; --w:100%; --jc:space-between">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('JWT Expiration')}</div>
						</div>

						<div style="--d:flex; --mt:0.5rem; --g:0.5rem">
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								type="text"
								placeholder={`e.g.) "30m","1h", "10d". `}
								bind:value={adminConfig.JWT_EXPIRES_IN}
							/>
						</div>

						<div style="--mt:0.5rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
							{$i18n.t('Valid time units:')}
							<span style="--c:var(--color-gray-300); --weight:500"
								>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
							>
						</div>
					</div>

					<div style="--g:0.6rem">
						<div style="--mt:0.5rem; --g:0.5rem; --pr:0.4rem">
							<div style="--d:flex; --jc:space-between; --ai:center; --size:0.8rem">
								<div style="--weight:500">{$i18n.t('LDAP')}</div>

								<div style="--mt:0.2rem">
									<Switch bind:state={ENABLE_LDAP} />
								</div>
							</div>

							{#if ENABLE_LDAP}
								<div style="--d:flex; --fd:column; --g:0.2rem">
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Label')}
											</div>
											<input
												style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
												required
												placeholder={$i18n.t('Enter server label')}
												bind:value={LDAP_SERVER.label}
											/>
										</div>
										<div style="--w:100%"></div>
									</div>
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Host')}
											</div>
											<input
												style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
												required
												placeholder={$i18n.t('Enter server host')}
												bind:value={LDAP_SERVER.host}
											/>
										</div>
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Port')}
											</div>
											<Tooltip
												placement="top-start"
												content={$i18n.t('Default to 389 or 636 if TLS is enabled')}
												className="w-full"
											>
												<input
													style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
													type="number"
													placeholder={$i18n.t('Enter server port')}
													bind:value={LDAP_SERVER.port}
												/>
											</Tooltip>
										</div>
									</div>
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Application DN')}
											</div>
											<Tooltip
												content={$i18n.t('The Application Account DN you bind with for search')}
												placement="top-start"
											>
												<input
													style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
													required
													placeholder={$i18n.t('Enter Application DN')}
													bind:value={LDAP_SERVER.app_dn}
												/>
											</Tooltip>
										</div>
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Application DN Password')}
											</div>
											<SensitiveInput
												placeholder={$i18n.t('Enter Application DN Password')}
												bind:value={LDAP_SERVER.app_dn_password}
											/>
										</div>
									</div>
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Attribute for Mail')}
											</div>
											<Tooltip
												content={$i18n.t(
													'The LDAP attribute that maps to the mail that users use to sign in.'
												)}
												placement="top-start"
											>
												<input
													style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
													required
													placeholder={$i18n.t('Example: mail')}
													bind:value={LDAP_SERVER.attribute_for_mail}
												/>
											</Tooltip>
										</div>
									</div>
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Attribute for Username')}
											</div>
											<Tooltip
												content={$i18n.t(
													'The LDAP attribute that maps to the username that users use to sign in.'
												)}
												placement="top-start"
											>
												<input
													style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
													required
													placeholder={$i18n.t(
														'Example: sAMAccountName or uid or userPrincipalName'
													)}
													bind:value={LDAP_SERVER.attribute_for_username}
												/>
											</Tooltip>
										</div>
									</div>
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Search Base')}
											</div>
											<Tooltip
												content={$i18n.t('The base to search for users')}
												placement="top-start"
											>
												<input
													style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
													required
													placeholder={$i18n.t('Example: ou=users,dc=foo,dc=example')}
													bind:value={LDAP_SERVER.search_base}
												/>
											</Tooltip>
										</div>
									</div>
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--w:100%">
											<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
												{$i18n.t('Search Filters')}
											</div>
											<input
												style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
												placeholder={$i18n.t('Example: (&(objectClass=inetOrgPerson)(uid=%s))')}
												bind:value={LDAP_SERVER.search_filters}
											/>
										</div>
									</div>
									<div style="--size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
										<a
											style="--c:var(--color-gray-300); --weight:500; --td:underline"
											href="https://ldap.com/ldap-filters/"
											target="_blank"
										>
											{$i18n.t('Click here for filter guides.')}
										</a>
									</div>
									<div>
										<div style="--d:flex; --jc:space-between; --ai:center; --size:0.8rem">
											<div style="--weight:500">{$i18n.t('TLS')}</div>

											<div style="--mt:0.2rem">
												<Switch bind:state={LDAP_SERVER.use_tls} />
											</div>
										</div>
										{#if LDAP_SERVER.use_tls}
											<div style="--d:flex; --w:100%; --g:0.5rem">
												<div style="--w:100%">
													<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem; --mt:0.2rem">
														{$i18n.t('Certificate Path')}
													</div>
													<input
														style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
														placeholder={$i18n.t('Enter certificate path')}
														bind:value={LDAP_SERVER.certificate_path}
													/>
												</div>
											</div>
											<div style="--d:flex; --jc:space-between; --ai:center; --size:0.6rem">
												<div style="--weight:500">Validate certificate</div>

												<div style="--mt:0.2rem">
													<Switch bind:state={LDAP_SERVER.validate_cert} />
												</div>
											</div>
											<div style="--d:flex; --w:100%; --g:0.5rem">
												<div style="--w:100%">
													<div style="--as:center; --size:0.6rem; --weight:500; --minw:fit-content; --mb:0.2rem">
														{$i18n.t('Ciphers')}
													</div>
													<Tooltip content={$i18n.t('Default to ALL')} placement="top-start">
														<input
															style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem"
															placeholder={$i18n.t('Example: ALL')}
															bind:value={LDAP_SERVER.ciphers}
														/>
													</Tooltip>
												</div>
												<div style="--w:100%"></div>
											</div>
										{/if}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<div style="--mb:0.6rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Features')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('Enable Community Sharing')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Enable Message Rating')}</div>

						<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('Notes')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_NOTES} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('Spaces')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('User Webhooks')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
					</div>

					<div style="--mb:0.625rem">
						<div style="--as:center; --size:0.6rem; --weight:500; --mb:0.5rem">
							{$i18n.t('Response Watermark')}
						</div>
						<Textarea
							placeholder={$i18n.t('Enter a watermark for the response. Leave empty for none.')}
							bind:value={adminConfig.RESPONSE_WATERMARK}
						/>
					</div>

					<div style="--mb:0.625rem; --w:100%; --jc:space-between">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('WebUI URL')}</div>
						</div>

						<div style="--d:flex; --mt:0.5rem; --g:0.5rem">
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								type="text"
								placeholder={`e.g.) "http://localhost:3000"`}
								bind:value={adminConfig.WEBUI_URL}
							/>
						</div>

						<div style="--mt:0.5rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
							{$i18n.t(
								'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
							)}
						</div>
					</div>

					<div style="--w:100%; --jc:space-between">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Webhook URL')}</div>
						</div>

						<div style="--d:flex; --mt:0.5rem; --g:0.5rem">
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								type="text"
								placeholder={`https://example.com/webhook`}
								bind:value={webhookUrl}
							/>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
		<button
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
