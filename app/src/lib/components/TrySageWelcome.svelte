<!--
  TrySageWelcome.svelte — invitation-only welcome page for try.sage trials.

  Shown in place of the standard /auth signin form when:
    1. `$config?.features?.enable_try_sage` is true
    2. The visitor is anonymous (no $user)
    3. There's no `magic_token` in the URL hash (the auth route's
       checkOauthCallback handles that case before we render).

  Design intent: warm, professional, invitation-gated. The trial is not
  open registration — visitors land here ONLY after a facilitator has
  shared a magic link, and that link is processed by /auth before this
  component ever paints. So this page is the "I landed here without an
  invite" surface. Be welcoming. Explain the trial briefly. Direct the
  visitor to whichever channel their facilitator used: in-person QR /
  email / direct link.

  No sign-in form, no signup, no escape hatch — strictly invite-only per
  the trial UX contract. The only path forward is a magic link from a
  facilitator.

  Visual chrome reuses OnBoarding.svelte's SlideShow + Marquee pattern
  so this feels like part of the same product family.
-->

<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding } from '$lib/apis/configs';
	import { config } from '$lib/stores';

	import Marquee from './common/Marquee.svelte';
	import SlideShow from './common/SlideShow.svelte';

	let branding: any = {};

	async function loadBranding() {
		try {
			branding = await getBranding();
		} catch (err) {
			// Branding is decorative — failure is non-fatal, fall through to defaults.
			console.error('TrySageWelcome: failed to load branding', err);
		}
	}

	function setLogoImage() {
		const logo = document.getElementById('try-sage-welcome-logo');
		if (!logo) return;

		// Same precedence as OnBoarding: custom branding logo wins, then
		// dark/light favicon, then default favicon. Kept in this component
		// rather than abstracted so the auth route can mount it without
		// pulling in the OnBoarding component's full slideshow handler.
		if (branding?.logo_url || branding?.logo_dark_url) {
			const isDarkMode = document.documentElement.classList.contains('dark');
			if (isDarkMode && branding?.logo_dark_url) {
				(logo as HTMLImageElement).src = branding.logo_dark_url;
			} else if (branding?.logo_url) {
				(logo as HTMLImageElement).src = branding.logo_url;
			}
			(logo as HTMLImageElement).style.filter = '';
			return;
		}

		const isDarkMode = document.documentElement.classList.contains('dark');
		if (isDarkMode) {
			const darkImage = new Image();
			darkImage.src = `${WEBUI_BASE_URL}/static/icons/favicon-dark.png`;
			darkImage.onload = () => {
				(logo as HTMLImageElement).src = `${WEBUI_BASE_URL}/static/icons/favicon-dark.png`;
				(logo as HTMLImageElement).style.filter = '';
			};
			darkImage.onerror = () => {
				(logo as HTMLImageElement).style.filter = '';
			};
		}
	}

	onMount(loadBranding);
	$: if (branding) setLogoImage();

	// Display copy for the three persona families. Static — these mirror
	// the seed in routers/sage_runtime.py + utils/try_sage_seed.py. If
	// TRY_SAGE_USER_SEAT_COUNT changes the actual count of users, the
	// copy here still reads accurately ("trial users") because we don't
	// list each one individually.
	const roles = [
		{
			title: 'Admin',
			detail:
				'Full control of this trial environment. Resets the workspace, extends the deadline, helps Facilitators and Users when something looks off.'
		},
		{
			title: 'Facilitator',
			detail:
				'Guide and helper. Sees what Users see. In schools, this is the teacher role. In offices, this is a project manager, team lead, or workshop host.'
		},
		{
			title: 'Users',
			detail:
				'Workshop attendees. Try the agents, explore models, build something small you can take with you. The trial resets cleanly each day so the next cohort starts fresh.'
		}
	];
</script>

<div
	style="--pos:fixed; --top:0; --left:0; --w:100vw; --h:100vh; --z:50; --c:#fff"
	class="font-primary"
>
	<!-- Slideshow + dimmer mirrors OnBoarding.svelte for visual continuity -->
	<SlideShow duration={5000} />

	<div
		style="--pos:absolute; --top:0; --left:0; --w:100%; --h:100%; --bgi:linear-gradient(0deg, var(--tw-gradient-stops)); --tw-gradient-from:#000; --tw-gradient-to:transparent"
		class="from-20%"
	></div>

	<div
		style="--pos:absolute; --top:0; --left:0; --w:100%; --h:100%; --bgc:rgb(0 0 0 / 0.55)"
		class="backdrop-blur-xs"
	></div>

	<!--
		Foreground content. Vertically centered hero, content stack below.
		Constrained to ~36rem so the copy stays readable on wide screens.
	-->
	<div
		style="--pos:relative; --z:10; --w:100%; --minh:100vh; --d:flex; --jc:center; --ai:center; --p:2rem"
	>
		<div style="--w:100%; --maxw:36rem; --d:flex; --fd:column; gap:1rem; --ta:center">
			<!-- Hero: logo + Marquee welcome -->
			<div style="--d:flex; --fd:column; --ai:center; gap:1rem">
				<img
					id="try-sage-welcome-logo"
					crossorigin="anonymous"
					src={branding?.logo_url || `${WEBUI_BASE_URL}/static/icons/favicon.png`}
					style="--w:4.5rem; --h:4.5rem; --radius:9999px"
					alt="logo"
				/>

				<div style="--size:2.25rem; --size-lg:3rem; --weight:600" class="font-secondary">
					<Marquee
						duration={5000}
						words={[
							$i18n.t('Welcome to try.sage.is AI'),
							$i18n.t('A friendly trial of Sage.is AI'),
							$i18n.t('Built for workshops and demos')
						]}
					/>
				</div>

				<p style="--size:1rem; --opacity:0.85; --maxw:30rem; --lh:1.5">
					{$i18n.t(
						'This trial is by invitation only. Your Sage.is AI workshop facilitator will share the link you need to sign in.'
					)}
				</p>
			</div>

			<!-- Roles available — informational, NOT clickable. The link to
			     each persona ships via email or in-person QR, not from this
			     public surface. -->
			<div
				style="--d:flex; --fd:column; gap:0.75rem; --ta:left; --bgc:rgb(255 255 255 / 0.06); --p:1.25rem; --radius:0.75rem"
				class="backdrop-blur-sm"
			>
				<div style="--size:0.85rem; --weight:600; --opacity:0.8; --tt:uppercase; --ls:0.05em">
					{$i18n.t('Roles in this trial')}
				</div>
				{#each roles as role}
					<div style="--d:flex; --fd:column; gap:0.2rem">
						<div style="--size:0.95rem; --weight:600">{$i18n.t(role.title)}</div>
						<div style="--size:0.85rem; --opacity:0.8; --lh:1.45">
							{$i18n.t(role.detail)}
						</div>
					</div>
				{/each}
			</div>

			<!-- Two-path sign-in instructions. The actual handoff happens
			     via QR or email — not from a button on this page — so the
			     copy is descriptive, not interactive. -->
			<div
				style="--d:flex; --fd:column; gap:0.85rem; --ta:left; --p:1.25rem; --radius:0.75rem; --bgc:rgb(255 255 255 / 0.06)"
				class="backdrop-blur-sm"
			>
				<div style="--size:0.85rem; --weight:600; --opacity:0.8; --tt:uppercase; --ls:0.05em">
					{$i18n.t('How to sign in')}
				</div>

				<div style="--d:flex; gap:0.6rem; --ai:flex-start">
					<span style="--size:1rem">📍</span>
					<div>
						<div style="--size:0.9rem; --weight:600">{$i18n.t('At an in-person workshop')}</div>
						<div style="--size:0.85rem; --opacity:0.8; --lh:1.45">
							{$i18n.t(
								'Scan the QR code your facilitator shared, or open the link they passed around.'
							)}
						</div>
					</div>
				</div>

				<div style="--d:flex; gap:0.6rem; --ai:flex-start">
					<span style="--size:1rem">✉️</span>
					<div>
						<div style="--size:0.9rem; --weight:600">{$i18n.t('Joining remotely')}</div>
						<div style="--size:0.85rem; --opacity:0.8; --lh:1.45">
							{$i18n.t(
								'Check the email your workshop organizer sent. Open the magic link there to sign in.'
							)}
						</div>
					</div>
				</div>
			</div>

			<!-- Footer: friendly recovery line — points back to the facilitator,
			     no self-serve resend per the trial's invite-only contract. -->
			<div style="--size:0.8rem; --opacity:0.65; --lh:1.45; --maxw:30rem; --m:0 auto">
				{$i18n.t(
					"Lost your link? Reach out to whoever invited you and they'll resend it."
				)}
			</div>

			<!-- Reset hint for projection contexts: the daily refresh is part
			     of the trial promise. Kept small and gentle. -->
			{#if $config?.try_sage?.banner_text}
				<div style="--size:0.75rem; --opacity:0.55">
					{$config.try_sage.banner_text}
				</div>
			{/if}
		</div>
	</div>
</div>
