<script>
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { user } from '$lib/stores';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ManageOllama from './Manage/ManageOllama.svelte';
	import { getOllamaConfig } from '$lib/apis/ollama';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ManageMultipleOllama from './Manage/ManageMultipleOllama.svelte';

	export let show = false;

	let selected = null;
	let ollamaConfig = null;

	onMount(async () => {
		if ($user?.role === 'admin') {
			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})()
			]);

			if (ollamaConfig) {
				selected = 'ollama';
				return;
			}

			selected = '';
		}
	});
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100, #ececec); --px:1.25rem; --pt:1rem">
			<div style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{$i18n.t('Manage Models')}
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:0.75rem; --pb:1rem; --g-md:1rem; --dark-c:var(--color-gray-200, #e3e3e3)">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				{#if selected === ''}
					<div style="--py:1.25rem; --c:var(--color-gray-400, #b4b4b4); --size:0.75rem">
						<div>
							{$i18n.t('No inference engine with management support found')}
						</div>
					</div>
				{:else if selected !== null}
					<div style="--d:flex; --w:100%; --fd:column">
						<div
							style="--d:flex; --g:0.25rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.875rem; --weight:500; --radius:9999px; --bgc:transparent; --dark-c:var(--color-gray-200, #e3e3e3)"
	class="scrollbar-none"
						>
							<button
								style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selected === 'ollama'
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selected = 'ollama';
								}}>{$i18n.t('Ollama')}</button
							>

							<!-- <button
								style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{selected === 'llamacpp'
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selected = 'llamacpp';
								}}>{$i18n.t('Llama.cpp')}</button
							> -->
						</div>

						<div style="--px:0.375rem; --py:0.25rem">
							{#if selected === 'ollama'}
								<ManageMultipleOllama {ollamaConfig} />
							{/if}
						</div>
					</div>
				{:else}
					<div style="--py:1.25rem">
						<Spinner />
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
