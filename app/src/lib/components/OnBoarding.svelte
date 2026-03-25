<script>
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding } from '$lib/apis/configs';

	import Marquee from './common/Marquee.svelte';
	import SlideShow from './common/SlideShow.svelte';
	import ArrowRightCircle from './icons/ArrowRightCircle.svelte';

	export let show = true;
	export let getStartedHandler = () => {};

	let branding = {};

	async function loadBranding() {
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}
	}

	function setLogoImage() {
		const logo = document.getElementById('logo');

		if (logo) {
			// If custom branding logo is set, use it
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
					logo.style.filter = ''; // Ensure no inversion is applied if splash-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = ''; // Fallback to default if dark image fails
				};
			}
		}
	}

	onMount(() => {
		loadBranding();
	});

	$: if (show && branding) {
		setLogoImage();
	}
</script>

{#if show}
	<div style="--w:100%; --h:100vh; --maxh:100dvh; --c:#fff; --pos:relative">
		<SlideShow duration={5000} />

		<div
			style="--w:100%; --h:100%; --pos:absolute; --top:0; --left:0; --bgi:linear-gradient(0deg, var(--tw-gradient-stops)); --tw-gradient-from:#000; --tw-gradient-to:transparent"
	class="from-20%"
		></div>

		<div style="--w:100%; --h:100%; --pos:absolute; --top:0; --left:0; --bgc:rgb(0 0 0 / 0.5)"
	class="backdrop-blur-xs"></div>

		<div style="--pos:relative; --bgc:transparent; --w:100%; --minh:100vh; --d:flex; --z:10">
			<div style="--d:flex; --fd:column; --jc:flex-end; --w:100%; --ai:center; --pb:2.5rem; --ta:center">
				<!-- Centered logo above rotating text -->
				<div style="--d:flex; --jc:center; --mb:1.5rem">
					<img
						id="logo"
						crossorigin="anonymous"
						src={branding?.logo_url || `${WEBUI_BASE_URL}/static/icons/favicon.png`}
						style="--w:5rem; --h:5rem; --radius:9999px"
						alt="logo"
					/>
				</div>

				<div style="--size:3rem; --size-lg:4.5rem"
	class="font-secondary">
					<Marquee
						duration={5000}
						words={[
							$i18n.t('Explore the cosmos'),
							$i18n.t('Unlock mysteries'),
							$i18n.t('Chart new frontiers'),
							$i18n.t('Dive into knowledge'),
							$i18n.t('Discover wonders'),
							$i18n.t('Ignite curiosity'),
							$i18n.t('Forge new paths'),
							$i18n.t('Unravel secrets'),
							$i18n.t('Pioneer insights'),
							$i18n.t('Embark on adventures')
						]}
					/>

					<div style="--mt:0.125rem">{$i18n.t(`with Sage.is AI-UI`)}</div>
				</div>

				<div style="--d:flex; --jc:center; --mt:2rem">
					<div style="--d:flex; --fd:column; --jc:center; --ai:center">
						<button
							aria-labelledby="get-started"
							style="--pos:relative; --z:20; --d:flex; --p:0.2rem; --radius:9999px; --bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(255 255 255 / 0.1); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.8rem"
							on:click={() => {
								getStartedHandler();
							}}
						>
							<ArrowRightCircle className="size-6" />
						</button>
						<div id="get-started" style="--mt:0.4rem; --size:1rem; --weight:500"
	class="font-primary">
							{$i18n.t(`Get started`)}
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
