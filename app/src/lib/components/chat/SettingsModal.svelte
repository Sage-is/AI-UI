<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { config, models, settings, user } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { getModels as _getModels } from '$lib/apis';
	import { goto } from '$app/navigation';

	import Modal from '../common/Modal.svelte';
	import Account from './Settings/Account.svelte';
	import About from './Settings/About.svelte';
	import General from './Settings/General.svelte';
	import Interface from './Settings/Interface.svelte';
	import Audio from './Settings/Audio.svelte';
	import Chats from './Settings/Chats.svelte';
	import Personalization from './Settings/Personalization.svelte';
	import Connections from './Settings/Connections.svelte';
	import Tools from './Settings/Tools.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	interface SettingsTab {
		id: string;
		title: string;
		keywords: string[];
	}

	const searchData: SettingsTab[] = [
		{
			id: 'general',
			title: 'General',
			keywords: [
				'advancedparams',
				'advancedparameters',
				'advanced params',
				'advanced parameters',
				'configuration',
				'defaultparameters',
				'default parameters',
				'defaultsettings',
				'default settings',
				'general',
				'keepalive',
				'keep alive',
				'languages',
				'notifications',
				'requestmode',
				'request mode',
				'systemparameters',
				'system parameters',
				'systemprompt',
				'system prompt',
				'systemsettings',
				'system settings',
				'theme',
				'translate',
				'webuisettings',
				'webui settings'
			]
		},
		{
			id: 'interface',
			title: 'Interface',
			keywords: [
				'allow user location',
				'allow voice interruption in call',
				'allowuserlocation',
				'allowvoiceinterruptionincall',
				'always collapse codeblocks',
				'always collapse code blocks',
				'always expand details',
				'always on web search',
				'always play notification sound',
				'alwayscollapsecodeblocks',
				'alwaysexpanddetails',
				'alwaysonwebsearch',
				'alwaysplaynotificationsound',
				'android',
				'auto chat tags',
				'auto copy response to clipboard',
				'auto title',
				'autochattags',
				'autocopyresponsetoclipboard',
				'autotitle',
				'beta',
				'call',
				'chat background image',
				'chat bubble ui',
				'chat direction',
				'chat tags autogen',
				'chat tags autogeneration',
				'chat ui',
				'chatbackgroundimage',
				'chatbubbleui',
				'chatdirection',
				'chat tags autogeneration',
				'chattagsautogeneration',
				'chatui',
				'copy formatted text',
				'copyformattedtext',
				'default model',
				'defaultmodel',
				'design',
				'detect artifacts automatically',
				'detectartifactsautomatically',
				'display emoji in call',
				'display username',
				'displayemojiincall',
				'displayusername',
				'enter key behavior',
				'enterkeybehavior',
				'expand mode',
				'expandmode',
				'file',
				'followup autogeneration',
				'followupautogeneration',
				'fullscreen',
				'fullwidthmode',
				'full width mode',
				'haptic feedback',
				'hapticfeedback',
				'high contrast mode',
				'highcontrastmode',
				'iframe sandbox allow forms',
				'iframe sandbox allow same origin',
				'iframesandboxallowforms',
				'iframesandboxallowsameorigin',
				'imagecompression',
				'image compression',
				'imagemaxcompressionsize',
				'image max compression size',
				'interface customization',
				'interface options',
				'interfacecustomization',
				'interfaceoptions',
				'landing page mode',
				'landingpagemode',
				'layout',
				'left to right',
				'left-to-right',
				'lefttoright',
				'ltr',
				'paste large text as file',
				'pastelargetextasfile',
				'reset background',
				'resetbackground',
				'response auto copy',
				'responseautocopy',
				'rich text input for chat',
				'richtextinputforchat',
				'right to left',
				'right-to-left',
				'righttoleft',
				'rtl',
				'scroll behavior',
				'scroll on branch change',
				'scrollbehavior',
				'scrollonbranchchange',
				'select model',
				'selectmodel',
				'settings',
				'show username',
				'showusername',
				'stream large chunks',
				'streamlargechunks',
				'stylized pdf export',
				'stylizedpdfexport',
				'title autogeneration',
				'titleautogeneration',
				'toast notifications for new updates',
				'toastnotificationsfornewupdates',
				'upload background',
				'uploadbackground',
				'user interface',
				'user location access',
				'userinterface',
				'userlocationaccess',
				'vibration',
				'voice control',
				'voicecontrol',
				'widescreen mode',
				'widescreenmode',
				'whatsnew',
				'whats new',
				'websearchinchat',
				'web search in chat'
			]
		},
		...($user?.role === 'admin' ||
		($user?.role === 'user' && $config?.features?.enable_direct_connections)
			? [
					{
						id: 'connections',
						title: 'Connections',
						keywords: [
							'addconnection',
							'add connection',
							'manageconnections',
							'manage connections',
							'manage direct connections',
							'managedirectconnections',
							'settings'
						]
					}
				]
			: []),

		...($user?.role === 'admin' ||
		($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers)
			? [
					{
						id: 'tools',
						title: 'Tools',
						keywords: [
							'addconnection',
							'add connection',
							'managetools',
							'manage tools',
							'manage tool servers',
							'managetoolservers',
							'settings'
						]
					}
				]
			: []),

		{
			id: 'personalization',
			title: 'Personalization',
			keywords: [
				'account preferences',
				'account settings',
				'accountpreferences',
				'accountsettings',
				'custom settings',
				'customsettings',
				'experimental',
				'memories',
				'memory',
				'personalization',
				'personalize',
				'personal settings',
				'personalsettings',
				'profile',
				'user preferences',
				'userpreferences'
			]
		},
		{
			id: 'audio',
			title: 'Audio',
			keywords: [
				'audio config',
				'audio control',
				'audio features',
				'audio input',
				'audio output',
				'audio playback',
				'audio voice',
				'audioconfig',
				'audiocontrol',
				'audiofeatures',
				'audioinput',
				'audiooutput',
				'audioplayback',
				'audiovoice',
				'auto playback response',
				'autoplaybackresponse',
				'auto transcribe',
				'autotranscribe',
				'instant auto send after voice transcription',
				'instantautosendaftervoicetranscription',
				'language',
				'non local voices',
				'nonlocalvoices',
				'save settings',
				'savesettings',
				'set voice',
				'setvoice',
				'sound settings',
				'soundsettings',
				'speech config',
				'speech mode',
				'speech playback speed',
				'speech rate',
				'speech recognition',
				'speech settings',
				'speech speed',
				'speech synthesis',
				'speech to text engine',
				'speechconfig',
				'speechmode',
				'speechplaybackspeed',
				'speechrate',
				'speechrecognition',
				'speechsettings',
				'speechspeed',
				'speechsynthesis',
				'speechtotextengine',
				'speedch playback rate',
				'speedchplaybackrate',
				'stt settings',
				'sttsettings',
				'text to speech engine',
				'text to speech',
				'textospeechengine',
				'texttospeech',
				'texttospeechvoice',
				'text to speech voice',
				'voice control',
				'voice modes',
				'voice options',
				'voice playback',
				'voice recognition',
				'voice speed',
				'voicecontrol',
				'voicemodes',
				'voiceoptions',
				'voiceplayback',
				'voicerecognition',
				'voicespeed',
				'volume'
			]
		},
		{
			id: 'chats',
			title: 'Chats',
			keywords: [
				'archive all chats',
				'archive chats',
				'archiveallchats',
				'archivechats',
				'archived chats',
				'archivedchats',
				'chat activity',
				'chat history',
				'chat settings',
				'chatactivity',
				'chathistory',
				'chatsettings',
				'conversation activity',
				'conversation history',
				'conversationactivity',
				'conversationhistory',
				'conversations',
				'convos',
				'delete all chats',
				'delete chats',
				'deleteallchats',
				'deletechats',
				'export chats',
				'exportchats',
				'import chats',
				'importchats',
				'message activity',
				'message archive',
				'message history',
				'messagearchive',
				'messagehistory'
			]
		},
		{
			id: 'account',
			title: 'Account',
			keywords: [
				'account preferences',
				'account settings',
				'accountpreferences',
				'accountsettings',
				'api keys',
				'apikeys',
				'change password',
				'changepassword',
				'jwt token',
				'jwttoken',
				'login',
				'new password',
				'newpassword',
				'notification webhook url',
				'notificationwebhookurl',
				'personal settings',
				'personalsettings',
				'privacy settings',
				'privacysettings',
				'profileavatar',
				'profile avatar',
				'profile details',
				'profile image',
				'profile picture',
				'profiledetails',
				'profileimage',
				'profilepicture',
				'security settings',
				'securitysettings',
				'update account',
				'update password',
				'updateaccount',
				'updatepassword',
				'user account',
				'user data',
				'user preferences',
				'user profile',
				'useraccount',
				'userdata',
				'username',
				'userpreferences',
				'userprofile',
				'webhook url',
				'webhookurl'
			]
		},
		{
			id: 'about',
			title: 'About',
			keywords: [
				'about app',
				'about me',
				'about open webui',
				'about page',
				'about us',
				'aboutapp',
				'aboutme',
				'aboutopenwebui',
				'aboutpage',
				'aboutus',
				'check for updates',
				'checkforupdates',
				'contact',
				'copyright',
				'details',
				'discord',
				'documentation',
				'github',
				'help',
				'information',
				'license',
				'redistributions',
				'release',
				'see what\'s new',
				'seewhatsnew',
				'settings',
				'software info',
				'softwareinfo',
				'support',
				'terms and conditions',
				'terms of use',
				'termsandconditions',
				'termsofuse',
				'timothy jae ryang baek',
				'timothy j baek',
				'timothyjaeryangbaek',
				'timothyjbaek',
				'twitter',
				'update info',
				'updateinfo',
				'version info',
				'versioninfo'
			]
		}
	];

	let search = '';
	let visibleTabs = searchData.map((tab) => tab.id);
	let searchDebounceTimeout;

	const searchSettings = (query: string): string[] => {
		const lowerCaseQuery = query.toLowerCase().trim();
		return searchData
			.filter(
				(tab) =>
					tab.title.toLowerCase().includes(lowerCaseQuery) ||
					tab.keywords.some((keyword) => keyword.includes(lowerCaseQuery))
			)
			.map((tab) => tab.id);
	};

	const searchDebounceHandler = () => {
		clearTimeout(searchDebounceTimeout);
		searchDebounceTimeout = setTimeout(() => {
			visibleTabs = searchSettings(search);
			if (visibleTabs.length > 0 && !visibleTabs.includes(selectedTab)) {
				selectedTab = visibleTabs[0];
			}
		}, 100);
	};

	const saveSettings = async (updated) => {
		console.log(updated);
		await settings.set({ ...$settings, ...updated });
		await models.set(await getModels());
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	const getModels = async () => {
		return await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
		);
	};

	let selectedTab = 'general';

	// Function to handle sideways scrolling
	const scrollHandler = (event) => {
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			event.preventDefault(); // Prevent default vertical scrolling
			settingsTabsContainer.scrollLeft += event.deltaY; // Scroll sideways
		}
	};

	const addScrollListener = async () => {
		await tick();
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			settingsTabsContainer.addEventListener('wheel', scrollHandler);
		}
	};

	const removeScrollListener = async () => {
		await tick();
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			settingsTabsContainer.removeEventListener('wheel', scrollHandler);
		}
	};

	$: if (show) {
		addScrollListener();
	} else {
		removeScrollListener();
	}
</script>

<Modal size="lg" bind:show>
	<div style="--c:var(--color-gray-700); --dark-c:var(--color-gray-100)">
		<div
			style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.2rem"
		>
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Settings')}</div>
			<button
				aria-label={$i18n.t('Close settings modal')}
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<Icon name="x-mark" className="w-5 h-5" />
			</button>
		</div>

		<div
			style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pt:0.2rem; --pb:1rem; --g-md:1rem"
		>
			<div
				role="tablist"
				id="settings-tabs-container"
				style="--d:flex; --fd:row; --ofx:auto; --g:0.625rem; --g-md:0.2rem; --fd-md:column; --fx:1 1 0%; --fx-md:none; --w-md:10rem; --minh-md:32rem; --maxh-md:32rem; --dark-c:var(--color-gray-200); --size:0.8rem; --weight:500; --ta:left; --mb:0.2rem; --mb-md:0; --translatey:-0.2rem; --p:0.2rem"
				class="tabs"
			>
				<div
					style="--d:none; --d-md:flex; --w:100%; --radius:0.6rem; --mb:-0.2rem; --px:0.125rem; --g:0.5rem"
					id="settings-search"
				>
					<div style="--as:center; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent">
						<Icon name="search" className="size-3.5"
							strokeWidth={($settings?.highContrastMode ?? false) ? '3' : '1.5'} />
					</div>
					<label class="sr-only" for="search-input-settings-modal">{$i18n.t('Search')}</label>
					<input
						class={`w-full py-1.5 text-sm bg-transparent dark:text-gray-300 outline-hidden
								${($settings?.highContrastMode ?? false) ? 'placeholder-gray-800' : ''}`}
						bind:value={search}
						id="search-input-settings-modal"
						on:input={searchDebounceHandler}
						placeholder={$i18n.t('Search')}
					/>
				</div>
				{#if visibleTabs.length > 0}
					{#each visibleTabs as tabId (tabId)}
						{#if tabId === 'general'}
							<button
								role="tab"
								aria-controls="tab-general"
								aria-selected={selectedTab === 'general'}
								style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
								'general'
									? ($settings?.highContrastMode ?? false)
										? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
										: ''
									: ($settings?.highContrastMode ?? false)
										? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
										: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
								on:click={() => {
									selectedTab = 'general';
								}}
							>
								<div style="--as:center; --mr:0.5rem">
									<Icon name="gear-fill-20" className="size-4" />
								</div>
								<div style="--as:center">{$i18n.t('General')}</div>
							</button>
						{:else if tabId === 'interface'}
							<button
								role="tab"
								aria-controls="tab-interface"
								aria-selected={selectedTab === 'interface'}
								style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
								'interface'
									? ($settings?.highContrastMode ?? false)
										? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
										: ''
									: ($settings?.highContrastMode ?? false)
										? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
										: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
								on:click={() => {
									selectedTab = 'interface';
								}}
							>
								<div style="--as:center; --mr:0.5rem">
									<Icon name="monitor-fill-16" className="size-4" />
								</div>
								<div style="--as:center">{$i18n.t('Interface')}</div>
							</button>
						{:else if tabId === 'connections'}
							{#if $user?.role === 'admin' || ($user?.role === 'user' && $config?.features?.enable_direct_connections)}
								<button
									role="tab"
									aria-controls="tab-connections"
									aria-selected={selectedTab === 'connections'}
									style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
									'connections'
										? ($settings?.highContrastMode ?? false)
											? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
											: ''
										: ($settings?.highContrastMode ?? false)
											? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
											: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
									on:click={() => {
										selectedTab = 'connections';
									}}
								>
									<div style="--as:center; --mr:0.5rem">
										<Icon name="cloud-fill-16" className="size-4" />
									</div>
									<div style="--as:center">{$i18n.t('Connections')}</div>
								</button>
							{/if}
						{:else if tabId === 'tools'}
							{#if $user?.role === 'admin' || ($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers)}
								<button
									role="tab"
									aria-controls="tab-tools"
									aria-selected={selectedTab === 'tools'}
									style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
									'tools'
										? ($settings?.highContrastMode ?? false)
											? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
											: ''
										: ($settings?.highContrastMode ?? false)
											? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
											: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
									on:click={() => {
										selectedTab = 'tools';
									}}
								>
									<div style="--as:center; --mr:0.5rem">
										<Icon name="wrench-solid" className="size-4" />
									</div>
									<div style="--as:center">{$i18n.t('Tools')}</div>
								</button>
							{/if}
						{:else if tabId === 'personalization'}
							<button
								role="tab"
								aria-controls="tab-personalization"
								aria-selected={selectedTab === 'personalization'}
								style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
								'personalization'
									? ($settings?.highContrastMode ?? false)
										? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
										: ''
									: ($settings?.highContrastMode ?? false)
										? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
										: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
								on:click={() => {
									selectedTab = 'personalization';
								}}
							>
								<div style="--as:center; --mr:0.5rem">
									<Icon name="user" />
								</div>
								<div style="--as:center">{$i18n.t('Personalization')}</div>
							</button>
						{:else if tabId === 'audio'}
							<button
								role="tab"
								aria-controls="tab-audio"
								aria-selected={selectedTab === 'audio'}
								style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
								'audio'
									? ($settings?.highContrastMode ?? false)
										? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
										: ''
									: ($settings?.highContrastMode ?? false)
										? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
										: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
								on:click={() => {
									selectedTab = 'audio';
								}}
							>
								<div style="--as:center; --mr:0.5rem">
									<Icon name="settingsmodal-icon-abc849" className="size-4" />
								</div>
								<div style="--as:center">{$i18n.t('Audio')}</div>
							</button>
						{:else if tabId === 'chats'}
							<button
								role="tab"
								aria-controls="tab-chats"
								aria-selected={selectedTab === 'chats'}
								style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
								'chats'
									? ($settings?.highContrastMode ?? false)
										? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
										: ''
									: ($settings?.highContrastMode ?? false)
										? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
										: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
								on:click={() => {
									selectedTab = 'chats';
								}}
							>
								<div style="--as:center; --mr:0.5rem">
									<Icon name="speech-bubble-fill" className="size-4" />
								</div>
								<div style="--as:center">{$i18n.t('Chats')}</div>
							</button>
						{:else if tabId === 'account'}
							<button
								role="tab"
								aria-controls="tab-account"
								aria-selected={selectedTab === 'account'}
								style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
								'account'
									? ($settings?.highContrastMode ?? false)
										? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
										: ''
									: ($settings?.highContrastMode ?? false)
										? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
										: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
								on:click={() => {
									selectedTab = 'account';
								}}
							>
								<div style="--as:center; --mr:0.5rem">
									<Icon name="user-circle-solid" className="size-4" />
								</div>
								<div style="--as:center">{$i18n.t('Account')}</div>
							</button>
						{:else if tabId === 'about'}
							<button
								role="tab"
								aria-controls="tab-about"
								aria-selected={selectedTab === 'about'}
								style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --d:flex; --ta:left; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); {selectedTab ===
								'about'
									? ($settings?.highContrastMode ?? false)
										? '--bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800)'
										: ''
									: ($settings?.highContrastMode ?? false)
										? '--hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-800)'
										: '--c:var(--color-gray-300); --dark-c:var(--color-gray-600); --hvr-c:var(--color-gray-700); --hvr-dark-c:#fff'}"
								on:click={() => {
									selectedTab = 'about';
								}}
							>
								<div style="--as:center; --mr:0.5rem">
									<Icon name="help-circle-fill-20" className="size-4" />
								</div>
								<div style="--as:center">{$i18n.t('About')}</div>
							</button>
						{/if}
					{/each}
				{:else}
					<div style="--ta:center; --c:var(--color-gray-500); --mt:1rem">
						{$i18n.t('No results found')}
					</div>
				{/if}
				{#if $user?.role === 'admin'}
					<a
						href="/admin/settings"
						style="--p:0.2rem; --minw:fit-content; --radius:0.5rem; --fx:1 1 0%; --fx-md:none; --mt-md:auto; --d:flex; --ta:left; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						class={$settings?.highContrastMode
							? 'hover:bg-gray-200 dark:hover:bg-gray-800'
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}
						on:click={async (e) => {
							e.preventDefault();
							await goto('/admin/settings');
							show = false;
						}}
					>
						<div style="--as:center; --mr:0.5rem">
							<Icon name="image-fill-24" className="size-4" />
						</div>
						<div style="--as:center">{$i18n.t('Admin Settings')}</div>
					</a>
				{/if}
			</div>
			<div style="--fx:1 1 0%; --minh-md:32rem; --maxh:32rem">
				{#if selectedTab === 'general'}
					<General
						{getModels}
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'interface'}
					<Interface
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'connections'}
					<Connections
						saveSettings={async (updated) => {
							await saveSettings(updated);
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'tools'}
					<Tools
						saveSettings={async (updated) => {
							await saveSettings(updated);
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'personalization'}
					<Personalization
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'audio'}
					<Audio
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'chats'}
					<Chats {saveSettings} />
				{:else if selectedTab === 'account'}
					<Account
						{saveSettings}
						saveHandler={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'about'}
					<About />
				{/if}
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		appearance: textfield;
		-moz-appearance: textfield; /* Firefox */
	}
</style>
