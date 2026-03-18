<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	const dispatch = createEventDispatcher();

	import { getBackendConfig } from '$lib/apis';
	import {
		getAudioConfig,
		updateAudioConfig,
		getModels as _getModels,
		getVoices as _getVoices
	} from '$lib/apis/audio';
	import { config, settings } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import { TTS_RESPONSE_SPLIT } from '$lib/types';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveHandler: () => void;

	// Audio
	let TTS_OPENAI_API_BASE_URL = '';
	let TTS_OPENAI_API_KEY = '';
	let TTS_API_KEY = '';
	let TTS_ENGINE = '';
	let TTS_MODEL = '';
	let TTS_VOICE = '';
	let TTS_SPLIT_ON: TTS_RESPONSE_SPLIT = TTS_RESPONSE_SPLIT.PUNCTUATION;
	let TTS_AZURE_SPEECH_REGION = '';
	let TTS_AZURE_SPEECH_BASE_URL = '';
	let TTS_AZURE_SPEECH_OUTPUT_FORMAT = '';

	let STT_OPENAI_API_BASE_URL = '';
	let STT_OPENAI_API_KEY = '';
	let STT_ENGINE = '';
	let STT_MODEL = '';
	let STT_SUPPORTED_CONTENT_TYPES = '';
	let STT_WHISPER_MODEL = '';
	let STT_AZURE_API_KEY = '';
	let STT_AZURE_REGION = '';
	let STT_AZURE_LOCALES = '';
	let STT_AZURE_BASE_URL = '';
	let STT_AZURE_MAX_SPEAKERS = '';
	let STT_DEEPGRAM_API_KEY = '';

	let STT_WHISPER_MODEL_LOADING = false;

	// eslint-disable-next-line no-undef
	let voices: SpeechSynthesisVoice[] = [];
	let models: Awaited<ReturnType<typeof _getModels>>['models'] = [];

	const getModels = async () => {
		if (TTS_ENGINE === '') {
			models = [];
		} else {
			const res = await _getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				console.log(res);
				models = res.models;
			}
		}
	};

	const getVoices = async () => {
		if (TTS_ENGINE === '') {
			const getVoicesLoop = setInterval(() => {
				voices = speechSynthesis.getVoices();

				// do your loop
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);
					voices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
				}
			}, 100);
		} else {
			const res = await _getVoices(localStorage.token).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				console.log(res);
				voices = res.voices;
				voices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
			}
		}
	};

	const updateConfigHandler = async () => {
		const res = await updateAudioConfig(localStorage.token, {
			tts: {
				OPENAI_API_BASE_URL: TTS_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: TTS_OPENAI_API_KEY,
				API_KEY: TTS_API_KEY,
				ENGINE: TTS_ENGINE,
				MODEL: TTS_MODEL,
				VOICE: TTS_VOICE,
				SPLIT_ON: TTS_SPLIT_ON,
				AZURE_SPEECH_REGION: TTS_AZURE_SPEECH_REGION,
				AZURE_SPEECH_BASE_URL: TTS_AZURE_SPEECH_BASE_URL,
				AZURE_SPEECH_OUTPUT_FORMAT: TTS_AZURE_SPEECH_OUTPUT_FORMAT
			},
			stt: {
				OPENAI_API_BASE_URL: STT_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: STT_OPENAI_API_KEY,
				ENGINE: STT_ENGINE,
				MODEL: STT_MODEL,
				SUPPORTED_CONTENT_TYPES: STT_SUPPORTED_CONTENT_TYPES.split(','),
				WHISPER_MODEL: STT_WHISPER_MODEL,
				DEEPGRAM_API_KEY: STT_DEEPGRAM_API_KEY,
				AZURE_API_KEY: STT_AZURE_API_KEY,
				AZURE_REGION: STT_AZURE_REGION,
				AZURE_LOCALES: STT_AZURE_LOCALES,
				AZURE_BASE_URL: STT_AZURE_BASE_URL,
				AZURE_MAX_SPEAKERS: STT_AZURE_MAX_SPEAKERS
			}
		});

		if (res) {
			saveHandler();
			config.set(await getBackendConfig());
		}
	};

	const sttModelUpdateHandler = async () => {
		STT_WHISPER_MODEL_LOADING = true;
		await updateConfigHandler();
		STT_WHISPER_MODEL_LOADING = false;
	};

	onMount(async () => {
		const res = await getAudioConfig(localStorage.token);

		if (res) {
			console.log(res);
			TTS_OPENAI_API_BASE_URL = res.tts.OPENAI_API_BASE_URL;
			TTS_OPENAI_API_KEY = res.tts.OPENAI_API_KEY;
			TTS_API_KEY = res.tts.API_KEY;

			TTS_ENGINE = res.tts.ENGINE;
			TTS_MODEL = res.tts.MODEL;
			TTS_VOICE = res.tts.VOICE;

			TTS_SPLIT_ON = res.tts.SPLIT_ON || TTS_RESPONSE_SPLIT.PUNCTUATION;

			TTS_AZURE_SPEECH_REGION = res.tts.AZURE_SPEECH_REGION;
			TTS_AZURE_SPEECH_BASE_URL = res.tts.AZURE_SPEECH_BASE_URL;
			TTS_AZURE_SPEECH_OUTPUT_FORMAT = res.tts.AZURE_SPEECH_OUTPUT_FORMAT;

			STT_OPENAI_API_BASE_URL = res.stt.OPENAI_API_BASE_URL;
			STT_OPENAI_API_KEY = res.stt.OPENAI_API_KEY;

			STT_ENGINE = res.stt.ENGINE;
			STT_MODEL = res.stt.MODEL;
			STT_SUPPORTED_CONTENT_TYPES = (res?.stt?.SUPPORTED_CONTENT_TYPES ?? []).join(',');
			STT_WHISPER_MODEL = res.stt.WHISPER_MODEL;
			STT_AZURE_API_KEY = res.stt.AZURE_API_KEY;
			STT_AZURE_REGION = res.stt.AZURE_REGION;
			STT_AZURE_LOCALES = res.stt.AZURE_LOCALES;
			STT_AZURE_BASE_URL = res.stt.AZURE_BASE_URL;
			STT_AZURE_MAX_SPEAKERS = res.stt.AZURE_MAX_SPEAKERS;
			STT_DEEPGRAM_API_KEY = res.stt.DEEPGRAM_API_KEY;
		}

		await getVoices();
		await getModels();
	});
</script>

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.875rem"
	on:submit|preventDefault={async () => {
		await updateConfigHandler();
		dispatch('save');
	}}
>
	<div style="--g:0.6rem; --ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		<div style="--d:flex; --fd:column; --g:0.6rem">
			<div>
				<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Speech-to-Text')}</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

				{#if STT_ENGINE !== 'web'}
					<div style="--mb:0.5rem">
						<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('Supported MIME Types')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%">
								<input
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
									bind:value={STT_SUPPORTED_CONTENT_TYPES}
									placeholder={$i18n.t(
										'e.g., audio/wav,audio/mpeg,video/* (leave blank for defaults)'
									)}
								/>
							</div>
						</div>
					</div>
				{/if}

				<div style="--mb:0.5rem; --py:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Speech-to-Text Engine')}</div>
					<div style="--d:flex; --ai:center; --pos:relative">
						<select
							style="--dark-bgc:var(--color-gray-900); --cur:pointer; --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.6rem; --bgc:transparent; --oe:none; --ta:right"
							bind:value={STT_ENGINE}
							placeholder="Select an engine"
						>
							<option value="">{$i18n.t('Whisper (Local)')}</option>
							<option value="openai">OpenAI</option>
							<option value="web">{$i18n.t('Web API')}</option>
							<option value="deepgram">Deepgram</option>
							<option value="azure">Azure AI Speech</option>
						</select>
					</div>
				</div>

				{#if STT_ENGINE === 'openai'}
					<div>
						<div style="--mt:0.25rem; --d:flex; --g:0.5rem; --mb:0.25rem">
							<input
								style="--fx:1 1 0%; --w:100%; --bgc:transparent; --oe:none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={STT_OPENAI_API_BASE_URL}
								required
							/>

							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={STT_OPENAI_API_KEY} />
						</div>
					</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div>
						<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('STT Model')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%">
								<input
									list="model-list"
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
									bind:value={STT_MODEL}
									placeholder="Select a model"
								/>

								<datalist id="model-list">
									<option value="whisper-1" />
								</datalist>
							</div>
						</div>
					</div>
				{:else if STT_ENGINE === 'deepgram'}
					<div>
						<div style="--mt:0.25rem; --d:flex; --g:0.5rem; --mb:0.25rem">
							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={STT_DEEPGRAM_API_KEY} />
						</div>
					</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div>
						<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('STT Model')}</div>
						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%">
								<input
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
									bind:value={STT_MODEL}
									placeholder="Select a model (optional)"
								/>
							</div>
						</div>
						<div style="--mt:0.5rem; --mb:0.25rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
							{$i18n.t('Leave model field empty to use the default model.')}
							<a
								style="--hvr-td:underline; --dark-c:var(--color-gray-200); --c:var(--color-gray-800)"
								href="https://developers.deepgram.com/docs/models"
								target="_blank"
							>
								{$i18n.t('Click here to see available models.')}
							</a>
						</div>
					</div>
				{:else if STT_ENGINE === 'azure'}
					<div>
						<div style="--mt:0.25rem; --d:flex; --g:0.5rem; --mb:0.25rem">
							<SensitiveInput
								placeholder={$i18n.t('API Key')}
								bind:value={STT_AZURE_API_KEY}
								required
							/>
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('Azure Region')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={STT_AZURE_REGION}
										placeholder={$i18n.t('e.g., westus (leave blank for eastus)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('Language Locales')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={STT_AZURE_LOCALES}
										placeholder={$i18n.t('e.g., en-US,ja-JP (leave blank for auto-detect)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('Endpoint URL')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={STT_AZURE_BASE_URL}
										placeholder={$i18n.t('(leave blank for to use commercial endpoint)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('Max Speakers')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={STT_AZURE_MAX_SPEAKERS}
										placeholder={$i18n.t('e.g., 3, 4, 5 (leave blank for default)')}
									/>
								</div>
							</div>
						</div>
					</div>
				{:else if STT_ENGINE === ''}
					<div>
						<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('STT Model')}</div>

						<div style="--d:flex; --w:100%">
							<div style="--fx:1 1 0%; --mr:0.5rem">
								<input
									style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
									placeholder={$i18n.t('Set whisper model')}
									bind:value={STT_WHISPER_MODEL}
								/>
							</div>

							<button
								style="--px:0.625rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-200); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-100); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								on:click={() => {
									sttModelUpdateHandler();
								}}
								disabled={STT_WHISPER_MODEL_LOADING}
							>
								{#if STT_WHISPER_MODEL_LOADING}
									<div style="--as:center">
										<Spinner />
									</div>
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										style="--w:1rem; --h:1rem"
									>
										<path
											d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
										/>
										<path
											d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
										/>
									</svg>
								{/if}
							</button>
						</div>

						<div style="--mt:0.5rem; --mb:0.25rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
							{$i18n.t(`Sage.is AI uses faster-whisper internally.`)}

							<a
								style="--hvr-td:underline; --dark-c:var(--color-gray-200); --c:var(--color-gray-800)"
								href="https://github.com/SYSTRAN/faster-whisper"
								target="_blank"
							>
								{$i18n.t(
									`Click here to learn more about faster-whisper and see the available models.`
								)}
							</a>
						</div>
					</div>
				{/if}
			</div>

			<div>
				<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Text-to-Speech')}</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

				<div style="--mb:0.5rem; --py:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Text-to-Speech Engine')}</div>
					<div style="--d:flex; --ai:center; --pos:relative">
						<select
							style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --cur:pointer; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.6rem; --bgc:transparent; --oe:none; --ta:right"
							bind:value={TTS_ENGINE}
							placeholder="Select a mode"
							on:change={async (e) => {
								await updateConfigHandler();
								await getVoices();
								await getModels();

								if (e.target?.value === 'openai') {
									TTS_VOICE = 'alloy';
									TTS_MODEL = 'tts-1';
								} else {
									TTS_VOICE = '';
									TTS_MODEL = '';
								}
							}}
						>
							<option value="">{$i18n.t('Web API')}</option>
							<option value="transformers">{$i18n.t('Transformers')} ({$i18n.t('Local')})</option>
							<option value="openai">{$i18n.t('OpenAI')}</option>
							<option value="elevenlabs">{$i18n.t('ElevenLabs')}</option>
							<option value="azure">{$i18n.t('Azure AI Speech')}</option>
						</select>
					</div>
				</div>

				{#if TTS_ENGINE === 'openai'}
					<div>
						<div style="--mt:0.25rem; --d:flex; --g:0.5rem; --mb:0.25rem">
							<input
								style="--fx:1 1 0%; --w:100%; --bgc:transparent; --oe:none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={TTS_OPENAI_API_BASE_URL}
								required
							/>

							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={TTS_OPENAI_API_KEY} />
						</div>
					</div>
				{:else if TTS_ENGINE === 'elevenlabs'}
					<div>
						<div style="--mt:0.25rem; --d:flex; --g:0.5rem; --mb:0.25rem">
							<input
								style="--fx:1 1 0%; --w:100%; --radius:0.5rem; --py:0.5rem; --pl:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								placeholder={$i18n.t('API Key')}
								bind:value={TTS_API_KEY}
								required
							/>
						</div>
					</div>
				{:else if TTS_ENGINE === 'azure'}
					<div>
						<div style="--mt:0.25rem; --d:flex; --g:0.5rem; --mb:0.25rem">
							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={TTS_API_KEY} required />
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('Azure Region')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={TTS_AZURE_SPEECH_REGION}
										placeholder={$i18n.t('e.g., westus (leave blank for eastus)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('Endpoint URL')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={TTS_AZURE_SPEECH_BASE_URL}
										placeholder={$i18n.t('(leave blank for to use commercial endpoint)')}
									/>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<div style="--mb:0.5rem">
					{#if TTS_ENGINE === ''}
						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('TTS Voice')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<select
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={TTS_VOICE}
									>
										<option value="" selected={TTS_VOICE !== ''}>{$i18n.t('Default')}</option>
										{#each voices as voice}
											<option
												value={voice.voiceURI}
												style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)"
												selected={TTS_VOICE === voice.voiceURI}>{voice.name}</option
											>
										{/each}
									</select>
								</div>
							</div>
						</div>
					{:else if TTS_ENGINE === 'transformers'}
						<div>
							<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('TTS Model')}</div>
							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										list="model-list"
										style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
										bind:value={TTS_MODEL}
										placeholder="CMU ARCTIC speaker embedding name"
									/>

									<datalist id="model-list">
										<option value="tts-1" />
									</datalist>
								</div>
							</div>
							<div style="--mt:0.5rem; --mb:0.25rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
								{$i18n.t(`Sage.is AI uses SpeechT5 and CMU Arctic speaker embeddings.`)}

								To learn more about SpeechT5,

								<a
									style="--hvr-td:underline; --dark-c:var(--color-gray-200); --c:var(--color-gray-800)"
									href="https://github.com/microsoft/SpeechT5"
									target="_blank"
								>
									{$i18n.t(`click here`, {
										name: 'SpeechT5'
									})}.
								</a>
								To see the available CMU Arctic speaker embeddings,
								<a
									style="--hvr-td:underline; --dark-c:var(--color-gray-200); --c:var(--color-gray-800)"
									href="https://huggingface.co/datasets/Matthijs/cmu-arctic-xvectors"
									target="_blank"
								>
									{$i18n.t(`click here`)}.
								</a>
							</div>
						</div>
					{:else if TTS_ENGINE === 'openai'}
						<div style="--d:flex; --g:0.5rem">
							<div style="--w:100%">
								<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('TTS Voice')}</div>
								<div style="--d:flex; --w:100%">
									<div style="--fx:1 1 0%">
										<input
											list="voice-list"
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
											bind:value={TTS_VOICE}
											placeholder="Select a voice"
										/>

										<datalist id="voice-list">
											{#each voices as voice}
												<option value={voice.id}>{voice.name}</option>
											{/each}
										</datalist>
									</div>
								</div>
							</div>
							<div style="--w:100%">
								<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('TTS Model')}</div>
								<div style="--d:flex; --w:100%">
									<div style="--fx:1 1 0%">
										<input
											list="tts-model-list"
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
											bind:value={TTS_MODEL}
											placeholder="Select a model"
										/>

										<datalist id="tts-model-list">
											{#each models as model}
												<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)" />
											{/each}
										</datalist>
									</div>
								</div>
							</div>
						</div>
					{:else if TTS_ENGINE === 'elevenlabs'}
						<div style="--d:flex; --g:0.5rem">
							<div style="--w:100%">
								<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('TTS Voice')}</div>
								<div style="--d:flex; --w:100%">
									<div style="--fx:1 1 0%">
										<input
											list="voice-list"
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
											bind:value={TTS_VOICE}
											placeholder="Select a voice"
										/>

										<datalist id="voice-list">
											{#each voices as voice}
												<option value={voice.id}>{voice.name}</option>
											{/each}
										</datalist>
									</div>
								</div>
							</div>
							<div style="--w:100%">
								<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('TTS Model')}</div>
								<div style="--d:flex; --w:100%">
									<div style="--fx:1 1 0%">
										<input
											list="tts-model-list"
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
											bind:value={TTS_MODEL}
											placeholder="Select a model"
										/>

										<datalist id="tts-model-list">
											{#each models as model}
												<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)" />
											{/each}
										</datalist>
									</div>
								</div>
							</div>
						</div>
					{:else if TTS_ENGINE === 'azure'}
						<div style="--d:flex; --g:0.5rem">
							<div style="--w:100%">
								<div style="--mb:0.375rem; --size:0.6rem; --weight:500">{$i18n.t('TTS Voice')}</div>
								<div style="--d:flex; --w:100%">
									<div style="--fx:1 1 0%">
										<input
											list="voice-list"
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
											bind:value={TTS_VOICE}
											placeholder="Select a voice"
										/>

										<datalist id="voice-list">
											{#each voices as voice}
												<option value={voice.id}>{voice.name}</option>
											{/each}
										</datalist>
									</div>
								</div>
							</div>
							<div style="--w:100%">
								<div style="--mb:0.375rem; --size:0.6rem; --weight:500">
									{$i18n.t('Output format')}
									<a
										href="https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech?tabs=streaming#audio-outputs"
										target="_blank"
									>
										<small>{$i18n.t('Available list')}</small>
									</a>
								</div>
								<div style="--d:flex; --w:100%">
									<div style="--fx:1 1 0%">
										<input
											list="tts-model-list"
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
											bind:value={TTS_AZURE_SPEECH_OUTPUT_FORMAT}
											placeholder="Select a output format"
										/>
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>

				<div style="--pt:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Response splitting')}</div>
					<div style="--d:flex; --ai:center; --pos:relative">
						<select
							style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --cur:pointer; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.6rem; --bgc:transparent; --oe:none; --ta:right"
							aria-label="Select how to split message text for TTS requests"
							bind:value={TTS_SPLIT_ON}
						>
							{#each Object.values(TTS_RESPONSE_SPLIT) as split}
								<option value={split}
									>{$i18n.t(split.charAt(0).toUpperCase() + split.slice(1))}</option
								>
							{/each}
						</select>
					</div>
				</div>
				<div style="--mt:0.5rem; --mb:0.25rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
					{$i18n.t(
						"Control how message text is split for TTS requests. 'Punctuation' splits into sentences, 'paragraphs' splits into paragraphs, and 'none' keeps the message as a single string."
					)}
				</div>
			</div>
		</div>
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
