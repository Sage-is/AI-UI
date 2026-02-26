<script lang="ts">
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { updateUserInfo } from '$lib/apis/users';
	import { getUserPosition } from '$lib/utils';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let backgroundImageUrl: string | null = null;
	let inputFiles: FileList | null = null;
	let filesInputElement: HTMLInputElement;
	let defaultModelId = '';
	let imageCompressionSize = { width: '', height: '' };

	// Data-driven settings configuration
	const settingsConfig = [
		// UI Section
		{
			section: 'UI',
			settings: [
				{
					key: 'highContrastMode',
					labelKey: 'High Contrast Mode',
					betaLabel: true,
					defaultValue: false,
					settingsPath: 'highContrastMode'
				},
				{
					key: 'landingPageMode',
					labelKey: 'Landing Page Mode',
					defaultValue: '',
					settingsPath: 'landingPageMode',
					getDisplayValue: (value) => value === '' ? 'Default' : 'Chat',
					customToggle: true
				},
				{
					key: 'chatBubble',
					labelKey: 'Chat Bubble UI',
					defaultValue: true,
					settingsPath: 'chatBubble'
				},
				{
					key: 'showUsername',
					labelKey: 'Display the username instead of You in the Chat',
					defaultValue: false,
					settingsPath: 'showUsername',
					conditionalDisplay: () => !$settings.chatBubble
				},
				{
					key: 'widescreenMode',
					labelKey: 'Widescreen Mode',
					defaultValue: false,
					settingsPath: 'widescreenMode'
				},
				{
					key: 'chatDirection',
					labelKey: 'Chat direction',
					defaultValue: 'auto',
					settingsPath: 'chatDirection',
					getDisplayValue: (value) => value === 'LTR' ? 'LTR' : value === 'RTL' ? 'RTL' : 'Auto',
					customToggle: true
				},
				{
					key: 'notificationSound',
					labelKey: 'Notification Sound',
					defaultValue: true,
					settingsPath: 'notificationSound'
				},
				{
					key: 'notificationSoundAlways',
					labelKey: 'Always Play Notification Sound',
					defaultValue: false,
					settingsPath: 'notificationSoundAlways',
					conditionalDisplay: () => settingsValues.notificationSound
				},
				{
					key: 'showUpdateToast',
					labelKey: 'Toast notifications for new updates',
					defaultValue: true,
					settingsPath: 'showUpdateToast',
					adminOnly: true
				},
				{
					key: 'showChangelog',
					labelKey: `Show "What's New" modal on login`,
					defaultValue: true,
					settingsPath: 'showChangelog',
					adminOnly: true
				}
			]
		},
		// Chat Section
		{
			section: 'Chat',
			settings: [
				{
					key: 'titleAutoGenerate',
					labelKey: 'Title Auto-Generation',
					defaultValue: true,
					settingsPath: 'title.auto',
					customSave: (value) => saveSettings({ title: { ...$settings.title, auto: value } })
				},
				{
					key: 'autoFollowUps',
					labelKey: 'Follow-Up Auto-Generation',
					defaultValue: true,
					settingsPath: 'autoFollowUps'
				},
				{
					key: 'autoTags',
					labelKey: 'Chat Tags Auto-Generation',
					defaultValue: true,
					settingsPath: 'autoTags'
				},
				{
					key: 'detectArtifacts',
					labelKey: 'Detect Artifacts Automatically',
					defaultValue: true,
					settingsPath: 'detectArtifacts'
				},
				{
					key: 'responseAutoCopy',
					labelKey: 'Auto-Copy Response to Clipboard',
					defaultValue: false,
					settingsPath: 'responseAutoCopy',
					requiresPermission: true
				},
				{
					key: 'chatFadeStreamingText',
					labelKey: 'Fade Effect for Streaming Text',
					defaultValue: true,
					settingsPath: 'chatFadeStreamingText'
				},
				{
					key: 'keepFollowUpPrompts',
					labelKey: 'Keep Follow-Up Prompts in Chat',
					defaultValue: false,
					settingsPath: 'keepFollowUpPrompts'
				},
				{
					key: 'insertFollowUpPrompt',
					labelKey: 'Insert Follow-Up Prompt to Input',
					defaultValue: false,
					settingsPath: 'insertFollowUpPrompt'
				},
				{
					key: 'richTextInput',
					labelKey: 'Rich Text Input for Chat',
					defaultValue: true,
					settingsPath: 'richTextInput'
				},
				{
					key: 'insertPromptAsRichText',
					labelKey: 'Insert Prompt as Rich Text',
					defaultValue: false,
					settingsPath: 'insertPromptAsRichText',
					conditionalDisplay: () => settingsValues.richTextInput
				},
				{
					key: 'promptAutocomplete',
					labelKey: 'Prompt Autocompletion',
					defaultValue: false,
					settingsPath: 'promptAutocomplete',
					conditionalDisplay: () => settingsValues.richTextInput && $config?.features?.enable_autocomplete_generation
				},
				{
					key: 'largeTextAsFile',
					labelKey: 'Paste Large Text as File',
					defaultValue: false,
					settingsPath: 'largeTextAsFile'
				},
				{
					key: 'copyFormatted',
					labelKey: 'Copy Formatted Text',
					defaultValue: false,
					settingsPath: 'copyFormatted'
				},
				{
					key: 'collapseCodeBlocks',
					labelKey: 'Always Collapse Code Blocks',
					defaultValue: false,
					settingsPath: 'collapseCodeBlocks'
				},
				{
					key: 'expandDetails',
					labelKey: 'Always Expand Details',
					defaultValue: false,
					settingsPath: 'expandDetails'
				},
				{
					key: 'userLocation',
					labelKey: 'Allow User Location',
					defaultValue: false,
					settingsPath: 'userLocation',
					requiresPermission: true
				},
				{
					key: 'hapticFeedback',
					labelKey: 'Haptic Feedback',
					androidLabel: true,
					defaultValue: false,
					settingsPath: 'hapticFeedback'
				},
				{
					key: 'splitLargeChunks',
					labelKey: 'Fluidly stream large external response chunks',
					defaultValue: false,
					settingsPath: 'splitLargeChunks'
				},
				{
					key: 'ctrlEnterToSend',
					labelKey: 'Enter Key Behavior',
					defaultValue: false,
					settingsPath: 'ctrlEnterToSend',
					getDisplayValue: (value) => value ? 'Ctrl+Enter to Send' : 'Enter to Send'
				},
				{
					key: 'scrollOnBranchChange',
					labelKey: 'Scroll On Branch Change',
					defaultValue: true,
					settingsPath: 'scrollOnBranchChange'
				},
				{
					key: 'webSearch',
					labelKey: 'Web Search in Chat',
					defaultValue: null,
					settingsPath: 'webSearch',
					getDisplayValue: (value) => value === 'always' ? 'Always' : 'Default',
					customToggle: true
				},
				{
					key: 'iframeSandboxAllowSameOrigin',
					labelKey: 'iframe Sandbox Allow Same Origin',
					defaultValue: false,
					settingsPath: 'iframeSandboxAllowSameOrigin'
				},
				{
					key: 'iframeSandboxAllowForms',
					labelKey: 'iframe Sandbox Allow Forms',
					defaultValue: false,
					settingsPath: 'iframeSandboxAllowForms'
				},
				{
					key: 'stylizedPdfExport',
					labelKey: 'Stylized PDF Export',
					defaultValue: true,
					settingsPath: 'stylizedPdfExport'
				}
			]
		},
		// Voice Section
		{
			section: 'Voice',
			settings: [
				{
					key: 'voiceInterruption',
					labelKey: 'Allow Voice Interruption in Call',
					defaultValue: false,
					settingsPath: 'voiceInterruption'
				},
				{
					key: 'showEmojiInCall',
					labelKey: 'Display Emoji in Call',
					defaultValue: false,
					settingsPath: 'showEmojiInCall'
				}
			]
		},
		// File Section
		{
			section: 'File',
			settings: [
				{
					key: 'imageCompression',
					labelKey: 'Image Compression',
					defaultValue: false,
					settingsPath: 'imageCompression'
				}
			]
		}
	];

	// Reactive values for all settings
	$: settingsValues = settingsConfig.reduce((acc: Record<string, any>, section) => {
		section.settings.forEach(setting => {
			acc[setting.key] = getSettingValue(setting);
		});
		return acc;
	}, {});

	// Helper function to get setting value from store
	function getSettingValue(setting: any) {
		const path = setting.settingsPath.split('.');
		let value = $settings;
		for (const key of path) {
			value = value?.[key];
		}
		return value ?? setting.defaultValue;
	}

	// Unified toggle handler for all settings
	const toggleSetting = async (settingConfig: any) => {
		const currentValue = settingsValues[settingConfig.key];

		// Handle custom toggle logic
		if (settingConfig.customToggle) {
			let newValue;
			if (settingConfig.key === 'landingPageMode') {
				newValue = currentValue === '' ? 'chat' : '';
			} else if (settingConfig.key === 'chatDirection') {
				if (currentValue === 'auto') {
					newValue = 'LTR';
				} else if (currentValue === 'LTR') {
					newValue = 'RTL';
				} else {
					newValue = 'auto';
				}
			} else if (settingConfig.key === 'webSearch') {
				newValue = currentValue === null ? 'always' : null;
			}
			
			if (settingConfig.customSave) {
				settingConfig.customSave(newValue);
			} else {
				saveSettings({ [settingConfig.settingsPath]: newValue });
			}
			return;
		}

		// Handle permission-required settings
		if (settingConfig.requiresPermission) {
			if (settingConfig.key === 'responseAutoCopy') {
				const permission = await navigator.clipboard
					.readText()
					.then(() => 'granted')
					.catch(() => '');
				
				if (permission !== 'granted') {
					toast.error(
						$i18n.t(
							'Clipboard write permission denied. Please check your browser settings to grant the necessary access.'
						)
					);
					return;
				}
			} else if (settingConfig.key === 'userLocation') {
				const newValue = !currentValue;
				if (newValue) {
					const position = await getUserPosition().catch((error) => {
						toast.error(error.message);
						return null;
					});

					if (position) {
						await updateUserInfo(localStorage.token, { location: position });
						toast.success($i18n.t('User location successfully retrieved.'));
					} else {
						return; // Don't update setting if location failed
					}
				}
			}
		}

		// Standard boolean toggle
		const newValue = !currentValue;
		
		if (settingConfig.customSave) {
			settingConfig.customSave(newValue);
		} else {
			saveSettings({ [settingConfig.settingsPath]: newValue });
		}
	};

	const updateInterfaceHandler = async () => {
		saveSettings({
			models: [defaultModelId],
			imageCompressionSize: imageCompressionSize
		});
	};

	onMount(async () => {
		// Initialize all settings from configuration
		settingsConfig.forEach(section => {
			section.settings.forEach(setting => {
				// Values are reactive and handled by settingsValues
			});
		});

		// Initialize non-reactive values
		defaultModelId = $settings?.models?.at(0) ?? '';
		if ($config?.default_models) {
			defaultModelId = $config.default_models.split(',')[0];
		}

		backgroundImageUrl = $settings?.backgroundImageUrl ?? null;
		imageCompressionSize = $settings?.imageCompressionSize ?? { width: '', height: '' };
	});
</script>

<form
	id="tab-interface"
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.75rem; --size:0.875rem"
	on:submit|preventDefault={() => {
		updateInterfaceHandler();
		dispatch('save');
	}}
>
	<input
		bind:this={filesInputElement}
		bind:files={inputFiles}
		type="file"
		hidden
		accept="image/*"
		on:change={() => {
			if (!inputFiles || inputFiles.length === 0) return;
			
			const file = inputFiles[0];
			if (!['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file.type)) {
				console.log(`Unsupported File Type '${file.type}'.`);
				inputFiles = null;
				return;
			}

			let reader = new FileReader();
			reader.onload = (event) => {
				const target = event.target;
				if (target && target.result) {
					let originalImageUrl = `${target.result}`;
					backgroundImageUrl = originalImageUrl;
					saveSettings({ backgroundImageUrl });
				}
			};
			reader.readAsDataURL(file);
		}}
	/>

	<div style="--g:0.75rem; --ofy:scroll; --maxh:28rem; --maxh-lg:100%">
		{#each settingsConfig as sectionConfig}
			<div>
				<h1 style="--mb:0.375rem; --size:0.875rem; --weight:500">{$i18n.t(sectionConfig.section)}</h1>

				{#each sectionConfig.settings as setting}
					{#if !setting.adminOnly || $user?.role === 'admin'}
						{#if !setting.conditionalDisplay || setting.conditionalDisplay()}
							<div>
								<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
									<div id="{setting.key}-label" style="--as:center; --size:0.75rem">
										{$i18n.t(setting.labelKey)}
										{#if setting.betaLabel}
											({$i18n.t('Beta')})
										{/if}
										{#if setting.androidLabel}
											({$i18n.t('Android')})
										{/if}
									</div>

									<button
										aria-labelledby="{setting.key}-label"
										style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										on:click={() => toggleSetting(setting)}
										type="button"
									>
										{#if setting.getDisplayValue}
											<span style="--ml:0.5rem; --as:center">{$i18n.t(setting.getDisplayValue(settingsValues[setting.key]))}</span>
										{:else}
											{#if settingsValues[setting.key] === true}
												<span style="--ml:0.5rem; --as:center">{$i18n.t('On')}</span>
											{:else}
												<span style="--ml:0.5rem; --as:center">{$i18n.t('Off')}</span>
											{/if}
										{/if}
									</button>
								</div>
							</div>
						{/if}
					{/if}
				{/each}
			</div>
		{/each}

		<!-- Special case: Chat Background Image -->
		<div>
			<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
				<div id="chat-background-label" style="--as:center; --size:0.75rem">
					{$i18n.t('Chat Background Image')}
				</div>

				<button
					aria-labelledby="chat-background-label"
					style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						if (backgroundImageUrl !== null) {
							backgroundImageUrl = null;
							saveSettings({ backgroundImageUrl });
						} else {
							filesInputElement.click();
						}
					}}
					type="button"
				>
					{#if backgroundImageUrl !== null}
						<span style="--ml:0.5rem; --as:center">{$i18n.t('Reset')}</span>
					{:else}
						<span style="--ml:0.5rem; --as:center">{$i18n.t('Upload')}</span>
					{/if}
				</button>
			</div>
		</div>

		<!-- Special case: Image Compression Size -->
		{#if settingsValues.imageCompression}
			<div>
				<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between; --size:0.75rem">
					<div id="image-compression-size-label" style="--as:center; --size:0.75rem">
						{$i18n.t('Image Max Compression Size')}
					</div>

					<div>
						<label class="sr-only" for="image-comp-width"
							>{$i18n.t('Image Max Compression Size width')}</label
						>
						<input
							bind:value={imageCompressionSize.width}
							type="number"
							style="--w:5rem; --bgc:transparent; --oe:none; --ta:center"
							min="0"
							placeholder="Width"
						/>x
						<label class="sr-only" for="image-comp-height"
							>{$i18n.t('Image Max Compression Size height')}</label
						>
						<input
							bind:value={imageCompressionSize.height}
							type="number"
							style="--w:5rem; --bgc:transparent; --oe:none; --ta:center"
							min="0"
							placeholder="Height"
						/>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --size:0.875rem; --weight:500">
		<button
			style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
