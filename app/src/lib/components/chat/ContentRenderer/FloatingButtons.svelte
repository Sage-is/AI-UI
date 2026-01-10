<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';

	export let id = '';
	export let model = null;
	export let messages = [];
	export let submitMessage = () => {};
	export let closeFloatingButtons = () => {};

	let floatingInput = false;
	let selectedText = '';
	let floatingInputValue = '';

	const askHandler = async () => {
		if (!model) {
			toast.error('Model not selected');
			return;
		}
		
		const prompt = [
			// Blockquote each line of the selected text
			...selectedText.split('\n').map((line) => `> ${line}`),
			'',
			// Then your question
			floatingInputValue
		].join('\n');
		
		// Directly submit to main conversation using submitMessage
		await submitMessage(id, prompt);
		
		// Reset state and close floating buttons
		floatingInputValue = '';
		closeHandler();
		closeFloatingButtons();
	};

	const explainHandler = async () => {
		if (!model) {
			toast.error('Model not selected');
			return;
		}
		
		const quotedText = selectedText
			.split('\n')
			.map((line) => `> ${line}`)
			.join('\n');
		const prompt = `${quotedText}\n\nExplain`;

		// Directly submit to main conversation using submitMessage
		await submitMessage(id, prompt);
		
		// Reset state and close floating buttons
		closeHandler();
		closeFloatingButtons();
	};

	export const closeHandler = () => {
		floatingInput = false;
		floatingInputValue = '';
	};
</script>

<div
	id={`floating-buttons-${id}`}
	class="absolute rounded-lg mt-1 text-xs z-9999"
	style="display: none"
>
	{#if !floatingInput}
		<div
			class="flex flex-row gap-0.5 shrink-0 p-1 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-lg shadow-xl"
		>
			<button
				class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm flex items-center gap-1 min-w-fit"
				on:click={async () => {
					selectedText = window.getSelection().toString();
					floatingInput = true;

					await tick();
					setTimeout(() => {
						const input = document.getElementById('floating-message-input');
						if (input) {
							input.focus();
						}
					}, 0);
				}}
			>
				<ChatBubble className="size-3 shrink-0" />
				<div class="shrink-0">{$i18n.t('Ask')}</div>
			</button>
			<button
				class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm flex items-center gap-1 min-w-fit"
				on:click={() => {
					selectedText = window.getSelection().toString();
					explainHandler();
				}}
			>
				<LightBulb className="size-3 shrink-0" />
				<div class="shrink-0">{$i18n.t('Explain')}</div>
			</button>
		</div>
	{:else}
		<div
			class="py-1 flex dark:text-gray-100 bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-850 w-72 rounded-full shadow-xl"
		>
			<input
				type="text"
				id="floating-message-input"
				class="ml-5 bg-transparent outline-hidden w-full flex-1 text-sm"
				placeholder={$i18n.t('Ask a question')}
				bind:value={floatingInputValue}
				on:keydown={(e) => {
					if (e.key === 'Enter') {
						askHandler();
					}
				}}
			/>

			<div class="ml-1 mr-2">
				<button
					class="{floatingInputValue !== ''
						? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
						: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
					on:click={() => {
						askHandler();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			</div>
		</div>
	{/if}
</div>
