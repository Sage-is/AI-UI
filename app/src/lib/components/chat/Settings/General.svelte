<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { getLanguages, changeLanguage } from '$lib/i18n';
	const dispatch = createEventDispatcher();

	import { models, settings, theme, user } from '$lib/stores';

	const i18n = getContext('i18n');

	import AdvancedParams from './Advanced/AdvancedParams.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	export let saveSettings: Function;
	export let getModels: Function;

	// Theme options: system (auto), dark, light, oled-dark (true black for AMOLED)
	let themes = ['dark', 'light', 'oled-dark'];
	let selectedTheme = 'system';

	let languages: Awaited<ReturnType<typeof getLanguages>> = [];
	let lang = $i18n.language;
	let notificationEnabled = false;
	let system = '';

	let showAdvanced = false;

	const toggleNotification = async () => {
		const permission = await Notification.requestPermission();

		if (permission === 'granted') {
			notificationEnabled = !notificationEnabled;
			saveSettings({ notificationEnabled: notificationEnabled });
		} else {
			toast.error(
				$i18n.t(
					'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
				)
			);
		}
	};

	let params = {
		// Advanced
		stream_response: null,
		function_calling: null,
		seed: null,
		temperature: null,
		reasoning_effort: null,
		logit_bias: null,
		frequency_penalty: null,
		presence_penalty: null,
		repeat_penalty: null,
		repeat_last_n: null,
		mirostat: null,
		mirostat_eta: null,
		mirostat_tau: null,
		top_k: null,
		top_p: null,
		min_p: null,
		stop: null,
		tfs_z: null,
		num_ctx: null,
		num_batch: null,
		num_keep: null,
		max_tokens: null,
		num_gpu: null
	};

	const saveHandler = async () => {
		saveSettings({
			system: system !== '' ? system : undefined,
			params: {
				stream_response: params.stream_response !== null ? params.stream_response : undefined,
				function_calling: params.function_calling !== null ? params.function_calling : undefined,
				seed: (params.seed !== null ? params.seed : undefined) ?? undefined,
				stop: params.stop ? params.stop.split(',').filter((e) => e) : undefined,
				temperature: params.temperature !== null ? params.temperature : undefined,
				reasoning_effort: params.reasoning_effort !== null ? params.reasoning_effort : undefined,
				logit_bias: params.logit_bias !== null ? params.logit_bias : undefined,
				frequency_penalty: params.frequency_penalty !== null ? params.frequency_penalty : undefined,
				presence_penalty: params.frequency_penalty !== null ? params.frequency_penalty : undefined,
				repeat_penalty: params.frequency_penalty !== null ? params.frequency_penalty : undefined,
				repeat_last_n: params.repeat_last_n !== null ? params.repeat_last_n : undefined,
				mirostat: params.mirostat !== null ? params.mirostat : undefined,
				mirostat_eta: params.mirostat_eta !== null ? params.mirostat_eta : undefined,
				mirostat_tau: params.mirostat_tau !== null ? params.mirostat_tau : undefined,
				top_k: params.top_k !== null ? params.top_k : undefined,
				top_p: params.top_p !== null ? params.top_p : undefined,
				min_p: params.min_p !== null ? params.min_p : undefined,
				tfs_z: params.tfs_z !== null ? params.tfs_z : undefined,
				num_ctx: params.num_ctx !== null ? params.num_ctx : undefined,
				num_batch: params.num_batch !== null ? params.num_batch : undefined,
				num_keep: params.num_keep !== null ? params.num_keep : undefined,
				max_tokens: params.max_tokens !== null ? params.max_tokens : undefined,
				use_mmap: params.use_mmap !== null ? params.use_mmap : undefined,
				use_mlock: params.use_mlock !== null ? params.use_mlock : undefined,
				num_thread: params.num_thread !== null ? params.num_thread : undefined,
				num_gpu: params.num_gpu !== null ? params.num_gpu : undefined,
				think: params.think !== null ? params.think : undefined,
				keep_alive: params.keep_alive !== null ? params.keep_alive : undefined,
				format: params.format !== null ? params.format : undefined
			}
		});
		dispatch('save');
	};

	onMount(async () => {
		selectedTheme = localStorage.theme ?? 'system';

		languages = await getLanguages();

		notificationEnabled = $settings.notificationEnabled ?? false;
		system = $settings.system ?? '';

		params = { ...params, ...$settings.params };
		params.stop = $settings?.params?.stop ? ($settings?.params?.stop ?? []).join(',') : null;
	});

	/**
	 * Apply theme to the document.
	 * Sets both .dark/.light class (Tailwind) and data-theme attribute (Startr.Style).
	 * Startr.Style's [data-theme="dark"] flips semantic colors (--primary, --background,
	 * --text-main, etc.) automatically via color-mix() — no manual overrides needed.
	 */
	const applyTheme = (_theme: string) => {
		const root = document.documentElement;

		// Resolve the effective mode: always 'dark' or 'light'
		let mode: 'dark' | 'light' = 'dark';
		if (_theme === 'system') {
			mode = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		} else if (_theme === 'light') {
			mode = 'light';
		}

		// Clear previous theme classes, then apply current
		themes.forEach((t) => root.classList.remove(t));
		root.classList.remove('dark', 'light');
		root.classList.add(mode);

		// Startr.Style uses [data-theme="dark"] to flip semantic color variables
		root.setAttribute('data-theme', mode);

		// Reset any OLED gray overrides when switching away from OLED
		if (_theme !== 'oled-dark') {
			root.style.removeProperty('--color-gray-800');
			root.style.removeProperty('--color-gray-850');
			root.style.removeProperty('--color-gray-900');
			root.style.removeProperty('--color-gray-950');
		}

		// OLED dark: push grays to true black for AMOLED screens
		if (_theme === 'oled-dark') {
			root.style.setProperty('--color-gray-800', '#101010');
			root.style.setProperty('--color-gray-850', '#050505');
			root.style.setProperty('--color-gray-900', '#000000');
			root.style.setProperty('--color-gray-950', '#000000');
		}

		// Update browser chrome color
		const metaThemeColor = document.querySelector('meta[name="theme-color"]');
		if (metaThemeColor) {
			const colors = { dark: '#171717', light: '#ffffff', 'oled-dark': '#000000' };
			metaThemeColor.setAttribute('content', colors[_theme] ?? colors[mode]);
		}
	};

	const themeChangeHandler = (_theme: string) => {
		theme.set(_theme);
		localStorage.setItem('theme', _theme);
		applyTheme(_theme);
	};
</script>

<div style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.8rem" id="tab-general">
	<div style="--ofy:scroll; --maxh:28rem; --maxh-lg:100%">
		<div class="">
			<div style="--mb:0.2rem; --size:0.8rem; --weight:500">{$i18n.t('WebUI Settings')}</div>

			<div style="--d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Theme')}</div>
				<div style="--d:flex; --ai:center; --pos:relative">
					<select
						style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --py:0.5rem; --px:0.5rem; --size:0.6rem; --bgc:transparent; --ta:right"
	class="{$settings.highContrastMode
							? ''
							: 'outline-hidden'}"
						bind:value={selectedTheme}
						placeholder="Select a theme"
						on:change={() => themeChangeHandler(selectedTheme)}
					>
						<option value="system">⚙️ {$i18n.t('System')}</option>
						<option value="dark">🌑 {$i18n.t('Dark')}</option>
						<option value="oled-dark">🌃 {$i18n.t('OLED Dark')}</option>
						<option value="light">☀️ {$i18n.t('Light')}</option>
					</select>
				</div>
			</div>

			<div style="--d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Language')}</div>
				<div style="--d:flex; --ai:center; --pos:relative">
					<select
						style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --py:0.5rem; --px:0.5rem; --size:0.6rem; --bgc:transparent; --ta:right"
	class="{$settings.highContrastMode
							? ''
							: 'outline-hidden'}"
						bind:value={lang}
						placeholder="Select a language"
						on:change={(e) => {
							changeLanguage(lang);
						}}
					>
						{#each languages as language}
							<option value={language['code']}>{language['title']}</option>
						{/each}
					</select>
				</div>
			</div>
			{#if $i18n.language === 'en-US'}
				<div style="--mb:0.5rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
					Couldn't find your language?
					<a
						style="--c:var(--color-gray-300); --weight:500; --td:underline"
						href="https://github.com/Sage-is/AI-UI/blob/main/docs/contributing.md#-translations-and-internationalization"
						target="_blank"
					>
						Help us translate Sage.is AI!
					</a>
				</div>
			{/if}

			<div>
				<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Notifications')}</div>

					<button
						style="--p:0.2rem; --px:0.6rem; --size:0.6rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							toggleNotification();
						}}
						type="button"
					>
						{#if notificationEnabled === true}
							<span style="--ml:0.5rem; --as:center">{$i18n.t('On')}</span>
						{:else}
							<span style="--ml:0.5rem; --as:center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>
		</div>

		{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
			<hr style="--bc:var(--color-gray-50); --dark-bc:var(--color-gray-850); --my:0.6rem" />

			<div>
				<div style="--my:0.6rem; --size:0.8rem; --weight:500">{$i18n.t('System Prompt')}</div>
				<Textarea
					bind:value={system}
					className={'w-full text-sm outline-hidden resize-vertical' +
						($settings.highContrastMode
							? ' p-2.5 border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 overflow-y-hidden'
							: ' bg-white dark:text-gray-300 dark:bg-gray-900')}
					rows="4"
					placeholder={$i18n.t('Enter system prompt here')}
				/>
			</div>
		{/if}

		{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
			<div style="--mt:0.5rem; --g:0.6rem; --pr:0.4rem">
				<div style="--d:flex; --jc:space-between; --ai:center; --size:0.8rem">
					<div style="--weight:500">{$i18n.t('Advanced Parameters')}</div>
					<button
						style="--size:0.6rem; --weight:500; --c:var(--color-gray-500)"
						type="button"
						on:click={() => {
							showAdvanced = !showAdvanced;
						}}>{showAdvanced ? $i18n.t('Hide') : $i18n.t('Show')}</button
					>
				</div>

				{#if showAdvanced}
					<AdvancedParams admin={$user?.role === 'admin'} bind:params />
				{/if}
			</div>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
		<button
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			on:click={() => {
				saveHandler();
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
