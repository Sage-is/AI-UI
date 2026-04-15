<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { tick, getContext, onMount, onDestroy } from 'svelte';
	import { config, settings } from '$lib/stores';
	import { blobToFile, calculateSHA256, extractCurlyBraceWords } from '$lib/utils';
	import Icon from '$lib/components/Icon.svelte';

	import { transcribeAudio } from '$lib/apis/audio';

	import dayjs from 'dayjs';
	import LocalizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(LocalizedFormat);

	const i18n = getContext('i18n');

	export let recording = false;
	export let transcribe = true;
	export let displayMedia = false;

	export let echoCancellation = true;
	export let noiseSuppression = true;
	export let autoGainControl = true;

	export let className = ' p-2.5 w-full max-w-full';

	export let onCancel = () => {};
	export let onConfirm = (data) => {};

	let loading = false;
	let confirmed = false;

	let durationSeconds = 0;
	let durationCounter = null;

	let transcription = '';

	const startDurationCounter = () => {
		durationCounter = setInterval(() => {
			durationSeconds++;
		}, 1000);
	};

	const stopDurationCounter = () => {
		clearInterval(durationCounter);
		durationSeconds = 0;
	};

	$: if (recording) {
		startRecording();
	} else {
		stopRecording();
	}

	const formatSeconds = (seconds) => {
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		const formattedSeconds = remainingSeconds < 10 ? `0${remainingSeconds}` : remainingSeconds;
		return `${minutes}:${formattedSeconds}`;
	};

	let stream;
	let speechRecognition;

	let mediaRecorder;
	let audioChunks = [];

	const MIN_DECIBELS = -45;
	let VISUALIZER_BUFFER_LENGTH = 300;

	let visualizerData = Array(VISUALIZER_BUFFER_LENGTH).fill(0);

	// Function to calculate the RMS level from time domain data
	const calculateRMS = (data: Uint8Array) => {
		let sumSquares = 0;
		for (let i = 0; i < data.length; i++) {
			const normalizedValue = (data[i] - 128) / 128; // Normalize the data
			sumSquares += normalizedValue * normalizedValue;
		}
		return Math.sqrt(sumSquares / data.length);
	};

	const normalizeRMS = (rms) => {
		rms = rms * 10;
		const exp = 1.5; // Adjust exponent value; values greater than 1 expand larger numbers more and compress smaller numbers more
		const scaledRMS = Math.pow(rms, exp);

		// Scale between 0.01 (1%) and 1.0 (100%)
		return Math.min(1.0, Math.max(0.01, scaledRMS));
	};

	const analyseAudio = (stream) => {
		const audioContext = new AudioContext();
		const audioStreamSource = audioContext.createMediaStreamSource(stream);

		const analyser = audioContext.createAnalyser();
		analyser.minDecibels = MIN_DECIBELS;
		audioStreamSource.connect(analyser);

		const bufferLength = analyser.frequencyBinCount;

		const domainData = new Uint8Array(bufferLength);
		const timeDomainData = new Uint8Array(analyser.fftSize);

		let lastSoundTime = Date.now();

		const detectSound = () => {
			const processFrame = () => {
				if (!recording || loading) return;

				if (recording && !loading) {
					analyser.getByteTimeDomainData(timeDomainData);
					analyser.getByteFrequencyData(domainData);

					// Calculate RMS level from time domain data
					const rmsLevel = calculateRMS(timeDomainData);
					// Push the calculated decibel level to visualizerData
					visualizerData.push(normalizeRMS(rmsLevel));

					// Ensure visualizerData array stays within the buffer length
					if (visualizerData.length >= VISUALIZER_BUFFER_LENGTH) {
						visualizerData.shift();
					}

					visualizerData = visualizerData;

					// if (domainData.some((value) => value > 0)) {
					// 	lastSoundTime = Date.now();
					// }

					// if (recording && Date.now() - lastSoundTime > 3000) {
					// 	if ($settings?.speechAutoSend ?? false) {
					// 		confirmRecording();
					// 	}
					// }
				}

				window.requestAnimationFrame(processFrame);
			};

			window.requestAnimationFrame(processFrame);
		};

		detectSound();
	};

	const onStopHandler = async (audioBlob, ext: string = 'wav') => {
		// Create a blob from the audio chunks

		await tick();
		const file = blobToFile(audioBlob, `Recording-${dayjs().format('L LT')}.${ext}`);

		if (transcribe) {
			if ($config.audio.stt.engine === 'web' || ($settings?.audio?.stt?.engine ?? '') === 'web') {
				// with web stt, we don't need to send the file to the server
				return;
			}

			const res = await transcribeAudio(
				localStorage.token,
				file,
				$settings?.audio?.stt?.language
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				console.log(res);
				onConfirm(res);
			}
		} else {
			onConfirm({
				file: file,
				blob: audioBlob
			});
		}
	};

	const startRecording = async () => {
		loading = true;

		try {
			if (displayMedia) {
				const mediaStream = await navigator.mediaDevices.getDisplayMedia({
					audio: true
				});

				stream = new MediaStream();
				for (const track of mediaStream.getAudioTracks()) {
					stream.addTrack(track);
				}

				for (const track of mediaStream.getVideoTracks()) {
					track.stop();
				}
			} else {
				stream = await navigator.mediaDevices.getUserMedia({
					audio: {
						echoCancellation: echoCancellation,
						noiseSuppression: noiseSuppression,
						autoGainControl: autoGainControl
					}
				});
			}
		} catch (err) {
			console.error('Error accessing media devices.', err);
			toast.error($i18n.t('Error accessing media devices.'));
			loading = false;
			recording = false;
			return;
		}

		const mineTypes = ['audio/webm; codecs=opus', 'audio/mp4'];

		mediaRecorder = new MediaRecorder(stream, {
			mimeType: mineTypes.find((type) => MediaRecorder.isTypeSupported(type))
		});

		mediaRecorder.onstart = () => {
			console.log('Recording started');
			loading = false;
			startDurationCounter();

			audioChunks = [];
			analyseAudio(stream);
		};
		mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);
		mediaRecorder.onstop = async () => {
			console.log('Recording stopped');

			if (confirmed) {
				// Use the actual type provided by MediaRecorder
				let type = audioChunks[0]?.type || mediaRecorder.mimeType || 'audio/webm';

				// split `/` and `;` to get the extension
				let ext = type.split('/')[1].split(';')[0] || 'webm';

				// If not audio, default to audio/webm
				if (!type.startsWith('audio/')) {
					ext = 'webm';
				}

				const audioBlob = new Blob(audioChunks, { type: type });
				await onStopHandler(audioBlob, ext);

				confirmed = false;
				loading = false;
			}

			audioChunks = [];
			recording = false;
		};

		try {
			mediaRecorder.start();
		} catch (error) {
			console.error('Error starting recording:', error);
			toast.error($i18n.t('Error starting recording.'));
			loading = false;
			recording = false;
			return;
		}

		if (transcribe) {
			if ($config.audio.stt.engine === 'web' || ($settings?.audio?.stt?.engine ?? '') === 'web') {
				if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
					// Create a SpeechRecognition object
					speechRecognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();

					// Set continuous to true for continuous recognition
					speechRecognition.continuous = true;

					// Set the timeout for turning off the recognition after inactivity (in milliseconds)
					const inactivityTimeout = 2000; // 3 seconds

					let timeoutId;
					// Start recognition
					speechRecognition.start();

					// Event triggered when speech is recognized
					speechRecognition.onresult = async (event) => {
						// Clear the inactivity timeout
						clearTimeout(timeoutId);

						// Handle recognized speech
						console.log(event);
						const transcript = event.results[Object.keys(event.results).length - 1][0].transcript;

						transcription = `${transcription}${transcript}`;

						await tick();
						document.getElementById('chat-input')?.focus();

						// Restart the inactivity timeout
						timeoutId = setTimeout(() => {
							console.log('Speech recognition turned off due to inactivity.');
							speechRecognition.stop();
						}, inactivityTimeout);
					};

					// Event triggered when recognition is ended
					speechRecognition.onend = function () {
						// Restart recognition after it ends
						console.log('recognition ended');

						confirmRecording();
						onConfirm({
							text: transcription
						});
						confirmed = false;
						loading = false;
					};

					// Event triggered when an error occurs
					speechRecognition.onerror = function (event) {
						console.log(event);
						toast.error($i18n.t(`Speech recognition error: {{error}}`, { error: event.error }));
						onCancel();

						stopRecording();
					};
				}
			}
		}
	};

	const stopRecording = async () => {
		if (recording && mediaRecorder) {
			await mediaRecorder.stop();
		}

		if (speechRecognition) {
			speechRecognition.stop();
		}

		stopDurationCounter();
		audioChunks = [];

		if (stream) {
			const tracks = stream.getTracks();
			tracks.forEach((track) => track.stop());
		}

		stream = null;
	};

	const confirmRecording = async () => {
		loading = true;
		confirmed = true;

		if (recording && mediaRecorder) {
			await mediaRecorder.stop();
		}
		clearInterval(durationCounter);

		if (stream) {
			const tracks = stream.getTracks();
			tracks.forEach((track) => track.stop());
		}

		stream = null;
	};

	let resizeObserver;
	let containerWidth;

	let maxVisibleItems = 300;
	$: maxVisibleItems = Math.floor(containerWidth / 5); // 2px width + 0.5px gap

	onMount(() => {
		// listen to width changes
		resizeObserver = new ResizeObserver(() => {
			VISUALIZER_BUFFER_LENGTH = Math.floor(window.innerWidth / 4);
			if (visualizerData.length > VISUALIZER_BUFFER_LENGTH) {
				visualizerData = visualizerData.slice(visualizerData.length - VISUALIZER_BUFFER_LENGTH);
			} else {
				visualizerData = Array(VISUALIZER_BUFFER_LENGTH - visualizerData.length)
					.fill(0)
					.concat(visualizerData);
			}
		});

		resizeObserver.observe(document.body);
	});

	onDestroy(() => {
		// remove resize observer
		resizeObserver.disconnect();
	});
</script>

<div
	bind:clientWidth={containerWidth}
	style="--radius:9999px; --d:flex; --jc:space-between"
	class="{loading
		? ' bg-gray-100/50 dark:bg-gray-850/50'
		: 'bg-indigo-300/10 dark:bg-indigo-500/10 '} {className}"
>
	<div style="--d:flex; --ai:center; --mr:0.2rem">
		<button
			type="button"
			style="--p:0.4rem; --radius:9999px"
	class="{loading
				? ' bg-gray-200 dark:bg-gray-700/50'
				: 'bg-indigo-400/20 text-indigo-600 dark:text-indigo-300 '}"
			on:click={async () => {
				stopRecording();
				onCancel();
			}}
		>
			<Icon name="x-mark" strokeWidth="2" className={'size-4'} />
		</button>
	</div>

	<div
		style="--d:flex; --fx:1 1 0%; --as:center; --ai:center; --jc:space-between; --ml:0.5rem; --mx:0.2rem; --of:hidden; --h:1.5rem"
		dir="rtl"
	>
		<div
			style="--d:flex; --ai:center; --g:0.125rem; --h:1.5rem; --w:100%; --maxw:100%; --of:hidden; --ofx:hidden; --fw:wrap"
		>
			{#each visualizerData.slice().reverse() as rms}
				<div style="--d:flex; --ai:center; --h:100%">
					<div
						class="{loading
							? ' bg-gray-500 dark:bg-gray-400   '
							: 'bg-indigo-500 dark:bg-indigo-400  '}"
						style="--w:2px; --fs:0; --d:inline-block; --h:100%; height: {Math.min(100, Math.max(14, rms * 100))}%;"
					/>
				</div>
			{/each}
		</div>
	</div>

	<div style="--d:flex">
		<div style="--mx:0.4rem; --pr:0.2rem; --d:flex; --jc:center; --ai:center">
			<div
				style="--size:0.8rem; --weight:500; --fx:1 1 0%; --mx:auto; --ta:center"
	class="{loading ? ' text-gray-500  dark:text-gray-400  ' : ' text-indigo-400 '}"
			>
				{formatSeconds(durationSeconds)}
			</div>
		</div>

		<div style="--d:flex; --ai:center">
			{#if loading}
				<div style="--c:var(--color-gray-500); --radius:9999px; --cur:not-allowed">
					<svg
						width="24"
						height="24"
						viewBox="0 0 24 24"
						xmlns="http://www.w3.org/2000/svg"
						fill="currentColor"
						><style>
							.spinner_OSmW {
								transform-origin: center;
								animation: spinner_T6mA 0.75s step-end infinite;
							}
							@keyframes spinner_T6mA {
								8.3% {
									transform: rotate(30deg);
								}
								16.6% {
									transform: rotate(60deg);
								}
								25% {
									transform: rotate(90deg);
								}
								33.3% {
									transform: rotate(120deg);
								}
								41.6% {
									transform: rotate(150deg);
								}
								50% {
									transform: rotate(180deg);
								}
								58.3% {
									transform: rotate(210deg);
								}
								66.6% {
									transform: rotate(240deg);
								}
								75% {
									transform: rotate(270deg);
								}
								83.3% {
									transform: rotate(300deg);
								}
								91.6% {
									transform: rotate(330deg);
								}
								100% {
									transform: rotate(360deg);
								}
							}
						</style><g class="spinner_OSmW"
							><rect x="11" y="1" width="2" height="5" opacity=".14" /><rect
								x="11"
								y="1"
								width="2"
								height="5"
								transform="rotate(30 12 12)"
								opacity=".29"
							/><rect
								x="11"
								y="1"
								width="2"
								height="5"
								transform="rotate(60 12 12)"
								opacity=".43"
							/><rect
								x="11"
								y="1"
								width="2"
								height="5"
								transform="rotate(90 12 12)"
								opacity=".57"
							/><rect
								x="11"
								y="1"
								width="2"
								height="5"
								transform="rotate(120 12 12)"
								opacity=".71"
							/><rect
								x="11"
								y="1"
								width="2"
								height="5"
								transform="rotate(150 12 12)"
								opacity=".86"
							/><rect x="11" y="1" width="2" height="5" transform="rotate(180 12 12)" /></g
						></svg
					>
				</div>
			{:else}
				<button
					type="button"
					style="--p:0.4rem; --bgc:#6366f1; --c:#fff; --dark-bgc:#6366f1; --dark-c:#172554; --radius:9999px"
					on:click={async () => {
						await confirmRecording();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2.5"
						stroke="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
					</svg>
				</button>
			{/if}
		</div>
	</div>
</div>

<style>
	.visualizer {
		display: flex;
		height: 100%;
	}

	.visualizer-bar {
		width: 2px;
		background-color: #4a5aba; /* or whatever color you need */
	}
</style>
