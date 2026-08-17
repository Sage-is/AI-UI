<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { getBranding, setBranding, type Branding } from '$lib/apis/configs';
	import { pruneSprig } from '$lib/apis/retrieval';
	import { applyBrandingColors } from '$lib/utils/branding';
	import { WEBUI_NAME } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	let loading = false;
	let saving = false;

	let branding: Branding = {
		logo_url: '',
		logo_dark_url: '',
		favicon_url: '',
		title: '',
		subtitle: '',
		primary_color: '',
		accent_color: ''
	};

	const loadBranding = async () => {
		loading = true;
		try {
			branding = await getBranding();
		} catch (error) {
			console.error('Error loading branding:', error);
			toast.error($i18n.t('Failed to load branding settings'));
		} finally {
			loading = false;
		}
	};

	// The one implementation lives in $lib/utils/branding — shared with +layout's
	// boot path and mirrored by the no-build shell.

	const pruneActiveTheme = async () => {
		if (!branding.active_theme_sprig) return;
		saving = true;
		try {
			await pruneSprig(localStorage.token, { name: branding.active_theme_sprig });
			toast.success($i18n.t('Theme Sprig pruned — your colors are live.'));
			branding = await getBranding();
			applyBrandingColors(branding);
		} catch (error) {
			console.error('Error pruning theme sprig:', error);
			toast.error($i18n.t('Failed to prune the theme Sprig'));
		} finally {
			saving = false;
		}
	};

	const saveBranding = async () => {
		saving = true;
		try {
			const token = localStorage.token;
			// GET-only annotations never go back on POST — a stored copy would go
			// stale the moment the Sprig is pruned.
			const { active_theme_sprig, active_theme_label, ...toSave } = branding;
			await setBranding(token, toSave);
			// Apply colors live so admin sees the effect immediately
			applyBrandingColors(branding);
			toast.success($i18n.t('Branding settings saved successfully!'));
			dispatch('save');
		} catch (error) {
			console.error('Error saving branding:', error);
			toast.error($i18n.t('Failed to save branding settings'));
		} finally {
			saving = false;
		}
	};

	onMount(() => {
		loadBranding();
	});
</script>

<div style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.8rem">
	<div style="--g:0.6rem; --pr:0.4rem">
		<div>
			<div style="--mb:0.5rem; --size:0.8rem; --weight:500">{$i18n.t('Theme & Branding')}  (Beta)</div>
		</div>

		<hr style="--dark-bc:var(--color-gray-850)" />

		{#if loading}
			<div style="--ta:center; --py:1rem">
				<div style="--d:inline-block; animation:spin 1s linear infinite; --radius:9999px; --h:2rem; --w:2rem; border-bottom-width:2px; --bc:var(--color-gray-900); --dark-bc:var(--color-gray-100)"></div>
			</div>
		{:else}
			<!-- Logo Settings -->
			<div style="--g:0.6rem">
				<div style="--size:0.8rem; --weight:500">{$i18n.t('Logo Settings')}</div>

				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.5rem" for="logo-url">
						{$i18n.t('Logo URL (Light Mode)')}
					</label>
					<input
						id="logo-url"
						data-cy="branding-logo-url"
						style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:2px solid transparent"
						placeholder="https://example.com/logo.png"
						bind:value={branding.logo_url}
					/>
					<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
						{$i18n.t('URL to your logo image for light mode')}
					</div>
				</div>

				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.5rem" for="logo-dark-url">
						{$i18n.t('Logo URL (Dark Mode)')}
					</label>
					<input
						id="logo-dark-url"
						data-cy="branding-logo-dark-url"
						style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:2px solid transparent"
						placeholder="https://example.com/logo-dark.png"
						bind:value={branding.logo_dark_url}
					/>
					<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
						{$i18n.t('URL to your logo image for dark mode (optional, falls back to light mode logo)')}
					</div>
				</div>

				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.5rem" for="favicon-url">
						{$i18n.t('Favicon URL')}
					</label>
					<input
						id="favicon-url"
						data-cy="branding-favicon-url"
						style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:2px solid transparent"
						placeholder="https://example.com/favicon.ico"
						bind:value={branding.favicon_url}
					/>
					<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
						{$i18n.t('URL to your favicon (browser tab icon)')}
					</div>
				</div>
			</div>

			<hr style="--dark-bc:var(--color-gray-850)" />

			<!-- Text Settings -->
			<div style="--g:0.6rem">
				<div style="--size:0.8rem; --weight:500">{$i18n.t('Text Settings')}</div>

				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.5rem" for="title">
						{$i18n.t('Application Title')}
					</label>
					<input
						id="title"
						data-cy="branding-title"
						style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:2px solid transparent"
						placeholder={$WEBUI_NAME}
						bind:value={branding.title}
					/>
					<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
						{$i18n.t('Main title displayed in your application')}
					</div>
				</div>

				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.5rem" for="subtitle">
						{$i18n.t('Application Subtitle')}
					</label>
					<input
						id="subtitle"
						data-cy="branding-subtitle"
						style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:2px solid transparent"
						placeholder="Powered by Sage.is AI UI"
						bind:value={branding.subtitle}
					/>
					<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
						{$i18n.t('Subtitle or tagline for your application')}
					</div>
				</div>
			</div>

			<hr style="--dark-bc:var(--color-gray-850)" />

			<!-- Color Settings — overrides Startr.Style --primary and --secondary CSS variables.
				 These cascade through the entire UI: links, backgrounds, focus rings, etc. -->
			<div style="--g:0.6rem">
				<div style="--size:0.8rem; --weight:500">{$i18n.t('Color Settings')}</div>
				<div style="--size:0.6rem; --c:var(--color-gray-500)">
					{$i18n.t('Overrides the Startr.Style theme colors. Leave empty to use defaults.')}
				</div>

				{#if branding.active_theme_sprig}
					<!-- A grafted theme Sprig owns the whole look (accents AND grays), so
						 the colors below are parked rather than half-applied. Honest UX over
						 silent precedence: say who is winning, offer the one-click way out. -->
					<div
						data-cy="branding-theme-sprig-warning"
						role="status"
						style="--p:0.6rem 0.8rem; --radius:0.4rem; --bg:var(--background-alt); --size:0.7rem"
					>
						<p style="--m:0; --weight:500">
							{$i18n.t('A theme Sprig is dressing this instance right now:')}
							{branding.active_theme_label || branding.active_theme_sprig}
						</p>
						<p style="--m:0.25rem 0 0">
							{$i18n.t(
								'While it is grafted, the Sprig picks the colors — the ones below are saved but will not show. Prune the Sprig to let your colors through.'
							)}
						</p>
						<button
							type="button"
							data-cy="branding-prune-theme"
							disabled={saving}
							on:click={pruneActiveTheme}
							style="--mt:0.5rem"
						>
							{$i18n.t('Prune the theme Sprig')}
						</button>
					</div>
				{/if}

				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.5rem" for="primary-color">
						{$i18n.t('Primary Color')}
					</label>
					<div style="--d:flex; --g:0.5rem; --ai:center">
						<input
							id="primary-color"
							data-cy="branding-primary-color"
							type="color"
							style="--h:2.5rem; --w:5rem; --radius:0.2rem; --cur:pointer"
							bind:value={branding.primary_color}
						/>
						<input
							type="text"
							data-cy="branding-primary-color-text"
							style="--fx:1 1 0%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:2px solid transparent"
							placeholder="#3B82F6"
							bind:value={branding.primary_color}
						/>
					</div>
					<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
						{$i18n.t('Main brand color (e.g., buttons, links)')}
					</div>
				</div>

				<div>
					<label style="--d:block; --size:0.8rem; --weight:500; --mb:0.5rem" for="accent-color">
						{$i18n.t('Accent Color')}
					</label>
					<div style="--d:flex; --g:0.5rem; --ai:center">
						<input
							id="accent-color"
							data-cy="branding-accent-color"
							type="color"
							style="--h:2.5rem; --w:5rem; --radius:0.2rem; --cur:pointer"
							bind:value={branding.accent_color}
						/>
						<input
							type="text"
							data-cy="branding-accent-color-text"
							style="--fx:1 1 0%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:2px solid transparent"
							placeholder="#10B981"
							bind:value={branding.accent_color}
						/>
					</div>
					<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
						{$i18n.t('Secondary accent color for highlights')}
					</div>
				</div>
			</div>

			<hr style="--dark-bc:var(--color-gray-850)" />

			<!-- Preview Section -->
			<div style="--g:0.6rem">
				<div style="--size:0.8rem; --weight:500">{$i18n.t('Preview')}</div>

				<div data-cy="branding-preview" style="--p:1rem; --radius:0.5rem;  --dark-bc:var(--color-gray-700); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)">
					<div style="--d:flex; --ai:center; --g:0.6rem; --mb:0.6rem">
						{#if branding.logo_url}
							<img
								src={branding.logo_url}
								alt="Logo"
								data-cy="branding-preview-logo"
								style="--h:2rem; --w:auto"
								on:error={() => {}}
							/>
						{/if}
						<div>
							{#if branding.title}
								<div style="--weight:600; --c:{branding.primary_color || 'var(--primary)'}">
									{branding.title}
								</div>
							{/if}
							{#if branding.subtitle}
								<div style="--size:0.6rem; --c:var(--text-muted)">
									{branding.subtitle}
								</div>
							{/if}
						</div>
					</div>
					<!-- Color swatches preview the actual --primary/--secondary overrides -->
					{#if branding.primary_color || branding.accent_color}
						<div style="--d:flex; --g:0.5rem; --mt:0.6rem">
							{#if branding.primary_color}
								<div
									data-cy="branding-swatch-primary"
									style="--px:0.6rem; --py:0.4rem; --radius:0.2rem; --size:0.6rem; --c:#fff; --bgc:{branding.primary_color}"
								>
									Primary
								</div>
							{/if}
							{#if branding.accent_color}
								<div
									data-cy="branding-swatch-accent"
									style="--px:0.6rem; --py:0.4rem; --radius:0.2rem; --size:0.6rem; --c:#fff; --bgc:{branding.accent_color}"
								>
									Accent
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem">
		<button
			data-cy="branding-save"
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			on:click={saveBranding}
			disabled={saving}
		>
			{#if saving}
				<div style="animation:spin 1s linear infinite; --radius:9999px; --h:1rem; --w:1rem; border-bottom-width:2px; --bc:#fff"></div>
			{/if}
			{$i18n.t('Save')}
		</button>
	</div>
</div>
