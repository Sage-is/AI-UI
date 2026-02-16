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

	// General
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

	const applyTheme = (_theme: string) => {
		let themeToApply = _theme === 'oled-dark' ? 'dark' : _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		if (themeToApply === 'dark' && !_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#333');
			document.documentElement.style.setProperty('--color-gray-850', '#262626');
			document.documentElement.style.setProperty('--color-gray-900', '#171717');
			document.documentElement.style.setProperty('--color-gray-950', '#0d0d0d');
		}

		themes
			.filter((e) => e !== themeToApply)
			.forEach((e) => {
				e.split(' ').forEach((e) => {
					document.documentElement.classList.remove(e);
				});
			});

		themeToApply.split(' ').forEach((e) => {
			document.documentElement.classList.add(e);
		});

		const metaThemeColor = document.querySelector('meta[name="theme-color"]');
		if (metaThemeColor) {
			if (_theme.includes('system')) {
				const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
					? 'dark'
					: 'light';
				console.log('Setting system meta theme color: ' + systemTheme);
				metaThemeColor.setAttribute('content', systemTheme === 'light' ? '#ffffff' : '#171717');
			} else {
				console.log('Setting meta theme color: ' + _theme);
				metaThemeColor.setAttribute(
					'content',
					_theme === 'dark'
						? '#171717'
						: _theme === 'oled-dark'
							? '#000000'
							: _theme === 'her'
								? '#ffffff'
								: '#ffffff'
				);
			}
		}

		if (typeof window !== 'undefined' && window.applyTheme) {
			window.applyTheme();
		}

		if (_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#101010');
			document.documentElement.style.setProperty('--color-gray-850', '#050505');
			document.documentElement.style.setProperty('--color-gray-900', '#000000');
			document.documentElement.style.setProperty('--color-gray-950', '#000000');
			document.documentElement.classList.add('dark');
		}

		console.log(_theme);
	};

	const themeChangeHandler = (_theme: string) => {
		theme.set(_theme);
		localStorage.setItem('theme', _theme);
		applyTheme(_theme);
	};
</script>

<div style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.875rem" id="tab-general">
	<div style="--ofy:scroll; --maxh:28rem; --maxh-lg:100%">
		<div class="">
			<div style="--mb:0.25rem; --size:0.875rem; --weight:500">{$i18n.t('WebUI Settings')}</div>

			<div style="--d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.75rem; --weight:500">{$i18n.t('Theme')}</div>
				<div style="--d:flex; --ai:center; --pos:relative">
					<select
						style="--dark-bgc:var(--color-gray-900, #171717); --w:fit-content; --pr:2rem; --radius:0.125rem; --py:0.5rem; --px:0.5rem; --size:0.75rem; --bgc:transparent; --ta:right"
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
						<!-- <option value="rose-pine dark">🪻 {$i18n.t('Rosé Pine')}</option>
						<option value="rose-pine-dawn light">🌷 {$i18n.t('Rosé Pine Dawn')}</option> -->
					</select>
				</div>
			</div>

			<div style="--d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.75rem; --weight:500">{$i18n.t('Language')}</div>
				<div style="--d:flex; --ai:center; --pos:relative">
					<select
						style="--dark-bgc:var(--color-gray-900, #171717); --w:fit-content; --pr:2rem; --radius:0.125rem; --py:0.5rem; --px:0.5rem; --size:0.75rem; --bgc:transparent; --ta:right"
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
				<div style="--mb:0.5rem; --size:0.75rem; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b)">
					Couldn't find your language?
					<a
						style="--c:var(--color-gray-300, #cdcdcd); --weight:500; --td:underline"
						href="https://github.com/Sage-is/AI-UI/blob/main/docs/CONTRIBUTING.md#-translations-and-internationalization"
						target="_blank"
					>
						Help us translate Sage.is AI!
					</a>
				</div>
			{/if}

			<div>
				<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.75rem; --weight:500">{$i18n.t('Notifications')}</div>

					<button
						style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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
			<hr style="--bc:var(--color-gray-50, #f9f9f9); --dark-bc:var(--color-gray-850, #262626); --my:0.75rem" />

			<div>
				<div style="--my:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('System Prompt')}</div>
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
			<div style="--mt:0.5rem; --g:0.75rem; --pr:0.375rem">
				<div style="--d:flex; --jc:space-between; --ai:center; --size:0.875rem">
					<div style="--weight:500">{$i18n.t('Advanced Parameters')}</div>
					<button
						style="--size:0.75rem; --weight:500; --c:var(--color-gray-500, #9b9b9b)"
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

	<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
		<button
			style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900, #171717); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			on:click={() => {
				saveHandler();
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
