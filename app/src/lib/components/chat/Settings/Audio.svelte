<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { KokoroTTS } from 'kokoro-js';

	import { user, settings, config } from '$lib/stores';
	import { getVoices as _getVoices } from '$lib/apis/audio';

	import Switch from '$lib/components/common/Switch.svelte';
	import { round } from '@huggingface/transformers';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Audio
	let conversationMode = false;
	let speechAutoSend = false;
	let responseAutoPlayback = false;
	let nonLocalVoices = false;

	let STTEngine = '';
	let STTLanguage = '';

	let TTSEngine = '';
	let TTSEngineConfig = {};

	let TTSModel = null;
	let TTSModelProgress = null;
	let TTSModelLoading = false;

	let voices = [];
	let voice = '';

	// Audio speed control
	let playbackRate = 1;

	const getVoices = async () => {
		if (TTSEngine === 'browser-kokoro') {
			if (!TTSModel) {
				await loadKokoro();
			}

			voices = Object.entries(TTSModel.voices).map(([key, value]) => {
				return {
					id: key,
					name: value.name,
					localService: false
				};
			});
		} else {
			if ($config.audio.tts.engine === '') {
				const getVoicesLoop = setInterval(async () => {
					voices = await speechSynthesis.getVoices();

					// do your loop
					if (voices.length > 0) {
						clearInterval(getVoicesLoop);
					}
				}, 100);
			} else {
				const res = await _getVoices(localStorage.token).catch((e) => {
					toast.error(`${e}`);
				});

				if (res) {
					console.log(res);
					voices = res.voices;
				}
			}
		}
	};

	const toggleResponseAutoPlayback = async () => {
		responseAutoPlayback = !responseAutoPlayback;
		saveSettings({ responseAutoPlayback: responseAutoPlayback });
	};

	const toggleSpeechAutoSend = async () => {
		speechAutoSend = !speechAutoSend;
		saveSettings({ speechAutoSend: speechAutoSend });
	};

	onMount(async () => {
		playbackRate = $settings.audio?.tts?.playbackRate ?? 1;
		conversationMode = $settings.conversationMode ?? false;
		speechAutoSend = $settings.speechAutoSend ?? false;
		responseAutoPlayback = $settings.responseAutoPlayback ?? false;

		STTEngine = $settings?.audio?.stt?.engine ?? '';
		STTLanguage = $settings?.audio?.stt?.language ?? '';

		TTSEngine = $settings?.audio?.tts?.engine ?? '';
		TTSEngineConfig = $settings?.audio?.tts?.engineConfig ?? {};

		if ($settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice) {
			voice = $settings?.audio?.tts?.voice ?? $config.audio.tts.voice ?? '';
		} else {
			voice = $config.audio.tts.voice ?? '';
		}

		nonLocalVoices = $settings.audio?.tts?.nonLocalVoices ?? false;

		await getVoices();
	});

	$: if (TTSEngine && TTSEngineConfig) {
		onTTSEngineChange();
	}

	const onTTSEngineChange = async () => {
		if (TTSEngine === 'browser-kokoro') {
			await loadKokoro();
		}
	};

	const loadKokoro = async () => {
		if (TTSEngine === 'browser-kokoro') {
			voices = [];

			if (TTSEngineConfig?.dtype) {
				TTSModel = null;
				TTSModelProgress = null;
				TTSModelLoading = true;

				const model_id = 'onnx-community/Kokoro-82M-v1.0-ONNX';

				TTSModel = await KokoroTTS.from_pretrained(model_id, {
					dtype: TTSEngineConfig.dtype, // Options: "fp32", "fp16", "q8", "q4", "q4f16"
					device: !!navigator?.gpu ? 'webgpu' : 'wasm', // Detect WebGPU
					progress_callback: (e) => {
						TTSModelProgress = e;
						console.log(e);
					}
				});

				await getVoices();

				// const rawAudio = await tts.generate(inputText, {
				// 	// Use `tts.list_voices()` to list all available voices
				// 	voice: voice
				// });

				// const blobUrl = URL.createObjectURL(await rawAudio.toBlob());
				// const audio = new Audio(blobUrl);

				// audio.play();
			}
		}
	};
</script>

<form
	id="tab-audio"
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.875rem"
	on:submit|preventDefault={async () => {
		saveSettings({
			audio: {
				stt: {
					engine: STTEngine !== '' ? STTEngine : undefined,
					language: STTLanguage !== '' ? STTLanguage : undefined
				},
				tts: {
					engine: TTSEngine !== '' ? TTSEngine : undefined,
					engineConfig: TTSEngineConfig,
					playbackRate: playbackRate,
					voice: voice !== '' ? voice : undefined,
					defaultVoice: $config?.audio?.tts?.voice ?? '',
					nonLocalVoices: $config.audio.tts.engine === '' ? nonLocalVoices : undefined
				}
			}
		});
		dispatch('save');
	}}
>
	<div style="--g:0.6rem; --ofy:scroll; --maxh:28rem; --maxh-lg:100%">
		<div>
			<div style="--mb:0.25rem; --size:0.875rem; --weight:500">{$i18n.t('STT Settings')}</div>

			{#if $config.audio.stt.engine !== 'web'}
				<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Speech-to-Text Engine')}</div>
					<div style="--d:flex; --ai:center; --pos:relative">
						<select
							style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.6rem; --bgc:transparent; --oe:none; --ta:right"
							bind:value={STTEngine}
							placeholder="Select an engine"
						>
							<option value="">{$i18n.t('Default')}</option>
							<option value="web">{$i18n.t('Web API')}</option>
						</select>
					</div>
				</div>

				<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Language')}</div>

					<div style="--d:flex; --ai:center; --pos:relative; --size:0.6rem; --px:0.6rem">
						<Tooltip
							content={$i18n.t(
								'The language of the input audio. Supplying the input language in ISO-639-1 (e.g. en) format will improve accuracy and latency. Leave blank to automatically detect the language.'
							)}
							placement="top"
						>
							<input
								type="text"
								bind:value={STTLanguage}
								placeholder={$i18n.t('e.g. en')}
								style="--size:0.875rem; --ta:right; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
							/>
						</Tooltip>
					</div>
				</div>
			{/if}

			<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.6rem; --weight:500">
					{$i18n.t('Instant Auto-Send After Voice Transcription')}
				</div>

				<button
					style="--p:0.25rem; --px:0.6rem; --size:0.6rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						toggleSpeechAutoSend();
					}}
					type="button"
				>
					{#if speechAutoSend === true}
						<span style="--ml:0.5rem; --as:center">{$i18n.t('On')}</span>
					{:else}
						<span style="--ml:0.5rem; --as:center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>
		</div>

		<div>
			<div style="--mb:0.25rem; --size:0.875rem; --weight:500">{$i18n.t('TTS Settings')}</div>

			<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Text-to-Speech Engine')}</div>
				<div style="--d:flex; --ai:center; --pos:relative">
					<select
						style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.6rem; --bgc:transparent; --oe:none; --ta:right"
						bind:value={TTSEngine}
						placeholder="Select an engine"
					>
						<option value="">{$i18n.t('Default')}</option>
						<option value="browser-kokoro">{$i18n.t('Kokoro.js (Browser)')}</option>
					</select>
				</div>
			</div>

			{#if TTSEngine === 'browser-kokoro'}
				<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
					<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Kokoro.js Dtype')}</div>
					<div style="--d:flex; --ai:center; --pos:relative">
						<select
							style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.6rem; --bgc:transparent; --oe:none; --ta:right"
							bind:value={TTSEngineConfig.dtype}
							placeholder="Select dtype"
						>
							<option value="" disabled selected>Select dtype</option>
							<option value="fp32">fp32</option>
							<option value="fp16">fp16</option>
							<option value="q8">q8</option>
							<option value="q4">q4</option>
						</select>
					</div>
				</div>
			{/if}

			<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Auto-playback response')}</div>

				<button
					style="--p:0.25rem; --px:0.6rem; --size:0.6rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={() => {
						toggleResponseAutoPlayback();
					}}
					type="button"
				>
					{#if responseAutoPlayback === true}
						<span style="--ml:0.5rem; --as:center">{$i18n.t('On')}</span>
					{:else}
						<span style="--ml:0.5rem; --as:center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>

			<div style="--py:0.125rem; --d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Speech Playback Speed')}</div>

				<div style="--d:flex; --ai:center; --pos:relative; --size:0.6rem; --px:0.6rem">
					<input
						type="number"
						min="0"
						step="0.01"
						bind:value={playbackRate}
						style="--size:0.875rem; --ta:right; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
					/>
					x
				</div>
			</div>
		</div>

		<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)" />

		{#if TTSEngine === 'browser-kokoro'}
			{#if TTSModel}
				<div>
					<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Voice')}</div>
					<div style="--d:flex; --w:100%">
						<div style="--fx:1 1 0%">
							<input
								list="voice-list"
								style="--w:100%; --size:0.875rem; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
								bind:value={voice}
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
			{:else}
				<div>
					<div style="--mb:0.625rem; --size:0.875rem; --weight:500; --d:flex; --g:0.5rem; --ai:center">
						<Spinner className="size-4" />

						<div style="--size:0.875rem; --weight:500"
	class="shimmer">
							{$i18n.t('Loading Kokoro.js...')}
							{TTSModelProgress && TTSModelProgress.status === 'progress'
								? `(${Math.round(TTSModelProgress.progress * 10) / 10}%)`
								: ''}
						</div>
					</div>

					<div style="--size:0.6rem; --c:var(--color-gray-500)">
						{$i18n.t('Please do not close the settings page while loading the model.')}
					</div>
				</div>
			{/if}
		{:else if $config.audio.tts.engine === ''}
			<div>
				<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Voice')}</div>
				<div style="--d:flex; --w:100%">
					<div style="--fx:1 1 0%">
						<select
							style="--w:100%; --size:0.875rem; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
							bind:value={voice}
						>
							<option value="" selected={voice !== ''}>{$i18n.t('Default')}</option>
							{#each voices.filter((v) => nonLocalVoices || v.localService === true) as _voice}
								<option
									value={_voice.name}
									style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)"
									selected={voice === _voice.name}>{_voice.name}</option
								>
							{/each}
						</select>
					</div>
				</div>
				<div style="--d:flex; --ai:center; --jc:space-between; --my:0.375rem">
					<div style="--size:0.6rem">
						{$i18n.t('Allow non-local voices')}
					</div>

					<div style="--mt:0.25rem">
						<Switch bind:state={nonLocalVoices} />
					</div>
				</div>
			</div>
		{:else if $config.audio.tts.engine !== ''}
			<div>
				<div style="--mb:0.625rem; --size:0.875rem; --weight:500">{$i18n.t('Set Voice')}</div>
				<div style="--d:flex; --w:100%">
					<div style="--fx:1 1 0%">
						<input
							list="voice-list"
							style="--w:100%; --size:0.875rem; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
							bind:value={voice}
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
