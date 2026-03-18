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
	style="--pos:absolute; --radius:0.5rem; --mt:0.2rem; --size:0.6rem; --z:9999; display: none"
>
	{#if !floatingInput}
		<div
			style="--d:flex; --fd:row; --g:0.125rem; --fs:0; --p:0.2rem; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-100); --radius:0.5rem; --shadow:5"
	class="text-medium"
		>
			<button
				style="--px:0.2rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.125rem; --d:flex; --ai:center; --g:0.2rem; --minw:fit-content"
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
				<div style="--fs:0">{$i18n.t('Ask')}</div>
			</button>
			<button
				style="--px:0.2rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.125rem; --d:flex; --ai:center; --g:0.2rem; --minw:fit-content"
				on:click={() => {
					selectedText = window.getSelection().toString();
					explainHandler();
				}}
			>
				<LightBulb className="size-3 shrink-0" />
				<div style="--fs:0">{$i18n.t('Explain')}</div>
			</button>
		</div>
	{:else}
		<div
			style="--py:0.2rem; --d:flex; --dark-c:var(--color-gray-100); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800);  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --w:18rem; --radius:9999px; --shadow:5"
		>
			<input
				type="text"
				id="floating-message-input"
				style="--ml:1.2rem; --bgc:transparent; --oe:none; --w:100%; --fx:1 1 0%; --size:0.8rem"
				placeholder={$i18n.t('Ask a question')}
				bind:value={floatingInputValue}
				on:keydown={(e) => {
					if (e.key === 'Enter') {
						askHandler();
					}
				}}
			/>

			<div style="--ml:0.2rem; --mr:0.5rem">
				<button
					style="--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --p:0.4rem; --m:0.125rem; --as:center"
	class="{floatingInputValue !== ''
						? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
						: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'}"
					on:click={() => {
						askHandler();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						style="--w:1rem; --h:1rem"
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
