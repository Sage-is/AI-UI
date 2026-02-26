<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';

	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import MicSolid from '$lib/components/icons/MicSolid.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VoiceRecording from '$lib/components/chat/MessageInput/VoiceRecording.svelte';
	export let show = false;

	let name = 'Untitled';
	let content = '';

	let voiceInput = false;
	
	// TODO: Future enhancement - Add logic to auto-stop voice input and ensure conversion 
	// is complete before allowing save. This would require:
	// 1. Hooking into VoiceRecording component's stop/convert lifecycle
	// 2. Adding promise-based conversion completion detection  
	// 3. Auto-triggering voice stop when save is clicked during recording
	// Current implementation: Save button is disabled during voice input for safety
</script>

<Modal size="full" containerClassName="" className="h-full bg-white dark:bg-gray-900" bind:show>
	<div style="--pos:absolute; --top:0; --right:0; --p:1.25rem">
		<button
			style="--as:center; --dark-c:#fff"
			type="button"
			on:click={() => {
				show = false;
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>
	<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --h:100%; --g-md:1rem; --dark-c:var(--color-gray-200)">
		<form
			style="--d:flex; --fd:column; --w:100%; --h:100%"
			on:submit|preventDefault={() => {
				if (name.trim() === '' || content.trim() === '') {
					toast.error($i18n.t('Please fill in all fields.'));
					name = name.trim();
					content = content.trim();
					return;
				}

				dispatch('submit', {
					name,
					content
				});
				show = false;
				name = '';
				content = '';
			}}
		>
			<div style="--fx:1 1 0%; --w:100%; --h:100%; --d:flex; --jc:center; --of:auto; --px:1.25rem; --py:1rem">
				<div style="--maxw:48rem; --py:0.5rem; --py-md:2.5rem; --w:100%; --d:flex; --fd:column; --g:0.5rem">
					<div style="--fs:0; --w:100%; --d:flex; --jc:space-between; --ai:center">
						<div style="--w:100%">
							<input
								style="--w:100%; --size:1.875rem; --weight:600; --bgc:transparent; --oe:none"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Title')}
								required
							/>
						</div>
					</div>

					<div style="--fx:1 1 0%; --w:100%; --h:100%">
						<RichTextInput
							bind:value={content}
							placeholder={$i18n.t('Write something...')}
							preserveBreaks={true}
						/>
					</div>
				</div>
			</div>

			<div
				style="--d:flex; --fd:row; --ai:center; --jc:flex-end; --size:0.875rem; --weight:500; --fs:0; --mt:0.25rem; --p:1rem; --g:0.375rem"
			>
				<div class="">
					{#if voiceInput}
						<div style="--maxw:100%; --w:100%">
							<VoiceRecording
								bind:recording={voiceInput}
								className="p-1"
								onCancel={() => {
									voiceInput = false;
								}}
								onConfirm={(data) => {
									const { text, filename } = data;
									content = `${content}${text} `;

									voiceInput = false;
								}}
							/>
						</div>
					{:else}
						<Tooltip content={$i18n.t('Voice Input')}>
							<button
								style="--p:0.5rem; --bgc:var(--color-gray-50); --c:var(--color-gray-700); --dark-bgc:var(--color-gray-700); --dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
								type="button"
								on:click={async () => {
									try {
										let stream = await navigator.mediaDevices
											.getUserMedia({ audio: true })
											.catch(function (err) {
												toast.error(
													$i18n.t(`Permission denied when accessing microphone: {{error}}`, {
														error: err
													})
												);
												return null;
											});

										if (stream) {
											voiceInput = true;
											const tracks = stream.getTracks();
											tracks.forEach((track) => track.stop());
										}
										stream = null;
									} catch {
										toast.error($i18n.t('Permission denied when accessing microphone'));
									}
								}}
							>
								<MicSolid className="size-5" />
							</button>
						</Tooltip>
					{/if}
				</div>

				<div style="--fs:0">
					<Tooltip content={$i18n.t('Save')}>
						<button
							style="--px:0.875rem; --py:0.5rem; --bgc:#000; --c:#fff; --dark-bgc:#fff; --dark-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
	class="disabled:opacity-50 disabled:cursor-not-allowed"
							type="submit"
							disabled={voiceInput}
						>
							{$i18n.t('Save')}
						</button>
					</Tooltip>
				</div>
			</div>
		</form>
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
		-moz-appearance: textfield; /* Firefox */
	}
</style>
