<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { getBranding, setBranding, type Branding } from '$lib/apis/configs';
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

	const saveBranding = async () => {
		saving = true;
		try {
			const token = localStorage.token;
			await setBranding(token, branding);
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

<div class="flex flex-col h-full justify-between text-sm">
	<div class="space-y-3 pr-1.5">
		<div>
			<div class="mb-2 text-sm font-medium">{$i18n.t('Theme & Branding')}</div>
		</div>

		<hr class="dark:border-gray-850" />

		{#if loading}
			<div class="text-center py-4">
				<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100"></div>
			</div>
		{:else}
			<!-- Logo Settings -->
			<div class="space-y-3">
				<div class="text-sm font-medium">{$i18n.t('Logo Settings')}</div>
				
				<div>
					<label class="block text-sm font-medium mb-2" for="logo-url">
						{$i18n.t('Logo URL (Light Mode)')}
					</label>
					<input
						id="logo-url"
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder="https://example.com/logo.png"
						bind:value={branding.logo_url}
					/>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('URL to your logo image for light mode')}
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2" for="logo-dark-url">
						{$i18n.t('Logo URL (Dark Mode)')}
					</label>
					<input
						id="logo-dark-url"
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder="https://example.com/logo-dark.png"
						bind:value={branding.logo_dark_url}
					/>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('URL to your logo image for dark mode (optional, falls back to light mode logo)')}
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2" for="favicon-url">
						{$i18n.t('Favicon URL')}
					</label>
					<input
						id="favicon-url"
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder="https://example.com/favicon.ico"
						bind:value={branding.favicon_url}
					/>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('URL to your favicon (browser tab icon)')}
					</div>
				</div>
			</div>

			<hr class="dark:border-gray-850" />

			<!-- Text Settings -->
			<div class="space-y-3">
				<div class="text-sm font-medium">{$i18n.t('Text Settings')}</div>
				
				<div>
					<label class="block text-sm font-medium mb-2" for="title">
						{$i18n.t('Application Title')}
					</label>
					<input
						id="title"
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder={$WEBUI_NAME}
						bind:value={branding.title}
					/>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('Main title displayed in your application')}
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2" for="subtitle">
						{$i18n.t('Application Subtitle')}
					</label>
					<input
						id="subtitle"
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder="Powered by Sage.is AI UI"
						bind:value={branding.subtitle}
					/>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('Subtitle or tagline for your application')}
					</div>
				</div>
			</div>

			<hr class="dark:border-gray-850" />

			<!-- Color Settings -->
			<div class="space-y-3">
				<div class="text-sm font-medium">{$i18n.t('Color Settings')}</div>
				
				<div>
					<label class="block text-sm font-medium mb-2" for="primary-color">
						{$i18n.t('Primary Color')}
					</label>
					<div class="flex gap-2 items-center">
						<input
							id="primary-color"
							type="color"
							class="h-10 w-20 rounded cursor-pointer"
							bind:value={branding.primary_color}
						/>
						<input
							type="text"
							class="flex-1 rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder="#3B82F6"
							bind:value={branding.primary_color}
						/>
					</div>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('Main brand color (e.g., buttons, links)')}
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2" for="accent-color">
						{$i18n.t('Accent Color')}
					</label>
					<div class="flex gap-2 items-center">
						<input
							id="accent-color"
							type="color"
							class="h-10 w-20 rounded cursor-pointer"
							bind:value={branding.accent_color}
						/>
						<input
							type="text"
							class="flex-1 rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder="#10B981"
							bind:value={branding.accent_color}
						/>
					</div>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('Secondary accent color for highlights')}
					</div>
				</div>
			</div>

			<hr class="dark:border-gray-850" />

			<!-- Preview Section -->
			<div class="space-y-3">
				<div class="text-sm font-medium">{$i18n.t('Preview')}</div>
				
				<div class="p-4 rounded-lg border dark:border-gray-700 bg-gray-50 dark:bg-gray-850">
					<div class="flex items-center gap-3 mb-3">
						{#if branding.logo_url}
							<img 
								src={branding.logo_url} 
								alt="Logo" 
								class="h-8 w-auto"
								on:error={() => {}}
							/>
						{/if}
						<div>
							{#if branding.title}
								<div class="font-semibold" style="color: {branding.primary_color || 'inherit'}">
									{branding.title}
								</div>
							{/if}
							{#if branding.subtitle}
								<div class="text-xs text-gray-500">
									{branding.subtitle}
								</div>
							{/if}
						</div>
					</div>
					{#if branding.primary_color || branding.accent_color}
						<div class="flex gap-2 mt-3">
							{#if branding.primary_color}
								<div 
									class="px-3 py-1.5 rounded text-xs text-white"
									style="background-color: {branding.primary_color}"
								>
									Primary
								</div>
							{/if}
							{#if branding.accent_color}
								<div 
									class="px-3 py-1.5 rounded text-xs text-white"
									style="background-color: {branding.accent_color}"
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

	<div class="flex justify-end pt-3">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={saveBranding}
			disabled={saving}
		>
			{#if saving}
				<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
			{/if}
			{$i18n.t('Save')}
		</button>
	</div>
</div>
