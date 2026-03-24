<script>
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';
	import { getBranding } from '$lib/apis/configs';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let branding = {};

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';

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

	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);
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
	<div style="--w:100%; --h:100%; --pos:absolute; --top:0; --left:0; --bgc:#fff; --dark-bgc:#000"></div>

	<div style="--w:100%; --pos:absolute; --top:0; --left:0; --right:0; --h:2rem"
	class="drag-region" />

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
						<div style="--maxw-sm:28rem; --my:auto; --pb:2.5rem; --w:100%; --dark-c:var(--color-gray-100)">
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
										<div style="--mt:0.2rem; --size:0.6rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-500)">
											{branding?.subtitle}
										</div>
									{:else if $config?.onboarding ?? false}
										<div style="--mt:0.2rem; --size:0.6rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-500)">
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
												<label for="name" style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
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
												<label for="username" style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
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
												<label for="email" style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
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
											<label for="password" style="--size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --d:block"
												>{$i18n.t('Password')}</label
											>
											<input
												bind:value={password}
												type="password"
												id="password"
												style="--my:0.125rem; --w:100%; --size:0.8rem; --oe:none; --bgc:transparent"
												placeholder={$i18n.t('Enter Password')}
												autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
												name="password"
												required
											/>
										</div>
									</div>

									{#if mode === 'signin' && Object.keys($config?.oauth?.providers ?? {}).length === 0}
										<div style="--d:flex; --ai:center; --g:0.3rem; --mt:0.5rem; --size:0.7rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
											{$i18n.t('Forgot your password? Contact your admin for help.')}
											<Tooltip content={$i18n.t('Your admin can reset your password, or enable Google, GitHub, or LDAP sign-in so you can log in without one.')} placement="top" className="flex items-center">
												<span style="cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
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

											{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
												<div style="--mt:1rem; --size:0.8rem; --ta:center">
													{mode === 'signin'
														? $i18n.t("Don't have an account?")
														: $i18n.t('Already have an account?')}

													<button
														style="--weight:500; --td:underline"
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
										{/if}
									{/if}
								</div>

								<div style="--mt:1rem; --size:0.6rem; --ta:center; --c:var(--color-gray-500)">
									{$i18n.t(
										'Usage of this service requires strictly necessary cookies for authentication.'
									)}
								</div>
							</form>

							<div style="--mt:1rem; --size:0.6rem; --ta:center; --c:var(--color-gray-500)">
								<a href="https://sage.is">Read about Age of Sage</a>
							</div>

							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div style="--d:inline-flex; --ai:center; --jc:center; --w:100%">
									<hr style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)" />
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
										<span
											style="--px:0.6rem; --size:0.8rem; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --bgc:transparent"
											>{$i18n.t('or')}</span
										>
									{/if}

									<hr style="--w:8rem; --h:1px; --my:1rem; --bw:0; --dark-bgc:rgb(236 236 236 / 0.1); --bgc:rgb(78 78 78 / 0.1)" />
								</div>
								<div style="--d:flex; --fd:column; --g:0.5rem">
									{#if $config?.oauth?.providers?.google}
										<button
											style="--d:flex; --jc:center; --ai:center; --bgc:rgb(78 78 78 / 0.05); --hvr-bgc:rgb(78 78 78 / 0.1); --dark-bgc:rgb(236 236 236 / 0.05); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --w:100%; --radius:9999px; --weight:500; --size:0.8rem; --py:0.625rem"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 48 48"
												style="--w:1.5rem; --h:1.5rem; --mr:0.6rem"
											>
												<path
													fill="#EA4335"
													d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
												/><path
													fill="#4285F4"
													d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
												/><path
													fill="#FBBC05"
													d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
												/><path
													fill="#34A853"
													d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
												/><path fill="none" d="M0 0h48v48H0z" />
											</svg>
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
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 21 21"
												style="--w:1.5rem; --h:1.5rem; --mr:0.6rem"
											>
												<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
													x="1"
													y="11"
													width="9"
													height="9"
													fill="#00a4ef"
												/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
													x="11"
													y="11"
													width="9"
													height="9"
													fill="#ffb900"
												/>
											</svg>
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
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												style="--w:1.5rem; --h:1.5rem; --mr:0.6rem"
											>
												<path
													fill="currentColor"
													d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
												/>
											</svg>
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
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												style="--w:1.5rem; --h:1.5rem; --mr:0.6rem"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
												/>
											</svg>

											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}
								</div>
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
						</div>
						{#if $config?.metadata?.login_footer}
							<div style="--maxw:48rem; --mx:auto">
								<div style="--mt:0.5rem; --size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
	class="marked">
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
