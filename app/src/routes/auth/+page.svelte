<script>
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		sendMagicLink,
		verifyMagicLink
	} from '$lib/apis/auths';
	import { getBranding } from '$lib/apis/configs';
	import { restoreFromBackup } from '$lib/apis/utils';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import BrandIcon from '$lib/components/BrandIcon.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let branding = {};

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';
	let showPassword = false;

	let ldapUsername = '';

	// Backup restore state
	let showRestoreBackup = false;
	let restoreFile = null;
	let restoreLoading = false;
	let restoreFileInput;

	// Magic link email login state
	let magicLinkMode = false;
	let magicLinkEmail = '';
	let magicLinkSent = false;
	let magicLinkSending = false;

	const querystringValue = (key) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log('Login successful:', sessionUser);
			if (sessionUser?.token) {
				localStorage.token = sessionUser.token;
			}
			toast.success($i18n.t(`Logging in.`));

			// Calculate redirect path early
			const redirectPath = querystringValue('redirect') || '/';

			try {
				// Optional: Update stores and emit socket event
				// These should not block navigation if they fail
				await user.set(sessionUser);

				if ($socket?.connected) {
					$socket.emit('user-join', { auth: {} });
				}

				// Try to get backend config, but don't block redirect
				const backendConfig = await getBackendConfig().catch((err) => {
					console.warn('Failed to get backend config:', err);
					return null;
				});
				if (backendConfig) {
					await config.set(backendConfig);
				}
			} catch (err) {
				console.error('Error during post-login setup:', err);
				// Continue to redirect anyway
			}

			// ALWAYS redirect after login
			console.log('Redirecting to:', redirectPath);
			window.location.href = redirectPath;
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const handleRestoreBackup = async () => {
		if (!restoreFile) return;
		restoreLoading = true;
		try {
			await restoreFromBackup(restoreFile);
			toast.success($i18n.t('Backup restored successfully. Reloading...'));
			setTimeout(() => {
				window.location.reload();
			}, 1500);
		} catch (error) {
			toast.error(`${error}`);
			restoreLoading = false;
		}
	};

	const formatFileSize = (bytes) => {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	};

	const handleMagicLinkSend = async () => {
		magicLinkSending = true;
		try {
			await sendMagicLink(magicLinkEmail);
			magicLinkSent = true;
		} catch {
			toast.error(
				$i18n.t('Failed to send login link. Check with your admin that SMTP is configured.')
			);
		}
		magicLinkSending = false;
	};

	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);

		// Magic link token (email login)
		const magicToken = params.get('magic_token');
		if (magicToken) {
			try {
				const sessionUser = await verifyMagicLink(magicToken);
				if (sessionUser) {
					await setSessionUser(sessionUser);
				}
			} catch (err) {
				toast.error($i18n.t('Invalid or expired link. Please request a new one.'));
			}
			return;
		}

		// OAuth token
		const token = params.get('token');
		if (!token) {
			return;
		}
		// In cookie-based auth, the backend should set the cookie on redirect.
		// We call getSessionUser() without args to verify the session.
		const sessionUser = await getSessionUser().catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			// If custom branding logo is set, use it (with dark mode variant support)
			if (branding?.logo_url || branding?.logo_dark_url) {
				const isDarkMode = document.documentElement.classList.contains('dark');
				if (isDarkMode && branding?.logo_dark_url) {
					logo.src = branding.logo_dark_url;
				} else if (branding?.logo_url) {
					logo.src = branding.logo_url;
				}
				logo.style.filter = '';
				return;
			}

			// Fallback to default logo behavior
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/icons/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/icons/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
		await checkOauthCallback();

		// Load branding
		try {
			branding = await getBranding();
			console.log('Loaded branding:', branding);

			// Apply custom colors if set
			if (branding.primary_color) {
				document.documentElement.style.setProperty('--brand-primary', branding.primary_color);
			}
			if (branding.accent_color) {
				document.documentElement.style.setProperty('--brand-accent', branding.accent_color);
			}

			// Update favicon if custom one is set
			if (branding.favicon_url) {
				const favicon =
					document.querySelector('link[rel="icon"]') || document.createElement('link');
				favicon.setAttribute('rel', 'icon');
				favicon.setAttribute('href', branding.favicon_url);
				if (!document.querySelector('link[rel="icon"]')) {
					document.head.appendChild(favicon);
				}
			}
		} catch (err) {
			console.error('Failed to load branding:', err);
		}

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div style="--w:100%; --h:100vh; --maxh:100dvh; --c:#fff; --pos:relative">
	<div
		style="--w:100%; --h:100%; --pos:absolute; --top:0; --left:0; --bgc:#fff; --dark-bgc:#000"
	></div>

	<div
		style="--w:100%; --pos:absolute; --top:0; --left:0; --right:0; --h:2rem"
		class="drag-region"
	/>

	{#if loaded}
		<div
			style="--pos:fixed; --bgc:transparent; --minh:100vh; --w:100%; --d:flex; --jc:center; --z:50; --c:#000; --dark-c:#fff"
			class="font-primary"
		>
			<div style="--w:100%; --px:2.5rem; --minh:100vh; --d:flex; --fd:column; --ta:center">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div style="--my:auto; --pb:2.5rem; --w:100%; --maxw-sm:28rem">
						<div
							style="--d:flex; --ai:center; --jc:center; --g:0.6rem; --size:1.2rem; --size-sm:1.5rem; --ta:center; --weight:600; --dark-c:var(--color-gray-200)"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', {
									WEBUI_NAME: branding?.title || $WEBUI_NAME
								})}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
					<div style="--my:auto; --d:flex; --fd:column; --jc:center; --ai:center">
						<div
							style="--maxw-sm:28rem; --my:auto; --pb:2.5rem; --w:100%; --dark-c:var(--color-gray-100)"
						>
							<form
								style="--d:flex; --fd:column; --jc:center"
								on:submit={(e) => {
									e.preventDefault();
									submitHandler();
								}}
							>
								<!-- Centered Logo -->
								<div style="--d:flex; --jc:center; --mb:1.5rem">
									<img
										id="logo"
										crossorigin="anonymous"
										src={branding?.logo_url || `${WEBUI_BASE_URL}/static/icons/favicon.png`}
										style="--w:4rem; --h:4rem; --radius:9999px"
										alt="Logo"
									/>
								</div>

								<div style="--mb:0.2rem">
									<div style="--size:1.5rem; --weight:500">
										{#if $config?.onboarding ?? false}
											{$i18n.t(`Get started with {{WEBUI_NAME}}`, {
												WEBUI_NAME: branding?.title || $WEBUI_NAME
											})}
										{:else if mode === 'ldap'}
											{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, {
												WEBUI_NAME: branding?.title || $WEBUI_NAME
											})}
										{:else if mode === 'signin'}
											{$i18n.t(`Sign in to {{WEBUI_NAME}}`, {
												WEBUI_NAME: branding?.title || $WEBUI_NAME
											})}
										{:else}
											{$i18n.t(`Sign up to {{WEBUI_NAME}}`, {
												WEBUI_NAME: branding?.title || $WEBUI_NAME
											})}
										{/if}
									</div>

									{#if branding?.subtitle}
										<div
											style="--mt:0.2rem; --size:0.6rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-500)"
										>
											{branding?.subtitle}
										</div>
									{:else if $config?.onboarding ?? false}
										<div
											style="--mt:0.2rem; --size:0.6rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-500)"
										>
											ⓘ {branding?.title || $WEBUI_NAME}
											{$i18n.t(
												'does not make any external connections, and your data stays securely on your locally hosted server.'
											)}
										</div>
									{/if}
								</div>

								{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
									<div style="--d:flex; --fd:column; --mt:1rem">
										{#if mode === 'signup'}
											<div style="--mb:0.5rem">
												<label
													for="name"
													style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
													>{$i18n.t('Name')}</label
												>
												<input
													bind:value={name}
													type="text"
													id="name"
													style="--my:0.125rem; --w:100%; --size:0.8rem; --oe:none; --bgc:transparent"
													autocomplete="name"
													placeholder={$i18n.t('Enter Full Name')}
													required
												/>
											</div>
										{/if}

										{#if mode === 'ldap'}
											<div style="--mb:0.5rem">
												<label
													for="username"
													style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
													>{$i18n.t('Username')}</label
												>
												<input
													bind:value={ldapUsername}
													type="text"
													style="--my:0.125rem; --w:100%; --size:0.8rem; --oe:none; --bgc:transparent"
													autocomplete="username"
													name="username"
													id="username"
													placeholder={$i18n.t('Enter Username')}
													required
												/>
											</div>
										{:else}
											<div style="--mb:0.5rem">
												<label
													for="email"
													style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
													>{$i18n.t('Email')}</label
												>
												<input
													bind:value={email}
													type="email"
													id="email"
													style="--my:0.125rem; --w:100%; --size:0.8rem; --oe:none; --bgc:transparent"
													autocomplete="email"
													name="email"
													placeholder={$i18n.t('Enter Email')}
													required
												/>
											</div>
										{/if}

										<div>
											<label
												for="password"
												style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
												>{$i18n.t('Password')}</label
											>
											<div style="--pos:relative">
												{#if showPassword}
													<input
														bind:value={password}
														type="text"
														id="password"
														style="--my:0.125rem; --w:100%; --size:0.8rem; --oe:none; --bgc:transparent; --pr:2rem"
														placeholder={$i18n.t('Enter Password')}
														autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
														name="password"
														required
													/>
												{:else}
													<input
														bind:value={password}
														type="password"
														id="password"
														style="--my:0.125rem; --w:100%; --size:0.8rem; --oe:none; --bgc:transparent; --pr:2rem"
														placeholder={$i18n.t('Enter Password')}
														autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
														name="password"
														required
													/>
												{/if}
												<button
													type="button"
													on:click={() => (showPassword = !showPassword)}
													style="--pos:absolute;
														--right:0.4rem; --top:calc(1rem - 20% );
														--transform:translateY(-50%); --bgc:transparent;
														--p:0; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --dark-hvr-c:var(--color-gray-300)"
													aria-label={showPassword
														? $i18n.t('Hide password')
														: $i18n.t('Show password')}
												>
													{#if showPassword}
														<Icon name="eye-slash" className="size-4" />
													{:else}
														<Icon name="eye" className="size-4" />
													{/if}
												</button>
											</div>
										</div>
									</div>

									{#if mode === 'signin' && Object.keys($config?.oauth?.providers ?? {}).length === 0}
										<div
											style="--d:flex; --ai:center; --g:0.3rem; --mt:0.5rem; --size:0.7rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)"
										>
											{$i18n.t('Forgetting your password(s)? Contact your admin for help.')}
											<Tooltip
												content={$i18n.t(
													'Ask your admin to enable Google, GitHub, or LDAP sign-in so you can log in without a password.'
												)}
												placement="top"
												className="flex items-center"
											>
												<span style="cursor:help"><Icon name="question-mark-circle" strokeWidth="2" className="size-3.5" /></span>
											</Tooltip>
										</div>
									{/if}
								{/if}
								<div style="--mt:1.2rem">
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
										{#if mode === 'ldap'}
											<button
												style="--bgc:rgb(78 78 78 / 0.05); --hvr-bgc:rgb(78 78 78 / 0.1); --dark-bgc:rgb(236 236 236 / 0.05); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem"
												type="submit"
											>
												{$i18n.t('Authenticate')}
											</button>
										{:else}
											<button
												style="--bgc:rgb(78 78 78 / 0.05);
													--hvr-bgc:rgb(78 78 78 / 0.1);
													--dark-bgc:rgb(236 236 236 / 0.05);
													--hvr-dark-bgc:rgb(236 236 236 / 0.1);
													--dark-c:var(--color-gray-300);
													--hvr-dark-c:#fff;
													--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1);
													--w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem; --p:1em 1.5em;
													--m:auto;
													--d:flex; --jc:center; --ai:center;"
												type="submit"
											>
												{mode === 'signin'
													? $i18n.t('Sign in')
													: ($config?.onboarding ?? false)
														? $i18n.t('Create Admin Account')
														: $i18n.t('Create Account')}
											</button>
										{/if}
									{/if}
								</div>
							</form>

							{#if $config?.onboarding ?? false}
								<div style="--d:inline-flex; --ai:center; --jc:center; --w:100%">
									<hr
										style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)"
									/>
									<span
										style="--px:0.6rem; --size:0.8rem; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --bgc:transparent"
										>{$i18n.t('or')}</span
									>
									<hr
										style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)"
									/>
								</div>

								<input
									bind:this={restoreFileInput}
									type="file"
									accept=".db,.sqlite,.zip"
									hidden
									on:change={(e) => {
										const files = e.target.files;
										if (files && files.length > 0) {
											restoreFile = files[0];
										}
									}}
								/>

								{#if !showRestoreBackup}
									<button
										style="--bgc:rgb(78 78 78 / 0.05);
											--hvr-bgc:rgb(78 78 78 / 0.1);
											--dark-bgc:rgb(236 236 236 / 0.05);
											--hvr-dark-bgc:rgb(236 236 236 / 0.1);
											--dark-c:var(--color-gray-300);
											--hvr-dark-c:#fff;
											--tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
											--w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem;
											--p:1em 1.5em; --m:auto;
											--d:flex; --jc:center; --ai:center;"
										type="button"
										on:click={() => {
											showRestoreBackup = true;
										}}
									>
										<Icon name="cloud-arrow-up" className="size-5" strokeWidth="1.5" />
										<span style="--ml:0.4rem">{$i18n.t('Restore from Backup')}</span>
									</button>
								{:else}
									<div style="--d:flex; --fd:column; --g:0.6rem; --w:100%">
										{#if !restoreFile}
											<button
												style="--bgc:rgb(78 78 78 / 0.05);
													--hvr-bgc:rgb(78 78 78 / 0.1);
													--dark-bgc:rgb(236 236 236 / 0.05);
													--hvr-dark-bgc:rgb(236 236 236 / 0.1);
													--dark-c:var(--color-gray-300);
													--hvr-dark-c:#fff;
													--tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
													--w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem;
													--p:1em 1.5em; --m:auto;
													--d:flex; --jc:center; --ai:center;"
												type="button"
												on:click={() => {
													restoreFileInput?.click();
												}}
											>
												{$i18n.t('Choose backup file...')}
											</button>
										{:else}
											<div
												style="--d:flex; --fd:column; --ai:center; --g:0.4rem; --ta:center"
											>
												<div
													style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
												>
													{restoreFile.name} ({formatFileSize(restoreFile.size)})
												</div>
												<div style="--d:flex; --g:0.5rem; --w:100%">
													<button
														style="--bgc:rgb(78 78 78 / 0.05);
															--hvr-bgc:rgb(78 78 78 / 0.1);
															--dark-bgc:rgb(236 236 236 / 0.05);
															--hvr-dark-bgc:rgb(236 236 236 / 0.1);
															--dark-c:var(--color-gray-300);
															--hvr-dark-c:#fff;
															--tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
															--w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem;
															--p:1em 1.5em; --m:auto;
															--d:flex; --jc:center; --ai:center;"
														type="button"
														disabled={restoreLoading}
														on:click={handleRestoreBackup}
													>
														{#if restoreLoading}
															<Spinner className="size-4 mr-2" />
															{$i18n.t('Restoring...')}
														{:else}
															{$i18n.t('Restore')}
														{/if}
													</button>
												</div>
												<button
													type="button"
													style="--size:0.7rem; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --td:underline; --bgc:transparent"
													on:click={() => {
														restoreFile = null;
														showRestoreBackup = false;
														if (restoreFileInput) restoreFileInput.value = '';
													}}
												>
													{$i18n.t('Cancel')}
												</button>
											</div>
										{/if}
									</div>
								{/if}
							{/if}

							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div style="--d:inline-flex; --ai:center; --jc:center; --w:100%">
									<hr
										style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)"
									/>
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
										<span
											style="--px:0.6rem; --size:0.8rem; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --bgc:transparent"
											>{$i18n.t('or')}</span
										>
									{/if}

									<hr
										style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)"
									/>
								</div>
								<div style="--d:flex;  --g:0.5rem">
									{#if $config?.oauth?.providers?.google}
										<button
											style="--d:flex; --jc:center; --ai:center; --bgc:rgb(78 78 78 / 0.05); --hvr-bgc:rgb(78 78 78 / 0.1); --dark-bgc:rgb(236 236 236 / 0.05); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<BrandIcon name="google" className="size-6" />
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.microsoft}
										<button
											style="--d:flex; --jc:center; --ai:center; --bgc:rgb(78 78 78 / 0.05); --hvr-bgc:rgb(78 78 78 / 0.1); --dark-bgc:rgb(236 236 236 / 0.05); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<BrandIcon name="microsoft" className="size-6" />
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.github}
										<button
											style="--d:flex; --jc:center; --ai:center; --bgc:rgb(78 78 78 / 0.05); --hvr-bgc:rgb(78 78 78 / 0.1); --dark-bgc:rgb(236 236 236 / 0.05); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<Icon name="github-fill-24" className="size-6" />
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.oidc}
										<button
											style="--d:flex; --jc:center; --ai:center; --bgc:rgb(78 78 78 / 0.05); --hvr-bgc:rgb(78 78 78 / 0.1); --dark-bgc:rgb(236 236 236 / 0.05); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<Icon name="key-outline" className="size-6" />

											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}
								</div>
							{/if}

							<!-- Magic Link Email Login -->
							{#if $config?.features?.enable_magic_link_login}
								{#if !magicLinkMode}
									<!-- Show divider + button when not yet in magic link mode -->
									{#if Object.keys($config?.oauth?.providers ?? {}).length === 0}
										<div style="--d:inline-flex; --ai:center; --jc:center; --w:100%">
											<hr
												style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)"
											/>
											<span
												style="--px:0.6rem; --size:0.8rem; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --bgc:transparent"
												>{$i18n.t('or')}</span
											>
											<hr
												style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)"
											/>
										</div>
									{/if}
									<button
										style="--mt:0.8rem; --d:flex; --jc:center; --ai:center; --bgc:rgb(78 78 78 / 0.05); --hvr-bgc:rgb(78 78 78 / 0.1); --dark-bgc:rgb(236 236 236 / 0.05); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem"
										type="button"
										on:click={() => {
											magicLinkMode = true;
										}}
									>
										<Icon name="envelope-outline" className="size-[1.2rem]" />
										<span>{$i18n.t('Sign in with Email Link')}</span>
									</button>
								{:else if magicLinkSent}
									<!-- Confirmation after sending -->
									<div style="--ta:center; --py:1rem">
										<div style="--size:0.85rem; --weight:500; --mb:0.4rem">
											{$i18n.t('Check your email')}
										</div>
										<div
											style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:0.8rem"
										>
											{$i18n.t('If an account with that email exists, a login link has been sent.')}
										</div>
										<button
											type="button"
											style="--m:auto; --size:0.7rem; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --td:underline"
											on:click={() => {
												magicLinkMode = false;
												magicLinkSent = false;
												magicLinkEmail = '';
											}}
										>
											{$i18n.t('Back to sign i')}
										</button>
									</div>
								{:else}
									<!-- Email input form -->
									<div style="--d:flex; --fd:column; --g:0.6rem; --py:0.5rem">
										<div style="--size:0.85rem; --weight:500; --ta:center">
											{$i18n.t('Sign in with Email Link')}
										</div>
										<input
											type="email"
											bind:value={magicLinkEmail}
											placeholder={$i18n.t('Enter your email')}
											style="--w:100%; --size:0.8rem; --p:0.6rem; --radius:9999px; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --bgc:transparent; --ta:center"
											on:keydown={(e) => {
												if (e.key === 'Enter') {
													e.preventDefault();
													handleMagicLinkSend();
												}
											}}
										/>
										<button
											type="button"
											disabled={magicLinkSending || !magicLinkEmail}
											style="--bgc:rgb(78 78 78 / 0.05);
													--hvr-bgc:rgb(78 78 78 / 0.1);
													--dark-bgc:rgb(236 236 236 / 0.05);
													--hvr-dark-bgc:rgb(236 236 236 / 0.1);
													--dark-c:var(--color-gray-300);
													--hvr-dark-c:#fff;
													--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1);
													--w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem; --p:1em 1.5em;
													--m:auto;
													--d:flex; --jc:center; --ai:center;"
											on:click={handleMagicLinkSend}
										>
											{magicLinkSending ? $i18n.t('Sending...') : $i18n.t('Send Login Link')}
										</button>
									</div>
								{/if}
							{/if}

							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<div style="--mt:0.5rem">
									<button
										style="--d:flex; --jc:center; --ai:center; --size:0.6rem; --w:100%; --ta:center; --td:underline"
										type="button"
										on:click={() => {
											if (mode === 'ldap')
												mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
											else mode = 'ldap';
										}}
									>
										<span
											>{mode === 'ldap'
												? $i18n.t('Continue with Email')
												: $i18n.t('Continue with LDAP')}</span
										>
									</button>
								</div>
							{/if}

							{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
								<div style="--m:1rem; --size:0.8rem; --ta:center">
									{mode === 'signin'
										? $i18n.t("Don't have an account?")
										: $i18n.t('Already have an account?')}

									<button
										style="--bgc:rgb(78 78 78 / 0.05);
													--hvr-bgc:rgb(78 78 78 / 0.1);
													--dark-bgc:rgb(236 236 236 / 0.05);
													--hvr-dark-bgc:rgb(236 236 236 / 0.1);
													--dark-c:var(--color-gray-300);
													--hvr-dark-c:#fff;
													--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1);
													--w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem; --p:1em 1.5em;
													--m:1rem auto;
													--d:flex; --jc:center; --ai:center;"
										type="button"
										on:click={() => {
											if (mode === 'signin') {
												mode = 'signup';
											} else {
												mode = 'signin';
											}
										}}
									>
										{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
									</button>
								</div>
							{/if}

							<div style="--mt:1rem; --size:0.6rem; --ta:center; --c:var(--color-gray-500)">
								{$i18n.t(
									'Usage of this service requires strictly necessary cookies for authentication.'
								)}
							</div>
							<div style="--mt:1rem; --size:0.6rem; --ta:center; --c:var(--color-gray-500)">
								<a href="https://sage.is">Read about Age of Sage</a>
							</div>
						</div>
						{#if $config?.metadata?.login_footer}
							<div style="--maxw:48rem; --mx:auto">
								<div
									style="--mt:0.5rem; --size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
									class="marked"
								>
									{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
